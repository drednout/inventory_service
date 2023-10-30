import logging

from aiohttp import web
import asyncpg


async def get_inventory(request):
    data = await request.json()

    # Validate and retrieve player_id from the request
    player_id = data.get('player_id')

    # Connect to the PostgreSQL database
    async with request.app.db_pool.acquire() as conn:
        # Perform a database query to get the player's inventory
        inventory = await conn.fetch("SELECT * FROM player_inventory WHERE player_id = $1", player_id)

        # Format the inventory data as needed
        inventory_data = [
            {'id': row[0], 'inventory_type': row[2], 'item_code': row[3], 'amount': row[4]}
            for row in inventory
        ]

    # Return the inventory data as JSON response
    return web.json_response({
        'status': 'OK',
        'data': {'player_id': player_id, 'inventory': inventory_data}
    })


async def grant_item(request):
    try:
        # Parse the JSON request body
        data = await request.json()

        # Validate and retrieve player_id, item_code, and amount from the request
        player_id = data.get('player_id')
        item_code = data.get('item_code')
        amount = data.get('amount')
        ext_trx_id = data.get('ext_trx_id')
        inventory_type = data.get('inventory_type', 'consumable')
        if player_id is None or item_code is None or amount is None:
            return web.json_response({
                'status': 'error',
                'error_code': '400',
                'error_message': 'Missing player_id, item_code or amount',
                'context': {}
            }, status=400)

        is_duplicate = False

        # Connect to the PostgreSQL database
        async with request.app.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    await conn.fetchrow("""
                        INSERT INTO player_inventory_trx (player_id, ext_trx_id)
                        VALUES ($1, $2)
                    """, player_id, ext_trx_id)
                except asyncpg.exceptions.IntegrityConstraintViolationError:
                    is_duplicate = True

                if not is_duplicate:
                    # Perform an upsert operation to grant items to the player's inventory
                    res = await conn.fetchrow("""
                        INSERT INTO player_inventory (player_id, inventory_type, item_code, amount)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (player_id, item_code)
                        DO UPDATE SET amount = player_inventory.amount + $4
                        RETURNING *, (xmax = 0) AS inserted;
                    """, player_id, inventory_type, item_code, amount)
                    if res['inserted']:
                        logging.info('A new inventory created for player_id: %s, item_code: %s, inventory_type: %s, '
                                     'ext_trx_id: %s', player_id, item_code, inventory_type, ext_trx_id)
                    else:
                        logging.info('An existing inventory updated for player_id: %s, item_code: %s, '
                                     'inventory_type: %s, ext_trx_id: %s', player_id, item_code,
                                     inventory_type, ext_trx_id)

                    sql = """
                        INSERT INTO log_player_event 
                            (player_id, event_type, event_value_int, meta_data, ext_trx_id)
                        VALUES ($1, $2, $3, $4, $5)
                    """
                    await conn.execute(sql, player_id, 'inventory_granted', amount,
                                       {'inventory_type': inventory_type, 'item_code': item_code}, ext_trx_id)
                else:
                    logging.info('Duplicate request detected when trying to add_item player_id: %s, item_code: %s, '
                                 'inventory_type: %s, ext_trx_id: %s', player_id, item_code,
                                 inventory_type, ext_trx_id)

        # Return a success response
        return web.json_response({
            'status': 'OK',
            'data': {}
        })

    except Exception as e:
        return web.json_response({
            'status': 'error',
            'error_code': '500',
            'error_message': str(e),
            'context': {}
        }, status=500)

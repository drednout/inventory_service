import argparse
import asyncio
import pathlib

import aiopg
from aiohttp_swagger3 import SwaggerFile, SwaggerUiSettings, ReDocUiSettings
from aiohttp import web
import yaml




async def get_inventory(request):
    try:
        # Parse the JSON request body
        data = await request.json()

        # Validate and retrieve player_id from the request
        player_id = data.get('player_id')
        if player_id is None:
            return web.json_response({
                'status': 'error',
                'error_code': '400',
                'error_message': 'Missing player_id',
                'context': {}
            }, status=400)

        # Connect to the PostgreSQL database
        async with request.app.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Perform a database query to get the player's inventory
                await cur.execute("SELECT * FROM player_inventory WHERE player_id = %s", (player_id,))
                inventory = await cur.fetchall()

                # Format the inventory data as needed
                inventory_data = [{'id': row[0], 'inventory_type': row[2], 'item_code': row[3], 'amount': row[4]} for row in inventory]

        # Return the inventory data as JSON response
        return web.json_response({
            'status': 'OK',
            'data': {'player_id': player_id, 'inventory': inventory_data}
        })

    except Exception as e:
        return web.json_response({
            'status': 'error',
            'error_code': '500',
            'error_message': str(e),
            'context': {}
        }, status=500)

async def grant_item(request):
    try:
        # Parse the JSON request body
        data = await request.json()

        # Validate and retrieve player_id, item_code, and amount from the request
        player_id = data.get('player_id')
        item_code = data.get('item_code')
        amount = data.get('amount')
        if player_id is None or item_code is None or amount is None:
            return web.json_response({
                'status': 'error',
                'error_code': '400',
                'error_message': 'Missing player_id, item_code, or amount',
                'context': {}
            }, status=400)

        # Connect to the PostgreSQL database
        async with request.app.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Perform an upsert operation to grant items to the player's inventory
                await cur.execute("""
                    INSERT INTO player_inventory (player_id, inventory_type, item_code, amount)
                    VALUES (%s, 'consumable', %s, %s)
                    ON CONFLICT (player_id, item_code)
                    DO UPDATE SET amount = player_inventory.amount + %s;
                """, (player_id, item_code, amount, amount))

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



def load_config(config_path):
    try:
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
            return config
    except FileNotFoundError:
        raise Exception(f"Config file '{config_path}' not found.")
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")


def get_database_settings(config):
    database_settings = config.get('database', {})
    return database_settings


async def main():
    parser = argparse.ArgumentParser(description='Inventory Service')
    parser.add_argument(
        '--config', '-c', 
        default='inventory.yaml', 
        help='Path to the YAML config file (default: inventory.yaml)'
    )
    args = parser.parse_args()

    config = load_config(args.config)
    db_settings = get_database_settings(config)

    pool = await aiopg.create_pool(**db_settings)

    app = web.Application()
    app.db_pool = pool
    app.config = config
    swagger = SwaggerFile(
        app,
        redoc_ui_settings=ReDocUiSettings(path='/docs'),
        swagger_ui_settings=SwaggerUiSettings(path='/swagger'),
        spec_file=str(pathlib.Path(__file__).parent / 'openapi_spec.yaml'),
    )
    swagger.add_routes([
         web.post('/v1/inventory/get', get_inventory),
         web.post('/v1/inventory/grant', grant_item),
    ])

    # Add other routes for the remaining API endpoints
    return app

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(main())
    web.run_app(app, loop=loop)


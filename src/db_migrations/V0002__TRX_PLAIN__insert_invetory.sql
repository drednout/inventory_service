CREATE OR REPLACE FUNCTION insert_inventory(
    _player_id bigint,
    _ext_trx_id varchar(40),
    _inventory_type inventory_type,
    _item_code varchar(20),
    _amount bigint
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO player_inventory_trx (player_id, ext_trx_id) VALUES (_player_id, _ext_trx_id);
    INSERT INTO player_inventory (player_id, inventory_type, item_code, amount)
        VALUES (_player_id, _inventory_type, _item_code, _amount)
        ON CONFLICT (player_id, item_code)
        DO UPDATE SET amount = player_inventory.amount + _amount;
    INSERT INTO log_player_event 
        (player_id, event_type, event_value_int, meta_data, ext_trx_id)
    VALUES (_player_id, 'inventory_granted', _amount, 
            ('{"inventory_type": "' || _inventory_type || '" , "item_code": "' || _item_code  || '"}')::JSON, _ext_trx_id);
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql
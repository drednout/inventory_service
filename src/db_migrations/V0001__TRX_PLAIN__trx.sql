CREATE TABLE player_inventory_trx (
    id bigserial NOT NULL,
    player_id bigint NOT NULL,
    ext_trx_id varchar(40) NOT NULL,
    created timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    updated timestamp without time zone DEFAULT timezone('UTC'::text, now()),
    CONSTRAINT pk_player_inventory_trx_id PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uniq_idx_player_inventory_trx_player_id_idempotency_key ON
    player_inventory_trx (player_id, ext_trx_id);

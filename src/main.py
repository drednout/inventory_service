import argparse
import asyncio
import pathlib
import logging
import json

import asyncpg
from aiohttp_swagger3 import SwaggerFile, SwaggerUiSettings, ReDocUiSettings
from aiohttp import web
import yaml

from monitoring import metrics_view, monitoring_middleware
from error import error_middleware
from view import get_inventory, grant_item, grant_item_stored_trx


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


async def init_dbconn_callback(conn):
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )


async def main():
    parser = argparse.ArgumentParser(description='Inventory Service')
    parser.add_argument(
        '--config', '-c', 
        default='inventory.yaml', 
        help='Path to the YAML config file (default: inventory.yaml)'
    )
    parser.add_argument(
        '--log-level', '-l',
        choices=('info', 'debug', 'warning', 'error', 'critical'),
        default='info',
        help='Specify log level, info by default'
    )
    parser.add_argument(
        '--disable-request-validation',
        default=False,
        action='store_true',
        help='Disable request validation using openapi schema(for perf testing).'
    )
    args = parser.parse_args()

    config = load_config(args.config)
    db_settings = get_database_settings(config)

    log_format = '%(asctime)s; %(levelname)s; %(message)s'
    logging.basicConfig(level=args.log_level.upper(), format=log_format)

    pool = await asyncpg.create_pool(**db_settings, init=init_dbconn_callback)
    middlewares = [
        monitoring_middleware,
        error_middleware,
    ]

    app = web.Application(middlewares=middlewares)
    app.db_pool = pool
    app.config = config
    need_request_validation = True
    if args.disable_request_validation:
        need_request_validation = False

    swagger = SwaggerFile(
        app,
        redoc_ui_settings=ReDocUiSettings(path='/docs'),
        swagger_ui_settings=SwaggerUiSettings(path='/swagger'),
        spec_file=str(pathlib.Path(__file__).parent / 'openapi_spec.yaml'),
        validate=need_request_validation
    )
    swagger.add_routes([
         web.get('/metrics', metrics_view),
         web.post('/v1/inventory/get', get_inventory),
         web.post('/v1/inventory/grant', grant_item),
        web.post('/internal/inventory/grant_stored_trx', grant_item_stored_trx),
    ])

    # Add other routes for the remaining API endpoints
    return app

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(main())
    web.run_app(app, loop=loop)


import argparse
import logging
import asyncio
import datetime
import calendar

import yaml
import asyncpg

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


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


def get_part_dates(target_date):
    start_datetime = datetime.datetime(year=target_date.year, month=target_date.month,
                                       day=1, hour=0, minute=0, second=0)
    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    end_datetime = datetime.datetime(year=target_date.year, month=target_date.month, day=last_day,
                                     hour=23, minute=59, second=59)

    return start_datetime, end_datetime


async def ensure_partitions_created(conn, target_date):
    trx = conn.transaction()
    try:
        await trx.start()
        await conn.execute("""
            INSERT INTO log_player_event (player_id, event_type, event_value_int, event_time)
            VALUES ($1, $2, $3, $4)
        """, -1, 'inventory_granted', 0, target_date)
        await trx.rollback()
    except asyncpg.exceptions.PostgresError:
        await trx.rollback()
        start_datetime, end_datetime = get_part_dates(target_date)
        year, month = start_datetime.year, start_datetime.month
        table = f'log_player_event_{year}{month}'
        create_table_sql = f"""
            CREATE TABLE {table} PARTITION OF log_player_event
            FOR VALUES FROM ('{start_datetime.strftime(DATETIME_FORMAT)}') TO
            ('{end_datetime.strftime(DATETIME_FORMAT)}');
        """
        await conn.execute(create_table_sql)
        logging.info(f'Created partition {table} for events in range [{start_datetime}..{end_datetime}]')


async def main():
    parser = argparse.ArgumentParser(description='DB partition management tool')
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
        '--target-date', '-t',
        help='Specify target date for creating partitions'
    )
    args = parser.parse_args()

    target_date = datetime.datetime.utcnow()
    if args.target_date:
        target_date = datetime.datetime.strptime(args.target_date, DATETIME_FORMAT)

    config = load_config(args.config)
    db_settings = get_database_settings(config)

    log_format = '%(asctime)s; %(levelname)s; %(message)s'
    logging.basicConfig(level=args.log_level.upper(), format=log_format)

    conn = await asyncpg.connect(database=db_settings['database'], user=db_settings['user'],
                                 password=db_settings['password'], host=db_settings['host'],
                                 port=db_settings['port'])
    try:
        await ensure_partitions_created(conn, target_date)
    finally:
        await conn.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

import argparse
import duckdb
import os
from kalshi_bot.util.logger import get_logger
from datetime import date

from pathlib import Path

import json


logger = get_logger('run_signals')

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR.parent / "sql"

def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

ROOT_PATH = "~/signals_db/"
def main():
    parser = argparse.ArgumentParser(description="Example script using argparse")

    parser.add_argument(
        "--config_path",          # argument name
        type=str,          # type of the argument
    )

    args = parser.parse_args()
    json_data = load_json(args.config_path)
    json_data['signal_query'] = os.path.join(SQL_DIR, json_data['signal_query'])

    params = json_data['params']
    signal_query = json_data['signal_query']

    run_date = date.today().isoformat()
    pq_file = f"{run_date}.parquet"
    logger.info(f"Running signals for: {run_date} ")
    # TODO: FIx path
    params['parquet_path'] = f"{params['parquet_path']}/*/{pq_file}"
    params = list(params.values())
    signal_db = json_data['signal_db']

    logger.info(f'Running signal: {signal_query} with params: {params}')
    run_signal(signal_query=signal_query, params=params, signal_db_file=signal_db)


def run_signal(signal_query, params, signal_db_file) -> None:

    db_path = Path(signal_db_file).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    sql_path = Path(signal_query).expanduser()


    # Create the table first
    sql_path_create = f"{str(sql_path).split('.')[0]}_create.sql"
    sql_path_create = Path(sql_path_create)
    logger.info(f"Creating table: {sql_path_create}")
    sql_path_create = sql_path_create.read_text()
    conn.execute(sql_path_create)

    sql = sql_path.read_text()
    logger.info("executing query")
    conn.execute(sql, params)
    logger.info('Succesfull execution!')


if __name__ == '__main__':
    main()
import argparse
import duckdb
import os
from kalshi_bot.util.logger import get_logger
from datetime import date


import json


logger = get_logger('run_signals')


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
    params = json_data['params']
    signal_query = json_data['signal_query']

    run_date = date.today().isoformat()
    pq_file = f"{run_date}.parquet"
    logger.info(f"Running signals for: {run_date} ")
    
    params['parquet_path'] = os.path.join(params['parquet_path'],'/*/', pq_file)
    logger.info(f"Running signal on matching pq files: {params['parquet_path']}")

    signal_db = json_data['signal_db']

    logger.info(f'Running signal: {signal_query} with params: {params}')
    run_signal(signal_query=signal_query, params=params, signal_db_file=signal_db)


def run_signal(signal_query, params, signal_db_file) -> None:
    conn = duckdb.connect(signal_db_file)
    conn.execute(signal_query, params)
    logger.info('Succesfull execution!')


if __name__ == '__main__':
    main()
from pathlib import Path

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = BASE_DIR / "sandbox.duckdb"


TABLE_FILES = {
    "crm_users_raw": DATA_DIR / "crm_users_raw.csv",
    "orders_hub": DATA_DIR / "orders_hub.csv",
    "geo_dictionary": DATA_DIR / "geo_dictionary.csv",
}


def initialize_database() -> None:
    for table_name, file_path in TABLE_FILES.items():
        if not file_path.exists():
            raise FileNotFoundError(
                f"Не найден файл для таблицы {table_name}: {file_path}"
            )

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        for table_name, file_path in TABLE_FILES.items():
            connection.execute(
                f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM read_csv_auto(
                    ?,
                    header = true,
                    sample_size = -1
                )
                """,
                [str(file_path)],
            )


def execute_query(sql: str) -> pd.DataFrame:
    with duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    ) as connection:
        return connection.execute(sql).df()


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )
import json
from typing import Any

from database import get_connection

def clean_unicode(value):
    if isinstance(value, str):
        return value.encode(
            "utf-8",
            errors="replace",
        ).decode("utf-8")

    if isinstance(value, list):
        return [clean_unicode(item) for item in value]

    if isinstance(value, dict):
        return {
            clean_unicode(key): clean_unicode(item)
            for key, item in value.items()
        }

    return value

def get_schema_metadata():
    connection = get_connection()

    try:
        table_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()

        result: list[dict[str, Any]] = []

        for (table_name,) in table_rows:
            column_rows = connection.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'main'
                  AND table_name = ?
                ORDER BY ordinal_position
                """,
                [table_name],
            ).fetchall()

            row_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            result.append(
                {
                    "table": table_name,
                    "row_count": row_count,
                    "columns": [
                        {
                            "name": column_name,
                            "type": data_type,
                            "nullable": nullable == "YES",
                        }
                        for column_name, data_type, nullable in column_rows
                    ],
                }
            )

        return result

    finally:
        connection.close()


def get_quality_report():
    connection = get_connection()

    try:
        duplicate_clients = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT client_ref_id
                FROM crm_users_raw
                WHERE client_ref_id IS NOT NULL
                GROUP BY client_ref_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        duplicate_geo_codes = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT geo_code
                FROM geo_dictionary
                WHERE geo_code IS NOT NULL
                GROUP BY geo_code
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        missing_emails = connection.execute(
            """
            SELECT COUNT(*)
            FROM crm_users_raw
            WHERE user_email IS NULL
               OR TRIM(CAST(user_email AS VARCHAR)) = ''
            """
        ).fetchone()[0]

        orders_without_customer = connection.execute(
            """
            SELECT COUNT(*)
            FROM orders_hub AS orders
            LEFT JOIN crm_users_raw AS users
                ON CAST(orders.user_link AS VARCHAR)
                 = CAST(users.client_ref_id AS VARCHAR)
            WHERE users.client_ref_id IS NULL
            """
        ).fetchone()[0]

        orders_without_geo = connection.execute(
            """
            SELECT COUNT(*)
            FROM orders_hub AS orders
            LEFT JOIN geo_dictionary AS geo
                ON CAST(orders.geo_code AS VARCHAR)
                 = CAST(geo.geo_code AS VARCHAR)
            WHERE geo.geo_code IS NULL
            """
        ).fetchone()[0]

        return {
            "duplicate_client_keys": duplicate_clients,
            "duplicate_geo_keys": duplicate_geo_codes,
            "missing_user_emails": missing_emails,
            "orders_without_customer": orders_without_customer,
            "orders_without_geo": orders_without_geo,
            "relationship_candidates": [
                {
                    "from": "orders_hub.user_link",
                    "to": "crm_users_raw.client_ref_id",
                    "warning": (
                        "client_ref_id может быть неуникальным, "
                        "поэтому JOIN способен размножить строки"
                    ),
                },
                {
                    "from": "orders_hub.geo_code",
                    "to": "geo_dictionary.geo_code",
                    "warning": (
                        "geo_code может быть неуникальным, "
                        "поэтому справочник нужно дедуплицировать"
                    ),
                },
            ],
        }

    finally:
        connection.close()


def build_metadata_context():
    payload = {
        "schema": get_schema_metadata(),
        "quality_report": get_quality_report(),
    }

    payload = clean_unicode(payload)

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    )
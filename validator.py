import re

import sqlglot
from sqlglot import expressions as exp


ALLOWED_TABLES = {
    "crm_users_raw",
    "orders_hub",
    "geo_dictionary",
}


FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "copy",
    "attach",
    "detach",
    "install",
    "load",
    "pragma",
    "call",
    "export",
    "import",
    "vacuum",
}


FORBIDDEN_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_parquet",
    "httpfs",
    "glob",
}


def validate_sql(sql: str) -> str:

    normalized = sql.strip().rstrip(";").strip()

    if not normalized:
        raise ValueError("SQL-запрос пуст")

    lowered = normalized.lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(
            rf"\b{re.escape(keyword)}\b",
            lowered,
        ):
            raise ValueError(
                f"SQL содержит запрещённое слово: {keyword}"
            )

    for function_name in FORBIDDEN_FUNCTIONS:
        if re.search(
            rf"\b{re.escape(function_name)}\s*\(",
            lowered,
        ):
            raise ValueError(
                f"Запрещённая SQL-функция: {function_name}"
            )

    statements = sqlglot.parse(
        normalized,
        read="duckdb",
    )

    statements = [
        statement
        for statement in statements
        if statement is not None
    ]

    if len(statements) != 1:
        raise ValueError(
            "Разрешён только один SQL-запрос"
        )

    statement = statements[0]

    if not isinstance(
        statement,
        (exp.Select, exp.Union, exp.Intersect, exp.Except),
    ):
        raise ValueError(
            "Разрешены только SELECT-запросы"
        )

    if statement.find(exp.Insert):
        raise ValueError("INSERT запрещён")

    if statement.find(exp.Update):
        raise ValueError("UPDATE запрещён")

    if statement.find(exp.Delete):
        raise ValueError("DELETE запрещён")

    if statement.find(exp.Create):
        raise ValueError("CREATE запрещён")

    if statement.find(exp.Drop):
        raise ValueError("DROP запрещён")

    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }

    referenced_tables = {
        table.name.lower()
        for table in statement.find_all(exp.Table)
        if table.name
    }

    physical_tables = referenced_tables - cte_names

    unknown_tables = physical_tables - ALLOWED_TABLES

    if unknown_tables:
        raise ValueError(
            "SQL использует неизвестные таблицы: "
            + ", ".join(sorted(unknown_tables))
        )

    return normalized
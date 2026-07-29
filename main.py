import json
from pathlib import Path

from database import execute_query, initialize_database
from llm import generate_analysis
from metadata import build_metadata_context
from validator import validate_sql

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "result.csv"
ANALYSIS_FILE = OUTPUT_DIR / "analysis.json"


def print_section(title: str) -> None:
    print()
    print(title)


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_section("1. Загрузка данных")

    initialize_database()

    print("CSV-файлы успешно загружены в DuckDB.")

    print_section("2. Извлечение метаданных")

    metadata_context = build_metadata_context()

    print(metadata_context)

    print_section("3. Аналитический запрос")

    question = input(
        "Напиши вопрос к данным:\n> "
    ).strip()

    question = question.encode(
        "utf-8",
        errors="replace",
    ).decode("utf-8")

    if not question:
        print("Вопрос не может быть пустым.")
        return

    print_section("4. Запрос к модели")

    analysis = generate_analysis(
        question=question,
        metadata_context=metadata_context,
    )

    print("Объяснение:")
    print(analysis["explanation"])

    print("\nИспользуемые таблицы:")
    tables=''
    warnings=''
    for table_name in analysis["tables_used"]:
        print(f"- {table_name}")
        tables+=f"- {table_name}\n"
    if analysis["warnings"]:
        print("\nПредупреждения:")
        for warning in analysis["warnings"]:
            print(f"- {warning}")


    print_section("5. Сгенерированный SQL")

    generated_sql = analysis["sql"]

    print(generated_sql)
    print_section("6. Проверка SQL")

    validated_sql = validate_sql(generated_sql)

    print("SQL прошёл проверку.")

    print_section("7. Выполнение запроса")

    dataframe = execute_query(validated_sql)

    if dataframe.empty:
        print("Запрос выполнен, но не вернул строк.")
    else:
        print(dataframe.head(20).to_string(index=False))

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    analysis["sql"] = validated_sql
    analysis["row_count"] = len(dataframe)
    analysis["result_columns"] = dataframe.columns.tolist()
    analysis["result_file"] = str(OUTPUT_FILE)

    with ANALYSIS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            analysis,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print_section("8. Результат")

    print(f"Количество строк: {len(dataframe)}")
    print(f"Таблица сохранена: {OUTPUT_FILE}")
    print(f"Описание сохранено: {ANALYSIS_FILE}")

    print_section("9. Предложенные DAX-меры")
    measure_pdf = ''
    if not analysis["dax_measures"]:
        print("Меры не предложены.")
    else:
        for measure in analysis["dax_measures"]:
            print(f"\n{measure['name']}:")
            print(measure["expression"])

    print_section("10. Предложенные визуализации")

    if not analysis["recommended_visuals"]:
        print("Визуализации не предложены.")
    else:
        for visual in analysis["recommended_visuals"]:
            print(
                json.dumps(
                    visual,
                    ensure_ascii=False,
                    indent=2,
                )
            )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем.")
    except Exception as error:
        print_section("ОШИБКА")
        print(type(error).__name__)
        print(str(error))
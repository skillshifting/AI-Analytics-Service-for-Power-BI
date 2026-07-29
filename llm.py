import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from prompts import SYSTEM_PROMPT


load_dotenv()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "В .env отсутствует OPENROUTER_API_KEY"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Модель вернула некорректный JSON.\n"
            f"Ответ модели:\n{cleaned}"
        ) from error


def generate_analysis(
    question: str,
    metadata_context: str,
) -> dict[str, Any]:
    model = os.getenv("OPENROUTER_MODEL")

    if not model:
        raise RuntimeError(
            "В .env отсутствует OPENROUTER_MODEL"
        )

    client = get_client()

    user_prompt = f"""
Вопрос пользователя:

{question}

Метаданные доступной базы:

{metadata_context}

Сгенерируй безопасный аналитический запрос.
Верни только JSON указанного формата.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0,
        max_tokens=1500,
        extra_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "Power BI AI Prototype",
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "OpenRouter вернул пустой ответ"
        )

    result = extract_json(content)

    required_fields = {
        "explanation",
        "tables_used",
        "warnings",
        "sql",
        "dax_measures",
        "recommended_visuals",
    }

    missing_fields = required_fields - result.keys()

    if missing_fields:
        raise ValueError(
            "В ответе модели отсутствуют поля: "
            + ", ".join(sorted(missing_fields))
        )

    return result
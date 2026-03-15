"""Prompt construction for the two-step LLM pipeline."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.chat.conversation import ConversationMessage
from app.db.metadata import DatasetRecord

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=8)
def _load_prompt(filename: str) -> str:
    """Load and cache a prompt template from the prompts directory."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _format_schema(schema_json: str) -> str:
    """Format schema as a readable table for the LLM."""
    columns = json.loads(schema_json)
    lines = ["| Column | Type | Sample Values |", "|--------|------|---------------|"]
    for col in columns:
        samples = ", ".join(str(s) for s in col.get("sample", [])[:3])
        lines.append(f"| {col['column']} | {col['type']} | {samples} |")
    return "\n".join(lines)


def _format_sample(sample_json: str) -> str:
    """Format sample rows as a readable table for the LLM."""
    rows = json.loads(sample_json)
    if not rows:
        return "(no sample data)"
    headers = list(rows[0].keys())
    lines = [" | ".join(headers)]
    lines.append(" | ".join("---" for _ in headers))
    for row in rows[:5]:
        lines.append(" | ".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines)


def build_sql_prompt(dataset: DatasetRecord, question: str, row_limit: int) -> tuple[str, str]:
    """Build the system + user prompts for SQL generation.

    Returns (system_prompt, user_message).
    """
    template = _load_prompt("sql_generation.md")
    system_prompt = template.format(
        file_path=dataset.file_path,
        schema=_format_schema(dataset.schema_json),
        sample=_format_sample(dataset.sample_json),
        row_limit=row_limit,
    )
    return system_prompt, question


def _format_dataset_block(dataset: DatasetRecord) -> str:
    """Format a single dataset's info for the multi-dataset prompt."""
    lines = [
        f"### Dataset: \"{dataset.name}\" (file: '{dataset.file_path}')",
        "",
        "Schema:",
        _format_schema(dataset.schema_json),
        "",
        "Sample data:",
        _format_sample(dataset.sample_json),
    ]
    return "\n".join(lines)


def build_multi_dataset_sql_prompt(
    datasets: list[DatasetRecord],
    question: str,
    row_limit: int,
) -> tuple[str, str]:
    """Build SQL prompt with ALL dataset schemas for multi-dataset queries.

    Returns (system_prompt, user_message).
    """
    template = _load_prompt("sql_generation_multi.md")
    datasets_block = "\n\n".join(_format_dataset_block(ds) for ds in datasets)
    system_prompt = template.format(
        datasets_block=datasets_block,
        row_limit=row_limit,
    )
    return system_prompt, question


def _format_history(messages: list[ConversationMessage], max_messages: int = 20) -> str:
    """Format conversation history for the interpretation prompt."""
    if not messages:
        return "(no previous conversation)"
    recent = messages[-max_messages:]
    lines = []
    for msg in recent:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def build_chat_interpretation_prompt(
    question: str,
    sql: str,
    result: list[dict[str, Any]],
    locale: str,
    history: list[ConversationMessage],
) -> tuple[str, str]:
    """Build interpretation prompt with conversation history.

    Returns (system_prompt, user_message).
    """
    template = _load_prompt("interpretation_chat.md")
    system_prompt = template.format(
        locale=locale,
        question=question,
        sql=sql,
        result=_format_result(result),
        history=_format_history(history),
    )
    return system_prompt, question


def _format_result(result: list[dict[str, Any]]) -> str:
    """Format query result rows as a readable table for the LLM."""
    if not result:
        return "(empty result set)"
    headers = list(result[0].keys())
    lines = [" | ".join(headers)]
    lines.append(" | ".join("---" for _ in headers))
    for row in result[:50]:  # cap to avoid huge prompts
        lines.append(" | ".join(str(row.get(h, "")) for h in headers))
    if len(result) > 50:
        lines.append(f"... ({len(result)} rows total)")
    return "\n".join(lines)


def build_interpretation_prompt(
    question: str,
    sql: str,
    result: list[dict[str, Any]],
    locale: str,
) -> tuple[str, str]:
    """Build the system + user prompts for result interpretation.

    Returns (system_prompt, user_message).
    """
    template = _load_prompt("interpretation.md")
    system_prompt = template.format(
        locale=locale,
        question=question,
        sql=sql,
        result=_format_result(result),
    )
    return system_prompt, question


def build_chart_prompt(
    question: str,
    sql: str,
    result: list[dict[str, Any]],
) -> tuple[str, str]:
    """Build prompt for chart generation.

    Returns (system_prompt, user_message).
    """
    template = _load_prompt("chart_generation.md")
    system_prompt = template.format(
        question=question,
        sql=sql,
        result=_format_result(result),
    )
    return system_prompt, question

"""Prompt construction for the two-step LLM pipeline."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

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

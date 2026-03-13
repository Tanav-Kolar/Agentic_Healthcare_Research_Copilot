"""Utility / helper functions for agent output parsing.

All parse_* functions extract structured JSON from raw LLM output,
handling markdown code fences and providing graceful fallbacks.
"""

from __future__ import annotations

import json
import logging

from rag.models import PICOQuery

logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return text


def parse_pico_output(raw_output: str) -> PICOQuery:
    """Parse Query Understanding agent output into a PICOQuery model."""
    text = _strip_markdown(raw_output)

    try:
        data = json.loads(text)
        return PICOQuery(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to parse PICO output: %s", e)
        return PICOQuery(
            original_question=raw_output,
            search_strings=[raw_output],
        )


def apply_grades(articles_json: str, grades_json: str) -> str:
    """Apply Evidence Grader results back to the articles list.

    Merges grade classifications (study_type, confidence, reasoning)
    into the original articles JSON by PMID lookup.
    """
    try:
        articles = json.loads(articles_json)
        grades = json.loads(grades_json)
    except json.JSONDecodeError:
        logger.warning("Failed to parse grading data, returning original articles")
        return articles_json

    grade_map = {g.get("pmid"): g for g in grades if g.get("pmid")}

    for article in articles:
        pmid = article.get("pmid")
        if pmid and pmid in grade_map:
            grade = grade_map[pmid]
            article["study_type"] = grade.get("study_type", article.get("study_type"))
            article["grade_confidence"] = grade.get("confidence", "low")
            article["grade_reasoning"] = grade.get("reasoning", "")

    return json.dumps(articles, indent=2)


def parse_synthesis(raw_output: str) -> dict:
    """Parse Synthesizer agent output into structured data."""
    text = _strip_markdown(raw_output)

    try:
        data = json.loads(text)
        # Normalize quotes: local LLMs often output 'article' instead of 'id'
        if "quotes" in data and isinstance(data["quotes"], list):
            for q in data["quotes"]:
                if isinstance(q, dict) and "article" in q and "id" not in q:
                    q["id"] = q["article"]
        return data
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse synthesis output as JSON: %s", e)
        return {
            "summary": raw_output,
            "key_evidence": [],
            "limitations": "Unable to parse structured output.",
            "conflicting_evidence": "",
            "references": [],
            "quotes": [],
        }


def parse_contradictions(raw_output: str) -> dict:
    """Parse Contradiction Detective output into structured data."""
    text = _strip_markdown(raw_output)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse contradiction output")
        return {
            "has_conflicts": False,
            "conflicts": [],
            "overall_assessment": "Unable to parse contradiction analysis.",
        }


def parse_verification(raw_output: str) -> dict:
    """Parse Citation Verifier output into structured data."""
    text = _strip_markdown(raw_output)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse verification output")
        return {
            "verification_status": "unknown",
            "total_citations": 0,
            "verified_citations": 0,
            "unverified_citations": 0,
            "issues": [],
            "recommendations": "Unable to parse verification results.",
        }

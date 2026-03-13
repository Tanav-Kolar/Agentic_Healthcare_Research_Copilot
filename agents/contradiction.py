"""Contradiction Detective Agent — identifies conflicting findings in retrieved evidence."""

from __future__ import annotations

import logging
from pathlib import Path

from crewai import Agent, Task, LLM

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "contradiction.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

# LLM instantiation.
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.1,
    timeout=settings.ollama_timeout,
)

# Agent
contradiction_agent = Agent(
    role="Contradiction Detective",
    goal=(
        "Identify conflicting findings, opposing outcomes, and contradictory "
        "recommendations within the retrieved evidence set."
    ),
    backstory=(
        "You are a critical appraisal expert who specialises in identifying "
        "inconsistencies and contradictions in medical literature. You help "
        "clinicians understand where the evidence disagrees."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Task
contradiction_task = Task(
    description=f"""
        {SYSTEM_PROMPT}

        ## Articles to Analyse
        {{articles_json}}

        Scan these articles for conflicting or opposing findings.
    """,
    expected_output="""
        A JSON object with: has_conflicts (bool), conflicts (array),
        and overall_assessment (string).
    """,
    agent=contradiction_agent,
)

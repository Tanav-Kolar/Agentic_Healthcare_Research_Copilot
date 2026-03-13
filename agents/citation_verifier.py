"""Citation Verifier Agent — validates that every claim has a verifiable source quote."""

from __future__ import annotations

import logging
from pathlib import Path

from crewai import Agent, Task, LLM

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "citation_verifier.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

# LLM instantiation.
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.0,
    timeout=settings.ollama_timeout,
)

# Agent
citation_verifier_agent = Agent(
    role="Citation Verifier",
    goal=(
        "Verify that every factual claim in the synthesized answer is "
        "supported by an exact verbatim quote from a retrieved source. "
        "Flag any unsupported claims."
    ),
    backstory=(
        "You are a meticulous fact-checker and journal editor. "
        "You ensure every statement in a medical review is traceable "
        "to its original source with exact quotes."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Task
citation_verifier_task = Task(
    description=f"""
        {SYSTEM_PROMPT}

        ## Synthesized Answer
        {{synthesis_json}}

        ## Source Articles
        {{articles_json}}

        Verify all citations and quotes.
    """,
    expected_output="""
        A JSON object with: verification_status, total_citations,
        verified_citations, unverified_citations, issues, recommendations.
    """,
    agent=citation_verifier_agent,
)

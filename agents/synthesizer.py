"""Synthesizer Agent — produces structured evidence summaries with citations.

Uses Gemma to compose balanced answers with inline [#] citations,
a quotes panel, limitations, and conflict sections.
"""

from __future__ import annotations

import logging
from pathlib import Path

from crewai import Agent, Task, LLM

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "synthesizer.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

# LLM instantiation.
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.2,
    timeout=settings.ollama_timeout,
)

# Agent
synthesizer_agent = Agent(
    role="Medical Evidence Synthesizer",
    goal=(
        "Produce comprehensive, balanced evidence summaries with inline "
        "citations. Every sentence must be grounded in the retrieved evidence. "
        "Structure output as: Summary, Key Evidence, Limitations, Conflicts, References."
    ),
    backstory=(
        "You are a senior clinical researcher and systematic review author. "
        "You synthesise complex medical evidence into clear, actionable summaries "
        "for busy clinicians. You never make claims without evidence."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Task
synthesizer_task = Task(
    description=f"""
        {SYSTEM_PROMPT}

        ## Clinical Question
        {{question}}

        ## Retrieved Evidence
        {{articles_json}}

        ## Contradiction Analysis
        {{contradictions_json}}

        Synthesise a comprehensive answer with inline [#] citations.
    """,
    expected_output="""
        A JSON object with: summary, key_evidence, limitations,
        conflicting_evidence, references, and quotes.
    """,
    agent=synthesizer_agent,
)

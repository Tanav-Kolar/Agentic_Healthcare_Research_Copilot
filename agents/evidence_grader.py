"""Evidence Grader Agent — classifies study designs and assigns quality labels.

Uses the evidence hierarchy:
Guideline > Meta-analysis > Systematic Review > RCT > Cohort > Case-Control > Case Report > Preprint
"""

from __future__ import annotations

import logging
from pathlib import Path

from crewai import Agent, Task, LLM

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "evidence_grader.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

# LLM instantiation.
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.1,
    timeout=settings.ollama_timeout,
)

# Agent
evidence_grader_agent = Agent(
    role="Evidence Quality Grader",
    goal=(
        "Classify each retrieved article by study design and assign "
        "evidence quality labels based on the standard evidence hierarchy: "
        "Guideline > Meta-analysis > Systematic Review > RCT > Cohort > "
        "Case-Control > Case Report > Preprint."
    ),
    backstory=(
        "You are an evidence-based medicine expert trained in critical "
        "appraisal and systematic review methodology. You can reliably "
        "identify study designs from titles, abstracts, and metadata."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Task
evidence_grader_task = Task(
    description=f"""
        {SYSTEM_PROMPT}

        ## Articles to Grade
        {{articles_json}}

        Classify each article's study design and assign quality labels.
    """,
    expected_output="""
        A JSON array with each item having: pmid, study_type, confidence, reasoning.
    """,
    agent=evidence_grader_agent,
)

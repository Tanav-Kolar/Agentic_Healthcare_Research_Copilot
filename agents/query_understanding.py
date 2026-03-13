"""Query Understanding Agent — decomposes clinical questions into PICO format.

Uses Gemma (via Ollama) to rewrite the user's question into structured
PICO fields and generate optimised PubMed search strings.
"""

from __future__ import annotations

import logging
from pathlib import Path

from crewai import Agent, Task, LLM

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "query_understanding.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

# LLM instantiation.
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.1,
    timeout=settings.ollama_timeout,
)

# Agent
query_understanding_agent = Agent(
    role="Query Understanding Specialist",
    goal=(
        "Decompose clinical research questions into structured PICO format "
        "and generate optimised PubMed search strings with synonyms and MeSH terms. "
        "P (Patient/Problem): Identify the specific group, disease, or health issue. "
        "I (Intervention): The treatment, diagnostic test, or exposure being considered. "
        "C (Comparison): The alternative treatment or control group (e.g., placebo, standard care). "
        "O (Outcome): The desired, measurable result (e.g., reduced symptoms, mortality rate)."
    ),
    backstory=(
        "You are an expert medical librarian with deep knowledge of PubMed search "
        "strategies, MeSH terminology, and the PICO framework. "
        "You help clinicians formulate precise literature searches."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

# Task definition.
query_understanding_task = Task(
    description=f"""
        {SYSTEM_PROMPT}

        ## Clinical Question
        {{question}}

        Decompose this question into PICO format and generate search strings.
    """,
    expected_output="""
        A JSON object with population, intervention, comparison, outcome,
        search_strings, mesh_terms, and original_question fields.
    """,
    agent=query_understanding_agent,
)

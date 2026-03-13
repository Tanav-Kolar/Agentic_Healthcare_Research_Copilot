"""Search / Retrieval Agent — fetches evidence from PubMed + Qdrant.

Calls PubMed E-utilities with the search strings from the Query Understanding
agent, and also performs hybrid search in the Qdrant vector store.
De-duplicates and ranks results by recency and study type.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from crewai import Agent, Task, LLM
from crewai.tools import BaseTool

from config import settings
from rag.retriever import Retriever

logger = logging.getLogger(__name__)


class PubMedSearchTool(BaseTool):
    """CrewAI tool that wraps the hybrid retriever."""

    name: str = "pubmed_search"
    description: str = (
        "Search PubMed and the local evidence store for research articles. "
        "Input should be a JSON string with: query (str), search_strings (list[str], optional), "
        "year_from (int, optional), year_to (int, optional), "
        "study_types (list[str], optional), limit (int, optional, default 30)."
    )

    _retriever: Optional[Retriever] = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever()
        return self._retriever

    def _run(self, input_str: str) -> str:
        """Execute the search."""
        try:
            params = json.loads(input_str) if isinstance(input_str, str) else input_str
        except json.JSONDecodeError:
            params = {"query": input_str}

        query = params.get("query", input_str)
        search_strings = params.get("search_strings", [])
        year_from = params.get("year_from")
        year_to = params.get("year_to")
        study_types = params.get("study_types")
        limit = params.get("limit", 30)

        articles = self.retriever.retrieve(
            query=query,
            search_strings=search_strings,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
            study_types=study_types,
        )

        result = [
            {
                "pmid": a.pmid,
                "title": a.title,
                "abstract": (a.abstract[:200] + "...") if len(a.abstract) > 200 else a.abstract,
                "year": a.year,
                "study_type": a.study_type.label,
            }
            for a in articles
        ]
        logger.info("Tool returning %d articles to agent", len(result))
        return json.dumps(result, indent=2)


# ── LLM instance ────────────────────────────────
llm = LLM(
    model=f"ollama/{settings.ollama_model}",
    base_url=settings.ollama_host,
    temperature=0.1,
    timeout=settings.ollama_timeout,
)

# Agent
search_retrieval_agent = Agent(
    role="Medical Literature Search Specialist",
    goal=(
        "Retrieve the most relevant and recent research articles from PubMed "
        "and the local evidence store. Your FINAL ANSWER must be the raw JSON "
        "array of articles returned by the tool, without any conversational filler."
    ),
    backstory=(
        "You are a clinical librarian trained in providing raw evidence sets "
        "to medical researchers. You strictly follow data formatting requirements."
    ),
    llm=llm,
    tools=[PubMedSearchTool()],
    verbose=True,
    allow_delegation=False,
)

# Task
search_retrieval_task = Task(
    description="""
        Using the following PICO decomposition, search for relevant evidence:

        {pico_json}

        {filter_text}

        Use the pubmed_search tool to retrieve articles.
        Prefer evidence from the last 24 months.
        Retrieve at least 15-30 articles for a comprehensive review.
    """,
    expected_output="""
        A JSON array of retrieved research articles with pmid, doi, title,
        abstract, authors, journal, year, study_type, and source_url.
    """,
    agent=search_retrieval_agent,
)

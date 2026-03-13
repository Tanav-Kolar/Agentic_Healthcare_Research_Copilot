"""CrewAI Orchestrator — wires all 6 agents into a sequential pipeline.

Flow: Query Understanding → Search/Retrieval → Evidence Grader
      → Contradiction Detective → Synthesizer → Citation Verifier

Produces structured output matching the /ask API contract and logs
agent message traces to JSONL.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from crewai import Crew, Process

from agents.query_understanding import query_understanding_agent, query_understanding_task
from agents.search_retrieval import search_retrieval_agent, search_retrieval_task
from agents.evidence_grader import evidence_grader_agent, evidence_grader_task
from agents.contradiction import contradiction_agent, contradiction_task
from agents.synthesizer import synthesizer_agent, synthesizer_task
from agents.citation_verifier import citation_verifier_agent, citation_verifier_task
from rag.retriever import Retriever
from agents.utils import (
    parse_pico_output,
    apply_grades,
    parse_synthesis,
    parse_contradictions,
    parse_verification,
)

logger = logging.getLogger(__name__)

# Directory for agent trace logs
TRACES_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)


class ResearchPipeline:
    """Orchestrates the full 6-agent research pipeline."""

    def __init__(self) -> None:
        self._traces: list[dict] = []
        self.retriever = Retriever()

    def run(
        self,
        question: str,
        thread_id: str = "",
        filters: Optional[dict] = None,
    ) -> dict:
        """Execute the full pipeline and return the /ask response."""
        start = time.time()
        self._traces = []

        # ── Step 1: Query Understanding ──────────
        self._log_trace("query_understanding", "start", {"question": question})

        pico_crew = Crew(
            agents=[query_understanding_agent],
            tasks=[query_understanding_task],
            process=Process.sequential,
            verbose=True,
        )
        pico_result = pico_crew.kickoff(inputs={"question": question})
        pico_raw = str(pico_result)
        pico = parse_pico_output(pico_raw)

        self._log_trace("query_understanding", "complete", {
            "pico": pico.model_dump(),
            "raw_output": pico_raw[:500],
        })

        # ── Step 2: Search / Retrieval ───────────
        # Refactored: Call Retriever directly to avoid LLM bottleneck with large JSON
        self._log_trace("search_retrieval", "start", {
            "search_strings": pico.search_strings,
            "filters": filters,
        })

        f_start = filters.get("year_from") if filters else None
        f_to = filters.get("year_to") if filters else None
        f_types = filters.get("study_types") if filters else None

        articles = self.retriever.retrieve(
            query=pico.original_question or question,
            search_strings=pico.search_strings,
            limit=10,
            year_from=f_start,
            year_to=f_to,
            study_types=f_types,
        )

        articles_json = json.dumps([
            {
                "pmid": a.pmid,
                "doi": a.doi,
                "title": a.title,
                "abstract": a.abstract,
                "authors": a.authors,
                "journal": a.journal,
                "year": a.year,
                "study_type": a.study_type.label,
                "source_url": a.source_url,
            }
            for a in articles
        ], indent=2)

        self._log_trace("search_retrieval", "direct_retrieval", {
            "count": len(articles),
            "articles_preview": articles_json[:500],
        })

        # ── Step 3: Evidence Grading ─────────────
        self._log_trace("evidence_grader", "start", {})

        grader_crew = Crew(
            agents=[evidence_grader_agent],
            tasks=[evidence_grader_task],
            process=Process.sequential,
            verbose=True,
        )
        grader_result = grader_crew.kickoff(inputs={
            "articles_json": articles_json,
        })
        grades_json = str(grader_result)
        graded_articles_json = apply_grades(articles_json, grades_json)

        self._log_trace("evidence_grader", "complete", {
            "grades_preview": grades_json[:500],
        })

        # ── Step 4: Contradiction Detection ──────
        self._log_trace("contradiction_detective", "start", {})

        contra_crew = Crew(
            agents=[contradiction_agent],
            tasks=[contradiction_task],
            process=Process.sequential,
            verbose=True,
        )
        contra_result = contra_crew.kickoff(inputs={
            "articles_json": graded_articles_json,
        })
        contra_raw = str(contra_result)
        contradictions = parse_contradictions(contra_raw)

        self._log_trace("contradiction_detective", "complete", contradictions)

        # ── Step 5: Synthesis ────────────────────
        self._log_trace("synthesizer", "start", {})

        synth_crew = Crew(
            agents=[synthesizer_agent],
            tasks=[synthesizer_task],
            process=Process.sequential,
            verbose=True,
        )
        synth_result = synth_crew.kickoff(inputs={
            "question": question,
            "articles_json": graded_articles_json,
            "contradictions_json": json.dumps(contradictions),
        })
        synth_raw = str(synth_result)
        synthesis = parse_synthesis(synth_raw)

        self._log_trace("synthesizer", "complete", {
            "summary_preview": synthesis.get("summary", "")[:300],
        })

        # ── Step 6: Citation Verification ────────
        self._log_trace("citation_verifier", "start", {})

        # Optimization: Filter articles to only those actually cited to save context tokens for local LLM
        cited_pmids = {str(q.get("pmid")) for q in synthesis.get("quotes", []) if q.get("pmid")}
        try:
            full_articles_list = json.loads(graded_articles_json)
            filtered_articles = [a for a in full_articles_list if str(a.get("pmid")) in cited_pmids]
            # If no PMIDs found, fall back to all (safer)
            if not filtered_articles and full_articles_list:
                filtered_articles = full_articles_list[:5] # Limit to top 5 if citations untraceable
            
            verify_articles_json = json.dumps(filtered_articles)
        except Exception:
            verify_articles_json = graded_articles_json

        verify_crew = Crew(
            agents=[citation_verifier_agent],
            tasks=[citation_verifier_task],
            process=Process.sequential,
            verbose=True,
        )
        verify_result = verify_crew.kickoff(inputs={
            "synthesis_json": json.dumps(synthesis),
            "articles_json": verify_articles_json,
        })
        verify_raw = str(verify_result)
        verification = parse_verification(verify_raw)

        self._log_trace("citation_verifier", "complete", verification)

        # ── Build response ───────────────────────
        elapsed = time.time() - start
        current_year = datetime.utcnow().year

        try:
            articles_list = json.loads(graded_articles_json)
        except json.JSONDecodeError:
            articles_list = []

        recent_changes = [
            {
                "id": str(idx + 1),
                "summary": a.get("title", ""),
                "year": a.get("year", 0),
                "pmid": a.get("pmid"),
                "doi": a.get("doi"),
            }
            for idx, a in enumerate(articles_list)
            if isinstance(a, dict) and a.get("year", 0) >= current_year - 2
        ][:10]

        evidence_table = [
            {
                "id": str(idx + 1),
                "title": a.get("title", ""),
                "journal": a.get("journal", ""),
                "type": a.get("study_type", "Unknown"),
                "year": a.get("year", 0),
                "population": "",
                "intervention": "",
                "outcomes": "",
                "doi": a.get("doi"),
                "pmid": a.get("pmid"),
                "source_url": a.get("source_url", ""),
            }
            for idx, a in enumerate(articles_list)
            if isinstance(a, dict)
        ]

        response = {
            "thread_id": thread_id,
            "answer": synthesis.get("summary", ""),
            "quotes": synthesis.get("quotes", []),
            "evidence_table": evidence_table,
            "changed_in_last_24_months": recent_changes,
            "pico": pico.model_dump(),
            "contradictions": contradictions,
            "verification": verification,
            "disclaimer": (
                "⚠️ This summary is for research and education purposes only. "
                "Not for clinical decision-making."
            ),
            "metadata": {
                "processing_time_seconds": round(elapsed, 2),
                "total_articles_retrieved": len(articles_list),
                "traces_file": str(self._save_traces(thread_id)),
            },
        }

        return response

    # ── trace logging ───────────────────────────

    def _log_trace(self, agent: str, event: str, data: dict) -> None:
        trace = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "event": event,
            "data": data,
        }
        self._traces.append(trace)
        logger.info("[TRACE] %s.%s", agent, event)

    def _save_traces(self, thread_id: str) -> Path:
        filename = f"trace_{thread_id or 'default'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
        filepath = TRACES_DIR / filename

        with open(filepath, "w") as f:
            for trace in self._traces:
                f.write(json.dumps(trace, default=str) + "\n")

        logger.info("Saved %d trace events to %s", len(self._traces), filepath)
        return filepath

    def get_traces(self) -> list[dict]:
        return self._traces

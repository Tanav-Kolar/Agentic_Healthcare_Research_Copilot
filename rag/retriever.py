"""Hybrid retriever — combines Qdrant search with PubMed live lookup.

Provides the main retrieval interface used by the Search/Retrieval agent.
Supports filtering by year, study type, and source, with re-ranking
by evidence hierarchy and recency.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from qdrant_client import models as qmodels

from rag.models import Article, StudyType
from rag.pubmed_client import PubMedClient
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Fetch, merge, and re-rank evidence from Qdrant + live PubMed."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        pubmed_client: Optional[PubMedClient] = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.pubmed = pubmed_client or PubMedClient()

    def retrieve(
        self,
        query: str,
        search_strings: Optional[list[str]] = None,
        limit: int = 30,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        study_types: Optional[list[str]] = None,
        sources: Optional[list[str]] = None,
    ) -> list[Article]:
        """Main retrieval entry point.

        1. Hybrid search in Qdrant (pre-ingested articles).
        2. Live PubMed search for fresh results.
        3. Merge, de-duplicate, and re-rank.
        """
        # Map study type labels to enum values for Qdrant filter
        study_type_values = None
        if study_types:
            study_type_values = self._labels_to_values(study_types)

        # ── 1. Qdrant hybrid search ──────────────
        qdrant_filter = VectorStore.build_filters(
            year_from=year_from,
            year_to=year_to,
            study_types=study_type_values,
            sources=sources,
        )
        qdrant_articles = self._search_qdrant(query, limit, qdrant_filter)
        logger.info("Qdrant returned %d articles", len(qdrant_articles))

        # ── 2. Live PubMed fetch ─────────────────
        all_queries = [query]
        if search_strings:
            all_queries.extend(search_strings)

        pubmed_articles: list[Article] = []
        for q in all_queries[:3]:  # limit to 3 queries to respect rate limits
            results = self.pubmed.search_and_fetch(
                q, max_results=limit, min_year=year_from, max_year=year_to
            )
            pubmed_articles.extend(results)

        logger.info("PubMed live returned %d articles", len(pubmed_articles))

        # ── 3. Merge + de-duplicate ──────────────
        merged = self._merge_and_dedup(qdrant_articles, pubmed_articles)

        # ── 4. Re-rank ───────────────────────────
        ranked = self._rerank(merged)

        # ── 5. Apply limit ───────────────────────
        return ranked[:limit]

    # ── private helpers ─────────────────────────

    def _search_qdrant(
        self,
        query: str,
        limit: int,
        filters: Optional[qmodels.Filter],
    ) -> list[Article]:
        """Search Qdrant and convert scored points back to Articles."""
        try:
            points = self.vector_store.hybrid_search(
                query=query, limit=limit, filters=filters
            )
        except Exception:
            logger.warning("Qdrant search failed, falling back to empty", exc_info=True)
            return []

        articles = []
        for pt in points:
            payload = pt.payload or {}
            study_type_val = payload.get("study_type", StudyType.UNKNOWN.value)
            try:
                st = StudyType(study_type_val)
            except ValueError:
                st = StudyType.UNKNOWN

            articles.append(
                Article(
                    pmid=payload.get("pmid"),
                    doi=payload.get("doi"),
                    title=payload.get("title", ""),
                    abstract=payload.get("abstract", ""),
                    authors=payload.get("authors", []),
                    journal=payload.get("journal", ""),
                    year=payload.get("year", 0),
                    month=payload.get("month", 0),
                    study_type=st,
                    source=payload.get("source", ""),
                    source_url=payload.get("source_url", ""),
                    is_preprint=payload.get("is_preprint", False),
                    mesh_terms=payload.get("mesh_terms", []),
                )
            )
        return articles

    @staticmethod
    def _merge_and_dedup(
        *article_lists: list[Article],
    ) -> list[Article]:
        """Combine multiple lists and drop duplicates by unique_id."""
        seen: set[str] = set()
        merged: list[Article] = []
        for articles in article_lists:
            for a in articles:
                uid = a.unique_id
                if uid not in seen:
                    seen.add(uid)
                    merged.append(a)
        return merged

    @staticmethod
    def _rerank(articles: list[Article]) -> list[Article]:
        """Re-rank by evidence quality (study type) and recency.

        Score = study_type_weight + recency_boost
        Lower score = higher rank.
        """
        current_year = datetime.utcnow().year

        def _score(a: Article) -> float:
            # Study type: lower enum value = stronger evidence = lower score
            type_score = a.study_type.value * 10

            # Recency: articles from the last 2 years get a boost
            year_diff = max(0, current_year - a.year) if a.year else 50
            recency_penalty = year_diff * 0.5

            return type_score + recency_penalty

        return sorted(articles, key=_score)

    @staticmethod
    def _labels_to_values(labels: list[str]) -> list[int]:
        """Convert study type labels like 'RCT', 'Guideline' to enum values."""
        mapping = {
            "guideline": StudyType.GUIDELINE.value,
            "meta-analysis": StudyType.META_ANALYSIS.value,
            "meta_analysis": StudyType.META_ANALYSIS.value,
            "systematic review": StudyType.SYSTEMATIC_REVIEW.value,
            "systematic_review": StudyType.SYSTEMATIC_REVIEW.value,
            "rct": StudyType.RCT.value,
            "randomized controlled trial": StudyType.RCT.value,
            "cohort": StudyType.COHORT.value,
            "cohort study": StudyType.COHORT.value,
            "case-control": StudyType.CASE_CONTROL.value,
            "case report": StudyType.CASE_REPORT.value,
            "preprint": StudyType.PREPRINT.value,
        }
        values = []
        for label in labels:
            val = mapping.get(label.lower().strip())
            if val is not None:
                values.append(val)
        return values

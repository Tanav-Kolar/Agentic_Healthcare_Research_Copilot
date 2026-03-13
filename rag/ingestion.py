"""Data ingestion pipeline.

Fetches articles from PubMed, embeds them with PubMedBERT,
and upserts into Qdrant. Includes a seed index creator for demo purposes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from rag.models import Article
from rag.pubmed_client import PubMedClient
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Seed topics for initial index (~200 abstracts)
# ──────────────────────────────────────────────
SEED_QUERIES = [
    "heart failure first-line therapy 2024",
    "GLP-1 receptor agonist cardiovascular outcomes",
    "SGLT2 inhibitor heart failure",
    "type 2 diabetes management guidelines 2024",
    "immunotherapy non-small cell lung cancer",
    "CAR-T cell therapy lymphoma",
    "CRISPR gene therapy sickle cell disease",
    "mRNA vaccine infectious disease",
    "Alzheimer disease anti-amyloid therapy",
    "obesity pharmacotherapy GLP-1",
    "sepsis management guidelines",
    "antibiotic resistance MRSA treatment",
    "hypertension management guidelines 2024",
    "atrial fibrillation anticoagulation",
    "chronic kidney disease progression",
]


class Ingestor:
    """Orchestrates bulk ingestion of PubMed articles into Qdrant."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        pubmed_client: Optional[PubMedClient] = None,
    ) -> None:
        self.store = vector_store or VectorStore()
        self.pubmed = pubmed_client or PubMedClient()

    def ingest_from_queries(
        self,
        queries: list[str],
        max_per_query: int = 20,
        min_year: Optional[int] = None,
    ) -> int:
        """Fetch articles for each query and upsert into Qdrant.

        Returns total number of articles ingested.
        """
        self.store.ensure_collection()

        all_articles: list[Article] = []
        seen_ids: set[str] = set()

        for query in queries:
            logger.info("Ingesting query: '%s'", query)
            articles = self.pubmed.search_and_fetch(
                query, max_results=max_per_query, min_year=min_year
            )
            # De-duplicate across queries
            for a in articles:
                uid = a.unique_id
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    all_articles.append(a)

        logger.info("Total unique articles fetched: %d", len(all_articles))
        upserted = self.store.upsert_articles(all_articles)
        logger.info("Upserted %d articles into Qdrant.", upserted)
        return upserted

    def create_seed_index(self, min_year: int = 2022) -> int:
        """Create the demo seed index using predefined medical queries.

        Targets ~200 abstracts from 2022 onwards.
        """
        logger.info("Creating seed index with %d queries...", len(SEED_QUERIES))
        return self.ingest_from_queries(
            SEED_QUERIES, max_per_query=15, min_year=min_year
        )

    def ingest_from_json(self, json_path: str | Path) -> int:
        """Ingest pre-downloaded articles from a JSON file.

        Expected format: list of dicts matching Article schema.
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        articles = [Article(**item) for item in data]
        logger.info("Loaded %d articles from %s", len(articles), path)

        self.store.ensure_collection()
        return self.store.upsert_articles(articles)

    def export_to_json(
        self, output_path: str | Path, queries: list[str], max_per_query: int = 20
    ) -> int:
        """Fetch articles and save to JSON (for offline use / submission)."""
        all_articles: list[Article] = []
        seen: set[str] = set()

        for q in queries:
            articles = self.pubmed.search_and_fetch(q, max_results=max_per_query)
            for a in articles:
                if a.unique_id not in seen:
                    seen.add(a.unique_id)
                    all_articles.append(a)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump([a.model_dump(mode="json") for a in all_articles], f, indent=2, default=str)

        logger.info("Exported %d articles to %s", len(all_articles), output)
        return len(all_articles)

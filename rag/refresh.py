"""Weekly refresh script / stub.

Run as:  python -m rag.refresh
"""

from __future__ import annotations

import logging
from datetime import datetime

from rag.ingestion import Ingestor, SEED_QUERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def refresh(min_year: int | None = None) -> int:
    """Re-ingest articles from all seed queries.

    Designed to be run weekly via cron or manual invocation.
    Qdrant upsert is idempotent (same ID overwrites), so safe to re-run.
    """
    if min_year is None:
        min_year = datetime.utcnow().year - 2  # Last 2 years

    logger.info("Starting weekly refresh (min_year=%d)...", min_year)
    ingestor = Ingestor()
    count = ingestor.ingest_from_queries(SEED_QUERIES, max_per_query=20, min_year=min_year)
    logger.info("Refresh complete. %d articles ingested/updated.", count)
    return count


if __name__ == "__main__":
    refresh()

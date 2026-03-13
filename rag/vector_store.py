"""Qdrant vector store interface with PubMedBERT embeddings.

Manages a Qdrant collection with:
  - Dense vectors from PubMedBERT (semantic similarity)
  - Sparse vectors for BM25 keyword matching
  - Rich payload metadata for filtering (year, study_type, journal, etc.)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from config import settings
from rag.models import Article

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
DENSE_DIM = 768  # PubMedBERT output dimension


class VectorStore:
    """Qdrant-backed store with hybrid dense + sparse vectors."""

    def __init__(self) -> None:
        self._qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        self._collection = settings.qdrant_collection
        self._embedder: Optional[SentenceTransformer] = None

    # ── lazy-load the embedding model ───────────

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info("Loading embedding model: %s", settings.embedding_model)
            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder

    # ── collection management ────────────────────

    def ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        collections = [c.name for c in self._qdrant.get_collections().collections]
        if self._collection in collections:
            logger.info("Collection '%s' already exists.", self._collection)
            return

        self._qdrant.create_collection(
            collection_name=self._collection,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=DENSE_DIM,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                ),
            },
        )

        # Create payload indexes for efficient filtering
        for field in ["year", "study_type", "journal", "source", "is_preprint"]:
            self._qdrant.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=(
                    models.PayloadSchemaType.INTEGER
                    if field in ("year", "study_type")
                    else models.PayloadSchemaType.KEYWORD
                    if field != "is_preprint"
                    else models.PayloadSchemaType.BOOL
                ),
            )
        logger.info("Created collection '%s' with payload indexes.", self._collection)

    def drop_collection(self) -> None:
        """Delete the collection if it exists."""
        self._qdrant.delete_collection(self._collection)

    # ── upsert articles ─────────────────────────

    def upsert_articles(self, articles: list[Article], batch_size: int = 64) -> int:
        """Embed articles and upsert into Qdrant. Returns count upserted."""
        if not articles:
            return 0

        upserted = 0
        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]
            points = self._build_points(batch)
            self._qdrant.upsert(
                collection_name=self._collection,
                points=points,
            )
            upserted += len(points)
            logger.info("Upserted batch %d–%d (%d points)", i, i + len(batch), len(points))

        return upserted

    # ── search ──────────────────────────────────

    def search_dense(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[models.Filter] = None,
    ) -> list[models.ScoredPoint]:
        """Pure dense (semantic) search."""
        query_vec = self.embedder.encode(query).tolist()
        return self._qdrant.query_points(
            collection_name=self._collection,
            query=query_vec,
            using=DENSE_VECTOR_NAME,
            limit=limit,
            query_filter=filters,
            with_payload=True,
        ).points

    def search_sparse(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[models.Filter] = None,
    ) -> list[models.ScoredPoint]:
        """Pure sparse (BM25) keyword search."""
        # Build a simple sparse vector from query tokens
        sparse_vec = self._text_to_sparse(query)
        return self._qdrant.query_points(
            collection_name=self._collection,
            query=models.SparseVector(**sparse_vec),
            using=SPARSE_VECTOR_NAME,
            limit=limit,
            query_filter=filters,
            with_payload=True,
        ).points

    def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[models.Filter] = None,
    ) -> list[models.ScoredPoint]:
        """Hybrid search: dense + sparse fused via RRF."""
        query_vec = self.embedder.encode(query).tolist()
        sparse_vec = self._text_to_sparse(query)

        results = self._qdrant.query_points(
            collection_name=self._collection,
            prefetch=[
                models.Prefetch(
                    query=query_vec,
                    using=DENSE_VECTOR_NAME,
                    limit=limit * 2,
                    filter=filters,
                ),
                models.Prefetch(
                    query=models.SparseVector(**sparse_vec),
                    using=SPARSE_VECTOR_NAME,
                    limit=limit * 2,
                    filter=filters,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        return results.points

    # ── helpers to build filters ─────────────────

    @staticmethod
    def build_filters(
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        study_types: Optional[list[int]] = None,
        sources: Optional[list[str]] = None,
        exclude_preprints: bool = False,
    ) -> Optional[models.Filter]:
        """Build a Qdrant filter from user-facing facets."""
        conditions: list[models.Condition] = []

        if year_from is not None:
            conditions.append(
                models.FieldCondition(
                    key="year",
                    range=models.Range(gte=year_from),
                )
            )
        if year_to is not None:
            conditions.append(
                models.FieldCondition(
                    key="year",
                    range=models.Range(lte=year_to),
                )
            )
        if study_types:
            conditions.append(
                models.FieldCondition(
                    key="study_type",
                    match=models.MatchAny(any=study_types),
                )
            )
        if sources:
            conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchAny(any=sources),
                )
            )
        if exclude_preprints:
            conditions.append(
                models.FieldCondition(
                    key="is_preprint",
                    match=models.MatchValue(value=False),
                )
            )

        if not conditions:
            return None
        return models.Filter(must=conditions)

    # ── private helpers ─────────────────────────

    def _build_points(self, articles: list[Article]) -> list[models.PointStruct]:
        """Build Qdrant points with dense + sparse vectors and payload."""
        texts = [self._article_text(a) for a in articles]

        # Dense embeddings via PubMedBERT
        dense_vecs = self.embedder.encode(texts, show_progress_bar=False)

        points: list[models.PointStruct] = []
        for idx, (article, dense_vec) in enumerate(zip(articles, dense_vecs)):
            sparse = self._text_to_sparse(texts[idx])
            payload = {
                "pmid": article.pmid,
                "doi": article.doi,
                "title": article.title,
                "abstract": article.abstract,
                "authors": article.authors,
                "journal": article.journal,
                "year": article.year,
                "month": article.month,
                "study_type": article.study_type.value,
                "study_type_label": article.study_type.label,
                "source": article.source,
                "source_url": article.source_url,
                "is_preprint": article.is_preprint,
                "mesh_terms": article.mesh_terms,
            }

            point_id = abs(hash(article.unique_id)) % (2**63)
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        DENSE_VECTOR_NAME: dense_vec.tolist(),
                        SPARSE_VECTOR_NAME: models.SparseVector(**sparse),
                    },
                    payload=payload,
                )
            )
        return points

    @staticmethod
    def _article_text(article: Article) -> str:
        """Combine title + abstract for embedding."""
        parts = [article.title]
        if article.abstract:
            parts.append(article.abstract)
        return " ".join(parts)

    @staticmethod
    def _text_to_sparse(text: str) -> dict:
        """Simple term-frequency sparse vector for BM25 indexing.

        Qdrant's server-side IDF modifier handles the full BM25 scoring.
        We just need to supply term indices and counts.
        """
        tokens = text.lower().split()
        token_counts: dict[str, int] = {}
        for t in tokens:
            t = t.strip(".,;:!?()[]{}\"'")
            if len(t) > 1:
                token_counts[t] = token_counts.get(t, 0) + 1

        # Map tokens to integer indices via hash
        indices = []
        values = []
        for token, count in token_counts.items():
            indices.append(abs(hash(token)) % (2**31))
            values.append(float(count))

        return {"indices": indices, "values": values}

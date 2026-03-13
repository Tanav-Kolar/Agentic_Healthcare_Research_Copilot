"""Pydantic schemas for the FastAPI backend."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PICO(BaseModel):
    """PICO decomposition of the clinical question."""
    population: str = Field(..., alias="population/problem")
    intervention: str
    comparison: str
    outcome: str
    search_strings: List[str]
    mesh_terms: List[str]
    original_question: str

    class Config:
        populate_by_name = True


class SearchFilters(BaseModel):
    """Filters for the search query."""
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    study_types: Optional[List[str]] = None
    is_preprint: Optional[bool] = None


class AskRequest(BaseModel):
    """Request schema for the /ask endpoint."""
    question: str
    thread_id: Optional[str] = None
    filters: Optional[SearchFilters] = None


class Quote(BaseModel):
    """A direct quote from a source article."""
    id: str = Field(..., alias="article")
    pmid: Optional[str] = None
    quote: str

    class Config:
        populate_by_name = True


class EvidenceItem(BaseModel):
    """An item in the evidence table."""
    id: str
    title: str
    journal: str
    type: str
    year: int
    population: str
    intervention: str
    outcomes: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    source_url: str


class RecentChange(BaseModel):
    """A recent change in evidence (last 24 months)."""
    id: str
    summary: str
    year: int
    pmid: Optional[str] = None
    doi: Optional[str] = None


class AskResponse(BaseModel):
    """Structured response for the /ask endpoint."""
    thread_id: str
    answer: str
    quotes: List[Quote]
    evidence_table: List[EvidenceItem]
    changed_in_last_24_months: List[RecentChange]
    pico: PICO
    contradictions: Any
    verification: Any
    disclaimer: str
    metadata: dict

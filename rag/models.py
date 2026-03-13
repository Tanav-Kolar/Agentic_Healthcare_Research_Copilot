"""Data models for the RAG pipeline.

Defines the core domain objects: Article, Citation, EvidenceItem,
and the StudyType evidence hierarchy enum.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class StudyType(IntEnum):
    """Evidence hierarchy — lower value = stronger evidence."""

    GUIDELINE = 1
    META_ANALYSIS = 2
    SYSTEMATIC_REVIEW = 3
    RCT = 4
    COHORT = 5
    CASE_CONTROL = 6
    CASE_REPORT = 7
    PREPRINT = 8
    UNKNOWN = 9

    @property
    def label(self) -> str:
        _labels = {
            1: "Guideline",
            2: "Meta-analysis",
            3: "Systematic Review",
            4: "RCT",
            5: "Cohort Study",
            6: "Case-Control Study",
            7: "Case Report",
            8: "Preprint (not peer-reviewed)",
            9: "Unknown",
        }
        return _labels[self.value]


class Article(BaseModel):
    """A single research article / record retrieved from PubMed or other sources."""

    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    year: int = 0
    month: int = 0
    study_type: StudyType = StudyType.UNKNOWN
    source: str = "PubMed"  # PubMed | Cochrane | ClinicalTrials | WHO | CDC | Preprint
    source_url: str = ""
    is_preprint: bool = False
    country: str = ""
    mesh_terms: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def unique_id(self) -> str:
        """Canonical dedup key: prefer DOI, fall back to PMID."""
        return self.doi or self.pmid or self.title[:80]


class Citation(BaseModel):
    """An inline citation linking a claim to a source article."""

    id: str  # e.g. "1", "2"
    pmid: Optional[str] = None
    doi: Optional[str] = None
    quote: str  # verbatim sentence from the abstract
    type: str  # StudyType label
    year: int = 0
    title: str = ""
    journal: str = ""
    source_url: str = ""


class EvidenceItem(BaseModel):
    """A row in the evidence table returned to the user."""

    id: str
    title: str
    journal: str = ""
    type: str  # StudyType label
    year: int = 0
    population: str = ""
    intervention: str = ""
    comparison: str = ""
    outcomes: str = ""
    doi: Optional[str] = None
    pmid: Optional[str] = None
    source_url: str = ""


class RecentChange(BaseModel):
    """An item in the 'What changed in last 24 months?' panel."""

    id: str
    summary: str
    year: int
    pmid: Optional[str] = None
    doi: Optional[str] = None


class PICOQuery(BaseModel):
    """Structured PICO decomposition of a clinical question."""

    population: str = ""
    intervention: str = ""
    comparison: str = ""
    outcome: str = ""
    search_strings: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    original_question: str = ""

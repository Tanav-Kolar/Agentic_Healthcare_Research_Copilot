"""PubMed E-utilities client.

Wraps ESearch → EFetch / ESummary to retrieve article metadata and abstracts.
Respects NCBI rate limits (3 req/sec without key, 10 with key).
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from xml.etree import ElementTree

import httpx

from config import settings
from rag.models import Article, StudyType

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# NCBI E-utilities base URLs
# ──────────────────────────────────────────────
_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH = f"{_BASE}/esearch.fcgi"
_EFETCH = f"{_BASE}/efetch.fcgi"
_ESUMMARY = f"{_BASE}/esummary.fcgi"

# Rate-limiting: minimum seconds between requests
_MIN_INTERVAL = 0.34  # ~3 req/sec (safe default)


class PubMedClient:
    """Stateless wrapper around PubMed E-utilities."""

    def __init__(self) -> None:
        self._last_request_time: float = 0.0
        self._client = httpx.Client(timeout=30.0)
        self._params: dict = {}
        if settings.ncbi_api_key:
            self._params["api_key"] = settings.ncbi_api_key
        if settings.ncbi_email:
            self._params["email"] = settings.ncbi_email

    # ── public API ──────────────────────────────

    def search(
        self,
        query: str,
        max_results: int = 50,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
    ) -> list[str]:
        """ESearch: returns a list of PMIDs matching *query*."""
        params = {
            **self._params,
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
            "sort": "relevance",
        }
        if min_year:
            params["mindate"] = f"{min_year}/01/01"
            params["datetype"] = "pdat"
        if max_year:
            params["maxdate"] = f"{max_year}/12/31"
            params["datetype"] = "pdat"

        self._throttle()
        resp = self._client.get(_ESEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
        pmids: list[str] = data.get("esearchresult", {}).get("idlist", [])
        logger.info("PubMed search '%s' → %d PMIDs", query, len(pmids))
        return pmids

    def fetch_articles(self, pmids: list[str]) -> list[Article]:
        """EFetch: retrieve full article metadata + abstracts for given PMIDs."""
        if not pmids:
            return []

        articles: list[Article] = []
        # Process in batches of 200 (NCBI limit)
        for i in range(0, len(pmids), 200):
            batch = pmids[i : i + 200]
            batch_articles = self._efetch_batch(batch)
            articles.extend(batch_articles)

        return articles

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 50,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
    ) -> list[Article]:
        """Convenience: ESearch + EFetch in one call."""
        pmids = self.search(query, max_results, min_year, max_year)
        return self.fetch_articles(pmids)

    # ── private helpers ─────────────────────────

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _efetch_batch(self, pmids: list[str]) -> list[Article]:
        """Fetch a single batch of PMIDs via EFetch XML."""
        params = {
            **self._params,
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        self._throttle()
        resp = self._client.get(_EFETCH, params=params)
        resp.raise_for_status()

        return self._parse_efetch_xml(resp.text)

    def _parse_efetch_xml(self, xml_text: str) -> list[Article]:
        """Parse EFetch PubMed XML into Article objects."""
        root = ElementTree.fromstring(xml_text)
        articles: list[Article] = []

        for pa in root.findall(".//PubmedArticle"):
            try:
                article = self._parse_single_article(pa)
                articles.append(article)
            except Exception:
                logger.warning("Failed to parse PubmedArticle", exc_info=True)

        return articles

    def _parse_single_article(self, pa: ElementTree.Element) -> Article:
        """Parse a single <PubmedArticle> element."""
        medline = pa.find(".//MedlineCitation")
        article_el = medline.find(".//Article")

        # PMID
        pmid = (medline.findtext("PMID") or "").strip()

        # Title
        title = (article_el.findtext(".//ArticleTitle") or "").strip()

        # Abstract
        abstract_parts = []
        for abs_text in article_el.findall(".//Abstract/AbstractText"):
            label = abs_text.get("Label", "")
            text = "".join(abs_text.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts)

        # Authors
        authors = []
        for author in article_el.findall(".//AuthorList/Author"):
            last = author.findtext("LastName") or ""
            fore = author.findtext("ForeName") or ""
            if last:
                authors.append(f"{last} {fore}".strip())

        # Journal
        journal = (article_el.findtext(".//Journal/Title") or "").strip()

        # Year
        year = 0
        year_el = article_el.find(".//Journal/JournalIssue/PubDate/Year")
        if year_el is not None and year_el.text:
            try:
                year = int(year_el.text)
            except ValueError:
                pass

        # Month
        month = 0
        month_el = article_el.find(".//Journal/JournalIssue/PubDate/Month")
        if month_el is not None and month_el.text:
            month_map = {
                "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
                "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
                "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
            }
            try:
                month = int(month_el.text)
            except ValueError:
                month = month_map.get(month_el.text[:3], 0)

        # DOI
        doi = ""
        for eid in pa.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if eid.get("IdType") == "doi":
                doi = (eid.text or "").strip()
                break

        # MeSH terms
        mesh_terms = [
            (mh.findtext("DescriptorName") or "").strip()
            for mh in medline.findall(".//MeshHeadingList/MeshHeading")
            if mh.findtext("DescriptorName")
        ]

        # Publication types
        pub_types = [
            (pt.text or "").strip()
            for pt in article_el.findall(".//PublicationTypeList/PublicationType")
            if pt.text
        ]

        # Infer study type from publication types
        study_type = self._infer_study_type(pub_types, title, abstract)

        # Is preprint?
        is_preprint = study_type == StudyType.PREPRINT

        return Article(
            pmid=pmid,
            doi=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=year,
            month=month,
            study_type=study_type,
            source="PubMed",
            source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            is_preprint=is_preprint,
            mesh_terms=mesh_terms,
            publication_types=pub_types,
        )

    @staticmethod
    def _infer_study_type(
        pub_types: list[str], title: str, abstract: str
    ) -> StudyType:
        """Best-effort study type classification from publication metadata."""
        combined = " ".join(pub_types).lower()
        title_lower = title.lower()
        abstract_lower = abstract.lower()

        if "practice guideline" in combined or "guideline" in combined:
            return StudyType.GUIDELINE
        if "meta-analysis" in combined or "meta-analysis" in title_lower:
            return StudyType.META_ANALYSIS
        if "systematic review" in combined or "systematic review" in title_lower:
            return StudyType.SYSTEMATIC_REVIEW
        if "randomized controlled trial" in combined or "randomised controlled trial" in combined:
            return StudyType.RCT
        if "rct" in title_lower or "randomized" in title_lower or "randomised" in title_lower:
            return StudyType.RCT
        if "cohort" in combined or "cohort study" in title_lower:
            return StudyType.COHORT
        if "case-control" in combined:
            return StudyType.CASE_CONTROL
        if "case report" in combined or "case reports" in combined:
            return StudyType.CASE_REPORT
        if "preprint" in combined or "preprint" in abstract_lower:
            return StudyType.PREPRINT

        return StudyType.UNKNOWN

"""Data models for lit-review-assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RelevanceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PaperType(str, Enum):
    EMPIRICAL = "empirical"
    THEORETICAL = "theoretical"
    REVIEW = "review"
    CASE_STUDY = "case_study"
    METHODS = "methods"
    UNKNOWN = "unknown"


class Venue(str, Enum):
    CHI = "CHI"
    CSCW = "CSCW"
    UIST = "UIST"
    FACCT = "FAccT"
    AIES = "AIES"
    ICLR = "ICLR"
    NEURIPS = "NeurIPS"
    ICML = "ICML"
    OTHER = "other"
    JOURNAL = "journal"
    PREPRINT = "preprint"
    UNKNOWN = "unknown"


@dataclass
class Paper:
    """A single paper in the literature review."""

    title: str
    authors: list[str]
    year: int
    venue: str
    abstract: str
    relevance: RelevanceLevel = RelevanceLevel.MEDIUM
    paper_type: PaperType = PaperType.UNKNOWN
    key_contribution: str = ""
    methodology: str = ""
    limitations: str = ""
    citation_key: str = ""
    doi: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)
    llm_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "relevance": self.relevance.value,
            "paper_type": self.paper_type.value,
            "key_contribution": self.key_contribution,
            "methodology": self.methodology,
            "limitations": self.limitations,
            "citation_key": self.citation_key,
            "doi": self.doi,
            "url": self.url,
            "tags": self.tags,
            "llm_summary": self.llm_summary,
        }


@dataclass
class LiteratureReview:
    """A structured literature review for a given research topic."""

    topic: str
    papers: list[Paper]
    synthesis: str = ""
    research_gaps: list[str] = field(default_factory=list)
    methodological_trends: list[str] = field(default_factory=list)
    venue_distribution: dict[str, int] = field(default_factory=dict)
    year_range: tuple[int, int] = field(default_factory=lambda: (0, 0))
    total_papers: int = 0
    llm_enriched: bool = False
    llm_model: str = ""
    citation_scaffold: str = ""

    def __post_init__(self):
        self.total_papers = len(self.papers)
        if self.papers:
            years = [p.year for p in self.papers if p.year > 0]
            if years:
                self.year_range = (min(years), max(years))
            venues: dict[str, int] = {}
            for p in self.papers:
                venues[p.venue] = venues.get(p.venue, 0) + 1
            self.venue_distribution = venues

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "total_papers": self.total_papers,
            "year_range": list(self.year_range),
            "venue_distribution": self.venue_distribution,
            "synthesis": self.synthesis,
            "research_gaps": self.research_gaps,
            "methodological_trends": self.methodological_trends,
            "llm_enriched": self.llm_enriched,
            "llm_model": self.llm_model,
            "citation_scaffold": self.citation_scaffold,
            "papers": [p.to_dict() for p in self.papers],
        }

"""Rule-based engine for lit-review-assistant.

Parses structured literature input (BibTeX-like or plain list),
classifies papers, identifies venue patterns, and scaffolds a review.
No LLM required for core functionality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    LiteratureReview,
    Paper,
    PaperType,
    RelevanceLevel,
)

# ---------------------------------------------------------------------------
# Venue detection
# ---------------------------------------------------------------------------

_VENUE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bCHI\b", re.IGNORECASE), "CHI"),
    (re.compile(r"\bCSCW\b", re.IGNORECASE), "CSCW"),
    (re.compile(r"\bUIST\b", re.IGNORECASE), "UIST"),
    (re.compile(r"\bFAccT\b|\bFACCT\b", re.IGNORECASE), "FAccT"),
    (re.compile(r"\bAIES\b", re.IGNORECASE), "AIES"),
    (re.compile(r"\bICLR\b", re.IGNORECASE), "ICLR"),
    (re.compile(r"\bNeurIPS\b|\bNIPS\b", re.IGNORECASE), "NeurIPS"),
    (re.compile(r"\bICML\b", re.IGNORECASE), "ICML"),
    (re.compile(r"\barXiv\b|\bpreprint\b", re.IGNORECASE), "preprint"),
    (re.compile(r"\bjournal\b|\bIJHCS\b|\bToCHI\b|\bTIIS\b", re.IGNORECASE), "journal"),
]

_METHODOLOGY_KEYWORDS = {
    "mixed methods": "mixed",
    "think aloud": "usability",
    "usability study": "usability",
    "interview": "qualitative",
    "survey": "quantitative",
    "experiment": "controlled experiment",
    "randomized": "RCT",
    "field study": "field study",
    "diary": "diary study",
    "ethnograph": "ethnography",
    "grounded theory": "grounded theory",
    "content analysis": "content analysis",
    "meta-analysis": "meta-analysis",
    "systematic review": "systematic review",
    "simulation": "simulation",
    "machine learning": "ML",
    "deep learning": "deep learning",
    "large language model": "LLM",
    "neural network": "neural network",
}

_PAPER_TYPE_INDICATORS = {
    PaperType.REVIEW: ["survey", "review", "meta-analysis", "systematic", "overview"],
    PaperType.THEORETICAL: ["framework", "theory", "model", "conceptual", "taxonomy"],
    PaperType.METHODS: ["method", "technique", "algorithm", "approach", "tool"],
    PaperType.CASE_STUDY: ["case study", "case-study", "deployment", "in-the-wild"],
    PaperType.EMPIRICAL: ["study", "experiment", "evaluation", "participants", "users"],
}

_RELEVANCE_HIGH_WORDS = [
    "directly", "strongly", "central", "primary", "core", "critical", "fundamental",
    "key", "main", "principal",
]
_RELEVANCE_LOW_WORDS = ["tangentially", "marginally", "loosely", "peripherally"]


def _detect_venue(text: str) -> str:
    for pattern, name in _VENUE_PATTERNS:
        if pattern.search(text):
            return name
    return "unknown"


def _detect_paper_type(title: str, abstract: str) -> PaperType:
    combined = (title + " " + abstract).lower()
    for ptype, keywords in _PAPER_TYPE_INDICATORS.items():
        if any(kw in combined for kw in keywords):
            return ptype
    return PaperType.UNKNOWN


def _detect_methodology(abstract: str) -> str:
    lower = abstract.lower()
    detected = []
    for kw, label in _METHODOLOGY_KEYWORDS.items():
        if kw in lower and label not in detected:
            detected.append(label)
    return ", ".join(detected[:3]) if detected else ""


def _detect_relevance(title: str, abstract: str, topic: str) -> RelevanceLevel:
    """Simple keyword-overlap relevance scoring."""
    topic_words = set(re.findall(r"\w{4,}", topic.lower()))
    combined = (title + " " + abstract).lower()
    combined_words = set(re.findall(r"\w{4,}", combined))
    overlap = topic_words & combined_words
    ratio = len(overlap) / max(len(topic_words), 1)
    if ratio >= 0.5:
        return RelevanceLevel.HIGH
    if ratio >= 0.2:
        return RelevanceLevel.MEDIUM
    return RelevanceLevel.LOW


def _make_citation_key(authors: list[str], year: int, title: str) -> str:
    first_author = authors[0].split()[-1] if authors else "Unknown"
    title_word = re.sub(r"\W", "", title.split()[0]) if title else "Paper"
    return f"{first_author}{year}{title_word}"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_bibtex_entry(entry: str) -> dict | None:
    """Parse a single BibTeX entry block into a dict."""
    result: dict = {}
    field_pattern = re.compile(r'(\w+)\s*=\s*[{"](.*?)[}"],?\s*$', re.DOTALL | re.MULTILINE)
    for m in field_pattern.finditer(entry):
        result[m.group(1).lower()] = m.group(2).strip()

    # Type line
    type_m = re.match(r"@(\w+)\{(\w+)", entry.strip())
    if type_m:
        result["_bibtex_type"] = type_m.group(1).lower()
        result["_key"] = type_m.group(2)

    return result if result else None


def _parse_plain_entry(line: str) -> dict | None:
    """Parse a plain-text reference line.

    Expected format (flexible):
      Authors (Year). Title. Venue.
      or: Authors, Year, Title, Venue
    """
    line = line.strip().lstrip("0123456789.-) ")
    if not line or len(line) < 20:
        return None

    # Try to extract year
    year_m = re.search(r"\b(19|20)\d{2}\b", line)
    year = int(year_m.group()) if year_m else 0

    # Heuristic split: everything before year is authors, after is title/venue
    if year_m:
        before_year = line[: year_m.start()].strip(" .,;()")
        after_year = line[year_m.end() :].strip(" .,;().")
    else:
        before_year = ""
        after_year = line

    # Split remaining on ". " to get title and venue
    parts = [p.strip() for p in after_year.split(".") if p.strip()]
    title = parts[0] if parts else after_year
    venue_hint = parts[1] if len(parts) > 1 else ""

    authors = [a.strip() for a in re.split(r",\s*(?:and\s+)?", before_year) if a.strip()] if before_year else []

    return {
        "title": title,
        "author": " and ".join(authors),
        "year": str(year) if year else "",
        "booktitle": venue_hint,
        "abstract": "",
    }


def _dict_to_paper(d: dict, topic: str) -> Paper:
    title = d.get("title", "").strip()
    abstract = d.get("abstract", "").strip()
    year_str = d.get("year", "0")
    year = int(re.sub(r"\D", "", year_str)) if year_str else 0
    author_str = d.get("author", d.get("authors", ""))
    authors = [a.strip() for a in re.split(r"\s+and\s+|,\s+", author_str) if a.strip()]
    venue_raw = d.get("booktitle", d.get("journal", d.get("venue", "")))
    venue = _detect_venue(venue_raw + " " + title)

    return Paper(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract=abstract,
        relevance=_detect_relevance(title, abstract, topic),
        paper_type=_detect_paper_type(title, abstract),
        methodology=_detect_methodology(abstract),
        citation_key=d.get("_key", "") or _make_citation_key(authors, year, title),
        doi=d.get("doi", ""),
        url=d.get("url", ""),
    )


# ---------------------------------------------------------------------------
# Gap & trend detection
# ---------------------------------------------------------------------------

def _detect_gaps(papers: list[Paper], topic: str) -> list[str]:
    """Infer research gaps from coverage patterns."""
    gaps = []
    methods = [p.methodology for p in papers if p.methodology]
    if not any("longitudinal" in m or "diary" in m for m in methods):
        gaps.append("No longitudinal or diary study designs found — long-term effects under-explored.")
    if not any("field study" in m or "in-the-wild" in p.paper_type.value for p in papers for m in [p.methodology]):
        gaps.append("Limited in-the-wild / deployment studies — ecological validity gap.")
    paper_types = [p.paper_type for p in papers]
    if PaperType.REVIEW not in paper_types:
        gaps.append("No systematic review or meta-analysis identified for this topic area.")
    if sum(1 for p in papers if p.year >= 2023) < 2:
        gaps.append("Sparse coverage post-2023 — recent LLM-era developments may be missing.")
    return gaps[:4]


def _detect_trends(papers: list[Paper]) -> list[str]:
    trends = []
    methods_all = " ".join(p.methodology for p in papers).lower()
    if "llm" in methods_all or "large language" in methods_all:
        trends.append("Increasing use of LLMs as research instruments or study artifacts.")
    if "mixed" in methods_all:
        trends.append("Mixed-methods designs appearing across multiple works.")
    recent = [p for p in papers if p.year >= 2022]
    if len(recent) > len(papers) * 0.4:
        trends.append("Publication volume accelerating post-2022.")
    venues = [p.venue for p in papers]
    if "CHI" in venues and ("FAccT" in venues or "AIES" in venues):
        trends.append("Cross-pollination between HCI and AI ethics venues.")
    return trends[:4]


def _build_synthesis(papers: list[Paper], topic: str) -> str:
    if not papers:
        return ""
    high = [p for p in papers if p.relevance == RelevanceLevel.HIGH]
    total = len(papers)
    year_range = f"{min(p.year for p in papers if p.year > 0)}–{max(p.year for p in papers if p.year > 0)}" if any(p.year > 0 for p in papers) else "various years"
    venues = list({p.venue for p in papers if p.venue != "unknown"})
    return (
        f"This review covers {total} paper(s) on '{topic}' spanning {year_range}, "
        f"drawing from {', '.join(venues[:4]) if venues else 'multiple venues'}. "
        f"{len(high)} paper(s) show high relevance to the stated topic. "
        f"The corpus spans {len(set(p.paper_type for p in papers))} paper type(s)."
    )


def _build_citation_scaffold(papers: list[Paper], topic: str) -> str:
    """Generate a basic citation scaffold paragraph."""
    if not papers:
        return ""
    high = [p for p in papers if p.relevance == RelevanceLevel.HIGH]
    cited = high[:3] if high else papers[:3]
    cites = ", ".join(f"[{p.citation_key}]" for p in cited)
    return (
        f"Research on {topic} has been explored across multiple venues "
        f"(see {cites}). "
        f"[ADD: characterise the main contributions here.] "
        f"Key methodological approaches include "
        f"{', '.join(set(p.methodology for p in cited if p.methodology)) or '[methodology]'}. "
        f"[ADD: synthesis of findings and tensions across works.]"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ReviewConfig:
    min_relevance: RelevanceLevel = RelevanceLevel.LOW
    max_papers: int = 50
    sort_by: str = "relevance"  # "relevance" | "year" | "venue"


def parse_bibtex(text: str, topic: str, config: ReviewConfig | None = None) -> LiteratureReview:
    """Parse a BibTeX string into a LiteratureReview."""
    if config is None:
        config = ReviewConfig()
    entries = re.split(r"(?=@\w+\{)", text)
    papers = []
    for entry in entries:
        entry = entry.strip()
        if not entry.startswith("@"):
            continue
        d = _parse_bibtex_entry(entry)
        if d:
            papers.append(_dict_to_paper(d, topic))
    return _build_review(papers, topic, config)


def parse_plain_list(text: str, topic: str, config: ReviewConfig | None = None) -> LiteratureReview:
    """Parse a plain-text reference list into a LiteratureReview."""
    if config is None:
        config = ReviewConfig()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    papers = []
    for line in lines:
        d = _parse_plain_entry(line)
        if d:
            papers.append(_dict_to_paper(d, topic))
    return _build_review(papers, topic, config)


def _build_review(papers: list[Paper], topic: str, config: ReviewConfig) -> LiteratureReview:
    # Filter by relevance
    level_order = {RelevanceLevel.HIGH: 2, RelevanceLevel.MEDIUM: 1, RelevanceLevel.LOW: 0}
    min_level = level_order[config.min_relevance]
    papers = [p for p in papers if level_order[p.relevance] >= min_level]

    # Sort
    if config.sort_by == "year":
        papers.sort(key=lambda p: p.year, reverse=True)
    elif config.sort_by == "venue":
        papers.sort(key=lambda p: p.venue)
    else:
        papers.sort(key=lambda p: level_order[p.relevance], reverse=True)

    papers = papers[: config.max_papers]

    review = LiteratureReview(
        topic=topic,
        papers=papers,
        synthesis=_build_synthesis(papers, topic),
        research_gaps=_detect_gaps(papers, topic),
        methodological_trends=_detect_trends(papers),
        citation_scaffold=_build_citation_scaffold(papers, topic),
    )
    return review

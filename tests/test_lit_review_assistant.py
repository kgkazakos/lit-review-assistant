"""Tests for lit-review-assistant."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lit_review_assistant.engine import ReviewConfig, parse_bibtex, parse_plain_list
from lit_review_assistant.export import to_bibtex_scaffold, to_csv, to_json, to_markdown
from lit_review_assistant.models import (
    LiteratureReview,
    Paper,
    PaperType,
    RelevanceLevel,
)

BIB_FIXTURE = Path(__file__).parent / "fixtures" / "sample_refs.bib"
PLAIN_FIXTURE = Path(__file__).parent / "fixtures" / "sample_refs_plain.txt"
BIB_TEXT = BIB_FIXTURE.read_text(encoding="utf-8")
PLAIN_TEXT = PLAIN_FIXTURE.read_text(encoding="utf-8")
TOPIC = "human-centred machine learning and UX"


# ── Parser tests ────────────────────────────────────────────────────────────

class TestBibtexParser:
    def test_returns_literature_review(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert isinstance(rv, LiteratureReview)

    def test_parses_all_entries(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert len(rv.papers) == 7

    def test_topic_set(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert rv.topic == TOPIC

    def test_year_extracted(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        for p in rv.papers:
            assert p.year > 2010

    def test_venue_detected(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        venues = [p.venue for p in rv.papers]
        assert "CHI" in venues

    def test_relevance_assigned(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        for p in rv.papers:
            assert p.relevance in RelevanceLevel.__members__.values()

    def test_paper_type_assigned(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        for p in rv.papers:
            assert p.paper_type in PaperType.__members__.values()

    def test_methodology_detected(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        # At least some papers should have methodology detected
        has_method = [p for p in rv.papers if p.methodology]
        assert len(has_method) >= 1

    def test_citation_keys_set(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        for p in rv.papers:
            assert p.citation_key

    def test_year_range_computed(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert rv.year_range[0] > 0
        assert rv.year_range[1] >= rv.year_range[0]

    def test_venue_distribution_computed(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert isinstance(rv.venue_distribution, dict)
        assert len(rv.venue_distribution) >= 1

    def test_synthesis_generated(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert rv.synthesis

    def test_research_gaps_detected(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert isinstance(rv.research_gaps, list)

    def test_methodological_trends_detected(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert isinstance(rv.methodological_trends, list)

    def test_citation_scaffold_generated(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        assert rv.citation_scaffold

    def test_max_papers_respected(self):
        config = ReviewConfig(max_papers=3)
        rv = parse_bibtex(BIB_TEXT, TOPIC, config)
        assert len(rv.papers) <= 3

    def test_sort_by_year(self):
        config = ReviewConfig(sort_by="year")
        rv = parse_bibtex(BIB_TEXT, TOPIC, config)
        years = [p.year for p in rv.papers]
        assert years == sorted(years, reverse=True)

    def test_min_relevance_filter(self):
        config = ReviewConfig(min_relevance=RelevanceLevel.HIGH)
        rv = parse_bibtex(BIB_TEXT, TOPIC, config)
        for p in rv.papers:
            assert p.relevance == RelevanceLevel.HIGH

    def test_empty_bibtex_graceful(self):
        rv = parse_bibtex("", TOPIC)
        assert isinstance(rv, LiteratureReview)
        assert rv.papers == []


class TestPlainListParser:
    def test_returns_literature_review(self):
        rv = parse_plain_list(PLAIN_TEXT, TOPIC)
        assert isinstance(rv, LiteratureReview)

    def test_parses_entries(self):
        rv = parse_plain_list(PLAIN_TEXT, TOPIC)
        assert len(rv.papers) >= 1

    def test_year_extracted(self):
        rv = parse_plain_list(PLAIN_TEXT, TOPIC)
        for p in rv.papers:
            assert p.year > 2010

    def test_venue_hint_extracted(self):
        rv = parse_plain_list(PLAIN_TEXT, TOPIC)
        venues = [p.venue for p in rv.papers]
        # CHI should be detected
        assert any(v != "unknown" for v in venues)


# ── Export tests ─────────────────────────────────────────────────────────────

class TestExports:
    @pytest.fixture
    def review(self):
        return parse_bibtex(BIB_TEXT, TOPIC)

    def test_to_markdown_returns_string(self, review):
        md = to_markdown(review)
        assert isinstance(md, str)
        assert "#" in md

    def test_to_markdown_contains_topic(self, review):
        md = to_markdown(review)
        assert review.topic in md

    def test_to_markdown_contains_papers(self, review):
        md = to_markdown(review)
        assert "Papers" in md

    def test_to_json_valid(self, review):
        j = to_json(review)
        data = json.loads(j)
        assert "topic" in data
        assert "papers" in data
        assert "research_gaps" in data

    def test_to_json_paper_structure(self, review):
        data = json.loads(to_json(review))
        for p in data["papers"]:
            assert "title" in p
            assert "year" in p
            assert "relevance" in p

    def test_to_csv_returns_string(self, review):
        csv_str = to_csv(review)
        assert "title" in csv_str.lower()
        assert "year" in csv_str.lower()

    def test_to_bibtex_scaffold_returns_string(self, review):
        bib = to_bibtex_scaffold(review)
        assert "@inproceedings" in bib or "@article" in bib

    def test_to_markdown_writes_file(self, review, tmp_path):
        p = tmp_path / "review.md"
        to_markdown(review, p)
        assert p.exists()

    def test_to_json_writes_file(self, review, tmp_path):
        p = tmp_path / "review.json"
        to_json(review, p)
        assert p.exists()

    def test_to_csv_writes_file(self, review, tmp_path):
        p = tmp_path / "review.csv"
        to_csv(review, p)
        assert p.exists()

    def test_to_bibtex_writes_file(self, review, tmp_path):
        p = tmp_path / "scaffold.bib"
        to_bibtex_scaffold(review, p)
        assert p.exists()


# ── LLM enrichment tests ──────────────────────────────────────────────────

class TestLLMEnrichment:
    def test_llm_disabled_returns_unchanged(self):
        from lit_review_assistant.llm import enrich_review
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        original_synthesis = rv.synthesis
        enriched = enrich_review(rv, llm_enabled=False)
        assert enriched.synthesis == original_synthesis
        assert enriched.llm_enriched is False

    def test_llm_failure_graceful(self):
        from lit_review_assistant.llm import enrich_review
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        enriched = enrich_review(rv, model="invalid/model-xyz", llm_enabled=True)
        assert isinstance(enriched, LiteratureReview)


# ── Model tests ──────────────────────────────────────────────────────────

class TestModels:
    def test_paper_defaults(self):
        p = Paper(title="Test", authors=["Smith, J."], year=2024, venue="CHI", abstract="")
        assert p.relevance == RelevanceLevel.MEDIUM
        assert p.paper_type == PaperType.UNKNOWN
        assert p.tags == []

    def test_literature_review_postinit(self):
        papers = [
            Paper(title="A", authors=["X"], year=2022, venue="CHI", abstract=""),
            Paper(title="B", authors=["Y"], year=2023, venue="CSCW", abstract=""),
        ]
        rv = LiteratureReview(topic="test", papers=papers)
        assert rv.total_papers == 2
        assert rv.year_range == (2022, 2023)
        assert "CHI" in rv.venue_distribution

    def test_paper_to_dict(self):
        rv = parse_bibtex(BIB_TEXT, TOPIC)
        d = rv.to_dict()
        assert isinstance(d, dict)
        assert isinstance(d["papers"], list)

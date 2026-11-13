"""LLM enrichment for lit-review-assistant.

Generates per-paper summaries, a synthesised narrative, and enriched
gap analysis. Uses LiteLLM for model-agnostic multi-backend support.

LLM enrichment is ON by default. Core parsing and metadata are never
modified by LLM output — enrichment is strictly additive.
"""

from __future__ import annotations

import json
import logging

from .models import LiteratureReview, Paper

logger = logging.getLogger(__name__)

# Locked model strings (CPR standard)
DEFAULT_MODELS = [
    "anthropic/claude-opus-4-7",
    "gemini/gemini-4-argon",
    "openai/gpt-5.5",
]

_SYSTEM_PAPER = """You are a research assistant specialising in HCI, AI, and product research.
Given a paper title, venue, year, and abstract, produce a compact structured summary.

Respond ONLY with valid JSON (no markdown):
{
  "summary": "2–3 sentence practitioner-facing summary",
  "key_contribution": "one sentence, precise",
  "methodology": "methodology label(s) if not already provided",
  "limitations": "one sentence about study limitations if detectable"
}"""

_SYSTEM_SYNTHESIS = """You are an expert HCI researcher writing a literature review.
Given a structured list of papers and a topic, produce:
1. A synthesis paragraph (150–200 words) suitable for a CHI-style related work section
2. Up to 4 research gaps as concise bullet points
3. Up to 3 methodological trend observations

Respond ONLY with valid JSON (no markdown, no preamble):
{
  "synthesis": "...",
  "research_gaps": ["...", "..."],
  "methodological_trends": ["...", "..."]
}"""


def _summarise_paper(paper: Paper, model: str) -> Paper:
    """Add LLM-generated summary to a single paper."""
    try:
        import litellm  # noqa: PLC0415

        prompt = json.dumps({
            "title": paper.title,
            "venue": paper.venue,
            "year": paper.year,
            "abstract": paper.abstract[:1500],
        })
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PAPER},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        paper.llm_summary = data.get("summary", "")
        if data.get("key_contribution"):
            paper.key_contribution = data["key_contribution"]
        if data.get("methodology") and not paper.methodology:
            paper.methodology = data["methodology"]
        if data.get("limitations"):
            paper.limitations = data["limitations"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Paper summary failed for '%s': %s", paper.title, exc)
    return paper


def enrich_review(
    review: LiteratureReview,
    model: str = DEFAULT_MODELS[0],
    llm_enabled: bool = True,
    summarise_papers: bool = True,
) -> LiteratureReview:
    """Enrich a LiteratureReview with LLM summaries and synthesis.

    Always returns the review unchanged if LLM is disabled or fails.
    """
    if not llm_enabled:
        return review

    # 1. Per-paper summaries (only for high/medium relevance papers)
    if summarise_papers:
        for paper in review.papers:
            if paper.abstract:
                _summarise_paper(paper, model)

    # 2. Synthesis and gap analysis
    try:
        import litellm  # noqa: PLC0415

        papers_payload = [
            {
                "title": p.title,
                "year": p.year,
                "venue": p.venue,
                "methodology": p.methodology,
                "relevance": p.relevance.value,
                "summary": p.llm_summary or p.abstract[:200],
            }
            for p in review.papers[:20]  # cap to avoid token limits
        ]
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_SYNTHESIS},
                {
                    "role": "user",
                    "content": json.dumps({"topic": review.topic, "papers": papers_payload}),
                },
            ],
            temperature=0.3,
            max_tokens=700,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if "synthesis" in data:
            review.synthesis = data["synthesis"]
        if "research_gaps" in data and isinstance(data["research_gaps"], list):
            review.research_gaps = data["research_gaps"][:4]
        if "methodological_trends" in data and isinstance(data["methodological_trends"], list):
            review.methodological_trends = data["methodological_trends"][:3]

        review.llm_enriched = True
        review.llm_model = model

    except ImportError:
        logger.warning("litellm not installed — skipping LLM enrichment.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM synthesis failed (%s) — using rule-based output.", exc)

    return review

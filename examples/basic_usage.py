"""Basic usage example for lit-review-assistant."""

from lit_review_assistant import parse_bibtex, parse_plain_list, to_markdown

# ── BibTeX input ────────────────────────────────────────────────────────────
BIBTEX = """
@inproceedings{Amershi2019Software,
  title     = {Software Engineering for Machine Learning: A Case Study},
  author    = {Amershi, Saleema and Begel, Andrew},
  year      = {2019},
  booktitle = {ICSE},
  abstract  = {We conducted interviews and surveys to understand ML engineering challenges.}
}

@inproceedings{Gillies2016Human,
  title     = {Human-Centred Machine Learning},
  author    = {Gillies, Marco and Fiebrink, Rebecca},
  year      = {2016},
  booktitle = {CHI},
  abstract  = {Interactive machine learning workshop. Field study with novice users.}
}
"""

topic = "human-centred machine learning"
review = parse_bibtex(BIBTEX, topic)
print(to_markdown(review))

# ── Plain list input ─────────────────────────────────────────────────────────
plain = """
1. Amershi, S. et al. (2019). Software Engineering for Machine Learning. ICSE.
2. Yang, Q. et al. (2018). Investigating How Experienced UX Designers Work with ML. TOCHI journal.
"""
review2 = parse_plain_list(plain, topic)
print(f"Parsed {review2.total_papers} papers from plain list")

# ── With LLM enrichment (requires API key) ───────────────────────────────────
# from lit_review_assistant.llm import enrich_review
# review = enrich_review(review, model="anthropic/claude-opus-4-7")
# print(review.synthesis)

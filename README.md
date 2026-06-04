# lit-review-assistant

**CPR Orbital Tool #40 · S6: Pre-study & impact**

Summarises relevant HCI and AI papers for a given research topic with citation scaffolding. Built for UX researchers and academics who need structured literature coverage without a library assistant or hours of manual annotation.

---

## The problem

Literature reviews are one of the most time-consuming parts of research — and one of the most poorly supported. You have a pile of PDFs, a BibTeX export from Google Scholar, and a topic to cover. Turning that into a structured related-work section with gaps, trends, and a citation scaffold takes time that most practitioners don't have.

`lit-review-assistant` automates the first pass: relevance scoring, paper classification, methodology detection, venue tagging, gap identification, and citation scaffold generation — from BibTeX or a plain reference list.

---

## Features

- **BibTeX and plain-list parsing** — accepts standard `.bib` exports or numbered reference lists
- **Relevance scoring** — keyword-overlap scoring against your stated research topic (high/medium/low)
- **Paper type classification** — empirical, theoretical, review, methods, case study
- **Venue detection** — CHI, CSCW, UIST, FAccT, AIES, ICLR, NeurIPS, ICML, journal, preprint
- **Methodology detection** — identifies study types from abstract text (interviews, surveys, experiments, etc.)
- **Research gap detection** — flags missing longitudinal studies, ecological validity gaps, sparse post-2023 coverage
- **Methodological trend detection** — identifies LLM adoption, mixed-methods patterns, venue cross-pollination
- **Citation scaffold** — a fill-in-the-blank paragraph for related work sections
- **LLM enrichment (on by default)** — Claude Opus 4, Gemini 3.1 Pro Preview, or GPT-5.5 via LiteLLM generate per-paper summaries and a synthesis paragraph; enrichment is strictly additive
- **Four export formats** — Markdown review, JSON (structured), CSV table, BibTeX scaffold
- **Rule-based fallback** — works fully offline with zero API calls

---

## Install

```bash
pip install lit-review-assistant
```

With Streamlit UI:

```bash
pip install lit-review-assistant[ui]
```

---

## Usage

### CLI

```bash
# Generate a literature review from a BibTeX file
lit-review-assistant review refs.bib --topic "LLMs as synthetic participants in UX research"

# Plain list input
lit-review-assistant review refs.txt --input-format plain --topic "human-centred ML"

# Filter and sort options
lit-review-assistant review refs.bib \
  --topic "AI explainability" \
  --min-relevance high \
  --sort-by year \
  --format all \
  --output ./review

# Use a specific LLM backend
lit-review-assistant review refs.bib \
  --topic "fairness in ML" \
  --model gemini/gemini-3.1-pro-preview

# Rule-based only (no API key needed)
lit-review-assistant review refs.bib --topic "UX research" --no-llm
```

### Streamlit UI

```bash
streamlit run lit_review_assistant/app.py
```

### Python API

```python
from lit_review_assistant import parse_bibtex, to_markdown
from lit_review_assistant.llm import enrich_review

bibtex = open("refs.bib").read()
topic = "synthetic participants in user research"

# Parse (rule-based, no API key)
review = parse_bibtex(bibtex, topic)

# Enrich with LLM (optional)
review = enrich_review(review, model="anthropic/claude-opus-4-7")

# Export
print(to_markdown(review))
```

---

## Input formats

### BibTeX (preferred)

Standard BibTeX entries. Abstract field is used for methodology detection and LLM enrichment.

```bibtex
@inproceedings{Amershi2019Software,
  title     = {Software Engineering for Machine Learning: A Case Study},
  author    = {Amershi, Saleema and Begel, Andrew},
  year      = {2019},
  booktitle = {ICSE},
  abstract  = {We conducted interviews and surveys...}
}
```

### Plain list

Flexible numbered or bulleted reference format:

```
1. Amershi, S. et al. (2019). Software Engineering for Machine Learning. ICSE.
2. Yang, Q. et al. (2018). Investigating How UX Designers Work with ML. TOCHI journal.
```

---

## Output example

```markdown
# Literature Review: human-centred machine learning and UX

**7 papers** · 2016–2022 · CHI (3) · FAccT (2) · ICSE (1) · journal (1)

## Synthesis
This review covers 7 papers on 'human-centred machine learning and UX' spanning
2016–2022, drawing from CHI, FAccT, ICSE, journal. 4 papers show high relevance.

## Research Gaps
- No longitudinal or diary study designs found — long-term effects under-explored.
- Sparse coverage post-2023 — recent LLM-era developments may be missing.

## Citation Scaffold
> Research on human-centred machine learning and UX has been explored across
> multiple venues (see [Amershi2019Software], [Gillies2016Human], [Cai2019Human]).
> [ADD: characterise the main contributions here.]...

## Papers

### 🟢 Human-Centered Tools for Coping with Imperfect Algorithms...
**Cai, Carrie J et al.** · CHI 2019 · `empirical` · relevance: **high**
*Methodology:* mixed, usability, qualitative, quantitative
```

---

## LLM backends

```bash
export ANTHROPIC_API_KEY=your_key
export GOOGLE_API_KEY=your_key
export OPENAI_API_KEY=your_key
```

Supported models:
- `anthropic/claude-opus-4-7`
- `gemini/gemini-3.1-pro-preview`
- `openai/gpt-5.5`

---

## Limitations

`lit-review-assistant` is a parsing and classification tool — it does not access external databases (Semantic Scholar, ACM DL, arXiv). You must supply the references. Relevance scoring uses keyword overlap and is an approximation; LLM enrichment improves precision but requires an API key.

**This tool does not replace deep reading.** The structured output it generates is a scaffold for review, not a substitute for engaging with the papers directly.

---

## Part of the CPR Ecosystem

`lit-review-assistant` is Tool #40 — the final tool in the [CPR Orbital series](https://kgkazakos.github.io).

Pairs well with:
- [**stakeholder-brief-writer**](https://github.com/kgkazakos/stakeholder-brief-writer) (#39) — compress the reviewed literature into a one-page brief
- [**evidence-chain**](https://github.com/kgkazakos/evidence-chain) (#23) — track which papers support which claims
- [**uxr-bench**](https://github.com/kgkazakos/uxr-bench) (#15) — benchmark LLM performance on the kind of tasks this tool performs
- [**insight-differ**](https://github.com/kgkazakos/insight-differ) (#05) — surface contradictions across multiple papers before synthesising

Part of [Computational Product Research](https://kgkazakos.github.io) — an independent discipline for AI-native product research infrastructure.

---

## License

MIT © Kostas Kazakos

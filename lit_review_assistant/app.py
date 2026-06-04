"""Streamlit UI for lit-review-assistant."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from lit_review_assistant.engine import ReviewConfig, parse_bibtex, parse_plain_list
from lit_review_assistant.export import to_bibtex_scaffold, to_csv, to_json, to_markdown
from lit_review_assistant.llm import DEFAULT_MODELS, enrich_review
from lit_review_assistant.models import RelevanceLevel

st.set_page_config(
    page_title="lit-review-assistant · CPR Orbital #40",
    page_icon="📚",
    layout="wide",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&display=swap');
html, body, [class*="css"] { font-family: 'DM Mono', monospace !important; }

section[data-testid="stSidebar"] {
    background: #0e0e0e !important;
    color: #e8e4dc !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
section[data-testid="stSidebar"] * { color: #e8e4dc !important; }
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #d94f2a !important;
    font-size: 11px !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.main .block-container {
    background: #f7f4ee !important;
    padding: 1.5rem 2rem !important;
}
.paper-card {
    background: #fff;
    border: 0.5px solid #e0dbd0;
    border-left: 3px solid #d94f2a;
    border-radius: 6px;
    padding: 11px 14px;
    margin-bottom: 9px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
}
.paper-card.rel-high { border-left-color: #0f6e56; }
.paper-card.rel-medium { border-left-color: #854f0b; }
.paper-card.rel-low { border-left-color: #993c1d; }
.badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 10px;
    font-family: 'DM Mono', monospace;
    margin-right: 4px;
}
.badge-high { background: #e1f5ee; color: #0f6e56; border: 0.5px solid #a3d9c4; }
.badge-medium { background: #faeeda; color: #854f0b; border: 0.5px solid #f5c77a; }
.badge-low { background: #fde8e4; color: #993c1d; border: 0.5px solid #f5b4a8; }
.badge-type { background: #f5f5f5; color: #555; border: 0.5px solid #ddd; }
.badge-venue { background: #e6f1fb; color: #185fa5; border: 0.5px solid #b5d4f4; }
.meta-line { font-size: 10px; color: #999; margin-top: 3px; }
.synthesis-box {
    background: #fff;
    border: 0.5px solid #e0dbd0;
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 12px;
    line-height: 1.65;
    margin-bottom: 14px;
}
.gap-item {
    background: #fff8f6;
    border-left: 2px solid #d94f2a;
    padding: 6px 10px;
    margin-bottom: 5px;
    font-size: 11px;
    border-radius: 0 4px 4px 0;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### CPR Orbital")
    st.markdown("**#40** lit-review-assistant")
    st.markdown("---")
    st.markdown("### Settings")
    llm_on = st.toggle("LLM enrichment", value=True)
    summarise_papers = st.toggle("Per-paper summaries", value=True, disabled=not llm_on)
    model_choice = st.selectbox(
        "Model",
        DEFAULT_MODELS,
        index=1,
        disabled=not llm_on,
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("### Filter & sort")
    min_relevance = st.select_slider(
        "Min relevance",
        options=["low", "medium", "high"],
        value="low",
    )
    sort_by = st.radio("Sort by", ["relevance", "year", "venue"], horizontal=True)
    max_papers = st.slider("Max papers", 5, 100, 50)
    st.markdown("---")
    st.markdown("### Export")
    export_fmt = st.radio("Format", ["Markdown", "JSON", "CSV", "BibTeX"], index=0)
    st.markdown("---")
    st.markdown(
        '<span style="font-size:10px;color:#555">Tool 40 of 40 · CPR Orbital<br>kgkazakos.github.io</span>',
        unsafe_allow_html=True,
    )

# ── MAIN ───────────────────────────────────────────────────────────────────
st.markdown("## lit-review-assistant")
st.markdown(
    '<span style="font-size:12px;color:#888">CPR Orbital #40 · HCI & AI literature review scaffolding</span>',
    unsafe_allow_html=True,
)

col_input, col_output = st.columns([1, 1], gap="large")

with col_input:
    st.markdown("**Research Topic**")
    topic = st.text_input(
        "Topic",
        placeholder="e.g. LLMs as synthetic research participants in UX studies",
        label_visibility="collapsed",
    )
    st.markdown("**References**")
    input_fmt = st.radio("Input format", ["BibTeX", "Plain list"], horizontal=True)
    refs_text = st.text_area(
        "Paste references (BibTeX or numbered plain list)",
        height=280,
        placeholder="@inproceedings{Amershi2019Software,\n  title={Software Engineering for Machine Learning},\n  author={Amershi, Saleema and others},\n  year={2019},\n  booktitle={ICSE}\n}",
        label_visibility="collapsed",
    )
    run_btn = st.button("Analyse Literature", type="primary", use_container_width=True)

with col_output:
    if run_btn and refs_text.strip() and topic.strip():
        rel_map = {
            "low": RelevanceLevel.LOW,
            "medium": RelevanceLevel.MEDIUM,
            "high": RelevanceLevel.HIGH,
        }
        config = ReviewConfig(
            min_relevance=rel_map[min_relevance],
            max_papers=max_papers,
            sort_by=sort_by,
        )
        with st.spinner("Parsing references…"):
            if input_fmt == "BibTeX":
                lit_review = parse_bibtex(refs_text, topic, config)
            else:
                lit_review = parse_plain_list(refs_text, topic, config)

        if llm_on:
            with st.spinner(f"Enriching via {model_choice}…"):
                lit_review = enrich_review(
                    lit_review,
                    model=model_choice,
                    llm_enabled=True,
                    summarise_papers=summarise_papers,
                )

        st.session_state["lit_review"] = lit_review

    if "lit_review" in st.session_state:
        rv = st.session_state["lit_review"]

        st.markdown(f"**{rv.topic}**")
        st.markdown(
            f'<div class="meta-line">'
            f'{rv.total_papers} papers · {rv.year_range[0]}–{rv.year_range[1]} · '
            + " · ".join(f"{v} ({n})" for v, n in sorted(rv.venue_distribution.items(), key=lambda x: -x[1])[:4])
            + "</div>",
            unsafe_allow_html=True,
        )

        if rv.synthesis:
            st.markdown(
                f'<div class="synthesis-box">{rv.synthesis}</div>',
                unsafe_allow_html=True,
            )

        if rv.research_gaps:
            st.markdown("**Research Gaps**")
            for g in rv.research_gaps:
                st.markdown(f'<div class="gap-item">· {g}</div>', unsafe_allow_html=True)
            st.markdown("")

        if rv.methodological_trends:
            st.markdown("**Methodological Trends**")
            for t in rv.methodological_trends:
                st.markdown(f"- {t}")

        st.divider()
        st.markdown(f"**{len(rv.papers)} Papers**")

        for p in rv.papers:
            rel_cls = f"rel-{p.relevance.value}"
            author_str = ", ".join(p.authors[:2]) + (" et al." if len(p.authors) > 2 else "")
            summary_html = f'<div style="color:#444;margin-top:5px;font-size:11px;line-height:1.5">{p.llm_summary}</div>' if p.llm_summary else ""
            contrib_html = f'<div class="meta-line">↳ {p.key_contribution}</div>' if p.key_contribution else ""
            st.markdown(
                f"""<div class="paper-card {rel_cls}">
<span style="font-weight:600">{p.title}</span>
<div style="margin-top:4px">
<span class="badge badge-{p.relevance.value}">{p.relevance.value}</span>
<span class="badge badge-venue">{p.venue}</span>
<span class="badge badge-type">{p.paper_type.value}</span>
<span style="font-size:10px;color:#999">{author_str} · {p.year}</span>
</div>
{summary_html}
{contrib_html}
</div>""",
                unsafe_allow_html=True,
            )

        st.divider()
        enrichment_note = f"✓ LLM ({rv.llm_model})" if rv.llm_enriched else "rule-based"
        st.caption(f"{enrichment_note}")

        if export_fmt == "Markdown":
            st.download_button(
                "Download Review (.md)",
                to_markdown(rv),
                file_name="lit_review.md",
                mime="text/markdown",
            )
        elif export_fmt == "JSON":
            st.download_button(
                "Download Review (.json)",
                to_json(rv),
                file_name="lit_review.json",
                mime="application/json",
            )
        elif export_fmt == "CSV":
            st.download_button(
                "Download Table (.csv)",
                to_csv(rv),
                file_name="lit_review.csv",
                mime="text/csv",
            )
        else:
            st.download_button(
                "Download BibTeX (.bib)",
                to_bibtex_scaffold(rv),
                file_name="lit_review_scaffold.bib",
                mime="text/plain",
            )
    elif run_btn:
        st.warning("Paste references and enter a topic first.")

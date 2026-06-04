"""Click CLI for lit-review-assistant."""

from __future__ import annotations

from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .engine import ReviewConfig, parse_bibtex, parse_plain_list
from .export import to_bibtex_scaffold, to_csv, to_json, to_markdown
from .llm import DEFAULT_MODELS, enrich_review
from .models import RelevanceLevel

console = Console()

_RELEVANCE_MAP = {"high": RelevanceLevel.HIGH, "medium": RelevanceLevel.MEDIUM, "low": RelevanceLevel.LOW}


@click.group()
@click.version_option(package_name="lit-review-assistant")
def cli():
    """lit-review-assistant — structured literature reviews for HCI & AI research.

    Part of the CPR Orbital series · kgkazakos.github.io
    """


@cli.command()
@click.argument("references", type=click.Path(exists=True))
@click.option("--topic", "-t", required=True, help="Research topic for relevance scoring.")
@click.option("--output", "-o", default=".", help="Output directory.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["markdown", "json", "csv", "bibtex", "all"]),
    default="markdown",
    show_default=True,
)
@click.option(
    "--input-format",
    "input_fmt",
    type=click.Choice(["bibtex", "plain"]),
    default="bibtex",
    show_default=True,
)
@click.option(
    "--min-relevance",
    type=click.Choice(["high", "medium", "low"]),
    default="low",
    show_default=True,
)
@click.option("--max-papers", default=50, show_default=True)
@click.option(
    "--sort-by",
    type=click.Choice(["relevance", "year", "venue"]),
    default="relevance",
    show_default=True,
)
@click.option("--model", default=DEFAULT_MODELS[0], show_default=True)
@click.option("--no-llm", is_flag=True, help="Disable LLM enrichment.")
@click.option("--no-paper-summaries", is_flag=True, help="Skip per-paper LLM summaries.")
def review(references, topic, output, fmt, input_fmt, min_relevance, max_papers, sort_by, model, no_llm, no_paper_summaries):
    """Generate a structured literature review from REFERENCES file."""
    text = Path(references).read_text(encoding="utf-8")
    config = ReviewConfig(
        min_relevance=_RELEVANCE_MAP[min_relevance],
        max_papers=max_papers,
        sort_by=sort_by,
    )

    with console.status("[bold]Parsing references…"):
        if input_fmt == "bibtex":
            lit_review = parse_bibtex(text, topic, config)
        else:
            lit_review = parse_plain_list(text, topic, config)

    if not no_llm:
        with console.status(f"[bold]Enriching with {model}…"):
            lit_review = enrich_review(
                lit_review,
                model=model,
                llm_enabled=True,
                summarise_papers=not no_paper_summaries,
            )

    # Display
    console.print(
        Panel(
            f"[bold]{lit_review.topic}[/bold]\n"
            f"[dim]{lit_review.total_papers} papers · "
            f"{lit_review.year_range[0]}–{lit_review.year_range[1]}[/dim]",
            title="[bold orange1]lit-review-assistant[/bold orange1]",
            border_style="orange1",
        )
    )

    if lit_review.synthesis:
        console.print(Panel(lit_review.synthesis, title="Synthesis", border_style="dim"))

    # Papers table
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    t.add_column("Rel", width=6)
    t.add_column("Year", width=6)
    t.add_column("Venue", width=8)
    t.add_column("Title")
    t.add_column("Type", width=10)
    rel_colours = {"high": "green", "medium": "yellow", "low": "red"}
    for p in lit_review.papers[:15]:
        col = rel_colours.get(p.relevance.value, "white")
        t.add_row(
            f"[{col}]{p.relevance.value}[/{col}]",
            str(p.year),
            p.venue[:8],
            p.title[:60] + ("…" if len(p.title) > 60 else ""),
            p.paper_type.value[:10],
        )
    if len(lit_review.papers) > 15:
        t.add_row("…", "", "", f"…and {len(lit_review.papers) - 15} more", "")
    console.print(t)

    if lit_review.research_gaps:
        console.print("[bold]Research gaps:[/bold]")
        for g in lit_review.research_gaps:
            console.print(f"  · {g}")

    # Write output
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(references).stem

    if fmt in ("markdown", "all"):
        p_ = out_dir / f"{stem}_review.md"
        to_markdown(lit_review, p_)
        console.print(f"[green]✓[/green] Markdown → {p_}")
    if fmt in ("json", "all"):
        p_ = out_dir / f"{stem}_review.json"
        to_json(lit_review, p_)
        console.print(f"[green]✓[/green] JSON → {p_}")
    if fmt in ("csv", "all"):
        p_ = out_dir / f"{stem}_review.csv"
        to_csv(lit_review, p_)
        console.print(f"[green]✓[/green] CSV → {p_}")
    if fmt in ("bibtex", "all"):
        p_ = out_dir / f"{stem}_scaffold.bib"
        to_bibtex_scaffold(lit_review, p_)
        console.print(f"[green]✓[/green] BibTeX scaffold → {p_}")

    enriched = f"[green]✓ LLM ({lit_review.llm_model})[/green]" if lit_review.llm_enriched else "[dim]rule-based[/dim]"
    console.print(f"\nEnrichment: {enriched}")


if __name__ == "__main__":
    cli()

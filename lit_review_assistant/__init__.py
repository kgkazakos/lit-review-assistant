"""lit-review-assistant — CPR Orbital Tool #40.

Summarises relevant HCI and AI papers for a given research topic
with citation scaffolding.
"""

__version__ = "0.1.0"

from .engine import ReviewConfig, parse_bibtex, parse_plain_list
from .export import to_bibtex_scaffold, to_csv, to_json, to_markdown
from .models import (
    LiteratureReview,
    Paper,
    PaperType,
    RelevanceLevel,
    Venue,
)

__all__ = [
    "parse_bibtex",
    "parse_plain_list",
    "ReviewConfig",
    "to_json",
    "to_markdown",
    "to_csv",
    "to_bibtex_scaffold",
    "LiteratureReview",
    "Paper",
    "PaperType",
    "RelevanceLevel",
    "Venue",
]

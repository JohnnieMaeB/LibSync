"""Formats a Crossref bibliographic record into a real citation via
citeproc-py — the same CSL 1.0.1 processor family Zotero uses — against a
real style file from `citeproc-py-styles` (the actual citationstyles.org
CSL repo). A citation is either right per the style spec or the style file
is missing; never "plausible-sounding" the way asking a model to recall
citation-formatting rules from memory would be.
"""

from citeproc import Citation, CitationItem, CitationStylesBibliography, CitationStylesStyle, formatter
from citeproc.source.json import CiteProcJSON

# Public style name -> citeproc-py-styles CSL filename (verified against
# `citeproc_styles.get_all_styles()` — these are real citationstyles.org
# filenames, not the style's common name; e.g. MLA's file is named
# "modern-language-association", not "mla").
STYLE_FILES = {
    "apa": "apa",
    "mla": "modern-language-association",
    "chicago": "chicago-author-date",
}

# Crossref `type` -> CSL-JSON `type`. Falls back to "article-journal" for
# anything unmapped, since journal articles are what this tool is asked
# about overwhelmingly often.
_CROSSREF_TYPE_TO_CSL = {
    "journal-article": "article-journal",
    "proceedings-article": "paper-conference",
    "book-chapter": "chapter",
    "book": "book",
    "monograph": "book",
    "report": "report",
    "posted-content": "manuscript",
    "dataset": "dataset",
}


def crossref_to_csl_json(work: dict) -> dict:
    """Map a raw Crossref work object into a CSL-JSON item.

    Optional fields are omitted entirely (not set to `None`) when absent —
    citeproc-py renders a present-but-`None` field literally (e.g. a missing
    issue number prints as the literal text "(None)") instead of treating it
    as unset, so a key must be missing, not null.
    """
    titles = work.get("title") or []
    container_titles = work.get("container-title") or []

    item = {
        "id": work.get("DOI") or "item-1",
        "type": _CROSSREF_TYPE_TO_CSL.get(work.get("type"), "article-journal"),
        "title": titles[0] if titles else "Untitled",
        "author": [
            {"given": author.get("given"), "family": author["family"]}
            for author in work.get("author", [])
            if author.get("family")
        ],
    }
    if work.get("issued"):
        item["issued"] = work["issued"]
    if container_titles:
        item["container-title"] = container_titles[0]
    for field in ("volume", "issue", "page", "publisher", "DOI"):
        if work.get(field):
            item[field] = work[field]
    return item


def format_citation(work: dict, style: str) -> str:
    """Format a Crossref work object as a citation string in the given
    style (see `STYLE_FILES` for supported values).

    Raises:
        KeyError: If `style` isn't a supported style.
    """
    style_file = STYLE_FILES[style]
    csl_item = crossref_to_csl_json(work)
    source = CiteProcJSON([csl_item])
    csl_style = CitationStylesStyle(style_file, validate=False)
    bibliography = CitationStylesBibliography(csl_style, source, formatter.plain)
    bibliography.register(Citation([CitationItem(csl_item["id"])]))
    return str(bibliography.bibliography()[0])

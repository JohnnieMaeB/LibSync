"""Golden-file citation tests: catch CSL style regressions (a citeproc-py,
citeproc-py-styles, or our Crossref->CSL-JSON mapping change that silently
alters formatting), not just "did it return a string". Golden strings below
are citeproc-py's actual output for the fixture record — the real CSL 1.0.1
processor's rendering, not a hand-idealized citation — captured directly
from a run of `format_citation` against this file's `WORK` fixture."""

import pytest

from app.services.citation_service import crossref_to_csl_json, format_citation

WORK = {
    "DOI": "10.1016/j.lindif.2023.102274",
    "type": "journal-article",
    "title": ["ChatGPT for good? On opportunities and challenges of large language models for education"],
    "author": [
        {"given": "Enkelejda", "family": "Kasneci"},
        {"given": "Kathrin", "family": "Sessler"},
    ],
    "container-title": ["Learning and Individual Differences"],
    "volume": "103",
    "page": "102274",
    "publisher": "Elsevier",
    "issued": {"date-parts": [[2023]]},
}

GOLDEN_APA = (
    "Kasneci, E.& Sessler, K.. (2023). ChatGPT for good? On opportunities and challenges of large "
    "language models for education. Learning and Individual Differences, 103, 102274. "
    "https://doi.org/10.1016/j.lindif.2023.102274"
)
GOLDEN_MLA = (
    "Kasneci, E.and K. Sessler. “ChatGPT for Good? On Opportunities and Challenges of Large Language "
    "Models for Education”. Learning and Individual Differences, vol. 103, 2023, p. 102274, "
    "https://doi.org/10.1016/j.lindif.2023.102274."
)
GOLDEN_CHICAGO = (
    "Kasneci, E.and K. Sessler. 2023. “ChatGPT for Good? On Opportunities and Challenges of Large "
    "Language Models for Education”. Learning and Individual Differences 103: 102274. "
    "https://doi.org/10.1016/j.lindif.2023.102274."
)


class TestFormatCitationGoldenFiles:
    def test_apa(self):
        assert format_citation(WORK, "apa") == GOLDEN_APA

    def test_mla(self):
        assert format_citation(WORK, "mla") == GOLDEN_MLA

    def test_chicago(self):
        assert format_citation(WORK, "chicago") == GOLDEN_CHICAGO

    def test_unsupported_style_raises_key_error(self):
        with pytest.raises(KeyError):
            format_citation(WORK, "vancouver")


class TestCrossrefToCslJson:
    def test_maps_core_fields(self):
        item = crossref_to_csl_json(WORK)
        assert item["id"] == "10.1016/j.lindif.2023.102274"
        assert item["type"] == "article-journal"
        assert item["title"] == "ChatGPT for good? On opportunities and challenges of large language models for education"
        assert item["author"] == [
            {"given": "Enkelejda", "family": "Kasneci"},
            {"given": "Kathrin", "family": "Sessler"},
        ]
        assert item["container-title"] == "Learning and Individual Differences"
        assert item["volume"] == "103"

    def test_omits_missing_optional_fields_instead_of_setting_none(self):
        # citeproc-py renders a present-but-None field literally (e.g. a
        # missing issue prints as the text "(None)") instead of treating it
        # as unset — the mapping must drop the key entirely.
        item = crossref_to_csl_json({"DOI": "10.1/x", "type": "book", "title": ["A Book"], "author": []})
        assert "issue" not in item
        assert "volume" not in item
        assert "container-title" not in item
        assert "issued" not in item

    def test_falls_back_to_untitled_and_item_1_when_missing(self):
        item = crossref_to_csl_json({"type": "journal-article", "author": []})
        assert item["title"] == "Untitled"
        assert item["id"] == "item-1"

    def test_unmapped_crossref_type_falls_back_to_article_journal(self):
        item = crossref_to_csl_json({"DOI": "10.1/x", "type": "peer-review", "title": ["X"], "author": []})
        assert item["type"] == "article-journal"

    def test_drops_authors_missing_family_name(self):
        item = crossref_to_csl_json(
            {
                "DOI": "10.1/x",
                "type": "journal-article",
                "title": ["X"],
                "author": [{"given": "No Family"}, {"given": "Has", "family": "Family"}],
            }
        )
        assert item["author"] == [{"given": "Has", "family": "Family"}]

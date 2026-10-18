"""BookResult's Pydantic validator grounds structured book answers in the
catalog's own results (moved from an output validator, for consistency with
Pydantic validation everywhere structured output exists)."""

import pytest
from pydantic import ValidationError

from app.schemas import CATALOG_BOOKS_CONTEXT, BookResult

CATALOG = {
    "project hail mary": {
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "first_publish_year": 2021,
        "cover_url": "https://covers.example/1.jpg",
        "url": "https://openlibrary.org/works/OL1W",
        "availability": "lendable",
    }
}

MODEL_ANSWER = {
    "intro": "Found it:",
    "books": [{"title": "Project Hail Mary", "author": "A. Weir", "availability": "available"}],
}


def test_facts_come_from_the_catalog_not_the_model():
    result = BookResult.model_validate(MODEL_ANSWER, context={CATALOG_BOOKS_CONTEXT: CATALOG})
    book = result.books[0]
    assert (book.availability, book.author, book.url) == ("lendable", "Andy Weir", "https://openlibrary.org/works/OL1W")
    assert result.intro == "Found it:"  # the model's own words stay


def test_a_book_the_catalog_never_returned_fails_validation():
    invented = {"intro": "x", "books": [{"title": "Not A Real Book", "author": "Nobody", "availability": "available"}]}
    with pytest.raises(ValidationError, match="was not in the search_catalog or recommend_books results"):
        BookResult.model_validate(invented, context={CATALOG_BOOKS_CONTEXT: CATALOG})


@pytest.mark.parametrize("context", [None, {}, {"other": 1}])
def test_without_the_agents_context_it_is_a_plain_model(context):
    result = BookResult.model_validate(MODEL_ANSWER, context=context)
    assert result.books[0].availability == "available"

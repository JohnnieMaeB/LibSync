"""Pydantic request/response models for the API."""

from pydantic import BaseModel, ValidationInfo, model_validator

# Key under which the agent passes the catalog's real results into Pydantic
# validation (pydantic-ai `validation_context`; see app/agent.py).
CATALOG_BOOKS_CONTEXT = "catalog_books"


class Book(BaseModel):
    title: str
    author: str
    first_publish_year: int | None = None
    cover_url: str | None = None
    url: str | None = None
    availability: str


class BookResult(BaseModel):
    """Structured chat output for book/catalog questions, so the frontend can
    render real cards from data instead of parsing prose."""

    intro: str
    books: list[Book]

    @model_validator(mode="after")
    def _ground_in_catalog(self, info: ValidationInfo) -> "BookResult":
        """When the agent validates its structured answer, every book must be
        one `search_catalog` returned, and its patron-facing facts
        (availability, year, author, links, cover) are taken from the catalog
        rather than from the model's restatement. A book the catalog never
        returned fails validation, which pydantic-ai turns into a retry.

        Without the agent's validation context (API responses, tests building
        a BookResult directly) this is a no-op."""
        context = info.context
        if not isinstance(context, dict) or CATALOG_BOOKS_CONTEXT not in context:
            return self
        seen: dict[str, dict] = context[CATALOG_BOOKS_CONTEXT]
        grounded = []
        for book in self.books:
            source = seen.get(book.title.casefold().strip())
            if source is None:
                raise ValueError(
                    f'"{book.title}" was not in the search_catalog results. List only books search_catalog '
                    "returned, with their titles exactly as returned, or answer in plain text."
                )
            grounded.append(Book(**{key: source.get(key) for key in Book.model_fields}))
        self.books = grounded
        return self


class ScholarlyWork(BaseModel):
    title: str
    authors: str
    year: int | None = None
    citation_count: int
    is_oa: bool
    doi: str | None = None
    abstract: str | None = None


class ResearchResult(BaseModel):
    """Structured chat output for research questions, so the frontend can
    render a real result-list card from data instead of parsing prose."""

    intro: str
    works: list[ScholarlyWork]


class Citation(BaseModel):
    """Structured chat output for citation requests, so the frontend can
    render a real citation card (formatted text, copy button, style
    switcher) instead of parsing prose."""

    formatted: str
    style: str
    doi: str | None = None
    available_styles: list[str]


class QueryRequest(BaseModel):
    text: str | None = None
    topK: int | None = None


class WidgetRegisterRequest(BaseModel):
    library_id: str | None = None

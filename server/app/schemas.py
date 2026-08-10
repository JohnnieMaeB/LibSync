"""Pydantic request/response models for the API."""

from pydantic import BaseModel


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

"""Pydantic request/response models for the API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str | None = None
    session_id: str | None = None


class Book(BaseModel):
    title: str
    author: str
    first_publish_year: int | None = None
    cover_url: str | None = None
    availability: str


class BookResult(BaseModel):
    """Structured chat output for book/catalog questions, so the frontend can
    render real cards from data instead of parsing prose."""

    intro: str
    books: list[Book]


class ChatResponse(BaseModel):
    reply: str | BookResult
    session_id: str


class ErrorResponse(BaseModel):
    error: str


class QueryRequest(BaseModel):
    text: str | None = None
    topK: int | None = None


class QueryMatch(BaseModel):
    id: str
    score: float | None = None
    text: str | None = None
    category: str | None = None


class QueryResponse(BaseModel):
    matches: list[QueryMatch]

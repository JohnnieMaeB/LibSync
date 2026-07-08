"""Pydantic request/response models for the API."""

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str | None = None


class ChatResponse(BaseModel):
    reply: str


class ErrorResponse(BaseModel):
    error: str


class QueryRequest(BaseModel):
    vector: list[float] | None = None
    topK: int | None = None


class QueryMatch(BaseModel):
    id: str
    score: float | None = None
    values: list[float] | None = None
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    matches: list[QueryMatch]

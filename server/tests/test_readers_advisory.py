"""Readers' advisory (NEXT_FEATURES.md P1.5): recommendations come from
Open Library's subjects and, when a library catalog is connected, only from
what that catalog holds. The model never chooses the titles."""

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import agent as agent_module
from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.library_config import LibraryConfig
from app.schemas import BookResult
from app.services import catalog, readers_advisory
from app.services.catalog import CatalogSearch

SEED = {
    "key": "/works/OL1W",
    "title": "Project Hail Mary",
    "author_name": ["Andy Weir"],
    "subject": ["nyt:hardcover-fiction=2021", "Fiction", "hard science-fiction", "Astronauts", "FICTION / Thrillers"],
}


def _doc(title: str, author: str = "Someone", key: str = "/works/OL2W") -> dict:
    return {"key": key, "title": title, "author_name": [author], "first_publish_year": 2001, "ebook_access": "borrowable"}


CANDIDATES = [
    _doc("Project Hail Mary"),  # the seed itself
    _doc("Summary of Project Hail Mary", "Quick Reads"),  # a knock-off
    _doc("Rendezvous with Rama", "Arthur C. Clarke", "/works/OL3W"),
    _doc("The Martian", "Andy Weir", "/works/OL4W"),
    _doc("Seveneves", "Neal Stephenson", "/works/OL5W"),
]


def _client(queries: list[str]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("q", "")
        queries.append(query)
        docs = CANDIDATES if query.startswith("subject:") else [SEED]
        return httpx.Response(200, json={"docs": docs})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_only_specific_subjects_are_used():
    assert readers_advisory.useful_subjects(SEED["subject"]) == ["hard science-fiction", "astronauts"]


async def test_read_alikes_skip_the_seed_and_its_knock_offs():
    queries: list[str] = []
    async with _client(queries) as client:
        books, source, subjects = await readers_advisory.recommend(client, None, like="Project Hail Mary")
    assert [b["title"] for b in books] == ["Rendezvous with Rama", "The Martian", "Seveneves"]
    assert source == "Open Library" and subjects == ["hard science-fiction", "astronauts"]
    # Closest match first, kept on the fiction shelf because the seed is fiction.
    assert queries[1] == 'subject:"hard science-fiction" subject:"astronauts" subject:"fiction"'


async def test_audience_narrows_every_subject_search():
    queries: list[str] = []
    async with _client(queries) as client:
        await readers_advisory.recommend(client, None, about="dragons", audience="children")
    assert queries[0] == 'subject:"dragons" subject:"juvenile fiction"'


async def test_with_a_library_catalog_only_held_books_are_recommended(monkeypatch):
    held = {"Seveneves": {"title": "Seveneves: a novel", "author": "Neal Stephenson", "availability": "available"}}

    async def library_search(client, config, query, limit=3):
        return CatalogSearch([book for title, book in held.items() if query.startswith(title)], "the library's catalog")

    monkeypatch.setattr(catalog, "search_catalog", library_search)
    config = LibraryConfig(id="lib", name="Lib", catalog_driver="koha")
    async with _client([]) as client:
        books, source, _ = await readers_advisory.recommend(client, config, like="Project Hail Mary")
    assert books == [held["Seveneves"]] and source == "the library's catalog"


async def test_a_silent_library_catalog_is_not_passed_off_as_the_library(monkeypatch):
    async def fell_back(client, config, query, limit=3):
        return CatalogSearch([], "Open Library", fell_back=True)

    monkeypatch.setattr(catalog, "search_catalog", fell_back)
    config = LibraryConfig(id="lib", name="Lib", catalog_driver="koha")
    async with _client([]) as client:
        books, source, _ = await readers_advisory.recommend(client, config, like="Project Hail Mary")
    assert books and "didn't respond" in source


async def test_recommended_books_ground_the_structured_answer(monkeypatch):
    book = {"title": "Seveneves", "author": "Neal Stephenson", "first_publish_year": 2015, "cover_url": None,
            "url": None, "availability": "available"}

    async def recommend(client, config, like=None, about=None, audience=None):
        return [book], "Open Library", ["hard science-fiction"]

    monkeypatch.setattr(readers_advisory, "recommend", recommend)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not any(isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", [])):
            return ModelResponse(parts=[ToolCallPart("recommend_books", {"like": "Project Hail Mary"})])
        output = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(output, {
            "intro": "You might like:",
            "books": [{"title": "Seveneves", "author": "N. Stephenson", "availability": "on the shelf"}],
        })])

    with chat_agent.override(model=FunctionModel(respond)):
        result = await chat_agent.run("Books like Project Hail Mary?", deps=LibSyncDeps(http_client=None))
    assert isinstance(result.output, BookResult)
    assert result.output.books[0].availability == "available"  # the catalog's fact, not the model's


def test_the_tool_is_a_switchable_group():
    assert agent_module.TOOL_GROUPS["recommendations"] == "recommend_books"


@pytest.mark.parametrize("title", ["SparkNotes: The Martian", "Study Guide for Dune", "Analysis of Beloved"])
def test_derivatives_are_recognized(title):
    assert readers_advisory._DERIVATIVE.search(title)


def test_genre_headings_come_first():
    subjects = ["African American History", "Ohio", "History", "19th century", "Fiction", "Reading Level-Grade 9",
                "Historical fiction", "Slaves, fiction"]
    assert readers_advisory.useful_subjects(subjects) == ["historical fiction", "slaves, fiction", "african american history", "ohio"]


async def test_a_teen_seed_gets_teen_read_alikes():
    teen_seed = {**SEED, "subject": ["Dystopian fiction", "Young adult fiction", "Fiction"]}
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("q", "")
        queries.append(query)
        return httpx.Response(200, json={"docs": CANDIDATES if query.startswith("subject:") else [teen_seed]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await readers_advisory.recommend(client, None, like="The Hunger Games")
    assert queries[1] == 'subject:"dystopian fiction" subject:"young adult fiction"'


@pytest.mark.parametrize(
    ("audience", "subject"),
    [
        ("children", "juvenile fiction"),
        ("children 10", "juvenile fiction"),  # what the model actually sent
        ("kids", "juvenile fiction"),
        ("age 15", "young adult fiction"),
        ("YA", "young adult fiction"),
        ("adult", None),
        ("Maya's book club", None),  # "ya" only as a word
        (None, None),
    ],
)
def test_audience_is_read_loosely(audience, subject):
    assert readers_advisory.audience_subject(audience) == subject

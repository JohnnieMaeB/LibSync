"""Readers' advisory grounded in the collection (NEXT_FEATURES.md P1.5).

"Books like Project Hail Mary", "something for a 10-year-old who loves
dragons". NoveList's critique of chatbots for readers' advisory is that they
recommend books the library doesn't have, or that don't exist. Here the model
never picks the titles:

1. Subjects come from Open Library: the seed book's own subject headings
   (generic and marketing tags dropped), or the patron's topic.
2. Candidates are Open Library works sharing those subjects, best rated
   first, without the seed book itself or summaries/study guides of it.
3. When the library has its own catalog connected, a candidate is kept only
   if that catalog finds it, with the library's own availability. Otherwise
   the results are labeled as coming from Open Library.

Every returned book goes to the patron as a card with the catalog's facts,
and the structured-answer validator (schemas.BookResult) rejects any title
this tool or `search_catalog` didn't return.
"""

import re

import httpx

from app.library_config import LibraryConfig
from app.services import catalog
from app.services.open_library_service import COVER_URL, SEARCH_URL, USER_AGENT, WORK_URL

# Subject headings that say nothing about what a book is like.
_GENERIC_SUBJECTS = re.compile(
    r"^(fiction|fiction, general|general|novel|novels|literature|english literature|american literature|"
    r"accessible book|protected daisy|in library|large type books|lending library|open library staff picks|"
    r"romans, nouvelles|translations into english|juvenile literature|history|social life and customs|"
    r"juvenile fiction|young adult fiction|juvenile works|young adult works|modern literature|roman)$|"
    r"reading level|fictional works by|"
    r":|bestseller|reviewed|award|^long now|\bcentury\b",
    re.IGNORECASE,
)
# Knock-offs that share a famous book's subjects: summaries, study guides.
_DERIVATIVE = re.compile(
    r"\b(summary|summaries|study guide|analysis of|workbook|sparknotes|cliffsnotes|book review|"
    r"discussion questions|trivia)\b",
    re.IGNORECASE,
)
AUDIENCE_SUBJECTS = {"children": "juvenile fiction", "teen": "young adult fiction"}
_CHILD_WORDS = re.compile(r"child|kid|juvenile|middle.grade|picture book|elementary", re.IGNORECASE)
_TEEN_WORDS = re.compile(r"teen|young adult|\bya\b|high school", re.IGNORECASE)


def audience_subject(audience: str | None) -> str | None:
    """The Open Library subject for an audience, read loosely: models write
    "children", "kids", "children 10" or "age 15". Ages up to 12 are
    children's books, 13 to 17 teen."""
    if not audience:
        return None
    age = re.search(r"\d+", audience)
    if age and int(age.group()) <= 12 or _CHILD_WORDS.search(audience):
        return AUDIENCE_SUBJECTS["children"]
    if age and int(age.group()) <= 17 or _TEEN_WORDS.search(audience):
        return AUDIENCE_SUBJECTS["teen"]
    return None


_FIELDS = "key,title,author_name,first_publish_year,cover_i,ebook_access,subject,ratings_count"
CANDIDATES = 10  # checked against a library catalog at most this many


def _fold(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def useful_subjects(subjects: list[str], limit: int = 4) -> list[str]:
    """The seed's specific subjects: generic, marketing and BISAC-style
    ("FICTION / ...") headings dropped, headings that differ only in case or
    punctuation kept once, and genre headings ("Dystopian fiction",
    "Slaves, fiction") first, since they say most about what a novel is like.
    Otherwise Open Library's order."""
    kept: list[str] = []
    seen: set[str] = set()
    for subject in sorted(subjects, key=lambda s: "fiction" not in s.lower()):
        cleaned = subject.strip()
        if not cleaned or _GENERIC_SUBJECTS.search(cleaned) or "/" in cleaned or cleaned.isupper():
            continue
        folded = _fold(cleaned)
        if folded in seen:
            continue
        seen.add(folded)
        kept.append(cleaned.lower())
        if len(kept) == limit:
            break
    return kept


async def _search(client: httpx.AsyncClient, query: str, limit: int, sort: str | None = "rating") -> list[dict]:
    params = {"q": query, "fields": _FIELDS, "limit": str(limit)}
    if sort:
        params["sort"] = sort
    response = await client.get(SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=10.0)
    response.raise_for_status()
    return response.json().get("docs", [])


def _quoted(subject: str) -> str:
    return 'subject:"' + subject.replace('"', "") + '"'


def _as_book(doc: dict) -> dict:
    cover = doc.get("cover_i")
    access = doc.get("ebook_access")
    return {
        "title": doc.get("title", "Unknown title"),
        "author": ", ".join(doc.get("author_name", [])) or "Unknown author",
        "first_publish_year": doc.get("first_publish_year"),
        "cover_url": COVER_URL.format(cover_id=cover) if cover else None,
        "url": WORK_URL.format(key=doc["key"]) if doc.get("key") else None,
        "availability": access if access in ("public", "borrowable") else "not available online",
    }


async def candidates(
    client: httpx.AsyncClient, like: str | None, about: str | None, audience: str | None
) -> tuple[list[dict], list[str], dict | None]:
    """(candidate Open Library docs, the subjects used, the seed doc)."""
    seed = None
    subjects: list[str] = []
    seed_subjects: list[str] = []
    if like:
        found = await _search(client, like, 1, sort=None)
        if found:
            seed = found[0]
            seed_subjects = [subject.lower() for subject in seed.get("subject") or []]
            subjects = useful_subjects(seed.get("subject") or [])
    if about:
        subjects = [about.strip().lower(), *subjects]
    shelf = audience_subject(audience)
    # A read-alike stays in the seed's shelf: a novel's subjects alone
    # ("african american history") also match nonfiction, and a children's
    # or teen book's should match children's or teen books.
    if shelf is None:
        shelf = next((s for s in AUDIENCE_SUBJECTS.values() if s in seed_subjects), None)
    if shelf is None and any("fiction" in subject for subject in seed_subjects):
        shelf = "fiction"

    # Pairs of subjects first (closest matches), then single subjects.
    queries = [f"{_quoted(a)} {_quoted(b)}" for i, a in enumerate(subjects[:3]) for b in subjects[i + 1 : 3]]
    queries += [_quoted(subject) for subject in subjects[:2]]
    if not queries and about:
        queries = [about]
    if shelf:
        queries = [f"{query} {_quoted(shelf)}" for query in queries]

    seed_title = _fold(seed.get("title", "")) if seed else ""
    seen: set[str] = {seed_title} if seed_title else set()
    docs: list[dict] = []
    for query in queries:
        for doc in await _search(client, query, 12):
            title = _fold(doc.get("title", ""))
            if not title or title in seen or (seed_title and seed_title in title) or _DERIVATIVE.search(doc.get("title", "")):
                continue
            seen.add(title)
            docs.append(doc)
        if len(docs) >= CANDIDATES:
            break
    return docs[:CANDIDATES], subjects, seed


async def recommend(
    client: httpx.AsyncClient,
    config: LibraryConfig | None,
    like: str | None = None,
    about: str | None = None,
    audience: str | None = None,
    limit: int = 3,
) -> tuple[list[dict], str, list[str]]:
    """(books, where they came from, the subjects used). Books held by the
    library's own catalog when one is connected; Open Library otherwise."""
    docs, subjects, _seed = await candidates(client, like, about, audience)
    if config is None or config.catalog_driver == "openlibrary":
        return [_as_book(doc) for doc in docs[:limit]], "Open Library", subjects

    held: list[dict] = []
    for doc in docs:
        title = doc.get("title", "")
        author = (doc.get("author_name") or [""])[0]
        search = await catalog.search_catalog(client, config, f"{title} {author}".strip(), limit=3)
        if search.fell_back:
            # The library's catalog isn't answering: say so rather than
            # passing Open Library's books off as the library's.
            return [_as_book(d) for d in docs[:limit]], "Open Library (the library's catalog didn't respond)", subjects
        wanted = _fold(title)
        match = next(
            (b for b in search.results if _fold(b["title"]).startswith(wanted) or wanted.startswith(_fold(b["title"]))),
            None,
        )
        if match:
            held.append(match)
        if len(held) == limit:
            break
    return held, "the library's catalog", subjects

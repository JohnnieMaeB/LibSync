"""Turns a library's uploaded policy document into searchable chunks in its
own Pinecone namespace — Tier 8 Phase 31 (TIER8_PLAN.md §2.1, §2.2).

Only the extracted text chunks are kept (in Pinecone) plus a metadata row (in
Supabase); the original file is not stored. Re-uploading a document with the
same name replaces it.
"""

import io
import re
import uuid
from html.parser import HTMLParser

from pypdf import PdfReader

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_CHUNKS = 400
TARGET_CHUNK_CHARS = 700

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md", ".html", ".htm")


class DocumentError(ValueError):
    """A problem with the uploaded file that the staff member can fix."""


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template"}
    _BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "section", "article"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skipping += 1
        elif tag in self._BLOCK:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skipping:
            self._skipping -= 1
        elif tag in self._BLOCK:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self._skipping:
            self.parts.append(data)


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError("That file is larger than 5 MB. Split it or remove images and try again.")
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            raise DocumentError("That PDF couldn't be read. If it's a scan, export it as text first.") from error
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    elif name.endswith((".html", ".htm")):
        extractor = _TextExtractor()
        extractor.feed(data.decode("utf-8", errors="replace"))
        text = "".join(extractor.parts)
    else:
        raise DocumentError("Upload a PDF, text, Markdown or HTML file.")
    if not text.strip():
        raise DocumentError("No text was found in that file. If it's a scanned PDF, it needs text, not images.")
    return text


def chunk_text(text: str, target: int = TARGET_CHUNK_CHARS) -> list[str]:
    """Paragraph-aware chunks of about `target` characters: paragraphs are
    merged until the next would overflow, and oversized paragraphs are split
    at sentence boundaries, so a chunk never cuts a policy mid-sentence."""
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    pieces: list[str] = []
    for paragraph in filter(None, paragraphs):
        if len(paragraph) <= target:
            pieces.append(paragraph)
            continue
        sentence_chunk = ""
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if sentence_chunk and len(sentence_chunk) + len(sentence) + 1 > target:
                pieces.append(sentence_chunk)
                sentence_chunk = sentence
            else:
                sentence_chunk = f"{sentence_chunk} {sentence}".strip()
        if sentence_chunk:
            pieces.append(sentence_chunk)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > target:
            chunks.append(current)
            current = piece
        else:
            current = f"{current}\n\n{piece}".strip()
    if current:
        chunks.append(current)
    if len(chunks) > MAX_CHUNKS:
        raise DocumentError(f"That document is too long ({len(chunks)} sections; the limit is {MAX_CHUNKS}).")
    return chunks


def new_document_id() -> str:
    return uuid.uuid4().hex[:16]


def chunk_records(doc_id: str, doc_name: str, chunks: list[str]) -> list[dict]:
    """Pinecone integrated-embedding records. Ids share the `<doc_id>#` prefix so
    a document's chunks can be listed and deleted together."""
    return [
        {"_id": f"{doc_id}#{n}", "chunk_text": chunk, "category": "uploaded", "doc_id": doc_id, "doc_name": doc_name}
        for n, chunk in enumerate(chunks)
    ]

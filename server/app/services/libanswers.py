"""Springshare LibAnswers FAQ export — Tier 8 Phase 37T part 2
(TIER8_PLAN.md §2.7). Libraries already maintain FAQs in LibAnswers; syncing
them into the library's policy namespace means the assistant answers from
them without anyone re-uploading documents.

Authenticates with LibAnswers API client credentials (Admin → API), then
pages through the FAQs of one LibAnswers group (`iid`).

**Not yet verified against a live LibAnswers site**: written to the
LibAnswers 1.1 API (/api/1.1/oauth/token, /api/1.1/faqs) with tolerant
parsing, and covered by mocked tests.

integrations.libanswers: {"site": "yourlibrary.libanswers.com", "iid": "123", "client_id": "..."}
secret: library_secrets.libanswers_client_secret
"""

import httpx

from app.documents import _TextExtractor

MAX_FAQS = 500
PAGE_SIZE = 100


def _plain(html: str | None) -> str:
    extractor = _TextExtractor()
    extractor.feed(html or "")
    return " ".join("".join(extractor.parts).split())


async def fetch_faqs(client: httpx.AsyncClient, settings: dict, client_secret: str | None) -> list[dict]:
    site = (settings.get("site") or "").strip().removeprefix("https://").rstrip("/")
    client_id = settings.get("client_id")
    if not site or not client_id or not client_secret:
        raise ValueError("LibAnswers needs integrations.libanswers.site, client_id and the libanswers_client_secret")
    base = f"https://{site}/api/1.1"
    token_response = await client.post(
        f"{base}/oauth/token",
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        timeout=10.0,
    )
    token_response.raise_for_status()
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    faqs: list[dict] = []
    page = 1
    while len(faqs) < MAX_FAQS:
        params = {"limit": str(PAGE_SIZE), "page": str(page)}
        if settings.get("iid"):
            params["iid"] = str(settings["iid"])
        response = await client.get(f"{base}/faqs", params=params, headers=headers, timeout=15.0)
        response.raise_for_status()
        body = response.json()
        rows = body.get("data", {}).get("faqs") if isinstance(body, dict) else body
        rows = rows or []
        for row in rows:
            question = _plain(row.get("question"))
            answer = _plain(row.get("answer"))
            if question and answer:
                faqs.append({"question": question, "answer": answer, "url": row.get("url")})
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return faqs[:MAX_FAQS]


def faq_chunks(faqs: list[dict], max_chars: int = 1500) -> list[str]:
    """One chunk per FAQ (question and answer together, so retrieval never
    separates them), trimmed to a sane length."""
    return [f"Q: {faq['question']}\nA: {faq['answer']}"[:max_chars] for faq in faqs]

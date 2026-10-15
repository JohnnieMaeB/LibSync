"""Tier 8 Phase 31: document extraction, chunking, staff auth and the upload
routes (Supabase and Pinecone mocked; the Pinecone calls were live-tested
against a throwaway namespace)."""

import io

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import documents as docs
from app import library_config, staff_auth, tenants
from app.documents import DocumentError, chunk_records, chunk_text, extract_text
from app.routers import documents as documents_router
from app.staff_auth import StaffMember


def test_extracts_plain_text_and_markdown():
    assert "renewals" in extract_text("policies.md", b"# Lending\n\nThree renewals.").lower()


def test_extracts_html_without_scripts_or_styles():
    html = b"<html><style>p{}</style><script>alert(1)</script><h1>Fines</h1><p>$0.25 a day</p></html>"
    text = extract_text("page.html", html)
    assert "Fines" in text and "$0.25 a day" in text
    assert "alert" not in text and "p{}" not in text


def test_rejects_unsupported_empty_and_oversized_files():
    with pytest.raises(DocumentError, match="PDF, text"):
        extract_text("sheet.xlsx", b"data")
    with pytest.raises(DocumentError, match="No text"):
        extract_text("blank.txt", b"   \n ")
    with pytest.raises(DocumentError, match="5 MB"):
        extract_text("big.txt", b"x" * (docs.MAX_UPLOAD_BYTES + 1))


def test_blank_pdf_is_reported_as_having_no_text():
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)
    with pytest.raises(DocumentError, match="No text"):
        extract_text("scan.pdf", buffer.getvalue())


def test_chunks_keep_paragraphs_and_sentences_whole():
    text = "Short intro.\n\n" + " ".join(f"Sentence number {n} about fines." for n in range(40))
    chunks = chunk_text(text, target=200)
    assert all(len(c) <= 200 for c in chunks)
    assert all(c.rstrip().endswith(".") for c in chunks)
    assert chunks[0].startswith("Short intro.")


def test_too_many_chunks_is_rejected(monkeypatch):
    monkeypatch.setattr(docs, "MAX_CHUNKS", 2)
    with pytest.raises(DocumentError, match="too long"):
        chunk_text("a.\n\nb.\n\nc.", target=2)


def test_records_share_a_document_prefix():
    records = chunk_records("doc1", "fines.txt", ["one", "two"])
    assert [r["_id"] for r in records] == ["doc1#0", "doc1#1"]
    assert {r["doc_name"] for r in records} == {"fines.txt"}


# --- staff auth -------------------------------------------------------------


def _auth_app(handler, monkeypatch):
    for module in (library_config, staff_auth):
        monkeypatch.setattr(module, "SUPABASE_URL", "https://proj.supabase.co")
        monkeypatch.setattr(module, "SUPABASE_SECRET_KEY", "sb_secret_test")
    app = FastAPI()
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    @app.get("/check")
    async def check(request: Request, admin: bool = False):
        member = await staff_auth.require_staff(request, "springfield-pl", admin=admin)
        return {"role": member.role}

    return TestClient(app)


def _supabase(role: str | None):
    def handler(request: httpx.Request):
        if request.url.path == "/auth/v1/user":
            if request.headers.get("authorization") != "Bearer good-token":
                return httpx.Response(401)
            return httpx.Response(200, json={"id": "user-1", "email": "a@b.example"})
        assert request.url.params["user_id"] == "eq.user-1"
        return httpx.Response(200, json=[{"role": role}] if role else [])

    return handler


def test_staff_auth_requires_a_token(monkeypatch):
    assert _auth_app(_supabase("staff"), monkeypatch).get("/check").status_code == 401


def test_staff_auth_rejects_a_bad_token(monkeypatch):
    client = _auth_app(_supabase("staff"), monkeypatch)
    assert client.get("/check", headers={"Authorization": "Bearer stolen"}).status_code == 401


def test_staff_auth_rejects_non_members(monkeypatch):
    client = _auth_app(_supabase(None), monkeypatch)
    assert client.get("/check", headers={"Authorization": "Bearer good-token"}).status_code == 403


def test_staff_auth_admin_only(monkeypatch):
    client = _auth_app(_supabase("staff"), monkeypatch)
    headers = {"Authorization": "Bearer good-token"}
    assert client.get("/check", headers=headers).json() == {"role": "staff"}
    assert client.get("/check?admin=true", headers=headers).status_code == 403


def test_staff_auth_off_without_supabase():
    app = FastAPI()
    app.state.http_client = None

    @app.get("/check")
    async def check(request: Request):
        await staff_auth.require_staff(request, "springfield-pl")

    assert TestClient(app).get("/check").status_code == 503


# --- upload routes ----------------------------------------------------------


@pytest.fixture()
def fake_backends(monkeypatch):
    state = {"rows": [], "upserts": [], "deleted": [], "staff": True}

    async def fake_staff(request, library_id, admin=False):
        if not state["staff"]:
            raise HTTPException(status_code=403, detail="no")
        return StaffMember(user_id="user-1", email=None, role="staff")

    async def fake_rest(request, method, path, **kwargs):
        params = kwargs.get("params", {})
        if method == "GET":
            rows = [r for r in state["rows"] if f"eq.{r['library_id']}" == params["library_id"]]
            for key in ("name", "id"):
                if key in params:
                    rows = [r for r in rows if f"eq.{r[key]}" == params[key]]
            return httpx.Response(200, json=rows)
        if method == "POST":
            state["rows"].append(kwargs["json"])
        if method == "DELETE":
            state["rows"] = [r for r in state["rows"] if f"eq.{r['id']}" != params["id"]]
        return httpx.Response(204)

    def fake_delete(namespace, prefix):
        state["deleted"].append((namespace, prefix))
        return 1

    monkeypatch.setattr(documents_router, "require_staff", fake_staff)
    monkeypatch.setattr(documents_router, "_rest", fake_rest)
    monkeypatch.setattr(documents_router, "upsert_chunks", lambda ns, recs: state["upserts"].append((ns, recs)))
    monkeypatch.setattr(documents_router, "delete_by_prefix", fake_delete)
    return state


def _upload(client, name="fines.txt", body=b"Overdue fines are $0.10 a day."):
    return client.post("/admin/libraries/springfield-pl/documents", files={"file": (name, body, "text/plain")})


def test_upload_indexes_into_the_librarys_namespace(client, fake_backends):
    response = _upload(client)
    assert response.status_code == 200, response.text
    namespace, records = fake_backends["upserts"][0]
    assert namespace == "springfield-pl"
    assert "$0.10 a day" in records[0]["chunk_text"]
    assert fake_backends["rows"][0]["name"] == "fines.txt"


def test_reuploading_a_name_replaces_the_old_version(client, fake_backends):
    first = _upload(client).json()["id"]
    second = _upload(client, body=b"Overdue fines are $0.20 a day.").json()["id"]
    assert [r["id"] for r in fake_backends["rows"]] == [second]
    assert fake_backends["deleted"] == [("springfield-pl", f"{first}#")]


def test_unreadable_upload_is_a_422_and_changes_nothing(client, fake_backends):
    response = _upload(client, name="sheet.xlsx")
    assert response.status_code == 422
    assert fake_backends["upserts"] == [] and fake_backends["rows"] == []


def test_non_staff_cannot_upload(client, fake_backends):
    fake_backends["staff"] = False
    assert _upload(client).status_code == 403
    assert fake_backends["upserts"] == []


def test_shared_namespace_can_never_be_targeted(client, fake_backends):
    response = client.post(
        f"/admin/libraries/{tenants.DEFAULT_NAMESPACE}/documents", files={"file": ("a.txt", b"text", "text/plain")}
    )
    assert response.status_code == 404


def test_delete_removes_chunks_and_row(client, fake_backends):
    doc_id = _upload(client).json()["id"]
    assert client.delete(f"/admin/libraries/springfield-pl/documents/{doc_id}").status_code == 200
    assert fake_backends["rows"] == []
    assert ("springfield-pl", f"{doc_id}#") in fake_backends["deleted"]
    assert client.delete("/admin/libraries/springfield-pl/documents/nope").status_code == 404

"""Staff document upload — Tier 8 Phase 31 (TIER8_PLAN.md §2.1, §2.2).

POST   /admin/libraries/{id}/documents        upload (replaces a same-named document)
GET    /admin/libraries/{id}/documents        list
DELETE /admin/libraries/{id}/documents/{doc}  remove

Text is chunked into the library's own Pinecone namespace; once that namespace
exists, the library's patrons get its policies instead of the shared demo set
(app/tenants.py). Metadata lives in Supabase's `library_documents` table; the
original file is not kept.
"""

import anyio
import httpx
from fastapi import APIRouter, HTTPException, Request, UploadFile

from app import tenants
from app.config import SUPABASE_URL
from app.documents import DocumentError, chunk_records, chunk_text, extract_text, new_document_id
from app.library_config import _headers
from app.rate_limit import RATE_LIMIT, limiter
from app.services.pinecone_service import delete_by_prefix, upsert_chunks
from app.staff_auth import require_staff
from app.tenants import normalize_library_id

router = APIRouter(prefix="/admin/libraries/{library_id}/documents")


def _library(library_id: str) -> str:
    normalized = normalize_library_id(library_id)
    if normalized is None or normalized == tenants.DEFAULT_NAMESPACE:
        raise HTTPException(status_code=404, detail="Unknown library.")
    return normalized


async def _rest(request: Request, method: str, path: str, **kwargs) -> httpx.Response:
    client: httpx.AsyncClient = request.app.state.http_client
    response = await client.request(method, f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers(), timeout=10.0, **kwargs)
    response.raise_for_status()
    return response


async def _documents(request: Request, library_id: str, **filters: str) -> list[dict]:
    params = {"library_id": f"eq.{library_id}", "select": "id,name,chunk_count,created_at", "order": "created_at.desc"}
    params.update({key: f"eq.{value}" for key, value in filters.items()})
    return (await _rest(request, "GET", "library_documents", params=params)).json()


async def _remove(request: Request, library_id: str, doc_id: str) -> None:
    await anyio.to_thread.run_sync(delete_by_prefix, library_id, f"{doc_id}#")
    await _rest(request, "DELETE", "library_documents", params={"id": f"eq.{doc_id}", "library_id": f"eq.{library_id}"})


@router.get("")
@limiter.limit(RATE_LIMIT)
async def list_documents(request: Request, library_id: str):
    library_id = _library(library_id)
    await require_staff(request, library_id)
    return await _documents(request, library_id)


@router.post("")
@limiter.limit("20/hour")
async def upload_document(request: Request, library_id: str, file: UploadFile):
    library_id = _library(library_id)
    staff = await require_staff(request, library_id)
    name = (file.filename or "document").strip()[:200]
    data = await file.read()
    try:
        chunks = chunk_text(extract_text(name, data))
    except DocumentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    doc_id = new_document_id()
    try:
        await anyio.to_thread.run_sync(upsert_chunks, library_id, chunk_records(doc_id, name, chunks))
    except Exception as error:
        print("Document indexing failed:", error)
        raise HTTPException(status_code=502, detail="Indexing failed. Nothing was changed; try again.") from error

    # Only after the new version is indexed: record it, then retire any older
    # document with the same name, so patrons never see a gap.
    await _rest(
        request,
        "POST",
        "library_documents",
        json={"id": doc_id, "library_id": library_id, "name": name, "chunk_count": len(chunks), "uploaded_by": staff.user_id},
    )
    for old in await _documents(request, library_id, name=name):
        if old["id"] != doc_id:
            await _remove(request, library_id, old["id"])
    # The library may have just gained its first namespace.
    tenants.reset_namespace_cache()
    return {"id": doc_id, "name": name, "chunk_count": len(chunks)}


@router.delete("/{doc_id}")
@limiter.limit(RATE_LIMIT)
async def delete_document(request: Request, library_id: str, doc_id: str):
    library_id = _library(library_id)
    await require_staff(request, library_id)
    if not await _documents(request, library_id, id=doc_id):
        raise HTTPException(status_code=404, detail="No such document.")
    await _remove(request, library_id, doc_id)
    tenants.reset_namespace_cache()
    return {"deleted": doc_id}

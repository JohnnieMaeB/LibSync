"""Sync a library's LibAnswers FAQs into its policy namespace (Phase 37T part 2).

Indexed as one document named "LibAnswers FAQs", so each sync replaces the
last (the same replace-after-indexing path as file uploads) and staff can see
or remove it in the documents list.
"""

from fastapi import APIRouter, HTTPException, Request

from app.library_config import get_library_config, get_library_secret
from app.rate_limit import limiter
from app.routers.documents import index_document
from app.services import libanswers
from app.staff_auth import require_staff
from app.tenants import DEFAULT_NAMESPACE, normalize_library_id

router = APIRouter()

FAQ_DOCUMENT_NAME = "LibAnswers FAQs"


@router.post("/admin/libraries/{library_id}/faq-sync")
@limiter.limit("10/hour")
async def sync_faqs(request: Request, library_id: str):
    normalized = normalize_library_id(library_id)
    if normalized is None or normalized == DEFAULT_NAMESPACE:
        raise HTTPException(status_code=404, detail="Unknown library.")
    staff = await require_staff(request, normalized)
    client = request.app.state.http_client
    config = await get_library_config(client, normalized)
    settings = config.integration("libanswers") if config else None
    if not settings:
        raise HTTPException(status_code=409, detail="Connect LibAnswers under Integrations first.")
    secret = await get_library_secret(client, normalized, "libanswers_client_secret")
    try:
        faqs = await libanswers.fetch_faqs(client, settings, secret)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        print("LibAnswers sync failed:", error)
        raise HTTPException(status_code=502, detail="Couldn't reach LibAnswers. Nothing was changed.") from error
    if not faqs:
        raise HTTPException(status_code=422, detail="No FAQs were found in that LibAnswers group.")
    result = await index_document(request, normalized, FAQ_DOCUMENT_NAME, libanswers.faq_chunks(faqs), staff.user_id)
    return {**result, "faq_count": len(faqs)}

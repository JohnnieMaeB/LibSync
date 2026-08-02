"""Routes for querying the Pinecone index."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.rate_limit import RATE_LIMIT, limiter
from app.schemas import QueryRequest
from app.services.pinecone_service import search_pinecone

router = APIRouter()


@router.post("/api/query")
@limiter.limit(RATE_LIMIT)
async def query(request: Request, payload: QueryRequest):
    if not payload.text:
        return JSONResponse(status_code=400, content={"error": "Query text is required."})

    try:
        top_k = payload.topK if payload.topK is not None else 5
        results = search_pinecone(payload.text, top_k)
        return results
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to search Pinecone index."})

"""Routes for querying the Pinecone index."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.rate_limit import RATE_LIMIT, limiter
from app.schemas import QueryRequest
from app.services.pinecone_service import query_pinecone

router = APIRouter()


@router.post("/api/query")
@limiter.limit(RATE_LIMIT)
async def query(request: Request, payload: QueryRequest):
    if not payload.vector:
        return JSONResponse(status_code=400, content={"error": "Query vector is required."})

    try:
        top_k = payload.topK if payload.topK is not None else 5
        results = query_pinecone(payload.vector, top_k)
        return results
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to query Pinecone index."})

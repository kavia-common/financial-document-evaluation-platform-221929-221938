from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .schemas import EvaluationMetadata, EvaluationCreateResponse, EvaluationResult
from .settings import get_settings

# Configure structured logging without PII
logger = logging.getLogger("app")
_handler = logging.StreamHandler()
_formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
)
_handler.setFormatter(_formatter)
if not logger.handlers:
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add essential security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Minimal hardening headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Minimal permissions policy - disallow sensitive features
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        return response


def _deterministic_id(content_bytes: bytes, metadata: EvaluationMetadata) -> str:
    """Create a deterministic placeholder ID based on file content + metadata."""
    h = hashlib.sha256()
    h.update(content_bytes)
    # Avoid PII in the ID by hashing only opaque metadata fields
    h.update(metadata.document_type.encode("utf-8"))
    h.update(metadata.requested_by.encode("utf-8"))
    return h.hexdigest()[:16]


def _deterministic_score(content_bytes: bytes) -> float:
    """Create a deterministic placeholder score from the bytes."""
    # Map hash to [0,1]
    digest = hashlib.md5(content_bytes).hexdigest()  # non-cryptographic usage OK
    n = int(digest[:8], 16)
    return (n % 1000) / 1000.0


# In-memory store for evaluations (ID -> result)
EVAL_STORE: Dict[str, EvaluationResult] = {}

settings = get_settings()

app = FastAPI(
    title="Financial Evaluation API",
    description="API for uploading and evaluating financial documents. Placeholder deterministic evaluation.",
    version="1.0.0",
)

# Restrictive CORS: only allow configured frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/", summary="Health Check", tags=["health"])
def health_check():
    """Health check endpoint returning simple status payload."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/evaluations",
    response_model=EvaluationCreateResponse,
    summary="Create evaluation",
    description="Upload a financial document (multipart/form-data) along with JSON metadata to start an evaluation.",
    tags=["evaluations"],
    responses={
        201: {"description": "Evaluation accepted and completed (placeholder)."},
        400: {"description": "Invalid input or file type/size."},
    },
)
async def create_evaluation(
    file: UploadFile = File(..., description="Financial document file."),
    document_type: str = Form(..., description="Type/category of the financial document."),
    requested_by: str = Form(..., description="Opaque identifier of the requester. Do not send PII."),
    notes: str | None = Form(None, description="Optional non-PII notes."),
):
    """Accept multipart file + metadata, validate type and size, and run a deterministic placeholder evaluation.

    Parameters:
    - file: The uploaded document file.
    - document_type: Category of the document.
    - requested_by: Opaque requester ID (avoid PII).
    - notes: Optional notes.

    Returns:
    - EvaluationCreateResponse with deterministic ID and status.
    """
    # Validate content type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        logger.info("upload_rejected content_type=%s", file.content_type)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_MIME_TYPES)}",
        )

    # Enforce size limit by reading chunks
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    received = 0
    chunks: list[bytes] = []
    try:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            received += len(chunk)
            if received > max_bytes:
                logger.info("upload_too_large size=%s max=%s", received, max_bytes)
                raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_MB} MB.")
            chunks.append(chunk)
    finally:
        await file.close()
    content = b"".join(chunks)

    metadata = EvaluationMetadata(document_type=document_type, requested_by=requested_by, notes=notes)

    eval_id = _deterministic_id(content, metadata)
    created_at = datetime.now(timezone.utc)

    # Deterministic placeholder evaluation
    score = _deterministic_score(content)
    summary = f"Deterministic placeholder evaluation for {metadata.document_type}"
    result = EvaluationResult(
        id=eval_id,
        status="completed",
        score=score,
        summary=summary,
        created_at=created_at,
        document_type=metadata.document_type,
        requested_by=metadata.requested_by,
        notes=metadata.notes,
    )
    EVAL_STORE[eval_id] = result

    logger.info(
        "evaluation_created id=%s size_bytes=%s mime=%s doc_type=%s",
        eval_id,
        received,
        file.content_type,
        metadata.document_type,
    )

    return JSONResponse(
        status_code=201,
        content=EvaluationCreateResponse(id=eval_id, status=result.status, created_at=created_at).model_dump(),
    )


# PUBLIC_INTERFACE
@app.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResult,
    summary="Get evaluation",
    description="Retrieve a previously created evaluation by its ID.",
    tags=["evaluations"],
    responses={
        200: {"description": "Evaluation found."},
        404: {"description": "Evaluation not found."},
    },
)
async def get_evaluation(evaluation_id: str):
    """Return the stored evaluation for the provided identifier."""
    result = EVAL_STORE.get(evaluation_id)
    if not result:
        logger.info("evaluation_not_found id=%s", evaluation_id)
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return result

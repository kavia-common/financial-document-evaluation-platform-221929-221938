from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, constr


# PUBLIC_INTERFACE
class EvaluationMetadata(BaseModel):
    """Metadata describing the evaluation request."""

    document_type: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Type/category of the financial document (e.g., 'invoice', 'statement')."
    )
    requested_by: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Opaque identifier of the requesting client. Do not send PII."
    )
    notes: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None, description="Optional non-PII notes for the evaluation."
    )


# PUBLIC_INTERFACE
class EvaluationCreateResponse(BaseModel):
    """Response returned when an evaluation is accepted for processing."""

    id: str = Field(..., description="Deterministically generated evaluation identifier.")
    status: str = Field(..., description="Status of the evaluation, placeholder: 'completed'.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")


# PUBLIC_INTERFACE
class EvaluationResult(BaseModel):
    """Full evaluation result returned from storage."""

    id: str = Field(..., description="Evaluation identifier.")
    status: str = Field(..., description="Status of the evaluation.")
    score: float = Field(..., ge=0.0, le=1.0, description="Deterministic placeholder score (0..1).")
    summary: str = Field(..., description="Brief summary of the placeholder evaluation.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    document_type: str = Field(..., description="Document type from the submitted metadata.")
    requested_by: str = Field(..., description="Opaque requester identifier from the submitted metadata.")
    notes: Optional[str] = Field(default=None, description="Optional notes from the submitted metadata.")

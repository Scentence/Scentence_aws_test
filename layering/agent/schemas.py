"""Pydantic schemas for the layering service domain objects."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import ACCORDS


class PerfumeAccord(BaseModel):
    accord: str = Field(description="Accord name aligned with ACCORDS order")
    ratio: float = Field(ge=0, description="Numeric contribution of the accord")

    @field_validator("accord")
    @classmethod
    def validate_accord(cls, value: str) -> str:  # noqa: D401
        if value not in ACCORDS:
            raise ValueError(f"Accord '{value}' not recognised")
        return value


class PerfumeBasic(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str


class PerfumeRecord(BaseModel):
    """Raw perfume information prior to vectorization."""

    perfume: PerfumeBasic
    accords: List[PerfumeAccord]
    base_notes: List[str] = Field(default_factory=list)


class PerfumeVector(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    vector: List[float]
    total_intensity: float
    persistence_score: float
    dominant_accords: List[str]
    base_notes: List[str] = Field(default_factory=list)

    @field_validator("vector")
    @classmethod
    def validate_vector_length(cls, value: List[float]) -> List[float]:
        if len(value) != len(ACCORDS):
            raise ValueError("Vector length mismatch with ACCORDS")
        return value

    @field_validator("base_notes")
    @classmethod
    def validate_base_notes(cls, value: List[str]) -> List[str]:
        return [note for note in value if note]


class LayeringRequest(BaseModel):
    base_perfume_id: str = Field(..., description="Base perfume identifier")
    keywords: List[str] = Field(default_factory=list)


class UserQueryRequest(BaseModel):
    user_text: str = Field(..., description="Free-form user question")


class ScoreBreakdown(BaseModel):
    base: float = Field(default=1.0)
    harmony: float
    bridge: float
    penalty: float
    target: float


class LayeringCandidate(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    total_score: float
    feasible: bool = True
    feasibility_reason: Optional[str]
    spray_order: List[str]
    score_breakdown: ScoreBreakdown
    clash_detected: bool
    analysis: str
    layered_vector: List[float] = Field(default_factory=list)


class LayeringResponse(BaseModel):
    base_perfume_id: str
    keywords: List[str]
    total_available: int
    recommendations: List[LayeringCandidate]
    note: Optional[str] = None


class DetectedPerfume(BaseModel):
    perfume_id: str
    perfume_name: str
    perfume_brand: str
    match_score: float
    matched_text: str


class DetectedPair(BaseModel):
    base_perfume_id: Optional[str]
    candidate_perfume_id: Optional[str]


class PairingAnalysis(BaseModel):
    base_perfume_id: str
    candidate_perfume_id: str
    result: LayeringCandidate


class UserQueryAnalysis(BaseModel):
    raw_text: str
    detected_perfumes: List[DetectedPerfume]
    detected_pair: Optional[DetectedPair] = None
    pairing_analysis: Optional[PairingAnalysis] = None


class UserQueryResponse(BaseModel):
    raw_text: str
    keywords: List[str]
    base_perfume_id: Optional[str] = None
    detected_perfumes: List[DetectedPerfume]
    detected_pair: Optional[DetectedPair] = None
    recommendation: Optional[LayeringCandidate] = None
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class LayeringError(BaseModel):
    code: str
    message: str
    step: str
    retriable: bool = False
    details: Optional[str] = None


class LayeringErrorResponse(BaseModel):
    error: LayeringError

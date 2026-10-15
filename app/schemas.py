from pydantic import BaseModel, Field
from typing import Literal


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    document_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class Evidence(BaseModel):
    document_id: str
    document_name: str
    page: int
    score: float
    text: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    evidence: list[Evidence]
    grounded: bool
    note: str


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks: int
    message: str


class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str
    similarity_threshold: float = Field(default=0.72, ge=0.1, le=1.0)

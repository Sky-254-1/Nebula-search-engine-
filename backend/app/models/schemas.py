"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# Base response schemas
class APIResponse(BaseModel):
    """Standard API response envelope."""
    status: str = "success"
    message: str = "Success"
    data: Optional[Any] = None
    metadata: dict = {}
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class APIError(BaseModel):
    """Standard API error response."""
    status: str = "error"
    error_code: str
    message: str
    validation_errors: list = []
    request_id: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: list[Any]
    pagination: PaginationMeta


# Authentication schemas
class AuthRequest(BaseModel):
    """Authentication request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AuthResponse(BaseModel):
    """Authentication response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: Optional[str] = None


class UserInfo(BaseModel):
    """User information."""
    email: str
    role: str
    email_verified: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


# Search schemas
class SearchResult(BaseModel):
    """Search result item."""
    document_id: int
    chunk_id: int
    filename: str
    content: str
    score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


class OrchestratedSearchResponse(BaseModel):
    """Orchestrated search response."""
    query: str
    results: list[SearchResult]
    backends_used: list[str]
    total: int


# Vector schemas
class VectorSearchRequest(BaseModel):
    """Vector search request."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    filters: Optional[dict] = None


class Citation(BaseModel):
    """Citation for RAG answer."""
    id: int
    document_id: int
    chunk_id: int
    query: str
    snippet: str
    score: float
    created_at: datetime


class VectorAskRequest(BaseModel):
    """Vector ask (RAG) request."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)


class VectorAskResponse(BaseModel):
    """Vector ask response."""
    query: str
    answer: str
    citations: list[Citation]
    sources: list[str]


# Storage schemas
class DocumentUploadResponse(BaseModel):
    """Document upload response."""
    id: int
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime
    status: str


# Webhook schemas
class WebhookCreate(BaseModel):
    """Webhook creation request."""
    url: str = Field(..., regex=r'^https?://')
    events: list[str] = Field(..., min_items=1)
    secret: Optional[str] = None
    description: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response."""
    id: int
    url: str
    events: list[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None


class WebhookDelivery(BaseModel):
    """Webhook delivery log."""
    id: int
    webhook_id: int
    event_type: str
    status: str
    response_code: Optional[int]
    attempts: int
    created_at: datetime


# Health schemas
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    cache: str
    timestamp: datetime


# Admin schemas
class SystemStats(BaseModel):
    """System statistics."""
    total_users: int
    active_users: int
    total_documents: int
    total_searches: int
    cache_hit_ratio: float
    uptime_seconds: float


# AI schemas
class AICompletionRequest(BaseModel):
    """AI completion request."""
    prompt: str = Field(..., min_length=1, max_length=10000)
    max_tokens: int = Field(500, ge=1, le=4000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    model: Optional[str] = None


class AICompletionResponse(BaseModel):
    """AI completion response."""
    text: str
    model: str
    tokens_used: int
    finish_reason: str


# Audio schemas
class AudioTranscriptionRequest(BaseModel):
    """Audio transcription request."""
    language: Optional[str] = Field(None, regex=r'^[a-z]{2}$')


class AudioTranscriptionResponse(BaseModel):
    """Audio transcription response."""
    text: str
    language: str
    duration: float
    segments: list[dict]


# Utility schemas
class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
"""API request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class AIResponse(BaseModel):
    answer: str
    provider: str = "unknown"


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    source: str


class OrchestratedSearchResponse(BaseModel):
    query: str
    expanded_queries: list[str]
    backends: list[str]
    results: list[SearchResult]
    total: int
    page: int
    page_size: int
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str
    database: str = "sqlite"
    cache: str = "memory"


class SynthesizeRequest(BaseModel):
    snippets: list[str] = Field(..., min_length=1, max_length=20)
    query: str = Field(..., min_length=1, max_length=500)


class SynthesizeResponse(BaseModel):
    synthesis: str

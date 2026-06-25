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


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str | None = None
    indexed_at: str | None = None
    created_at: str = ""


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class SettingsResponse(BaseModel):
    settings: dict


class SettingsUpdateRequest(BaseModel):
    settings: dict = Field(default_factory=dict)


class ExportCreateRequest(BaseModel):
    export_type: str = Field(..., min_length=1, max_length=50)
    data: dict | None = None


class ExportResponse(BaseModel):
    id: int
    export_type: str
    storage_path: str
    created_at: str = ""


class ExportListResponse(BaseModel):
    exports: list[ExportResponse]


class DocumentIndexStatusResponse(BaseModel):
    id: int
    filename: str
    status: str = "pending"
    indexed_at: str | None = None
    error_message: str | None = None


class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class VectorSearchResult(BaseModel):
    document_id: int | None = None
    chunk_id: int | None = None
    filename: str = ""
    content: str = ""
    score: float = 0
    vector_score: float = 0
    keyword_score: float = 0


class VectorSearchResponse(BaseModel):
    query: str
    results: list[VectorSearchResult]
    total: int


class VectorCitationResponse(BaseModel):
    id: int
    document_id: int | None = None
    chunk_id: int | None = None
    query: str
    snippet: str | None = None
    score: float = 0
    created_at: str = ""


class VectorCitationListResponse(BaseModel):
    citations: list[VectorCitationResponse]


class VectorReindexRequest(BaseModel):
    limit: int | None = Field(default=100, ge=1, le=500)

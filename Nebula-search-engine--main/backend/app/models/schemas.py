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


class CrawlStartRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    max_pages: int = Field(default=10, ge=1, le=10000)
    depth: int = Field(default=3, ge=1, le=10)


class CrawlJobResponse(BaseModel):
    id: int
    url: str
    status: str
    depth: int = 0
    max_pages: int = 10
    pages_crawled: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    created_at: str = ""


class CrawlJobListResponse(BaseModel):
    jobs: list[CrawlJobResponse]


class CrawledPageResponse(BaseModel):
    id: int
    job_id: int
    url: str
    title: str | None = None
    excerpt: str | None = None
    extracted_at: str = ""


class CrawledPageListResponse(BaseModel):
    pages: list[CrawledPageResponse]
    total: int


# Saved Searches
class SavedSearchCreate(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: dict = Field(default_factory=dict)
    label: str | None = Field(default=None, max_length=100)


class SavedSearchResponse(BaseModel):
    id: int
    query: str
    filters: dict = {}
    label: str | None = None
    created_at: str


class SavedSearchListResponse(BaseModel):
    saved_searches: list[SavedSearchResponse]


# Collections
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_public: bool = False
    item_count: int = 0
    created_at: str
    updated_at: str


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]


class CollectionItemCreate(BaseModel):
    document_id: int | None = None
    search_result_id: int | None = None
    note: str | None = None


class CollectionItemResponse(BaseModel):
    id: int
    collection_id: int
    document_id: int | None = None
    search_result_id: int | None = None
    note: str | None = None
    created_at: str


# Bookmarks
class BookmarkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1, max_length=2000)
    snippet: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)


class BookmarkResponse(BaseModel):
    id: int
    title: str
    url: str
    snippet: str | None = None
    tags: list[str] = []
    created_at: str


class BookmarkListResponse(BaseModel):
    bookmarks: list[BookmarkResponse]


class BookmarkUpdate(BaseModel):
    title: str | None = None
    snippet: str | None = None
    tags: list[str] | None = None


# Notifications
class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    type: str
    read: bool = False
    created_at: str


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int = 0


# Sharing
class ShareCreate(BaseModel):
    collection_id: int
    recipient_email: str = Field(..., max_length=254)
    permission: str = "view"  # view, edit


class ShareResponse(BaseModel):
    id: int
    collection_id: int
    recipient_email: str
    permission: str
    created_at: str

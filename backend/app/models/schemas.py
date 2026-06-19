"""API request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class AIResponse(BaseModel):
    answer: str


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    source: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str


class SynthesizeRequest(BaseModel):
    snippets: list[str] = Field(..., min_length=1, max_length=20)
    query: str = Field(..., min_length=1, max_length=500)


class SynthesizeResponse(BaseModel):
    synthesis: str

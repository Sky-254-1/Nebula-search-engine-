from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth.dependencies import get_current_user
from ai.ollama import OllamaClient

router = APIRouter()

class AIRequest(BaseModel):
    prompt: str
    context: str | None = None

class AIResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=AIResponse)
async def ask(req: AIRequest, user=Depends(get_current_user)):
    client = OllamaClient()
    full_prompt = f"Context: {req.context}\n\nQuestion: {req.prompt}\nAnswer:" if req.context else req.prompt
    answer = await client.generate(full_prompt)
    return AIResponse(answer=answer)
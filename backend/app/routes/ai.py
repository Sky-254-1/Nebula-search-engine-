"""AI answer and synthesis routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.rate_limit import rate_limit
from app.models.schemas import AIRequest, AIResponse, SynthesizeRequest, SynthesizeResponse
from app.services.ai import get_ai_answer, synthesize_snippets
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.post("/ask", response_model=AIResponse, dependencies=[Depends(rate_limit)])
async def ai_ask(body: AIRequest, email: str = Depends(get_current_user)):
    _ = email
    answer = await get_ai_answer(body.prompt)
    if not answer:
        raise HTTPException(
            status_code=404,
            detail="No AI answer available for this query. Try rephrasing.",
        )
    return AIResponse(answer=answer)


@router.post("/synthesize", response_model=SynthesizeResponse, dependencies=[Depends(rate_limit)])
async def synthesize(body: SynthesizeRequest, email: str = Depends(get_current_user)):
    _ = email
    return await synthesize_snippets(body.query, body.snippets)

"""AI provider health check service."""

from app.providers.ai.router import AIProviderRouter

_router = AIProviderRouter()


async def check_ai_health() -> bool:
    answer, _ = await _router.complete("Say OK", system="Respond with exactly 'OK'")
    return answer is not None

import httpx
from config import OLLAMA_URL

class OllamaClient:
    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
import httpx
import json
from config import OLLAMA_URL, MODEL

async def ask_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]


async def ask_llm_stream(prompt: str):
    """
    Потоковая генерация ответа от Ollama.
    Возвращает асинхронный генератор, выдающий фрагменты текста.
    """
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": True
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
import os
from typing import List
import httpx


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Calls Azure OpenAI embeddings endpoint with a batch of texts.
    Returns embeddings in the same order as input.
    """
    endpoint = _env("AZURE_OPENAI_ENDPOINT").rstrip("/")
    api_key = _env("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_EMBEDDINGS_API_VERSION", "2024-02-15-preview")
    deployment = _env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")

    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
    payload = {"input": texts}

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Azure returns: {"data":[{"embedding":[...], "index":0}, ...]}
    items = sorted(data["data"], key=lambda x: x["index"])
    return [it["embedding"] for it in items]

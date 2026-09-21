import os

import httpx


class JevClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.jev.com"):
        self.api_key = api_key or os.getenv("JEV_API_KEY")
        self.base_url = base_url.rstrip("/")

    async def systemone(self, state: dict, questions: dict) -> dict:
        if not self.api_key:
            raise RuntimeError("JEV_API_KEY not set — Jev is required (mocking disabled)")
        url = f"{self.base_url}/v1/systemone"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json={"state": state, "questions": questions}, headers=headers)
            resp.raise_for_status()
            return resp.json()

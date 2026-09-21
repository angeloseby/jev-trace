"""JevClient — thin SDK wrapper using TypeSafe's official client."""

import os
from typing import Any


class JevClient:
    """Compatibility wrapper. Prefer direct use of typesafe_sdk.AsyncTypeSafeClient.

    Keeps JEV_API_KEY support while delegating to TypeSafe SDK.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
        if base_url:
            os.environ["TYPESAFE_BASE_URL"] = base_url
        # Also mirror to SDK's expected env for fallback
        if self.api_key:
            os.environ["TYPESAFE_API_KEY"] = self.api_key

    async def systemone(self, state: dict, questions: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("JEV_API_KEY (or TYPESAFE_API_KEY) not set — Jev is required (mocking disabled)")
        # Convert raw dict questions to SDK objects if needed, or pass through as dicts
        # SDK accepts raw dicts (type + instructions + criteria) as valid questions.
        from typesafe_sdk import AsyncTypeSafeClient

        async with AsyncTypeSafeClient(api_key=self.api_key) as client:
            result = await client.system_one(state=state, questions=questions)  # type: ignore[arg-type]
            # Return raw dict for backward compat
            return {
                "model": result.model,
                "answers": {
                    k: v.model_dump() if hasattr(v, "model_dump") else dict(v) for k, v in result.answers.items()
                },
                "usage": result.usage.model_dump() if result.usage else None,
            }

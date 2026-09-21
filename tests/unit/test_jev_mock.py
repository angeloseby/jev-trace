import os

import pytest


@pytest.mark.asyncio
async def test_jev_requires_key():
    # Jev must be real — no mock. Without key it should raise.
    orig = os.environ.pop("JEV_API_KEY", None)
    # Also clear settings cache if needed
    try:
        from app.services import jev_service

        # Force no key by clearing settings and env
        import app.core.config as cfg

        old = cfg.settings.jev_api_key
        cfg.settings.jev_api_key = None
        os.environ.pop("JEV_API_KEY", None)
        with pytest.raises(RuntimeError, match="JEV_API_KEY"):
            await jev_service.analyze_trace({"task": "t", "steps": [{"component": "retriever", "status": "failed"}]})
        cfg.settings.jev_api_key = old
    finally:
        if orig is not None:
            os.environ["JEV_API_KEY"] = orig
        else:
            os.environ.pop("JEV_API_KEY", None)
        # Restore from .env
        import importlib

        importlib.reload(cfg)

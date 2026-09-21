import os

import pytest


@pytest.mark.asyncio
async def test_jev_requires_key():
    # Jev must be real — no mock. Without key it should raise.
    orig = os.environ.pop("JEV_API_KEY", None)
    orig2 = os.environ.pop("TYPESAFE_API_KEY", None)
    try:
        from app.services import jev_service

        import app.core.config as cfg

        old = cfg.settings.jev_api_key
        old2 = cfg.settings.typesafe_api_key
        cfg.settings.jev_api_key = None
        cfg.settings.typesafe_api_key = None
        os.environ.pop("JEV_API_KEY", None)
        os.environ.pop("TYPESAFE_API_KEY", None)
        with pytest.raises(RuntimeError, match="JEV_API_KEY"):
            await jev_service.analyze_trace({"task": "t", "steps": [{"component": "retriever", "status": "failed"}]})
        cfg.settings.jev_api_key = old
        cfg.settings.typesafe_api_key = old2
    finally:
        if orig is not None:
            os.environ["JEV_API_KEY"] = orig
        if orig2 is not None:
            os.environ["TYPESAFE_API_KEY"] = orig2
        import importlib

        importlib.reload(cfg)

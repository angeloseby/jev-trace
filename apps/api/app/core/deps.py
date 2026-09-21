import hashlib

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    # If auth not required (demo mode), allow anonymous
    if not settings.require_auth:
        # Still try to validate if token provided, but don't require
        if credentials is None:
            return {"sub": "anonymous", "demo": True}
        payload = decode_token(credentials.credentials)
        if payload is None:
            return {"sub": "anonymous", "demo": True}
        return payload
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


async def get_api_key_or_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(None, alias="X-Api-Key"),
    authorization: str | None = Header(None),
):
    # Supports both JWT (Bearer <jwt>) and ApiKey (Basic base64(public:secret) or X-Api-Key)
    # For ingestion endpoints that need project scoping
    if credentials and credentials.credentials:
        # Try JWT first
        payload = decode_token(credentials.credentials)
        if payload:
            return {"type": "jwt", "user": payload}
        # Try Basic public:secret via Bearer
        if ":" in credentials.credentials and credentials.credentials.startswith("jt_"):
            return {"type": "api_key", "public_key": credentials.credentials.split(":")[0]}
    # Fallback to headers handled in ingest logic
    if x_api_key or authorization:
        return {"type": "api_key_header", "auth": authorization, "x_api_key": x_api_key}
    if not settings.require_auth:
        return {"type": "anonymous"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

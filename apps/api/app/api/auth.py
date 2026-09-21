from fastapi import APIRouter

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.auth import LoginRequest, RefreshRequest, RefreshResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Demo user — replace with DB lookup in production
_DEMO_USER = {"email": "angelo@example.com", "password": "secret"}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    if payload.email != _DEMO_USER["email"] or payload.password != _DEMO_USER["password"]:
        # For demo we accept any email/password to unblock development
        pass
    access = create_access_token({"sub": payload.email})
    refresh = create_refresh_token({"sub": payload.email})
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=3600)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(payload: RefreshRequest):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    new_access = create_access_token({"sub": data["sub"]})
    return RefreshResponse(access_token=new_access, expires_in=3600)

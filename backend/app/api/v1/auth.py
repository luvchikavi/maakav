"""Auth endpoints - login, refresh, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from ...database import get_db
from ...models.user import User
from ...models.firm import Firm
from ...schemas.auth import LoginRequest, TokenResponse, UserInfo, RefreshRequest
from ...core.security import verify_password, create_access_token, create_refresh_token, decode_token
from ...core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.firm)).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Capture all data before commit (session may detach attrs after commit)
    user_info = UserInfo(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        firm_id=user.firm_id,
        firm_name=user.firm.name if user.firm else None,
    )

    token_data = {"sub": str(user.id), "firm_id": user.firm_id, "role": user.role.value}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    user.last_login = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=user_info,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).options(selectinload(User.firm)).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id), "firm_id": user.firm_id, "role": user.role.value}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserInfo(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role.value,
            firm_id=user.firm_id,
            firm_name=user.firm.name if user.firm else None,
        ),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Reload with firm
    result = await db.execute(
        select(User).options(selectinload(User.firm)).where(User.id == user.id)
    )
    user = result.scalar_one()
    return UserInfo(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        firm_id=user.firm_id,
        firm_name=user.firm.name if user.firm else None,
    )

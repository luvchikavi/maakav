"""User management endpoints - list, invite, update role, deactivate."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from ...database import get_db
from ...models.user import User, UserRole
from ...core.dependencies import get_current_user
from ...core.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    last_login: str | None
    created_at: str
    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "appraiser"
    password: str


class UpdateUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    new_password: str


@router.get("")
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the firm."""
    result = await db.execute(
        select(User)
        .where(User.firm_id == user.firm_id)
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "last_login": str(u.last_login) if u.last_login else None,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


@router.post("")
async def invite_user(
    body: InviteUserRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user in the firm. Admin only."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="רק מנהל יכול להוסיף משתמשים")

    # Check email not taken
    existing = (await db.execute(
        select(User).where(User.email == body.email)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="כתובת האימייל כבר בשימוש")

    # Validate role
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="תפקיד לא תקין")

    new_user = User(
        firm_id=user.firm_id,
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "role": new_user.role.value,
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user details. Admin only."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="רק מנהל יכול לעדכן משתמשים")

    target = (await db.execute(
        select(User).where(User.id == user_id, User.firm_id == user.firm_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")

    if body.first_name is not None:
        target.first_name = body.first_name
    if body.last_name is not None:
        target.last_name = body.last_name
    if body.role is not None:
        try:
            target.role = UserRole(body.role)
        except ValueError:
            raise HTTPException(status_code=400, detail="תפקיד לא תקין")
    if body.is_active is not None:
        target.is_active = body.is_active

    await db.commit()
    return {"ok": True}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset user password. Admin only, or self."""
    target = (await db.execute(
        select(User).where(User.id == user_id, User.firm_id == user.firm_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")

    if user.role != UserRole.ADMIN and user.id != user_id:
        raise HTTPException(status_code=403, detail="אין הרשאה לאפס סיסמה")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="הסיסמה חייבת להכיל לפחות 6 תווים")

    target.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user. Admin only. Cannot delete self."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="רק מנהל יכול למחוק משתמשים")

    if user.id == user_id:
        raise HTTPException(status_code=400, detail="לא ניתן למחוק את עצמך")

    target = (await db.execute(
        select(User).where(User.id == user_id, User.firm_id == user.firm_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")

    await db.delete(target)
    await db.commit()
    return {"ok": True}

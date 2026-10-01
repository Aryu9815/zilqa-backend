from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.security import create_access_token
from app.models.admin import Admin
from app.repositories.admin_repository import admin_repository
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminInfo(BaseModel):
    id: Any
    name: str
    email: str


class AdminTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin: AdminInfo


class AdminRefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=AdminTokenResponse)
async def login_admin(request: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    admin = await admin_repository.authenticate(db, email=request.email, password=request.password)

    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account deactivated")

    from datetime import timedelta
    access_token = create_access_token(
        subject=admin.id,
        additional_claims={"is_admin": True, "type": "access"},
    )
    
    refresh_token = create_access_token(
        subject=admin.id,
        expires_delta=timedelta(hours=12),
        additional_claims={"is_admin": True, "type": "refresh"},
    )

    return AdminTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        admin=AdminInfo(id=str(admin.id), name=admin.name, email=admin.email),
    )


from app.core.security import decode_token

@router.post("/refresh", response_model=AdminTokenResponse)
async def refresh_admin_token(request: AdminRefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
            
        admin = await admin_repository.get_by_id(db, admin_id)
        if not admin or not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account deactivated or not found")
            
        from datetime import timedelta
        access_token = create_access_token(
            subject=admin.id,
            additional_claims={"is_admin": True, "type": "access"},
        )
        
        new_refresh_token = create_access_token(
            subject=admin.id,
            expires_delta=timedelta(hours=12),
            additional_claims={"is_admin": True, "type": "refresh"},
        )
        
        return AdminTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            admin=AdminInfo(id=str(admin.id), name=admin.name, email=admin.email),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


@router.get("/me")
async def get_admin_me(current_admin: Admin = Depends(get_current_admin)):
    """Admin verification endpoint — confirms the token belongs to a valid, active admin."""
    return {
        "id": str(current_admin.id),
        "name": current_admin.name,
        "email": current_admin.email,
        "is_active": current_admin.is_active,
    }

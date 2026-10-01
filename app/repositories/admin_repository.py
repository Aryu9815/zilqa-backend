from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.core.security import verify_password


class AdminRepository:

    async def get_by_id(self, db: AsyncSession, admin_id: UUID) -> Optional[Admin]:
        return await db.get(Admin, admin_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Admin]:
        from sqlalchemy import select, func
        stmt = select(Admin).where(func.lower(Admin.email) == email.lower())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[Admin]:
        admin = await self.get_by_email(db, email)
        if not admin:
            return None
        if not admin.password_hash:
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return admin


admin_repository = AdminRepository()

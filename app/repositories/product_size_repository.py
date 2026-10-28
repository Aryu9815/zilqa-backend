from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product_size import ProductSize
from app.schemas.product_size import ProductSizeCreate, ProductSizeUpdate


class ProductSizeRepository:

    async def get_by_id(
        self,
        db: AsyncSession,
        size_id: UUID,
        is_active_only: bool = False,
        include_deleted: bool = False,
    ) -> Optional[ProductSize]:
        conditions = [ProductSize.id == size_id]
        if not include_deleted:
            conditions.append(ProductSize.is_deleted == False)
        if is_active_only:
            conditions.append(ProductSize.is_active == True)

        stmt = select(ProductSize).options(selectinload(ProductSize.category)).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_unique_categories(
        self,
        db: AsyncSession,
    ):
        stmt = select(func.distinct(ProductSize.category_id)).where(ProductSize.is_deleted == False, ProductSize.is_active == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_sizes(
        self,
        db: AsyncSession,
        category_id: Optional[UUID] = None,
        country_code: Optional[str] = None,
        is_active_only: bool = True,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 100,
    ) -> Tuple[List[ProductSize], int]:
        conditions = []
        if not include_deleted:
            conditions.append(ProductSize.is_deleted == False)
        if is_active_only:
            conditions.append(ProductSize.is_active == True)
        if category_id is not None:
            # Match specified category or global sizes without category
            conditions.append(or_(ProductSize.category_id == category_id, ProductSize.category_id.is_(None)))
        if country_code is not None:
            cleaned = country_code.strip()
            if cleaned.lower() in ("none", "null", ""):
                conditions.append(or_(ProductSize.country_code.is_(None), ProductSize.country_code == ""))
            else:
                conditions.append(func.lower(func.trim(ProductSize.country_code)) == cleaned.lower())

        count_stmt = select(func.count()).select_from(ProductSize)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await db.scalar(count_stmt) or 0

        stmt = select(ProductSize).options(selectinload(ProductSize.category))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(ProductSize.display_order.asc(), ProductSize.name.asc())

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_available_countries(
        self,
        db: AsyncSession,
        category_id: Optional[UUID] = None,
        is_active_only: bool = True,
        include_deleted: bool = False,
    ) -> List[str]:
        conditions = [
            ProductSize.country_code.isnot(None),
            ProductSize.country_code != "",
        ]
        if not include_deleted:
            conditions.append(ProductSize.is_deleted == False)
        if is_active_only:
            conditions.append(ProductSize.is_active == True)
        if category_id is not None:
            conditions.append(or_(ProductSize.category_id == category_id, ProductSize.category_id.is_(None)))

        stmt = (
            select(func.distinct(ProductSize.country_code))
            .where(and_(*conditions))
            .order_by(func.distinct(ProductSize.country_code).asc())
        )
        result = await db.execute(stmt)
        return [r for r in result.scalars().all() if r]

    async def create(self, db: AsyncSession, size_in: ProductSizeCreate) -> ProductSize:
        code = size_in.country_code.strip().upper() if size_in.country_code else None
        product_size = ProductSize(
            name=size_in.name.strip(),
            category_id=size_in.category_id,
            country_code=code,
            display_order=size_in.display_order if size_in.display_order is not None else 0,
            is_active=size_in.is_active if size_in.is_active is not None else True,
        )
        db.add(product_size)
        await db.flush()
        await db.refresh(product_size)
        # Load category relationship
        stmt = select(ProductSize).options(selectinload(ProductSize.category)).where(ProductSize.id == product_size.id)
        res = await db.execute(stmt)
        return res.scalar_one()

    async def update(
        self,
        db: AsyncSession,
        size_id: UUID,
        size_in: ProductSizeUpdate,
    ) -> Optional[ProductSize]:
        product_size = await self.get_by_id(db, size_id, include_deleted=False)
        if not product_size:
            return None

        if size_in.name is not None:
            product_size.name = size_in.name.strip()
        if size_in.category_id is not None:
            product_size.category_id = size_in.category_id
        if size_in.country_code is not None:
            product_size.country_code = size_in.country_code.strip().upper() if size_in.country_code else None
        if size_in.display_order is not None:
            product_size.display_order = size_in.display_order
        if size_in.is_active is not None:
            product_size.is_active = size_in.is_active

        await db.flush()
        await db.refresh(product_size)
        stmt = select(ProductSize).options(selectinload(ProductSize.category)).where(ProductSize.id == size_id)
        res = await db.execute(stmt)
        return res.scalar_one()

    async def delete(self, db: AsyncSession, size_id: UUID, soft: bool = True) -> bool:
        product_size = await self.get_by_id(db, size_id, include_deleted=True)
        if not product_size:
            return False

        if soft:
            if product_size.is_deleted:
                return False
            product_size.is_deleted = True
            product_size.is_active = False
        else:
            await db.delete(product_size)

        await db.flush()
        return True


product_size_repository = ProductSizeRepository()

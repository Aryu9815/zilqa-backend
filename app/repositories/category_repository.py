from typing import List, Optional, Tuple, Any
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryRepository:

    async def get_by_id(
        self,
        db: AsyncSession,
        category_id: UUID,
        include_deleted: bool = False,
    ) -> Optional[Category]:
        conditions = [Category.id == category_id]
        if not include_deleted:
            conditions.append(Category.is_deleted == False)
        stmt = select(Category).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        db: AsyncSession,
        category_ids: List[UUID],
        include_deleted: bool = False,
    ) -> List[Category]:
        if not category_ids:
            return []
        conditions = [Category.id.in_(category_ids)]
        if not include_deleted:
            conditions.append(Category.is_deleted == False)
        stmt = select(Category).where(and_(*conditions)).order_by(Category.priority.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[Category]:
        conditions = [func.lower(Category.name) == func.lower(name.strip())]
        if not include_deleted:
            conditions.append(Category.is_deleted == False)
        stmt = select(Category).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_categories(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        include_deleted: bool = False,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Category], int]:
        conditions = []
        if not include_deleted:
            conditions.append(Category.is_deleted == False)
        if is_active is not None:
            conditions.append(Category.is_active == is_active)

        count_stmt = select(func.count()).select_from(Category)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = await db.scalar(count_stmt) or 0

        stmt = select(Category)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Category.priority.asc())

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await db.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def create(
        self,
        db: AsyncSession,
        category_in: CategoryCreate,
    ) -> Category:
        import re
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", category_in.name.strip().lower()).strip("-")
        category = Category(
            name=category_in.name.strip(),
            description=category_in.description,
            image_url=category_in.image_url,
            slug=slug,
            seo_title=category_in.name.strip(),
            seo_description=category_in.description or f"Shop {category_in.name.strip()} on Zelqa",
            og_title=category_in.name.strip(),
            og_description=category_in.description or f"Shop {category_in.name.strip()} on Zelqa",
            is_active=True,
            is_deleted=False,
        )
        db.add(category)
        await db.flush()
        await db.refresh(category)
        return category

    async def update(
        self,
        db: AsyncSession,
        category_id: UUID,
        category_in: CategoryUpdate,
    ) -> Optional[Category]:
        category = await self.get_by_id(db, category_id, include_deleted=False)
        if not category:
            return None

        if category_in.name is not None:
            category.name = category_in.name.strip()
            import re
            category.slug = re.sub(r"[^a-zA-Z0-9]+", "-", category_in.name.strip().lower()).strip("-")
            category.seo_title = category_in.name.strip()
            category.og_title = category_in.name.strip()

        if category_in.description is not None:
            category.description = category_in.description

        if category_in.image_url is not None:
            category.image_url = category_in.image_url

        if category_in.slug is not None:
            category.slug = category_in.slug
        elif category_in.name is not None and not category.slug:
            import re
            category.slug = re.sub(r"[^a-zA-Z0-9]+", "-", category_in.name.strip().lower()).strip("-")

        if category_in.seo_title is not None:
            category.seo_title = category_in.seo_title
        elif category_in.name is not None and not category.seo_title:
            category.seo_title = category_in.name.strip()

        if category_in.og_title is not None:
            category.og_title = category_in.og_title
        elif category_in.name is not None and not category.og_title:
            category.og_title = category_in.name.strip()

        if category_in.seo_description is not None:
            category.seo_description = category_in.seo_description
        if category_in.og_description is not None:
            category.og_description = category_in.og_description
        if category_in.priority is not None:
            category.priority = category_in.priority

        await db.flush()
        await db.refresh(category)
        return category

    async def delete(
        self,
        db: AsyncSession,
        category_id: UUID,
        soft: bool = True,
    ) -> bool:
        category = await self.get_by_id(db, category_id, include_deleted=True)
        if not category:
            return False

        if soft:
            category.is_deleted = True
            await db.flush()
        else:
            await db.delete(category)
            await db.flush()
        return True

    async def upload_image(
        self,
        db: AsyncSession,
        category_id: UUID,
        file: UploadFile,
    ) -> Optional[Category]:
        category = await self.get_by_id(db, category_id, include_deleted=False)
        if not category:
            return None

        from app.services.r2_service import upload_to_r2
        import re
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", category.name.strip().lower()).strip("-")
        ext = file.filename[-4:] if (file.filename and "." in file.filename) else ".webp"
        image_name = f"category-{slug}{ext}"
        image = await upload_to_r2(file=file, image_name=image_name)
        category.image_url = image["path"]
        await db.flush()
        await db.refresh(category)
        return category

    async def add_products(
        self,
        db: AsyncSession,
        category_id: UUID,
        product_ids: List[UUID],
    ) -> bool:
        category = await self.get_by_id(db, category_id, include_deleted=False)
        if not category:
            return False

        stmt = select(Product).where(Product.id.in_(product_ids), Product.is_deleted == False)
        result = await db.execute(stmt)
        products = result.scalars().all()
        for p in products:
            cats = list(p.category_ids or [])
            if category_id not in cats:
                cats.append(category_id)
                p.category_ids = cats
        await db.flush()
        return True

    async def remove_products(
        self,
        db: AsyncSession,
        category_id: UUID,
        product_ids: List[UUID],
    ) -> bool:
        category = await self.get_by_id(db, category_id, include_deleted=False)
        if not category:
            return False

        stmt = select(Product).where(Product.id.in_(product_ids), Product.is_deleted == False)
        result = await db.execute(stmt)
        products = result.scalars().all()
        for p in products:
            cats = list(p.category_ids or [])
            if category_id in cats:
                cats.remove(category_id)
                p.category_ids = cats
        await db.flush()
        return True


category_repository = CategoryRepository()

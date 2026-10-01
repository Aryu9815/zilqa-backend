from app.services.r2_service import upload_to_r2, delete_from_r2
import json
from decimal import Decimal
from typing import Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, update, and_, func, cast, String, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import UUID as SQLA_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.category import Category
from app.schemas.product import ProductCreate, ProductSortBy, ProductUpdate
from fastapi import UploadFile, HTTPException
import re

class ProductRepository:

    async def get_by_id(
        self,
        db: AsyncSession,
        product_id: UUID,
        is_active_only: bool = True,
        include_deleted: bool = False,
    ) -> Optional[Product]:
        conditions = [Product.id == product_id]
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
        if is_active_only:
            conditions.append(Product.is_active == True)

        stmt = select(Product).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(
        self,
        db: AsyncSession,
        product_ids: List[UUID],
        is_active_only: bool = True,
        include_deleted: bool = False,
    ) -> List[Product]:
        if not product_ids:
            return []
        conditions = [Product.id.in_(product_ids)]
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
        if is_active_only:
            conditions.append(Product.is_active == True)

        stmt = select(Product).where(and_(*conditions)).order_by(Product.name.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_products(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[UUID] = None,
        category_ids: Optional[List[UUID]] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        search: Optional[str] = None,
        sort_by: Optional[ProductSortBy] = ProductSortBy.NEWEST,
        is_active_only: bool = True,
        include_deleted: bool = False,
    ) -> Tuple[List[Product], int]:
        conditions = []

        if not include_deleted:
            conditions.append(Product.is_deleted == False)
        if is_active_only:
            conditions.append(Product.is_active == True)
        if category_id is not None:
            conditions.append(
                text("(:cid)::uuid = ANY(category_ids)").bindparams(cid=str(category_id))
            )
        if category_ids:
            ids_str = "{" + ",".join(str(i) for i in category_ids) + "}"
            conditions.append(text("category_ids && (:cids)::uuid[]").bindparams(cids=ids_str))
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        if search:
            pattern = f"%{search.strip()}%"
            conditions.append(
                Product.name.ilike(pattern)
                | Product.description.ilike(pattern)
                | Product.product_description.ilike(pattern)
            )

        where_clause = and_(*conditions) if conditions else None

        count_stmt = select(func.count()).select_from(Product)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = select(Product)
        if where_clause is not None:
            stmt = stmt.where(where_clause)

        if sort_by == ProductSortBy.PRICE_ASC:
            stmt = stmt.order_by(Product.price.asc())
        elif sort_by == ProductSortBy.PRICE_DESC:
            stmt = stmt.order_by(Product.price.desc())
        elif sort_by == ProductSortBy.OLDEST:
            stmt = stmt.order_by(Product.created_at.asc())
        elif sort_by == ProductSortBy.NAME_ASC:
            stmt = stmt.order_by(Product.name.asc())
        elif sort_by == ProductSortBy.NAME_DESC:
            stmt = stmt.order_by(Product.name.desc())
        else:
            stmt = stmt.order_by(Product.created_at.desc())

        offset = (page - 1) * limit
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, product_in: ProductCreate) -> Product:
        faqs = [
            f.model_dump() if hasattr(f, "model_dump") else dict(f)
            for f in (product_in.faqs or [])
        ]
        product = Product(
            name=product_in.name,
            # main_image_url=product_in.get('main_image_url', ''),
            other_image_urls=[],
            price=product_in.price,
            category_ids=[str(c) for c in (product_in.category_ids or [])],
            description=product_in.description,
            related_product_ids=[str(r) for r in (product_in.related_product_ids or [])],
            product_description=product_in.product_description,
            faqs=faqs,
            is_active=product_in.is_active if product_in.is_active is not None else True,
            seo_title=product_in.seo_title,
            seo_description=product_in.seo_description,
            og_title=product_in.og_title,
            og_description=product_in.og_description,
            og_image=product_in.og_image,
            slug=product_in.slug,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)
        return product

    async def update(
        self,
        db: AsyncSession,
        product_id: UUID,
        product_in: ProductUpdate,
    ) -> Optional[Product]:
        product = await self.get_by_id(db, product_id, is_active_only=False, include_deleted=False)
        if not product:
            return None

        if product_in.name is not None:
            product.name = product_in.name
        if product_in.main_image_url is not None:
            product.main_image_url = product_in.main_image_url
        if product_in.other_image_urls is not None:
            product.other_image_urls = product_in.other_image_urls
        if product_in.price is not None:
            product.price = product_in.price
        if product_in.category_ids is not None:
            product.category_ids = [str(c) for c in product_in.category_ids]
        if product_in.description is not None:
            product.description = product_in.description
        if product_in.related_product_ids is not None:
            product.related_product_ids = [str(r) for r in product_in.related_product_ids]
        if product_in.product_description is not None:
            product.product_description = product_in.product_description
        if product_in.is_active is not None:
            product.is_active = product_in.is_active
        if product_in.seo_title is not None:
            product.seo_title = product_in.seo_title
        if product_in.seo_description is not None:
            product.seo_description = product_in.seo_description
        if product_in.slug is not None:
            product.slug = product_in.slug
        if product_in.og_image is not None:
            product.og_image = product_in.og_image
        if product_in.og_title is not None:
            product.og_title = product_in.og_title
        if product_in.og_description is not None:
            product.og_description = product_in.og_description
        if product_in.faqs is not None:
            product.faqs = [
                f.model_dump() if hasattr(f, "model_dump") else dict(f)
                for f in product_in.faqs
            ]

        await db.flush()
        await db.refresh(product)
        return product

    async def delete(self, db: AsyncSession, product_id: UUID, soft: bool = True) -> bool:
        product = await db.get(Product, product_id)
        if not product:
            return False
        if soft:
            if product.is_deleted:
                return False
            product.is_deleted = True
            product.is_active = False
        else:
            await db.delete(product)
        await db.flush()
        return True




    def create_image_name(self,  product_name: str, index: int, extension: str, is_main:bool = False) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", product_name.strip().lower())
        slug = slug.strip("-")
        if is_main:
            return f"{slug}{extension}"
        return f"{slug}-{index:03d}{extension}"
    
    
    async def upload_main_image(self, db: AsyncSession, product_id: UUID, file: UploadFile):
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product:
            return None

        # Upload to R2
        image = await upload_to_r2(file=file, image_name=self.create_image_name(product.name, 0, file.filename[-4:], is_main=True))

        # Save new URL
        product.main_image_url = image["path"]

        await db.commit()
        await db.refresh(product)
        return image

    async def upload_other_images(
        self,
        db: AsyncSession,
        product_id: UUID,
        images_data: dict,
        files: List[UploadFile],
    ):
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )

        product = result.scalar_one_or_none()

        if not product:
            return None

        # Validate slots
        expected_slots = {"1", "2", "3", "4", "5"}

        if set(images_data.keys()) != expected_slots:
            print("length validation failed")
            raise HTTPException(
                status_code=400,
                detail="Images must contain slots 1, 2, 3, 4 and 5.",
            )

        # Count active images
        active_slots = [
            slot
            for slot, value in images_data.items()
            if value is not None
        ]

        if len(active_slots) < 3:
            print("minimum validation failed")
            raise HTTPException(
                status_code=400,
                detail="Minimum 3 other images are required.",
            )

        if len(active_slots) > 5:
            print("maximum validation failed")
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 other images are allowed.",
            )

        # Existing images
        existing_urls = list(
            product.other_image_urls or []
        )

        # Map frontend fileKey -> UploadFile
        file_map = {
            file.filename: file
            for file in files
            if file.filename
        }

        uploaded_files_on_r2 = []
        new_urls = []

        try:

            # Process slots in exact order
            for slot in range(1, 6):

                slot_data = images_data.get(str(slot))

                # Empty slot
                if slot_data is None:
                    continue

                if not isinstance(slot_data, dict):
                    print("invalid format")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid data for image slot {slot}.",
                    )

                is_new = slot_data.get("isNew", False)

                # Existing image
                if not is_new:

                    link = slot_data.get("link")

                    if not link:
                        print("link is required")
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Link is required for "
                                f"image slot {slot}."
                            ),
                        )

                    new_urls.append(link)

                    continue

                # New / replaced image
                file_key = slot_data.get("fileKey")
                if not file_key:
                    print("filekey is required")
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"fileKey is required for "
                            f"image slot {slot}."
                        ),
                    )
                print("file key:", file_key)
                print("files:", file_map)
                file = file_map.get(file_key)

                if not file:
                    print("file not found")
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"File '{file_key}' not found "
                            f"for image slot {slot}."
                        ),
                    )

                # Force WebP
                if file.content_type not in {
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                }:
                    print("invalid format for slot")
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid image format for slot {slot}. "
                            "Only JPG, PNG and WebP are allowed."
                        ),
                    )

                # Fixed filename for every slot
                image_name = (
                    f"{product.slug}-{slot:03d}.webp"
                )

                # Upload — this overwrites the existing R2 object if this slot already exists.
                image = await upload_to_r2(
                    file=file,
                    image_name=image_name,
                )

                uploaded_path = image["path"]

                uploaded_files_on_r2.append(
                    uploaded_path
                )

                new_urls.append(
                    uploaded_path
                )

            # Final validation
            if len(new_urls) < 3 or len(new_urls) > 5:
                print("length validation failed final")
                raise HTTPException(
                    status_code=400,
                    detail="Product must have between 3 and 5 images.",
                )

            # Update database
            product.other_image_urls = new_urls

            await db.commit()
            await db.refresh(product)

            return {
                "images": product.other_image_urls
            }

        except Exception:
            await db.rollback()
            for r2_path in uploaded_files_on_r2:
                try:
                    delete_from_r2(r2_path)
                except Exception:
                    pass
            raise        

product_repository = ProductRepository()

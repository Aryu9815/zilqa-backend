from decimal import Decimal
from typing import List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.category_repository import category_repository
from app.repositories.product_repository import product_repository
from app.schemas.common import PaginatedResponse
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductSortBy,
    ProductUpdate,
    ProductVariantBrief,
)
from app.services.offer_service import offer_service
from app.utils.helpers import calculate_pagination


class ProductService:

    async def _enrich_with_categories(self, db: AsyncSession, records: List[Any]) -> List[Any]:
        if not records:
            return records
            
        all_category_ids = set()
        for r in records:
            for cid in (r.get("category_ids") or []):
                all_category_ids.add(str(cid))
                
        category_map = {}
        if all_category_ids:
            from uuid import UUID
            uuid_cids = []
            for cid_str in all_category_ids:
                try:
                    uuid_cids.append(UUID(cid_str))
                except ValueError:
                    pass
            if uuid_cids:
                categories = await category_repository.get_by_ids(db, uuid_cids)
                category_map = {str(c.id): c.name for c in categories}
                
        for r in records:
            cids = r.get("category_ids") or []
            cat_names = [category_map[str(cid)] for cid in cids if str(cid) in category_map]
            r["category_names"] = cat_names
            
        return records

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
        is_active_only: bool = True
    ) -> PaginatedResponse[ProductResponse]:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise BadRequestException(
                message="min_price cannot be greater than max_price",
                error_code="INVALID_PRICE_RANGE"
            )

        records, total = await product_repository.list_products(
            db=db,
            page=page,
            limit=limit,
            category_id=category_id,
            category_ids=category_ids,
            min_price=min_price,
            max_price=max_price,
            search=search,
            sort_by=sort_by,
            is_active_only=is_active_only
        )
        enriched = await offer_service.enrich_product_records(db, records)
        enriched = await self._enrich_with_categories(db, enriched)
        items = [ProductResponse.model_validate(r) for r in enriched]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def _enrich_with_variants(
        self, db: AsyncSession, product_dict: Any, is_active_only: bool = True
    ) -> Any:
        raw_variants = product_dict.get("variants") or []
        variant_uuids = []
        for v in raw_variants:
            try:
                variant_uuids.append(UUID(str(v)))
            except (ValueError, TypeError):
                pass

        if not variant_uuids:
            product_dict["variant_products"] = []
            return product_dict

        variant_records = await product_repository.get_by_ids(
            db,
            variant_uuids,
            is_active_only=is_active_only,
            include_deleted=False
        )
        variant_briefs = []
        for vr in variant_records:
            variant_briefs.append(ProductVariantBrief.model_validate(vr))
        product_dict["variant_products"] = variant_briefs
        return product_dict

    async def _sync_bidirectional_variants(
        self,
        db: AsyncSession,
        product_id: UUID,
        old_variant_ids: List[UUID],
        new_variant_ids: List[UUID]
    ) -> None:
        old_set = {str(v) for v in old_variant_ids}
        new_set = {str(v) for v in new_variant_ids}
        added = new_set - old_set
        removed = old_set - new_set

        for vid_str in added:
            try:
                vid = UUID(vid_str)
                await product_repository.add_variant_to_product(db, vid, product_id)
            except (ValueError, TypeError):
                continue

        for vid_str in removed:
            try:
                vid = UUID(vid_str)
                await product_repository.remove_variant_from_product(db, vid, product_id)
            except (ValueError, TypeError):
                continue

    async def get_product(self, db: AsyncSession, product_id: UUID, is_active_only: bool = True) -> ProductResponse:
        record = await product_repository.get_by_id(db, product_id, is_active_only=is_active_only, include_deleted=False)
        if not record:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")
        enriched = await offer_service.enrich_single_product_record(db, record)
        enriched = await self._enrich_with_variants(db, enriched, is_active_only=is_active_only)
        enriched_list = await self._enrich_with_categories(db, [enriched])
        return ProductResponse.model_validate(enriched_list[0])
    
    async def get_product_by_slug(self, db: AsyncSession, product_slug: str, is_active_only: bool = True) -> ProductResponse:
        record = await product_repository.get_by_slug(db, product_slug, is_active_only=is_active_only, include_deleted=False)
        if not record:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")
        enriched = await offer_service.enrich_single_product_record(db, record)
        enriched = await self._enrich_with_variants(db, enriched, is_active_only=is_active_only)
        enriched_list = await self._enrich_with_categories(db, [enriched])
        return ProductResponse.model_validate(enriched_list[0])

    async def get_product_variants(
        self, db: AsyncSession, product_id: UUID, is_active_only: bool = True
    ) -> List[ProductResponse]:
        product = await product_repository.get_by_id(db, product_id, is_active_only=is_active_only, include_deleted=False)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        raw_variants = product.variants or []
        variant_uuids = []
        for v in raw_variants:
            try:
                variant_uuids.append(UUID(str(v)))
            except (ValueError, TypeError):
                pass

        if not variant_uuids:
            return []

        variant_records = await product_repository.get_by_ids(
            db,
            variant_uuids,
            is_active_only=is_active_only,
            include_deleted=False
        )
        if not variant_records:
            return []

        enriched = await offer_service.enrich_product_records(db, variant_records)
        enriched = await self._enrich_with_categories(db, enriched)
        return [ProductResponse.model_validate(r) for r in enriched]

    async def get_related_products(self, db: AsyncSession, product_id: UUID) -> List[ProductResponse]:
        product = await product_repository.get_by_id(db, product_id, is_active_only=True, include_deleted=False)
        if not product:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        related_ids = product.get("related_product_ids") or []
        if related_ids:
            records = await product_repository.get_by_ids(db, related_ids, is_active_only=True, include_deleted=False)
            if records:
                enriched = await offer_service.enrich_product_records(db, records)
                enriched = await self._enrich_with_categories(db, enriched)
                return [ProductResponse.model_validate(r) for r in enriched]

        # Fallback: if there are no related products, use that product's first category products
        category_ids = product.get("category_ids") or []
        if category_ids:
            first_cat_id = category_ids[0]
            cat_records, _ = await product_repository.list_products(
                db=db,
                page=1,
                limit=10,
                category_id=first_cat_id,
                is_active_only=True,
                include_deleted=False
            )
            filtered = [r for r in cat_records if r["id"] != product_id]
            enriched = await offer_service.enrich_product_records(db, filtered)
            enriched = await self._enrich_with_categories(db, enriched)
            return [ProductResponse.model_validate(r) for r in enriched]

        return []

    async def create_product(self, db: AsyncSession, product_in: ProductCreate) -> ProductResponse:
        # Validate all categories exist
        if product_in.category_ids:
            found_categories = await category_repository.get_by_ids(db, product_in.category_ids)
            found_ids = {r["id"] for r in found_categories}
            missing_ids = [str(cid) for cid in product_in.category_ids if cid not in found_ids]
            if missing_ids:
                raise BadRequestException(
                    message=f"Specified category does not exist: {', '.join(missing_ids)}",
                    error_code="CATEGORY_NOT_FOUND"
                )

        # Validate related product IDs if provided
        if product_in.related_product_ids:
            found_related = await product_repository.get_by_ids(db, product_in.related_product_ids, is_active_only=False, include_deleted=False)
            found_related_ids = {r["id"] for r in found_related}
            missing_related = [str(pid) for pid in product_in.related_product_ids if pid not in found_related_ids]
            if missing_related:
                raise BadRequestException(
                    message=f"Specified related product does not exist: {', '.join(missing_related)}",
                    error_code="RELATED_PRODUCT_NOT_FOUND"
                )

        # Validate variant IDs if provided
        if product_in.variants:
            found_variants = await product_repository.get_by_ids(db, product_in.variants, is_active_only=False, include_deleted=False)
            found_variant_ids = {p.id for p in found_variants}
            missing_variants = [str(pid) for pid in product_in.variants if pid not in found_variant_ids]
            if missing_variants:
                raise BadRequestException(
                    message=f"Specified variant product does not exist: {', '.join(missing_variants)}",
                    error_code="VARIANT_PRODUCT_NOT_FOUND"
                )

        record = await product_repository.create(db, product_in)

        # Bidirectional sync: link the newly created product to the selected variants
        if product_in.variants:
            await self._sync_bidirectional_variants(
                db=db,
                product_id=record.id,
                old_variant_ids=[],
                new_variant_ids=product_in.variants
            )

        # Fetch with category names and variants
        full_record = await product_repository.get_by_id(db, record.id, is_active_only=False, include_deleted=False)
        assert full_record is not None
        enriched = await offer_service.enrich_single_product_record(db, full_record)
        enriched = await self._enrich_with_variants(db, enriched, is_active_only=False)
        enriched_list = await self._enrich_with_categories(db, [enriched])
        return ProductResponse.model_validate(enriched_list[0])

    async def update_product(self, db: AsyncSession, product_id: UUID, product_in: ProductUpdate) -> ProductResponse:
        existing = await product_repository.get_by_id(db, product_id, is_active_only=False, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        if product_in.category_ids is not None:
            if product_in.category_ids:
                found_categories = await category_repository.get_by_ids(db, product_in.category_ids)
                found_ids = {r["id"] for r in found_categories}
                missing_ids = [str(cid) for cid in product_in.category_ids if cid not in found_ids]
                if missing_ids:
                    raise BadRequestException(
                        message=f"Specified category does not exist: {', '.join(missing_ids)}",
                        error_code="CATEGORY_NOT_FOUND"
                    )

        if product_in.related_product_ids is not None:
            if product_id in product_in.related_product_ids:
                raise BadRequestException(
                    message="A product cannot include itself in related products",
                    error_code="INVALID_RELATED_PRODUCT"
                )
            if product_in.related_product_ids:
                found_related = await product_repository.get_by_ids(db, product_in.related_product_ids, is_active_only=False, include_deleted=False)
                found_related_ids = {r["id"] for r in found_related}
                missing_related = [str(pid) for pid in product_in.related_product_ids if pid not in found_related_ids]
                if missing_related:
                    raise BadRequestException(
                        message=f"Specified related product does not exist: {', '.join(missing_related)}",
                        error_code="RELATED_PRODUCT_NOT_FOUND"
                    )

        if product_in.variants is not None:
            if product_id in product_in.variants:
                raise BadRequestException(
                    message="A product cannot include itself in variants",
                    error_code="INVALID_VARIANT_PRODUCT"
                )
            if product_in.variants:
                found_variants = await product_repository.get_by_ids(db, product_in.variants, is_active_only=False, include_deleted=False)
                found_variant_ids = {p.id for p in found_variants}
                missing_variants = [str(pid) for pid in product_in.variants if pid not in found_variant_ids]
                if missing_variants:
                    raise BadRequestException(
                        message=f"Specified variant product does not exist: {', '.join(missing_variants)}",
                        error_code="VARIANT_PRODUCT_NOT_FOUND"
                    )

            # Bidirectional sync: sync additions and removals
            old_variant_ids = []
            for v in (existing.variants or []):
                try:
                    old_variant_ids.append(UUID(str(v)))
                except (ValueError, TypeError):
                    pass
            await self._sync_bidirectional_variants(
                db=db,
                product_id=product_id,
                old_variant_ids=old_variant_ids,
                new_variant_ids=product_in.variants
            )

        record = await product_repository.update(db, product_id, product_in)
        assert record is not None
        full_record = await product_repository.get_by_id(db, product_id, is_active_only=False, include_deleted=False)
        assert full_record is not None
        enriched = await offer_service.enrich_single_product_record(db, full_record)
        enriched = await self._enrich_with_variants(db, enriched, is_active_only=False)
        enriched_list = await self._enrich_with_categories(db, [enriched])
        return ProductResponse.model_validate(enriched_list[0])

    async def delete_product(self, db: AsyncSession, product_id: UUID) -> None:
        existing = await product_repository.get_by_id(db, product_id, is_active_only=False, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")

        # Bidirectional cleanup: remove this product from all other products' variants
        await product_repository.remove_variant_from_all_products(db, product_id)

        deleted = await product_repository.delete(db, product_id, soft=True)
        if not deleted:
            raise NotFoundException(message="Product not found", error_code="PRODUCT_NOT_FOUND")


product_service = ProductService()


from typing import Optional
from uuid import UUID

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.country_repository import country_repository
from app.schemas.common import PaginatedResponse
from app.schemas.country import CountryCreate, CountryResponse, CountryUpdate
from app.utils.helpers import calculate_pagination


class CountryService:

    async def list_countries(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_deleted: bool = False
    ) -> PaginatedResponse[CountryResponse]:
        records, total = await country_repository.list_countries(
            page=page,
            limit=limit,
            search=search,
            is_active=is_active,
            include_deleted=include_deleted
        )
        items = [CountryResponse.model_validate(dict(r)) for r in records]
        pagination = calculate_pagination(total=total, page=page, limit=limit)
        return PaginatedResponse(data=items, pagination=pagination)

    async def get_country(self, country_id: UUID, is_active_only: bool = False, include_deleted: bool = False) -> CountryResponse:
        record = await country_repository.get_by_id(country_id, is_active_only=is_active_only, include_deleted=include_deleted)
        if not record:
            raise NotFoundException(message="Country not found", error_code="COUNTRY_NOT_FOUND")
        return CountryResponse.model_validate(dict(record))

    async def create_country(self, country_in: CountryCreate) -> CountryResponse:
        existing_name = await country_repository.get_by_name(country_in.name, include_deleted=True)
        if existing_name:
            if existing_name["is_deleted"]:
                raise ConflictException(
                    message=f"Country with name '{country_in.name}' was previously deleted. Please restore or update it.",
                    error_code="COUNTRY_NAME_EXISTS_DELETED"
                )
            raise ConflictException(
                message=f"Country with name '{country_in.name}' already exists",
                error_code="COUNTRY_NAME_EXISTS"
            )

        existing_code = await country_repository.get_by_code(country_in.code, include_deleted=True)
        if existing_code:
            if existing_code["is_deleted"]:
                raise ConflictException(
                    message=f"Country with code '{country_in.code}' was previously deleted.",
                    error_code="COUNTRY_CODE_EXISTS_DELETED"
                )
            raise ConflictException(
                message=f"Country with code '{country_in.code}' already exists",
                error_code="COUNTRY_CODE_EXISTS"
            )

        record = await country_repository.create(country_in)
        return CountryResponse.model_validate(dict(record))

    async def update_country(self, country_id: UUID, country_in: CountryUpdate) -> CountryResponse:
        existing = await country_repository.get_by_id(country_id, include_deleted=False)
        if not existing:
            raise NotFoundException(message="Country not found", error_code="COUNTRY_NOT_FOUND")

        if country_in.name and country_in.name.lower() != existing["name"].lower():
            duplicate_name = await country_repository.get_by_name(
                country_in.name,
                exclude_id=country_id,
                include_deleted=True
            )
            if duplicate_name:
                raise ConflictException(
                    message=f"Country with name '{country_in.name}' already exists",
                    error_code="COUNTRY_NAME_EXISTS"
                )

        if country_in.code and country_in.code.strip().upper() != existing["code"].strip().upper():
            duplicate_code = await country_repository.get_by_code(
                country_in.code,
                exclude_id=country_id,
                include_deleted=True
            )
            if duplicate_code:
                raise ConflictException(
                    message=f"Country with code '{country_in.code}' already exists",
                    error_code="COUNTRY_CODE_EXISTS"
                )

        record = await country_repository.update(country_id, country_in)
        if not record:
            raise NotFoundException(message="Country not found", error_code="COUNTRY_NOT_FOUND")
        return CountryResponse.model_validate(dict(record))

    async def delete_country(self, country_id: UUID, soft: bool = True) -> None:
        deleted = await country_repository.delete(country_id, soft=soft)
        if not deleted:
            raise NotFoundException(message="Country not found", error_code="COUNTRY_NOT_FOUND")


country_service = CountryService()

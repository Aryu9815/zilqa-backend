from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Country
from app.schemas.country import CountryCreate, CountryUpdate


class CountryRepository:

    async def get_by_id(
        self,
        db: AsyncSession,
        country_id: UUID,
        is_active_only: bool = False,
        include_deleted: bool = False,
    ) -> Optional[Country]:
        conditions = [Country.id == country_id]
        if not include_deleted:
            conditions.append(Country.is_deleted == False)
        if is_active_only:
            conditions.append(Country.is_active == True)

        stmt = select(Country).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        exclude_id: Optional[UUID] = None,
        include_deleted: bool = False,
    ) -> Optional[Country]:
        conditions = [func.lower(Country.name) == func.lower(name.strip())]

        if exclude_id is not None:
            conditions.append(Country.id != exclude_id)

        if not include_deleted:
            conditions.append(Country.is_deleted == False)

        stmt = select(Country).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        db: AsyncSession,
        code: str,
        exclude_id: Optional[UUID] = None,
        include_deleted: bool = False,
    ) -> Optional[Country]:
        conditions = [func.lower(func.trim(Country.code)) == func.lower(code.strip())]

        if exclude_id is not None:
            conditions.append(Country.id != exclude_id)

        if not include_deleted:
            conditions.append(Country.is_deleted == False)

        stmt = select(Country).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_countries(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_deleted: bool = False,
    ) -> Tuple[List[Country], int]:
        conditions = []

        if not include_deleted:
            conditions.append(Country.is_deleted == False)

        if is_active is not None:
            conditions.append(Country.is_active == is_active)

        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(
                (Country.name.ilike(search_pattern)) | (func.trim(Country.code).ilike(search_pattern))
            )

        where_clause = and_(*conditions) if conditions else None

        count_stmt = select(func.count()).select_from(Country)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = select(Country)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        
        stmt = stmt.order_by(Country.name.asc())

        offset = (page - 1) * limit
        stmt = stmt.limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def create(
        self,
        db: AsyncSession,
        country_in: CountryCreate,
    ) -> Country:
        country = Country(
            name=country_in.name,
            code=country_in.code,
            rate_from_usd=country_in.rate_from_usd,
            exchange_available=country_in.exchange_available,
            is_active=country_in.is_active if country_in.is_active is not None else True,
            is_deleted=False
        )
        db.add(country)
        await db.flush()
        await db.refresh(country)
        return country

    async def update(
        self,
        db: AsyncSession,
        country_id: UUID,
        country_in: CountryUpdate,
    ) -> Optional[Country]:
        country = await self.get_by_id(db, country_id, include_deleted=True)
        if not country or country.is_deleted:
            return None

        if country_in.name is not None:
            country.name = country_in.name
        if country_in.code is not None:
            country.code = country_in.code
        if country_in.rate_from_usd is not None:
            country.rate_from_usd = country_in.rate_from_usd
        if country_in.exchange_available is not None:
            country.exchange_available = country_in.exchange_available
        if country_in.is_active is not None:
            country.is_active = country_in.is_active

        await db.flush()
        await db.refresh(country)
        return country

    async def delete(
        self,
        db: AsyncSession,
        country_id: UUID,
        soft: bool = True,
    ) -> bool:
        country = await self.get_by_id(db, country_id, include_deleted=False)
        if not country:
            return False

        if soft:
            country.is_deleted = True
            country.is_active = False
            await db.flush()
        else:
            await db.delete(country)
            await db.flush()
        return True


country_repository = CountryRepository()


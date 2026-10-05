import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.core.database import init_db_pool, close_db_pool
from app.services.country_service import (
    country_service,
    get_exchange_rate_currency_for_country,
    get_exchage_rate_currency_for_country,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db_pool()
    yield
    await close_db_pool()


@pytest.mark.asyncio
async def test_get_exchange_rate_helper():
    # Test helper functions with US
    rate_info = await get_exchange_rate_currency_for_country("US")
    assert rate_info is not None
    assert rate_info["country_code"] == "US"
    # Exchange rate is None if exchange_available is False
    if not rate_info["exchange_available"]:
        assert rate_info["exchange_rate"] is None

    # Test alias spelling
    rate_info_alias = await get_exchage_rate_currency_for_country("US")
    assert rate_info_alias == rate_info

    # Nonexistent country code
    non_existent = await get_exchange_rate_currency_for_country("NONEXISTENT")
    assert non_existent is None


@pytest.mark.asyncio
async def test_location_endpoints_without_login(client: AsyncClient):
    # 1. Test /api/v1/auth/location
    resp_auth = await client.get("/api/v1/auth/location")
    assert resp_auth.status_code == 200
    data_auth = resp_auth.json()
    assert "country_code" in data_auth
    assert "exchange_rate" in data_auth
    assert data_auth["country_code"] == "US"

    # 2. Test /api/v1/countries/location
    resp_countries = await client.get("/api/v1/countries/location")
    assert resp_countries.status_code == 200
    data_countries = resp_countries.json()
    assert data_countries["country_code"] == "US"

    # 3. Test /api/v1/location
    resp_root = await client.get("/api/v1/location")
    assert resp_root.status_code == 200
    data_root = resp_root.json()
    assert data_root["country_code"] == "US"

    # 4. Test query parameter override for country_code
    resp_override = await client.get("/api/v1/location?country_code=IN")
    assert resp_override.status_code == 200
    data_override = resp_override.json()
    assert data_override["country_code"] == "IN"

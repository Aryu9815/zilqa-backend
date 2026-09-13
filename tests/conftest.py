import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict
from uuid import UUID, uuid4
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture configured for ASGI FastAPI testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_admin_user() -> Dict:
    return {
        "id": UUID("a0000000-0000-0000-0000-000000000001"),
        "name": "System Administrator",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def test_customer_user() -> Dict:
    return {
        "id": UUID("a0000000-0000-0000-0000-000000000002"),
        "name": "Jane Customer",
        "email": "jane@example.com",
        "role": "customer",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def admin_token(test_admin_user: Dict) -> str:
    return create_access_token(subject=test_admin_user["id"], role=test_admin_user["role"])


@pytest.fixture
def customer_token(test_customer_user: Dict) -> str:
    return create_access_token(subject=test_customer_user["id"], role=test_customer_user["role"])


@pytest.fixture
def admin_auth_headers(admin_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def customer_auth_headers(customer_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {customer_token}"}

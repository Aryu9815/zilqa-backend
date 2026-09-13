import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.api.router import api_router
from app.core.config import settings
from app.core.database import close_db_pool, init_db_pool
from app.core.exceptions import APIException
from app.schemas.common import ErrorResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zilqa_backend")

UPLOAD_DIR = Path("app/uploads")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    logger.info("Starting up FastAPI E-Commerce application...")

    await init_db_pool()

    logger.info("FastAPI E-Commerce application started successfully.")

    yield

    logger.info("Shutting down FastAPI E-Commerce application...")

    await close_db_pool()

    logger.info("FastAPI E-Commerce application shut down successfully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Production-grade, asynchronous E-Commerce Backend API built with FastAPI, "
        "PostgreSQL, and asyncpg. Supports customer checkout, authentication with JWT & refresh tokens, "
        "product catalog search & filters, address management, cart & wishlist operations, "
        "and administrative dashboard analytics."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication", "description": "Registration, Login, Token Refresh & Revocation"},
        {"name": "Users", "description": "Customer Profile & Account Management"},
        {"name": "Addresses", "description": "Shipping Address Management & Default Selector"},
        {"name": "Countries", "description": "Country Management for Shipping & Address Selection"},
        {"name": "Categories", "description": "Product Category Management & Browsing"},
        {"name": "Products", "description": "Product Catalog, Search, Filtering & Admin CRUD"},
        {"name": "Cart", "description": "Shopping Cart & Live Subtotal Computation"},
        {"name": "Wishlist", "description": "Customer Wishlist Operations"},
        {"name": "Orders", "description": "Order Placement & Customer Order History"},
        {"name": "Admin Orders", "description": "Admin Order Fulfillment & Status Transitions"},
        {"name": "Admin Analytics", "description": "Revenue, Orders & Top Products Dashboard Analytics"},
        {"name": "Health", "description": "System & Database Health Probes"},
    ]
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(APIException)
async def custom_api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(f"APIException on {request.method} {request.url.path}: {exc.message} [{exc.error_code}]")
    error_payload = ErrorResponse(
        success=False,
        message=exc.message,
        error_code=exc.error_code,
        errors=exc.errors
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    logger.info(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    error_payload = ErrorResponse(
        success=False,
        message="Request validation failed. Please check your input parameters.",
        error_code="VALIDATION_ERROR",
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload.model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard FastAPI HTTPExceptions."""
    error_payload = ErrorResponse(
        success=False,
        message=str(exc.detail),
        error_code="HTTP_ERROR"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump()
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled server exceptions without leaking internal details."""
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    error_payload = ErrorResponse(
        success=False,
        message="An unexpected server error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump()
    )


# =============================================================================
# MOUNT ROUTERS
# =============================================================================

app.include_router(health.router)
app.include_router(api_router, prefix=settings.API_V1_STR)

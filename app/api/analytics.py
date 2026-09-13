from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_admin
from app.schemas.analytics import (
    AnalyticsTimeRange,
    OrderAnalyticsResponse,
    OverviewAnalyticsResponse,
    RecentOrderResponse,
    RevenueAnalyticsResponse,
    TopCategoryResponse,
    TopProductResponse,
)
from app.schemas.common import ResponseEnvelope
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get(
    "/overview",
    response_model=ResponseEnvelope[OverviewAnalyticsResponse],
    summary="Get overall e-commerce KPI metrics (Admin only)"
)
async def get_overview(
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OverviewAnalyticsResponse]:
    overview = await analytics_service.get_overview()
    return ResponseEnvelope(
        success=True,
        message="Overview analytics retrieved successfully",
        data=overview
    )


@router.get(
    "/revenue",
    response_model=ResponseEnvelope[RevenueAnalyticsResponse],
    summary="Get aggregated revenue analytics for charts (Admin only)"
)
async def get_revenue(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.THIRTY_DAYS, description="Date preset range"),
    start_date: Optional[datetime] = Query(None, description="Custom start datetime (ISO)"),
    end_date: Optional[datetime] = Query(None, description="Custom end datetime (ISO)"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[RevenueAnalyticsResponse]:
    revenue_data = await analytics_service.get_revenue_analytics(
        time_range=time_range,
        start_date=start_date,
        end_date=end_date
    )
    return ResponseEnvelope(
        success=True,
        message="Revenue analytics retrieved successfully",
        data=revenue_data
    )


@router.get(
    "/orders",
    response_model=ResponseEnvelope[OrderAnalyticsResponse],
    summary="Get order status breakdowns and time-series volume (Admin only)"
)
async def get_orders(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.THIRTY_DAYS, description="Date preset range"),
    start_date: Optional[datetime] = Query(None, description="Custom start datetime (ISO)"),
    end_date: Optional[datetime] = Query(None, description="Custom end datetime (ISO)"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[OrderAnalyticsResponse]:
    order_data = await analytics_service.get_order_analytics(
        time_range=time_range,
        start_date=start_date,
        end_date=end_date
    )
    return ResponseEnvelope(
        success=True,
        message="Order analytics retrieved successfully",
        data=order_data
    )


@router.get(
    "/recent-orders",
    response_model=ResponseEnvelope[List[RecentOrderResponse]],
    summary="Get most recent customer orders (Admin only)"
)
async def get_recent_orders(
    limit: int = Query(10, ge=1, le=100, description="Number of recent orders to fetch"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[List[RecentOrderResponse]]:
    recent_orders = await analytics_service.get_recent_orders(limit=limit)
    return ResponseEnvelope(
        success=True,
        message="Recent orders retrieved successfully",
        data=recent_orders
    )


@router.get(
    "/top-products",
    response_model=ResponseEnvelope[List[TopProductResponse]],
    summary="Get top selling products by units & revenue (Admin only)"
)
async def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Top products limit"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[List[TopProductResponse]]:
    top_products = await analytics_service.get_top_products(limit=limit)
    return ResponseEnvelope(
        success=True,
        message="Top products retrieved successfully",
        data=top_products
    )


@router.get(
    "/top-categories",
    response_model=ResponseEnvelope[List[TopCategoryResponse]],
    summary="Get top selling categories by units & revenue (Admin only)"
)
async def get_top_categories(
    limit: int = Query(10, ge=1, le=100, description="Top categories limit"),
    current_admin: Dict[str, Any] = Depends(require_admin)
) -> ResponseEnvelope[List[TopCategoryResponse]]:
    top_categories = await analytics_service.get_top_categories(limit=limit)
    return ResponseEnvelope(
        success=True,
        message="Top categories retrieved successfully",
        data=top_categories
    )

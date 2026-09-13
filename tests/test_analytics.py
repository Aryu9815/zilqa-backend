from decimal import Decimal
from uuid import uuid4

from app.schemas.analytics import (
    AnalyticsTimeRange,
    OrderAnalyticsResponse,
    OrderStatusBreakdown,
    OverviewAnalyticsResponse,
    RecentOrderResponse,
    RevenueAnalyticsResponse,
    RevenueDataPoint,
    TopCategoryResponse,
    TopProductResponse,
)
from app.utils.helpers import resolve_date_range


def test_analytics_date_range_resolver():
    start, end = resolve_date_range(AnalyticsTimeRange.SEVEN_DAYS)
    assert start < end
    diff = end - start
    assert diff.days >= 6


def test_analytics_overview_schema():
    overview = OverviewAnalyticsResponse(
        total_revenue=Decimal("125000.00"),
        total_orders=150,
        total_customers=85,
        total_products=42,
        pending_orders=5,
        completed_orders=130
    )
    assert overview.total_revenue == Decimal("125000.00")
    assert overview.total_orders == 150


def test_revenue_analytics_schema():
    revenue = RevenueAnalyticsResponse(
        total_revenue=Decimal("15000.00"),
        data=[
            RevenueDataPoint(date="2026-09-01", revenue=Decimal("5000.00")),
            RevenueDataPoint(date="2026-09-02", revenue=Decimal("10000.00")),
        ]
    )
    assert len(revenue.data) == 2
    assert revenue.total_revenue == Decimal("15000.00")


def test_top_products_schema():
    top_prod = TopProductResponse(
        product_id=uuid4(),
        product_name="India Flag Ring",
        units_sold=25,
        revenue=Decimal("24975.00")
    )
    assert top_prod.units_sold == 25
    assert top_prod.revenue == Decimal("24975.00")

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from app.repositories.analytics_repository import analytics_repository
from app.schemas.analytics import (
    AnalyticsTimeRange,
    OrderAnalyticsResponse,
    OrderChartDataPoint,
    OrderStatusBreakdown,
    OverviewAnalyticsResponse,
    RecentOrderResponse,
    RevenueAnalyticsResponse,
    RevenueDataPoint,
    TopCategoryResponse,
    TopProductResponse,
)
from app.utils.helpers import resolve_date_range


class AnalyticsService:

    async def get_overview(self) -> OverviewAnalyticsResponse:
        data = await analytics_repository.get_overview()
        return OverviewAnalyticsResponse(
            total_revenue=Decimal(str(data["total_revenue"])),
            total_orders=int(data["total_orders"]),
            total_customers=int(data["total_customers"]),
            total_products=int(data["total_products"]),
            pending_orders=int(data["pending_orders"]),
            completed_orders=int(data["completed_orders"])
        )

    async def get_revenue_analytics(
        self,
        time_range: AnalyticsTimeRange = AnalyticsTimeRange.THIRTY_DAYS,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RevenueAnalyticsResponse:
        resolved_start, resolved_end = resolve_date_range(time_range, start_date, end_date)
        total_rev, series = await analytics_repository.get_revenue_time_series(resolved_start, resolved_end)
        
        points = [
            RevenueDataPoint(
                date=r["date"],
                revenue=Decimal(str(r["revenue"]))
            )
            for r in series
        ]
        return RevenueAnalyticsResponse(
            total_revenue=Decimal(str(total_rev)),
            data=points
        )

    async def get_order_analytics(
        self,
        time_range: AnalyticsTimeRange = AnalyticsTimeRange.THIRTY_DAYS,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> OrderAnalyticsResponse:
        resolved_start, resolved_end = resolve_date_range(time_range, start_date, end_date)
        breakdown_dict, chart_records = await analytics_repository.get_order_analytics(resolved_start, resolved_end)

        breakdown = OrderStatusBreakdown(
            total_orders=int(breakdown_dict.get("total_orders", 0)),
            pending_orders=int(breakdown_dict.get("pending_orders", 0)),
            confirmed_orders=int(breakdown_dict.get("confirmed_orders", 0)),
            processing_orders=int(breakdown_dict.get("processing_orders", 0)),
            shipped_orders=int(breakdown_dict.get("shipped_orders", 0)),
            delivered_orders=int(breakdown_dict.get("delivered_orders", 0)),
            cancelled_orders=int(breakdown_dict.get("cancelled_orders", 0))
        )

        chart_points = [
            OrderChartDataPoint(
                date=r["date"],
                orders_count=int(r["orders_count"])
            )
            for r in chart_records
        ]

        return OrderAnalyticsResponse(
            breakdown=breakdown,
            chart_data=chart_points
        )

    async def get_recent_orders(self, limit: int = 10) -> List[RecentOrderResponse]:
        records = await analytics_repository.get_recent_orders(limit=limit)
        return [
            RecentOrderResponse(
                order_id=r["order_id"],
                customer_name=r["customer_name"],
                customer_email=r["customer_email"],
                total_amount=Decimal(str(r["total_amount"])),
                status=r["status"],
                payment_status=r["payment_status"],
                created_at=r["created_at"]
            )
            for r in records
        ]

    async def get_top_products(self, limit: int = 10) -> List[TopProductResponse]:
        records = await analytics_repository.get_top_products(limit=limit)
        return [
            TopProductResponse(
                product_id=r["product_id"],
                product_name=r["product_name"],
                units_sold=int(r["units_sold"]),
                revenue=Decimal(str(r["revenue"]))
            )
            for r in records
        ]

    async def get_top_categories(self, limit: int = 10) -> List[TopCategoryResponse]:
        records = await analytics_repository.get_top_categories(limit=limit)
        return [
            TopCategoryResponse(
                category_id=r["category_id"],
                category_name=r["category_name"],
                units_sold=int(r["units_sold"]),
                revenue=Decimal(str(r["revenue"]))
            )
            for r in records
        ]


analytics_service = AnalyticsService()

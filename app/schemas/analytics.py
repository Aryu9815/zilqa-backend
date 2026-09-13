from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AnalyticsTimeRange(str, Enum):
    TODAY = "today"
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    NINETY_DAYS = "90_days"
    ONE_YEAR = "1_year"
    CUSTOM = "custom"


class OverviewAnalyticsResponse(BaseModel):
    total_revenue: Decimal = Decimal("0.00")
    total_orders: int = 0
    total_customers: int = 0
    total_products: int = 0
    pending_orders: int = 0
    completed_orders: int = 0


class RevenueDataPoint(BaseModel):
    date: str
    revenue: Decimal


class RevenueAnalyticsResponse(BaseModel):
    total_revenue: Decimal
    data: List[RevenueDataPoint] = []


class OrderStatusBreakdown(BaseModel):
    total_orders: int = 0
    pending_orders: int = 0
    confirmed_orders: int = 0
    processing_orders: int = 0
    shipped_orders: int = 0
    delivered_orders: int = 0
    cancelled_orders: int = 0


class OrderChartDataPoint(BaseModel):
    date: str
    orders_count: int


class OrderAnalyticsResponse(BaseModel):
    breakdown: OrderStatusBreakdown
    chart_data: List[OrderChartDataPoint] = []


class RecentOrderResponse(BaseModel):
    order_id: UUID
    customer_name: str
    customer_email: str
    total_amount: Decimal
    status: str
    payment_status: str
    created_at: datetime


class TopProductResponse(BaseModel):
    product_id: Optional[UUID] = None
    product_name: str
    units_sold: int
    revenue: Decimal


class TopCategoryResponse(BaseModel):
    category_id: Optional[UUID] = None
    category_name: str
    units_sold: int
    revenue: Decimal

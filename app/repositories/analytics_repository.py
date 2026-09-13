from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg

from app.repositories.base_repository import BaseRepository


class AnalyticsRepository(BaseRepository):

    async def get_overview(
        self,
        connection: Optional[asyncpg.Connection] = None
    ) -> Dict[str, Any]:
        query = """
            SELECT
                COALESCE((
                    SELECT SUM(total_amount)
                    FROM orders
                    WHERE status != 'cancelled' AND payment_status = 'paid'
                ), 0.00) AS total_revenue,
                (SELECT COUNT(*) FROM orders) AS total_orders,
                (SELECT COUNT(*) FROM users WHERE role = 'customer') AS total_customers,
                (SELECT COUNT(*) FROM products WHERE is_active = TRUE) AS total_products,
                (SELECT COUNT(*) FROM orders WHERE status = 'pending') AS pending_orders,
                (SELECT COUNT(*) FROM orders WHERE status = 'delivered') AS completed_orders;
        """
        row = await self.fetch_one(query, connection=connection)
        if not row:
            return {
                "total_revenue": Decimal("0.00"),
                "total_orders": 0,
                "total_customers": 0,
                "total_products": 0,
                "pending_orders": 0,
                "completed_orders": 0,
            }
        return dict(row)

    async def get_revenue_time_series(
        self,
        start_date: datetime,
        end_date: datetime,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[Decimal, List[asyncpg.Record]]:
        total_query = """
            SELECT COALESCE(SUM(total_amount), 0.00)
            FROM orders
            WHERE status != 'cancelled' 
              AND payment_status = 'paid'
              AND created_at >= $1 AND created_at <= $2
        """
        total_revenue = await self.fetch_val(total_query, start_date, end_date, connection=connection) or Decimal("0.00")

        series_query = """
            SELECT 
                TO_CHAR(DATE_TRUNC('day', created_at), 'YYYY-MM-DD') AS date,
                COALESCE(SUM(total_amount), 0.00) AS revenue
            FROM orders
            WHERE status != 'cancelled' 
              AND payment_status = 'paid'
              AND created_at >= $1 AND created_at <= $2
            GROUP BY DATE_TRUNC('day', created_at)
            ORDER BY DATE_TRUNC('day', created_at) ASC;
        """
        records = await self.fetch_all(series_query, start_date, end_date, connection=connection)
        return total_revenue, records

    async def get_order_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        connection: Optional[asyncpg.Connection] = None
    ) -> Tuple[Dict[str, int], List[asyncpg.Record]]:
        breakdown_query = """
            SELECT
                COUNT(*) AS total_orders,
                COUNT(*) FILTER (WHERE status = 'pending') AS pending_orders,
                COUNT(*) FILTER (WHERE status = 'confirmed') AS confirmed_orders,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing_orders,
                COUNT(*) FILTER (WHERE status = 'shipped') AS shipped_orders,
                COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_orders,
                COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders
            FROM orders
            WHERE created_at >= $1 AND created_at <= $2;
        """
        breakdown_row = await self.fetch_one(breakdown_query, start_date, end_date, connection=connection)
        breakdown = dict(breakdown_row) if breakdown_row else {
            "total_orders": 0,
            "pending_orders": 0,
            "confirmed_orders": 0,
            "processing_orders": 0,
            "shipped_orders": 0,
            "delivered_orders": 0,
            "cancelled_orders": 0
        }

        series_query = """
            SELECT 
                TO_CHAR(DATE_TRUNC('day', created_at), 'YYYY-MM-DD') AS date,
                COUNT(*) AS orders_count
            FROM orders
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY DATE_TRUNC('day', created_at)
            ORDER BY DATE_TRUNC('day', created_at) ASC;
        """
        chart_data = await self.fetch_all(series_query, start_date, end_date, connection=connection)
        return breakdown, chart_data

    async def get_recent_orders(
        self,
        limit: int = 10,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT o.id AS order_id, u.name AS customer_name, u.email AS customer_email,
                   o.total_amount, o.status, o.payment_status, o.created_at
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT $1
        """
        return await self.fetch_all(query, limit, connection=connection)

    async def get_top_products(
        self,
        limit: int = 10,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT 
                oi.product_id,
                oi.product_name,
                COALESCE(SUM(oi.quantity), 0) AS units_sold,
                COALESCE(SUM(oi.subtotal), 0.00) AS revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY oi.product_id, oi.product_name
            ORDER BY revenue DESC, units_sold DESC
            LIMIT $1
        """
        return await self.fetch_all(query, limit, connection=connection)

    async def get_top_categories(
        self,
        limit: int = 10,
        connection: Optional[asyncpg.Connection] = None
    ) -> List[asyncpg.Record]:
        query = """
            SELECT 
                c.id AS category_id,
                c.name AS category_name,
                COALESCE(SUM(oi.quantity), 0) AS units_sold,
                COALESCE(SUM(oi.subtotal), 0.00) AS revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN products p ON oi.product_id = p.id
            LEFT JOIN categories c ON c.id = ANY(p.category_ids)
            WHERE o.status != 'cancelled' AND c.id IS NOT NULL
            GROUP BY c.id, c.name
            ORDER BY revenue DESC, units_sold DESC
            LIMIT $1
        """
        return await self.fetch_all(query, limit, connection=connection)


analytics_repository = AnalyticsRepository()

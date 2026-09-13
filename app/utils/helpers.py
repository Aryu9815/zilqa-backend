import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import asyncpg

from app.core.config import settings
from app.schemas.analytics import AnalyticsTimeRange
from app.schemas.common import PaginationMeta


def resolve_media_url(url: Optional[str]) -> Optional[str]:
    """Prefix a relative media path (e.g. /image/name.jpg) with R2_PUBLIC_URL if configured."""
    if not url:
        return url
    url_str = str(url).strip()
    if not url_str:
        return url_str
    if url_str.startswith(("http://", "https://", "data:", "blob:")):
        return url_str

    r2_public_url = getattr(settings, "R2_PUBLIC_URL", "")
    if not r2_public_url:
        return url_str

    prefix = str(r2_public_url).strip().rstrip("/")
    if not prefix:
        return url_str

    path = url_str.lstrip("/")
    return f"{prefix}/{path}"


def resolve_media_urls(urls: Optional[List[str]]) -> List[str]:
    """Prefix a list of relative media paths with R2_PUBLIC_URL if configured."""
    if not urls:
        return []
    return [resolve_media_url(u) for u in urls if u is not None]


def strip_media_url_prefix(url: Optional[str]) -> Optional[str]:
    """Strip R2_PUBLIC_URL prefix from incoming media URL so DB stores relative path."""
    if not url:
        return url
    url_str = str(url).strip()
    r2_public_url = getattr(settings, "R2_PUBLIC_URL", "")
    if r2_public_url:
        prefix = str(r2_public_url).strip().rstrip("/")
        if prefix and url_str.startswith(prefix):
            rel = url_str[len(prefix):].lstrip("/")
            return f"/{rel}"
    return url_str


def strip_media_urls_prefix(urls: Optional[List[str]]) -> List[str]:
    """Strip R2_PUBLIC_URL prefix from a list of media URLs."""
    if not urls:
        return []
    return [strip_media_url_prefix(u) for u in urls if u is not None]


def record_to_dict(record: Optional[asyncpg.Record]) -> Optional[Dict[str, Any]]:
    """Convert an asyncpg Record to a standard Python dictionary."""
    if record is None:
        return None
    return dict(record)


def records_to_list(records: Sequence[asyncpg.Record]) -> List[Dict[str, Any]]:
    """Convert a sequence of asyncpg Records to a list of standard dictionaries."""
    return [dict(r) for r in records]


def calculate_pagination(total: int, page: int, limit: int) -> PaginationMeta:
    """Calculate total pages and return standard PaginationMeta."""
    total_pages = math.ceil(total / limit) if limit > 0 else 0
    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages
    )


def resolve_date_range(
    time_range: AnalyticsTimeRange,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """Calculate start and end timestamps for analytics queries based on time range."""
    now = datetime.now(timezone.utc)
    
    if time_range == AnalyticsTimeRange.TODAY:
        start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        return start, now
    elif time_range == AnalyticsTimeRange.SEVEN_DAYS:
        start = now - timedelta(days=7)
        return start, now
    elif time_range == AnalyticsTimeRange.THIRTY_DAYS:
        start = now - timedelta(days=30)
        return start, now
    elif time_range == AnalyticsTimeRange.NINETY_DAYS:
        start = now - timedelta(days=90)
        return start, now
    elif time_range == AnalyticsTimeRange.ONE_YEAR:
        start = now - timedelta(days=365)
        return start, now
    elif time_range == AnalyticsTimeRange.CUSTOM:
        if not start_date:
            start_date = now - timedelta(days=30)
        if not end_date:
            end_date = now
        return start_date, end_date
    
    return now - timedelta(days=30), now

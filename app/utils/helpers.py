import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import asyncpg
import httpx
from fastapi import Request
import ipaddress
from app.core.config import settings
from app.schemas.analytics import AnalyticsTimeRange
from app.schemas.common import PaginationMeta


def get_client_ip(request: Request) -> str:
    """Extract client IP address from FastAPI request, checking proxy headers first."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


# async def get_country_from_ip(ip: Optional[str]) -> Optional[str]:
#     """
#     Fetch ISO country code from IP address using ipapi.co.
#     Returns country code (e.g. 'US', 'IN') or None if lookup fails or IP is local/private.
#     """
#     if not ip:
#         return None
#     ip_clean = ip.strip()
#     if not ip_clean or ip_clean in ("127.0.0.1", "::1", "localhost", "testclient"):
#         print("local")
#         return None
#     if ip_clean.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
#         return None

#     url = f"https://ipapi.co/{ip_clean}/json/"
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.get(url, headers={"User-Agent": "zelqa-backend"})
#             response.raise_for_status()
#             data = response.json()
#             code = data.get("country_code")
#             return code.strip().upper() if code else None
#     except Exception:
#         return None



async def get_country_from_ip(ip: Optional[str]) -> Optional[str]:
    """
    Fetch ISO country code from IP address using ipapi.co.

    Returns:
        Country code such as 'US' or 'IN'
        None if the IP is missing, local/private, invalid,
        or the lookup fails.
    """

    if not ip:
        return None

    ip_clean = ip.strip()

    # Local/test values
    if ip_clean in ("localhost", "testclient"):
        print("Local/test IP")
        return None

    # Validate IP and reject private/local/reserved addresses
    try:
        ip_obj = ipaddress.ip_address(ip_clean)

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            print(f"Local/private/reserved IP: {ip_clean}")
            return None

    except ValueError:
        print(f"Invalid IP address: {ip_clean}")
        return None

    url = f"https://ipapi.co/{ip_clean}/json/"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "zilqa-backend"}
            )

            response.raise_for_status()

            data = response.json()

            country_code = data.get("country_code")

            if country_code:
                return country_code.strip().upper()

            return None

    except httpx.HTTPError as e:
        print(f"IP geolocation request failed: {e}")
        return None

    except Exception as e:
        print(f"IP geolocation error: {e}")
        return None

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


COUNTRY_CURRENCY_MAP: Dict[str, str] = {
    "IN": "INR",
    "US": "USD",
    "CA": "CAD",
    "GB": "GBP",
    "AU": "AUD",
    "DE": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "ES": "EUR",
    "NL": "EUR",
    "BE": "EUR",
    "AT": "EUR",
    "IE": "EUR",
    "PT": "EUR",
    "GR": "EUR",
    "FI": "EUR",
    "AE": "AED",
    "SA": "SAR",
    "SG": "SGD",
    "JP": "JPY",
    "KR": "KRW",
    "CH": "CHF",
    "NZ": "NZD",
    "MX": "MXN",
    "BR": "BRL",
    "SE": "SEK",
    "NO": "NOK",
    "DK": "DKK",
    "ZA": "ZAR",
    "MY": "MYR",
    "TH": "THB",
    "ID": "IDR",
    "PH": "PHP",
    "VN": "VND",
    "TR": "TRY",
    "PL": "PLN",
    "CZ": "CZK",
    "HU": "HUF",
    "RO": "RON",
    "IL": "ILS",
    "QA": "QAR",
    "KW": "KWD",
    "OM": "OMR",
    "BH": "BHD",
    "EG": "EGP",
    "AR": "ARS",
    "CL": "CLP",
    "CO": "COP",
    "HK": "HKD",
    "TW": "TWD",
}

CODE_TO_COUNTRY_NAME: Dict[str, str] = {
    "US": "United States",
    "IN": "India",
    "CA": "Canada",
    "GB": "United Kingdom",
    "AU": "Australia",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "SG": "Singapore",
    "JP": "Japan",
    "CH": "Switzerland",
    "NL": "Netherlands",
    "ES": "Spain",
    "MX": "Mexico",
    "BR": "Brazil",
    "NZ": "New Zealand",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "IE": "Ireland",
    "BE": "Belgium",
    "AT": "Austria",
    "KR": "South Korea",
    "ZA": "South Africa",
}


def get_currency_for_country(country_code: Optional[str]) -> str:
    """Return currency code (e.g. 'USD', 'INR') corresponding to the ISO country code."""
    if not country_code:
        return "USD"
    return COUNTRY_CURRENCY_MAP.get(country_code.strip().upper(), "USD")


def get_country_name_for_code(country_code: Optional[str]) -> str:
    """Return standard country name for the given country code."""
    if not country_code:
        return "United States"
    return CODE_TO_COUNTRY_NAME.get(country_code.strip().upper(), country_code.strip().upper())


DEFAULT_EXCHANGE_RATES: Dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "INR": Decimal("83.50"),
    "EUR": Decimal("0.92"),
    "GBP": Decimal("0.79"),
    "CAD": Decimal("1.36"),
    "AUD": Decimal("1.52"),
    "AED": Decimal("3.67"),
    "SAR": Decimal("3.75"),
    "SGD": Decimal("1.35"),
    "JPY": Decimal("150.00"),
    "KRW": Decimal("1350.00"),
    "CHF": Decimal("0.89"),
    "NZD": Decimal("1.65"),
    "MXN": Decimal("17.00"),
    "BRL": Decimal("5.00"),
    "SEK": Decimal("10.50"),
    "NOK": Decimal("10.80"),
    "DKK": Decimal("6.90"),
    "ZAR": Decimal("18.50"),
    "MYR": Decimal("4.70"),
    "THB": Decimal("36.00"),
    "IDR": Decimal("15800.00"),
    "PHP": Decimal("56.50"),
    "VN": Decimal("24800.00"),
    "TRY": Decimal("32.00"),
    "PLN": Decimal("4.00"),
    "CZK": Decimal("23.00"),
    "HUF": Decimal("360.00"),
    "RON": Decimal("4.60"),
    "ILS": Decimal("3.70"),
    "QAR": Decimal("3.64"),
    "KWD": Decimal("0.31"),
    "OMR": Decimal("0.38"),
    "BHD": Decimal("0.38"),
    "EGP": Decimal("47.00"),
    "ARS": Decimal("870.00"),
    "CLP": Decimal("950.00"),
    "COP": Decimal("3900.00"),
    "HKD": Decimal("7.80"),
    "TWD": Decimal("32.00"),
}


async def get_user_currency_and_rate(
    user_id: Optional[Any],
    user_repository: Any,
    country_repository: Any,
) -> Tuple[str, Decimal, str, str, bool]:
    """
    Returns (currency, exchange_rate, country_code, country_name, exchange_available)
    by looking up user's saved country_code in the user table.
    """
    user_country_code = None
    if user_id:
        user = await user_repository.get_by_id(user_id)
        if user and user.get("country_code"):
            user_country_code = user["country_code"].strip().upper()

    if not user_country_code:
        user_country_code = "US"

    currency = get_currency_for_country(user_country_code)
    country_name = get_country_name_for_code(user_country_code)

    if user_country_code == "US" or currency == "USD":
        return "USD", Decimal("1.0"), "US", "United States", True

    exchange_available = False
    rate = Decimal("1.0")

    country_record = await country_repository.get_by_code(user_country_code)
    if country_record:
        if country_record.get("name"):
            country_name = country_record["name"]
        db_rate = country_record.get("rate_from_usd")
        is_avail = bool(country_record.get("exchange_available"))
        if db_rate is not None and Decimal(str(db_rate)) > Decimal("0.00"):
            rate = Decimal(str(db_rate))
            exchange_available = is_avail
        else:
            rate = DEFAULT_EXCHANGE_RATES.get(currency, Decimal("1.0"))
            exchange_available = is_avail
    else:
        rate = DEFAULT_EXCHANGE_RATES.get(currency, Decimal("1.0"))

    return currency, rate, user_country_code, country_name, exchange_available



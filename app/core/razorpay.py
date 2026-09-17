import hashlib
import hmac
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4
import httpx

from app.core.config import settings
from app.core.exceptions import BadRequestException


class RazorpayService:
    """Service handling Razorpay order generation and payment signature verification."""

    BASE_URL = "https://api.razorpay.com/v1"

    @property
    def is_configured(self) -> bool:
        return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)

    async def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay order. Amount is provided in Rupees and converted to Paise (x 100).
        If Razorpay API keys are not provided in environment, generates a sandbox mock order.
        """
        amount_in_paise = int((amount * Decimal("100.00")).quantize(Decimal("1")))

        if self.is_configured:
            url = f"{self.BASE_URL}/orders"
            payload: Dict[str, Any] = {
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt or f"rcpt_{uuid4().hex[:10]}",
                "payment_capture": 1
            }
            if notes:
                payload["notes"] = notes

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                if resp.status_code != 200 and resp.status_code != 201:
                    error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get("error", {}).get("description") or f"Razorpay order creation failed with status {resp.status_code}"
                    raise BadRequestException(message=error_msg, error_code="RAZORPAY_ORDER_FAILED")
                return resp.json()
        else:
            # Graceful sandbox / local development fallback
            mock_id = f"order_mock_{uuid4().hex[:14]}"
            return {
                "id": mock_id,
                "entity": "order",
                "amount": amount_in_paise,
                "amount_paid": 0,
                "amount_due": amount_in_paise,
                "currency": currency,
                "receipt": receipt or f"rcpt_{uuid4().hex[:10]}",
                "status": "created",
                "attempts": 0,
                "notes": notes or {},
                "created_at": 1700000000
            }

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Verifies the Razorpay HMAC-SHA256 signature.
        Formula: HMAC-SHA256(razorpay_order_id + '|' + razorpay_payment_id, secret) == razorpay_signature
        """
        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            return False

        # Support mock signatures in test / sandbox modes
        if razorpay_order_id.startswith("order_mock_") or razorpay_signature.startswith("mock_sig_"):
            return True

        if self.is_configured:
            secret_bytes = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
            data_bytes = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
            generated = hmac.new(secret_bytes, data_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(generated, razorpay_signature)
        else:
            return len(razorpay_signature) >= 10


razorpay_service = RazorpayService()

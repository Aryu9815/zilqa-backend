from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, Optional
import os
import smtplib
from email.message import EmailMessage
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

executor = ThreadPoolExecutor(max_workers=5)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.SENDER_EMAIL

    def _send_email_sync(self, to_email: str, subject: str, content: str):
        if not self.smtp_user or not self.smtp_password:
            print(f"MOCK EMAIL: To: {to_email} | Subject: {subject} | Content: {content}")
            return

        msg = EmailMessage()
        msg.set_content(content, subtype="html")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to_email

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            print(f"Email sent successfully to {to_email}")
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            raise e


    async def send_otp_email(self, to_email: str, otp: str, user_name: str):
        print("OTP sending")

        subject = "Your Zelqa Verification Code"

        content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your Zelqa Verification Code</title>
        </head>

        <body style="
            margin: 0;
            padding: 0;
            background-color: #f4f6f8;
            font-family: Arial, Helvetica, sans-serif;
            color: #333333;
        ">

            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                style="background-color: #f4f6f8; padding: 40px 15px;">

                <tr>
                    <td align="center">

                        <!-- Main Container -->
                        <table width="600" cellpadding="0" cellspacing="0" border="0"
                            style="
                                max-width: 600px;
                                width: 100%;
                                background-color: #ffffff;
                                border-radius: 12px;
                                overflow: hidden;
                            ">

                            <!-- Header -->
                            <tr>
                                <td align="center"
                                    style="
                                        padding: 28px 30px;
                                        background-color: #111827;
                                    ">

                                    <div style="
                                        font-size: 30px;
                                        font-weight: bold;
                                        color: #ffffff;
                                        letter-spacing: 1px;
                                    ">
                                        ZELQA
                                    </div>

                                    <div style="
                                        margin-top: 6px;
                                        font-size: 13px;
                                        color: #d1d5db;
                                    ">
                                        Shop Smart. Live Better.
                                    </div>

                                </td>
                            </tr>

                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px 40px 30px;">

                                    <h2 style="
                                        margin: 0 0 18px;
                                        font-size: 24px;
                                        color: #111827;
                                    ">
                                        Verify Your Email
                                    </h2>

                                    <p style="
                                        margin: 0 0 15px;
                                        font-size: 15px;
                                        line-height: 1.7;
                                        color: #4b5563;
                                    ">
                                        Hi <strong>{user_name}</strong>,
                                    </p>

                                    <p style="
                                        margin: 0 0 25px;
                                        font-size: 15px;
                                        line-height: 1.7;
                                        color: #4b5563;
                                    ">
                                        Thank you for creating an account with
                                        <strong>Zelqa</strong>. Please use the
                                        verification code below to complete your
                                        registration.
                                    </p>

                                    <!-- OTP Box -->
                                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center"
                                                style="
                                                    background-color: #f3f4f6;
                                                    border-radius: 10px;
                                                    padding: 25px;
                                                ">

                                                <div style="
                                                    font-size: 13px;
                                                    color: #6b7280;
                                                    margin-bottom: 10px;
                                                ">
                                                    YOUR VERIFICATION CODE
                                                </div>

                                                <div style="
                                                    font-size: 36px;
                                                    font-weight: bold;
                                                    letter-spacing: 8px;
                                                    color: #111827;
                                                ">
                                                    {otp}
                                                </div>

                                                <div style="
                                                    margin-top: 12px;
                                                    font-size: 13px;
                                                    color: #6b7280;
                                                ">
                                                    Valid for 10 minutes
                                                </div>

                                            </td>
                                        </tr>
                                    </table>

                                    <!-- Security Notice -->
                                    <table width="100%" cellpadding="0" cellspacing="0" border="0"
                                        style="margin-top: 25px;">

                                        <tr>
                                            <td style="
                                                background-color: #fff7ed;
                                                border-left: 4px solid #f97316;
                                                padding: 14px 16px;
                                            ">

                                                <p style="
                                                    margin: 0;
                                                    font-size: 13px;
                                                    line-height: 1.6;
                                                    color: #7c2d12;
                                                ">
                                                    <strong>Security reminder:</strong>
                                                    Never share this verification
                                                    code with anyone. Zelqa will
                                                    never ask you for your OTP.
                                                </p>

                                            </td>
                                        </tr>

                                    </table>

                                    <p style="
                                        margin: 25px 0 0;
                                        font-size: 14px;
                                        line-height: 1.7;
                                        color: #6b7280;
                                    ">
                                        If you did not request this verification
                                        code, you can safely ignore this email.
                                        Your account will remain secure.
                                    </p>

                                </td>
                            </tr>

                            <!-- Divider -->
                            <tr>
                                <td style="padding: 0 40px;">
                                    <div style="
                                        height: 1px;
                                        background-color: #e5e7eb;
                                    "></div>
                                </td>
                            </tr>

                            <!-- Contact -->
                            <tr>
                                <td align="center"
                                    style="padding: 25px 30px;">

                                    <p style="
                                        margin: 0 0 8px;
                                        font-size: 14px;
                                        color: #374151;
                                    ">
                                        Need help?
                                        <a href="mailto:support@zelqa.com"
                                        style="
                                            color: #111827;
                                            font-weight: bold;
                                            text-decoration: none;
                                        ">
                                            Contact Zelqa Support
                                        </a>
                                    </p>

                                    <p style="
                                        margin: 0;
                                        font-size: 12px;
                                        color: #9ca3af;
                                    ">
                                        © 2026 Zelqa. All rights reserved.
                                    </p>

                                </td>
                            </tr>

                        </table>

                        <!-- Footer -->
                        <table width="600" cellpadding="0" cellspacing="0" border="0"
                            style="max-width: 600px; width: 100%;">

                            <tr>
                                <td align="center" style="padding: 20px 15px;">

                                    <p style="
                                        margin: 0;
                                        font-size: 11px;
                                        line-height: 1.5;
                                        color: #9ca3af;
                                    ">
                                        This is an automated message from Zelqa.
                                        Please do not reply directly to this email.
                                    </p>

                                </td>
                            </tr>

                        </table>

                    </td>
                </tr>

            </table>

        </body>
        </html>
        """

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            executor,
            self._send_email_sync,
            to_email,
            subject,
            content
        )

    async def send_order_confirmation_email(
        self,
        to_email: str,
        order: Any,
        user_name: Optional[str] = None
    ) -> None:
        """
        Sends an order confirmation email to the user with a formatted bill and invoice breakdown.
        """
        try:
            order_id = getattr(order, "id", None) or (order.get("id") if isinstance(order, dict) else "")
            order_id_str = str(order_id)
            short_id = order_id_str[:8].upper() if order_id_str else "N/A"

            currency = getattr(order, "currency", None) or (order.get("currency") if isinstance(order, dict) else "INR") or "INR"

            currency_symbols: Dict[str, str] = {
                "INR": "₹",
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "CAD": "CA$",
                "AUD": "AU$",
                "AED": "AED ",
                "SAR": "SAR ",
                "SGD": "S$",
                "JPY": "¥",
                "CHF": "CHF ",
                "CNY": "¥",
            }

            def fmt_money(val: Any) -> str:
                try:
                    num = Decimal(str(val or 0))
                except Exception:
                    num = Decimal("0.00")
                curr = str(currency or "INR").upper().strip()
                sym = currency_symbols.get(curr, f"{curr} ")
                return f"{sym}{num:,.2f}"

            # Determine customer name
            name = user_name
            if not name:
                cust = getattr(order, "customer", None) or (order.get("customer") if isinstance(order, dict) else None)
                if cust:
                    name = getattr(cust, "name", None) or (cust.get("name") if isinstance(cust, dict) else None)
            if not name:
                sa = getattr(order, "shipping_address", None) or (order.get("shipping_address") if isinstance(order, dict) else None)
                if isinstance(sa, dict):
                    name = sa.get("full_name")
            if not name:
                name = "Valued Customer"

            # Format created date
            created_at = getattr(order, "created_at", None) or (order.get("created_at") if isinstance(order, dict) else None)
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%B %d, %Y, %I:%M %p")
            elif isinstance(created_at, str):
                date_str = created_at
            else:
                date_str = datetime.now().strftime("%B %d, %Y, %I:%M %p")

            # Extract totals
            subtotal = getattr(order, "subtotal", None) or (order.get("subtotal") if isinstance(order, dict) else 0)
            discount_amount = getattr(order, "discount_amount", None) or (order.get("discount_amount") if isinstance(order, dict) else 0)
            shipping_amount = getattr(order, "shipping_amount", None) or (order.get("shipping_amount") if isinstance(order, dict) else 0)
            total_amount = getattr(order, "total_amount", None) or (order.get("total_amount") if isinstance(order, dict) else 0)
            coupon_code = getattr(order, "coupon_code", None) or (order.get("coupon_code") if isinstance(order, dict) else None)
            payment_status = getattr(order, "payment_status", "confirmed") or "confirmed"
            payment_id = getattr(order, "razorpay_payment_id", None) or (order.get("razorpay_payment_id") if isinstance(order, dict) else None)

            # Build items rows
            items = getattr(order, "items", None) or (order.get("items") if isinstance(order, dict) else []) or []
            items_rows = ""
            for it in items:
                p_name = getattr(it, "product_name", None) or (it.get("product_name") if isinstance(it, dict) else "Product")
                qty = getattr(it, "quantity", None) or (it.get("quantity") if isinstance(it, dict) else 1)
                u_price = getattr(it, "unit_price", None) or getattr(it, "final_unit_price", None) or (it.get("unit_price") if isinstance(it, dict) else 0)
                t_price = getattr(it, "total_price", None) or (it.get("total_price") if isinstance(it, dict) else 0)
                img = getattr(it, "product_image_url", None) or (it.get("product_image_url") if isinstance(it, dict) else None)

                img_tag = (
                    f'<img src="{img}" alt="{p_name}" width="50" height="50" style="object-fit: cover; border-radius: 6px; border: 1px solid #e5e7eb; display: block; margin-right: 12px;" />'
                    if img
                    else '<div style="width: 50px; height: 50px; background-color: #f3f4f6; border-radius: 6px; border: 1px solid #e5e7eb; display: inline-block; margin-right: 12px; text-align: center; line-height: 50px; font-size: 20px;">🛍️</div>'
                )

                items_rows += f"""
                <tr>
                    <td style="padding: 12px 10px; border-bottom: 1px solid #f3f4f6; vertical-align: middle;">
                        <table cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td style="vertical-align: middle;">{img_tag}</td>
                                <td style="vertical-align: middle;">
                                    <div style="font-size: 14px; font-weight: 600; color: #111827; line-height: 1.4;">{p_name}</div>
                                    <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">Qty: {qty} &times; {fmt_money(u_price)}</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td align="right" style="padding: 12px 10px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; font-size: 14px; font-weight: 600; color: #111827; white-space: nowrap;">
                        {fmt_money(t_price)}
                    </td>
                </tr>
                """

            # Build discount row
            discount_html = ""
            if Decimal(str(discount_amount or 0)) > Decimal("0.00"):
                coupon_badge = f'<span style="background-color: #ecfdf5; color: #047857; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600; margin-left: 6px;">{coupon_code}</span>' if coupon_code else ""
                discount_html = f"""
                <tr>
                    <td style="padding: 8px 0; font-size: 14px; color: #4b5563;">
                        Discount {coupon_badge}
                    </td>
                    <td align="right" style="padding: 8px 0; font-size: 14px; font-weight: 600; color: #059669;">
                        - {fmt_money(discount_amount)}
                    </td>
                </tr>
                """

            # Build shipping display
            if Decimal(str(shipping_amount or 0)) == Decimal("0.00"):
                shipping_display = '<span style="color: #059669; font-weight: 600;">FREE</span>'
            else:
                shipping_display = fmt_money(shipping_amount)

            # Build shipping address block
            shipping_address_html = ""
            sa_data = getattr(order, "shipping_address", None) or (order.get("shipping_address") if isinstance(order, dict) else None)
            if isinstance(sa_data, dict):
                full_n = sa_data.get("full_name") or name
                a1 = sa_data.get("address_line_1") or ""
                a2 = f"<br>{sa_data.get('address_line_2')}" if sa_data.get("address_line_2") else ""
                loc = ", ".join(filter(None, [sa_data.get("city"), sa_data.get("state"), sa_data.get("postal_code")]))
                c_name = sa_data.get("country") or ""
                ph = sa_data.get("phone")
                shipping_address_html = f"""
                <table width="100%" cellpadding="0" cellspacing="0" border="0"
                    style="margin-top: 25px; background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px;">
                    <tr>
                        <td style="padding: 18px 20px;">
                            <div style="font-size: 12px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">
                                📍 Delivery Address
                            </div>
                            <div style="font-size: 14px; font-weight: 600; color: #111827; margin-bottom: 4px;">
                                {full_n}
                            </div>
                            <div style="font-size: 13px; color: #4b5563; line-height: 1.6;">
                                {a1}{a2}<br>
                                {loc}<br>
                                {c_name}
                            </div>
                            {f'<div style="font-size: 13px; color: #6b7280; margin-top: 6px;">📞 Phone: {ph}</div>' if ph else ''}
                        </td>
                    </tr>
                </table>
                """

            # Payment badge
            if str(payment_status).lower() in ("paid", "completed"):
                payment_badge = '<span style="background-color: #ecfdf5; color: #047857; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; text-transform: uppercase;">PAID</span>'
            else:
                payment_badge = f'<span style="background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; text-transform: uppercase;">{str(payment_status).upper()}</span>'

            payment_info_note = f'<div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Payment ID: <span style="font-family: monospace;">{payment_id}</span></div>' if payment_id else ''

            subject = f"Order Confirmed #{short_id} - Your Zelqa Bill & Invoice"

            content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="
                margin: 0;
                padding: 0;
                background-color: #f4f6f8;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: #333333;
            ">
                <div style="display: none; max-height: 0px; overflow: hidden;">
                    Thank you for your order #{short_id}. View your official bill and order details.
                </div>

                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f6f8; padding: 35px 15px;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="
                                max-width: 600px;
                                width: 100%;
                                background-color: #ffffff;
                                border-radius: 12px;
                                overflow: hidden;
                                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                            ">
                                <!-- Header -->
                                <tr>
                                    <td align="center" style="
                                        padding: 26px 30px;
                                        background-color: #111827;
                                    ">
                                        <div style="
                                            font-size: 28px;
                                            font-weight: 800;
                                            color: #ffffff;
                                            letter-spacing: 2px;
                                        ">
                                            ZELQA
                                        </div>
                                        <div style="
                                            margin-top: 4px;
                                            font-size: 12px;
                                            color: #d1d5db;
                                            letter-spacing: 0.5px;
                                        ">
                                            Shop Smart. Live Better.
                                        </div>
                                    </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 35px 25px;">
                                        <!-- Order Confirmation Title -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                            <tr>
                                                <td>
                                                    <div style="display: inline-block; background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 700; color: #047857; margin-bottom: 12px;">
                                                        ✓ ORDER CONFIRMED
                                                    </div>
                                                    <h1 style="margin: 0 0 8px; font-size: 22px; color: #111827; font-weight: 700;">
                                                        Thank you for your order, {name}!
                                                    </h1>
                                                    <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #4b5563;">
                                                        We have received your order and are preparing it for shipment. Here is a summary of your bill and purchase details.
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Order Meta Card -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 25px;">
                                            <tr>
                                                <td style="padding: 16px 20px;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                                        <tr>
                                                            <td style="vertical-align: top; width: 50%;">
                                                                <div style="font-size: 11px; text-transform: uppercase; color: #6b7280; font-weight: 600; letter-spacing: 0.5px;">Order Number</div>
                                                                <div style="font-size: 15px; font-weight: 700; color: #111827; margin-top: 3px;">#{short_id}</div>
                                                                <div style="font-size: 11px; color: #9ca3af; margin-top: 2px;">{order_id_str}</div>
                                                            </td>
                                                            <td align="right" style="vertical-align: top; width: 50%;">
                                                                <div style="font-size: 11px; text-transform: uppercase; color: #6b7280; font-weight: 600; letter-spacing: 0.5px;">Payment Status</div>
                                                                <div style="margin-top: 4px;">{payment_badge}</div>
                                                                {payment_info_note}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td colspan="2" style="padding-top: 10px; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; margin-top: 10px;">
                                                                📅 <strong>Date:</strong> {date_str}
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Order Items List -->
                                        <div style="font-size: 13px; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">
                                            Items in Your Order
                                        </div>
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px; border-collapse: collapse;">
                                            {items_rows}
                                        </table>

                                        <!-- Bill Calculation Summary -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top: 2px solid #e5e7eb; padding-top: 12px; margin-top: 10px;">
                                            <tr>
                                                <td style="padding: 6px 0; font-size: 14px; color: #4b5563;">Subtotal</td>
                                                <td align="right" style="padding: 6px 0; font-size: 14px; color: #111827; font-weight: 500;">
                                                    {fmt_money(subtotal)}
                                                </td>
                                            </tr>
                                            {discount_html}
                                            <tr>
                                                <td style="padding: 6px 0; font-size: 14px; color: #4b5563;">
                                                    Insured Express Delivery
                                                </td>
                                                <td align="right" style="padding: 6px 0; font-size: 14px; color: #111827;">
                                                    {shipping_display}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="padding: 8px 0 0;">
                                                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #111827; border-radius: 8px; padding: 14px 16px;">
                                                        <tr>
                                                            <td style="color: #ffffff; font-size: 15px; font-weight: 700; letter-spacing: 0.5px;">
                                                                TOTAL AMOUNT
                                                            </td>
                                                            <td align="right" style="color: #ffffff; font-size: 20px; font-weight: 800;">
                                                                {fmt_money(total_amount)}
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Shipping Address -->
                                        {shipping_address_html}

                                        <!-- Help / Support info -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 25px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                            <tr>
                                                <td align="center">
                                                    <p style="margin: 0 0 6px; font-size: 13px; color: #4b5563;">
                                                        Need help or want to modify your order?
                                                    </p>
                                                    <a href="mailto:support@zelqa.com" style="
                                                        color: #111827;
                                                        font-weight: 700;
                                                        font-size: 13px;
                                                        text-decoration: underline;
                                                    ">
                                                        support@zelqa.com
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td align="center" style="
                                        padding: 20px 30px;
                                        background-color: #f9fafb;
                                        border-top: 1px solid #e5e7eb;
                                        font-size: 12px;
                                        color: #9ca3af;
                                        line-height: 1.5;
                                    ">
                                        <div>© 2026 Zelqa. All rights reserved.</div>
                                        <div style="margin-top: 4px; font-size: 11px;">
                                            This is an automated bill confirmation for order #{short_id}.
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self._send_email_sync,
                to_email,
                subject,
                content
            )
            print(f"Order confirmation bill email dispatched to {to_email} for order #{short_id}")
        except Exception as e:
            print(f"Error preparing or sending order confirmation email to {to_email}: {e}")

    async def send_order_tracking_email(
        self,
        to_email: str,
        order: Any,
        tracking_url: str,
        user_name: Optional[str] = None,
        courier_name: Optional[str] = None
    ) -> None:
        """
        Sends an email with the live order tracking link to the customer.
        """
        try:
            order_id = getattr(order, "id", None) or (order.get("id") if isinstance(order, dict) else "")
            order_id_str = str(order_id)
            short_id = order_id_str[:8].upper() if order_id_str else "N/A"

            # Determine customer name
            name = user_name
            if not name:
                cust = getattr(order, "customer", None) or (order.get("customer") if isinstance(order, dict) else None)
                if cust:
                    name = getattr(cust, "name", None) or (cust.get("name") if isinstance(cust, dict) else None)
            if not name:
                sa = getattr(order, "shipping_address", None) or (order.get("shipping_address") if isinstance(order, dict) else None)
                if isinstance(sa, dict):
                    name = sa.get("full_name")
            if not name:
                name = "Valued Customer"

            # Format created date
            created_at = getattr(order, "created_at", None) or (order.get("created_at") if isinstance(order, dict) else None)
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%B %d, %Y")
            elif isinstance(created_at, str):
                date_str = created_at
            else:
                date_str = datetime.now().strftime("%B %d, %Y")

            # Build items list
            items = getattr(order, "items", None) or (order.get("items") if isinstance(order, dict) else []) or []
            items_rows = ""
            for it in items:
                p_name = getattr(it, "product_name", None) or (it.get("product_name") if isinstance(it, dict) else "Product")
                qty = getattr(it, "quantity", None) or (it.get("quantity") if isinstance(it, dict) else 1)
                img = getattr(it, "product_image_url", None) or (it.get("product_image_url") if isinstance(it, dict) else None)

                img_tag = (
                    f'<img src="{img}" alt="{p_name}" width="46" height="46" style="object-fit: cover; border-radius: 6px; border: 1px solid #e5e7eb; display: block; margin-right: 12px;" />'
                    if img
                    else '<div style="width: 46px; height: 46px; background-color: #f3f4f6; border-radius: 6px; border: 1px solid #e5e7eb; display: inline-block; margin-right: 12px; text-align: center; line-height: 46px; font-size: 18px;">📦</div>'
                )

                items_rows += f"""
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #f3f4f6; vertical-align: middle;">
                        <table cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td style="vertical-align: middle;">{img_tag}</td>
                                <td style="vertical-align: middle;">
                                    <div style="font-size: 14px; font-weight: 600; color: #111827; line-height: 1.4;">{p_name}</div>
                                    <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">Quantity: {qty}</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                """

            # Build courier badge if specified
            courier_html = ""
            if courier_name:
                courier_html = f"""
                <div style="margin-top: 10px; font-size: 13px; color: #4b5563;">
                    🚚 Delivery Partner: <strong>{courier_name}</strong>
                </div>
                """

            # Build shipping address block
            shipping_address_html = ""
            sa_data = getattr(order, "shipping_address", None) or (order.get("shipping_address") if isinstance(order, dict) else None)
            if isinstance(sa_data, dict):
                full_n = sa_data.get("full_name") or name
                a1 = sa_data.get("address_line_1") or ""
                a2 = f"<br>{sa_data.get('address_line_2')}" if sa_data.get("address_line_2") else ""
                loc = ", ".join(filter(None, [sa_data.get("city"), sa_data.get("state"), sa_data.get("postal_code")]))
                c_name = sa_data.get("country") or ""
                ph = sa_data.get("phone")
                shipping_address_html = f"""
                <table width="100%" cellpadding="0" cellspacing="0" border="0"
                    style="margin-top: 25px; background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px;">
                    <tr>
                        <td style="padding: 18px 20px;">
                            <div style="font-size: 12px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">
                                📍 Delivering To
                            </div>
                            <div style="font-size: 14px; font-weight: 600; color: #111827; margin-bottom: 4px;">
                                {full_n}
                            </div>
                            <div style="font-size: 13px; color: #4b5563; line-height: 1.6;">
                                {a1}{a2}<br>
                                {loc}<br>
                                {c_name}
                            </div>
                            {f'<div style="font-size: 13px; color: #6b7280; margin-top: 6px;">📞 Phone: {ph}</div>' if ph else ''}
                        </td>
                    </tr>
                </table>
                """

            subject = f"Your Zelqa Order #{short_id} is on the Way - Track Your Delivery"

            content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
            </head>
            <body style="
                margin: 0;
                padding: 0;
                background-color: #f4f6f8;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: #333333;
            ">
                <div style="display: none; max-height: 0px; overflow: hidden;">
                    Great news! Your order #{short_id} has been dispatched. Track your delivery status here.
                </div>

                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f6f8; padding: 35px 15px;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="
                                max-width: 600px;
                                width: 100%;
                                background-color: #ffffff;
                                border-radius: 12px;
                                overflow: hidden;
                                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                            ">
                                <!-- Header -->
                                <tr>
                                    <td align="center" style="
                                        padding: 26px 30px;
                                        background-color: #111827;
                                    ">
                                        <div style="
                                            font-size: 28px;
                                            font-weight: 800;
                                            color: #ffffff;
                                            letter-spacing: 2px;
                                        ">
                                            ZELQA
                                        </div>
                                        <div style="
                                            margin-top: 4px;
                                            font-size: 12px;
                                            color: #d1d5db;
                                            letter-spacing: 0.5px;
                                        ">
                                            Shop Smart. Live Better.
                                        </div>
                                    </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 35px 25px;">
                                        <!-- Shipment Status Title -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                            <tr>
                                                <td>
                                                    <div style="display: inline-block; background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 700; color: #1d4ed8; margin-bottom: 12px;">
                                                        🚚 SHIPPED & ON THE WAY
                                                    </div>
                                                    <h1 style="margin: 0 0 8px; font-size: 22px; color: #111827; font-weight: 700;">
                                                        Your package is on its way, {name}!
                                                    </h1>
                                                    <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #4b5563;">
                                                        Great news! Your Zelqa order <strong>#{short_id}</strong> has been dispatched and is currently in transit. You can follow the live delivery progress using the link below.
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Prominent Tracking CTA Card -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8fafc; border: 2px solid #e2e8f0; border-radius: 12px; margin-bottom: 25px; text-align: center;">
                                            <tr>
                                                <td align="center" style="padding: 28px 20px;">
                                                    <div style="font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 1px; margin-bottom: 15px;">
                                                        Live Order Tracking
                                                    </div>

                                                    <a href="{tracking_url}" target="_blank" style="
                                                        display: inline-block;
                                                        background-color: #111827;
                                                        color: #ffffff;
                                                        padding: 15px 36px;
                                                        font-size: 15px;
                                                        font-weight: 700;
                                                        text-decoration: none;
                                                        border-radius: 8px;
                                                        letter-spacing: 0.5px;
                                                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
                                                    ">
                                                        TRACK YOUR DELIVERY &rarr;
                                                    </a>

                                                    {courier_html}

                                                    <p style="margin: 18px 0 0; font-size: 12px; color: #64748b; line-height: 1.5; word-break: break-all;">
                                                        Can't click the button? Copy and paste this tracking link into your browser:<br>
                                                        <a href="{tracking_url}" style="color: #2563eb; text-decoration: underline; font-weight: 500;">{tracking_url}</a>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Order Info Details -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 25px;">
                                            <tr>
                                                <td style="padding: 14px 18px; font-size: 13px; color: #4b5563;">
                                                    <div><strong>Order Number:</strong> #{short_id} <span style="font-size: 11px; color: #9ca3af;">({order_id_str})</span></div>
                                                    <div style="margin-top: 4px;"><strong>Order Date:</strong> {date_str}</div>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Items List -->
                                        {f'''
                                        <div style="font-size: 13px; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;">
                                            Items in this Shipment
                                        </div>
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px; border-collapse: collapse;">
                                            {items_rows}
                                        </table>
                                        ''' if items_rows else ''}

                                        <!-- Shipping Address -->
                                        {shipping_address_html}

                                        <!-- Help / Support info -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 25px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                            <tr>
                                                <td align="center">
                                                    <p style="margin: 0 0 6px; font-size: 13px; color: #4b5563;">
                                                        Questions about your delivery? We are here to help.
                                                    </p>
                                                    <a href="mailto:support@zelqa.com" style="
                                                        color: #111827;
                                                        font-weight: 700;
                                                        font-size: 13px;
                                                        text-decoration: underline;
                                                    ">
                                                        support@zelqa.com
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td align="center" style="
                                        padding: 20px 30px;
                                        background-color: #f9fafb;
                                        border-top: 1px solid #e5e7eb;
                                        font-size: 12px;
                                        color: #9ca3af;
                                        line-height: 1.5;
                                    ">
                                        <div>&copy; 2026 Zelqa. All rights reserved.</div>
                                        <div style="margin-top: 4px; font-size: 11px;">
                                            This is an automated shipment notification for order #{short_id}.
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self._send_email_sync,
                to_email,
                subject,
                content
            )
            print(f"Order delivery tracking email dispatched to {to_email} for order #{short_id}")
        except Exception as e:
            print(f"Error preparing or sending order tracking email to {to_email}: {e}")


email_service = EmailService()

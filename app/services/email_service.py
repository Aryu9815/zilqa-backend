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


email_service = EmailService()

"""Pluggable SMS delivery.

Supports:
- console : logs the message to the server console (development only)
- twilio  : sends via Twilio REST API
- msg91   : sends via MSG91 (popular in India)

The provider is selected with the SMS_PROVIDER setting. All providers share the
same `send_sms(mobile, message)` signature so the rest of the app is agnostic.
"""
import logging

import httpx

from .config import settings

logger = logging.getLogger("societyhub.sms")


def normalize_mobile(mobile: str) -> str:
    """Ensure the number is in E.164-ish format with a country code."""
    mobile = mobile.strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+"):
        return mobile
    # Bare 10-digit Indian-style number -> prepend default country code.
    return f"{settings.DEFAULT_COUNTRY_CODE}{mobile}"


def _send_console(mobile: str, message: str) -> None:
    logger.warning("[DEV SMS] to=%s | %s", mobile, message)
    print(f"\n===== DEV SMS =====\nTo: {mobile}\n{message}\n===================\n")


def _send_twilio(mobile: str, message: str) -> None:
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM):
        raise RuntimeError("Twilio is not configured. Set TWILIO_* environment variables.")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    data = {"To": mobile, "From": settings.TWILIO_FROM, "Body": message}
    resp = httpx.post(
        url,
        data=data,
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        timeout=15,
    )
    resp.raise_for_status()


def _send_msg91(mobile: str, message: str) -> None:
    if not settings.MSG91_AUTH_KEY:
        raise RuntimeError("MSG91 is not configured. Set MSG91_AUTH_KEY environment variable.")
    # MSG91 wants numbers without the leading '+'.
    number = mobile.lstrip("+")
    url = "https://api.msg91.com/api/v2/sendsms"
    payload = {
        "sender": settings.MSG91_SENDER,
        "route": settings.MSG91_ROUTE,
        "country": "0",
        "sms": [{"message": message, "to": [number]}],
    }
    if settings.MSG91_TEMPLATE_ID:
        payload["DLT_TE_ID"] = settings.MSG91_TEMPLATE_ID
    headers = {"authkey": settings.MSG91_AUTH_KEY, "Content-Type": "application/json"}
    resp = httpx.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()


def send_sms(mobile: str, message: str) -> None:
    """Send an SMS using the configured provider. Raises on hard failures."""
    mobile = normalize_mobile(mobile)
    provider = settings.SMS_PROVIDER.lower()
    if provider == "twilio":
        _send_twilio(mobile, message)
    elif provider == "msg91":
        _send_msg91(mobile, message)
    else:
        _send_console(mobile, message)


def send_otp_sms(mobile: str, code: str) -> None:
    minutes = settings.OTP_EXPIRY_MINUTES
    message = (
        f"Your SocietyHub verification code is {code}. "
        f"It is valid for {minutes} minute(s). Do not share this code with anyone."
    )
    send_sms(mobile, message)

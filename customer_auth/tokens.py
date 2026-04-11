"""
Customer JWT — separate from the admin JWT issued by SimpleJWT.
Customers are not Django Users, so we issue our own lightweight token.
Signed with the same SECRET_KEY but with a different payload shape
so admin and customer tokens can never be confused.
"""
import time
import hmac
import hashlib
import base64
import json

from django.conf import settings


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_customer_token(customer) -> str:
    """
    Returns a signed JWT-like token valid for 30 days.
    Payload: { sub, email, name, avatar, iat, exp, type }
    """
    now = int(time.time())
    header  = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "type":   "customer",           # distinguishes from admin tokens
        "sub":    customer.id,
        "email":  customer.email,
        "name":   customer.name,
        "avatar": customer.avatar_url,
        "iat":    now,
        "exp":    now + 60 * 60 * 24 * 30,  # 30 days
    }).encode())

    sig_input = f"{header}.{payload}".encode()
    sig = _b64(
        hmac.new(
            settings.SECRET_KEY.encode(),
            sig_input,
            hashlib.sha256,
        ).digest()
    )
    return f"{header}.{payload}.{sig}"


def decode_customer_token(token: str) -> dict | None:
    """
    Verifies and decodes a customer token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        header, payload, sig = token.split(".")
    except ValueError:
        return None

    # Verify signature
    sig_input = f"{header}.{payload}".encode()
    expected = _b64(
        hmac.new(
            settings.SECRET_KEY.encode(),
            sig_input,
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(expected, sig):
        return None

    # Decode payload
    padding = 4 - len(payload) % 4
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * padding))
    except Exception:
        return None

    # Check expiry and type
    if data.get("type") != "customer":
        return None
    if data.get("exp", 0) < int(time.time()):
        return None

    return data
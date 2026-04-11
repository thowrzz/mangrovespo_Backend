import threading
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .models import CustomerSession, EmailOTP
from .tokens import make_customer_token

logger = logging.getLogger(__name__)


# ── OTP: Send ─────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp(request):
    """
    POST /api/v1/auth/otp/send/
    Body: { "email": "user@example.com" }
    Sends a 6-digit OTP to the email. Rate limiting should be added
    at the nginx/API gateway level in production.
    """
    email = request.data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return Response(
            {"error": "Enter a valid email address"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = EmailOTP.generate(email)

    # Send in background so response is instant
    threading.Thread(
        target=_send_otp_email,
        args=(email, code),
        daemon=True,
    ).start()

    return Response({"message": "OTP sent. Check your inbox."})


def _send_otp_email(email: str, code: str):
    try:
        from django.core.mail import send_mail
        send_mail(
            subject="Your MangroveSpot login code",
            message=f"Your login code is: {code}\n\nExpires in 10 minutes.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=f"""
            <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;">
              <h2 style="color:#2d7a4f;margin-bottom:8px;">🌿 MangroveSpot</h2>
              <p style="color:#444;font-size:15px;">Your one-time login code:</p>
              <div style="font-size:48px;font-weight:bold;letter-spacing:12px;color:#2d7a4f;
                          margin:24px 0;font-family:monospace;">{code}</div>
              <p style="color:#888;font-size:13px;">Expires in 10 minutes. Don't share this code.</p>
            </div>
            """,
            fail_silently=False,
        )
    except Exception:
        logger.error("Gmail SMTP error for %s", email, exc_info=True)

# ── OTP: Verify ───────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    POST /api/v1/auth/otp/verify/
    Body: { "email": "user@example.com", "code": "123456" }
    Returns a customer JWT on success.
    """
    email = request.data.get("email", "").strip().lower()
    code  = str(request.data.get("code", "")).strip()

    if not email or not code:
        return Response(
            {"error": "Email and code are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not EmailOTP.verify(email, code):
        return Response(
            {"error": "Invalid or expired code. Request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get or create customer session
    customer, _ = CustomerSession.objects.get_or_create(
        email=email,
        defaults={"name": email.split("@")[0].capitalize()},
    )

    token = make_customer_token(customer)
    return Response({
        "token":  token,
        "name":   customer.name,
        "email":  customer.email,
        "avatar": customer.avatar_url,
    })


# ── Google OAuth ──────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):
    """
    POST /api/v1/auth/google/
    Body: { "credential": "<Google ID token from frontend>" }
    Verifies the token with Google, returns a customer JWT.
    """
    credential = request.data.get("credential", "")
    if not credential:
        return Response(
            {"error": "Google credential is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except Exception as e:
        logger.warning("Google token verification failed: %s", e)
        return Response(
            {"error": "Invalid Google token. Please try again."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email      = info.get("email", "").lower()
    name       = info.get("name", "")
    google_sub = info.get("sub", "")
    avatar     = info.get("picture", "")

    if not email:
        return Response(
            {"error": "Could not get email from Google account"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Upsert customer — update name/avatar if they changed in Google
    customer, created = CustomerSession.objects.get_or_create(
        email=email,
        defaults={
            "name":       name,
            "google_sub": google_sub,
            "avatar_url": avatar,
        },
    )
    if not created:
        updated = False
        if name and customer.name != name:
            customer.name = name
            updated = True
        if google_sub and customer.google_sub != google_sub:
            customer.google_sub = google_sub
            updated = True
        if avatar and customer.avatar_url != avatar:
            customer.avatar_url = avatar
            updated = True
        if updated:
            customer.save(update_fields=["name", "google_sub", "avatar_url"])

    token = make_customer_token(customer)
    return Response({
        "token":  token,
        "name":   customer.name,
        "email":  customer.email,
        "avatar": customer.avatar_url,
    })
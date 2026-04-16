
# apps/payments/views.py
import hmac
import hashlib
import json
import threading
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.models import Booking

logger = logging.getLogger(__name__)


# ── Background email dispatcher ───────────────────────────────────
# Spawns a daemon thread so the HTTP response returns immediately.
# SendGrid takes 800ms–3s per call — we never make the user wait for it.
#
# Logic:
#   - If Celery broker is reachable  → use .delay() (proper async queue)
#   - If Celery is not running       → call the task function directly
#     in the thread (works on localhost without Redis)

def _fire_emails(booking_id: int, include_owner: bool = True):
    """Non-blocking email dispatch. Safe to call from any view."""
    def _run():
        try:
            from apps.notifications.tasks import (
                send_booking_confirmation_email,
                send_owner_new_booking_alert,
            )
            if _celery_up():
                send_booking_confirmation_email.delay(booking_id)
                if include_owner:
                    send_owner_new_booking_alert.delay(booking_id)
            else:
                # Celery not available (local dev) — run synchronously
                # but inside this thread, so the HTTP response is already gone
                send_booking_confirmation_email(booking_id)
                if include_owner:
                    send_owner_new_booking_alert(booking_id)
        except Exception:
            logger.warning(
                "Email dispatch failed for booking %s", booking_id, exc_info=True
            )

    threading.Thread(target=_run, daemon=True).start()


def _celery_up() -> bool:
    """
    Quick non-blocking broker check.
    Times out in 1 s so it never slows down the request.
    """
    try:
        from celery import current_app
        conn = current_app.connection_for_read()
        conn.ensure_connection(max_retries=1, timeout=1)
        conn.release()
        return True
    except Exception:
        return False


# ── verify_payment ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    POST /api/v1/payments/verify/
    Called by Next.js after Razorpay modal success.
    Returns in <100ms — emails fire in the background.
    """
    razorpay_order_id   = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature  = request.data.get('razorpay_signature')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response(
            {'error': 'Missing payment details'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # HMAC-SHA256 — fast, pure Python, no I/O
    message  = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        return Response(
            {'error': 'Invalid payment signature'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Single indexed DB lookup
    try:
        booking = Booking.objects.get(razorpay_order_id=razorpay_order_id)
    except Booking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Idempotent — already confirmed (webhook may have beaten us)
    if booking.status == 'confirmed':
        return Response({
            'status': 'confirmed',
            'booking_reference': booking.reference,
            'message': 'Booking confirmed! Check your email for details.',
        })

    # update_fields writes only 3 columns — much faster than full save()
    booking.razorpay_payment_id = razorpay_payment_id
    booking.razorpay_signature  = razorpay_signature
    booking.status              = 'confirmed'
    booking.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status'])

    # Fire emails in background — response returns NOW, not after SendGrid
    _fire_emails(booking.id, include_owner=True)

    return Response({
        'status': 'confirmed',
        'booking_reference': booking.reference,
        'message': 'Booking confirmed! Check your email for details.',
    })


# ── razorpay_webhook ──────────────────────────────────────────────

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """
    POST /api/v1/payments/webhook/
    Server-to-server fallback from Razorpay.
    Must return 200 quickly — Razorpay retries on anything else.
    """
    webhook_signature = request.headers.get('X-Razorpay-Signature', '')

    if not webhook_signature:
        return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, webhook_signature):
        return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

    if payload.get('event') == 'payment.captured':
        try:
            entity     = payload['payload']['payment']['entity']
            order_id   = entity['order_id']
            payment_id = entity['id']
        except (KeyError, TypeError):
            return Response({'error': 'Malformed payload'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(razorpay_order_id=order_id)
            if booking.status == 'pending':
                booking.razorpay_payment_id = payment_id
                booking.status = 'confirmed'
                booking.save(update_fields=['razorpay_payment_id', 'status'])
                _fire_emails(booking.id, include_owner=True)
        except Booking.DoesNotExist:
            pass

    # Always 200 — Razorpay retries indefinitely on non-2xx
    return Response({'status': 'ok'})
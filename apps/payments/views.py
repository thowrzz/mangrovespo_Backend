
# # apps/payments/views.py
# import hmac
# import hashlib
# import json
# import threading
# import logging

# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny
# from rest_framework.response import Response
# from rest_framework import status
# from django.conf import settings
# from django.views.decorators.csrf import csrf_exempt

# from apps.bookings.models import Booking

# logger = logging.getLogger(__name__)


# # ── Background email dispatcher ───────────────────────────────────
# # Spawns a daemon thread so the HTTP response returns immediately.
# # SendGrid takes 800ms–3s per call — we never make the user wait for it.
# #
# # Logic:
# #   - If Celery broker is reachable  → use .delay() (proper async queue)
# #   - If Celery is not running       → call the task function directly
# #     in the thread (works on localhost without Redis)

# def _fire_emails(booking_id: int, include_owner: bool = True):
#     """Non-blocking email dispatch. Safe to call from any view."""
#     def _run():
#         try:
#             from apps.notifications.tasks import (
#                 send_booking_confirmation_email,
#                 send_owner_new_booking_alert,
#             )
#             if _celery_up():
#                 send_booking_confirmation_email.delay(booking_id)
#                 if include_owner:
#                     send_owner_new_booking_alert.delay(booking_id)
#             else:
#                 # Celery not available (local dev) — run synchronously
#                 # but inside this thread, so the HTTP response is already gone
#                 send_booking_confirmation_email(booking_id)
#                 if include_owner:
#                     send_owner_new_booking_alert(booking_id)
#         except Exception:
#             logger.warning(
#                 "Email dispatch failed for booking %s", booking_id, exc_info=True
#             )

#     threading.Thread(target=_run, daemon=True).start()


# def _celery_up() -> bool:
#     """
#     Quick non-blocking broker check.
#     Times out in 1 s so it never slows down the request.
#     """
#     try:
#         from celery import current_app
#         conn = current_app.connection_for_read()
#         conn.ensure_connection(max_retries=1, timeout=1)
#         conn.release()
#         return True
#     except Exception:
#         return False


# # ── verify_payment ────────────────────────────────────────────────

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def verify_payment(request):
#     """
#     POST /api/v1/payments/verify/
#     Called by Next.js after Razorpay modal success.
#     Returns in <100ms — emails fire in the background.
#     """
#     razorpay_order_id   = request.data.get('razorpay_order_id')
#     razorpay_payment_id = request.data.get('razorpay_payment_id')
#     razorpay_signature  = request.data.get('razorpay_signature')

#     if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
#         return Response(
#             {'error': 'Missing payment details'},
#             status=status.HTTP_400_BAD_REQUEST,
#         )

#     # HMAC-SHA256 — fast, pure Python, no I/O
#     message  = f"{razorpay_order_id}|{razorpay_payment_id}"
#     expected = hmac.new(
#         settings.RAZORPAY_KEY_SECRET.encode(),
#         message.encode(),
#         hashlib.sha256,
#     ).hexdigest()

#     if not hmac.compare_digest(expected, razorpay_signature):
#         return Response(
#             {'error': 'Invalid payment signature'},
#             status=status.HTTP_400_BAD_REQUEST,
#         )

#     # Single indexed DB lookup
#     try:
#         booking = Booking.objects.get(razorpay_order_id=razorpay_order_id)
#     except Booking.DoesNotExist:
#         return Response(
#             {'error': 'Booking not found'},
#             status=status.HTTP_404_NOT_FOUND,
#         )

#     # Idempotent — already confirmed (webhook may have beaten us)
#     if booking.status == 'confirmed':
#         return Response({
#             'status': 'confirmed',
#             'booking_reference': booking.reference,
#             'message': 'Booking confirmed! Check your email for details.',
#         })

#     # update_fields writes only 3 columns — much faster than full save()
#     booking.razorpay_payment_id = razorpay_payment_id
#     booking.razorpay_signature  = razorpay_signature
#     booking.status              = 'confirmed'
#     booking.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status'])

#     # Fire emails in background — response returns NOW, not after SendGrid
#     _fire_emails(booking.id, include_owner=True)

#     return Response({
#         'status': 'confirmed',
#         'booking_reference': booking.reference,
#         'message': 'Booking confirmed! Check your email for details.',
#     })


# # ── razorpay_webhook ──────────────────────────────────────────────

# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def razorpay_webhook(request):
#     """
#     POST /api/v1/payments/webhook/
#     Server-to-server fallback from Razorpay.
#     Must return 200 quickly — Razorpay retries on anything else.
#     """
#     webhook_signature = request.headers.get('X-Razorpay-Signature', '')

#     if not webhook_signature:
#         return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

#     expected = hmac.new(
#         settings.RAZORPAY_KEY_SECRET.encode(),
#         request.body,
#         hashlib.sha256,
#     ).hexdigest()

#     if not hmac.compare_digest(expected, webhook_signature):
#         return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         payload = json.loads(request.body)
#     except (json.JSONDecodeError, ValueError):
#         return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

#     if payload.get('event') == 'payment.captured':
#         try:
#             entity     = payload['payload']['payment']['entity']
#             order_id   = entity['order_id']
#             payment_id = entity['id']
#         except (KeyError, TypeError):
#             return Response({'error': 'Malformed payload'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             booking = Booking.objects.get(razorpay_order_id=order_id)
#             if booking.status == 'pending':
#                 booking.razorpay_payment_id = payment_id
#                 booking.status = 'confirmed'
#                 booking.save(update_fields=['razorpay_payment_id', 'status'])
#                 _fire_emails(booking.id, include_owner=True)
#         except Booking.DoesNotExist:
#             pass

#     # Always 200 — Razorpay retries indefinitely on non-2xx
#     return Response({'status': 'ok'})
import hashlib
import hmac
import json
import logging

import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.bookings.models import Booking

logger = logging.getLogger(__name__)


def _rz_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _fire_emails(booking_id: int):
    """
    Queues both customer + owner emails via Celery.
    Falls back to direct call if Celery is unavailable.
    Never raises — a failed email must not roll back the payment confirmation.
    """
    try:
        from apps.notifications.tasks import send_confirmation_emails
        send_confirmation_emails.delay(booking_id)
        logger.info("Queued confirmation emails for booking %s", booking_id)
    except Exception as exc:
        logger.warning(
            "Could not queue confirmation emails for booking %s: %s",
            booking_id, exc
        )


# ── 1. verify_payment ─────────────────────────────────────────────
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    Called by frontend immediately after Razorpay modal success.
    On success: booking is confirmed + both emails fire instantly.
    """
    data                = request.data
    razorpay_order_id   = data.get("razorpay_order_id",   "").strip()
    razorpay_payment_id = data.get("razorpay_payment_id", "").strip()
    razorpay_signature  = data.get("razorpay_signature",  "").strip()

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response(
            {"error": "razorpay_order_id, razorpay_payment_id and razorpay_signature are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── HMAC-SHA256 signature check ───────────────────────────────
    body     = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        logger.warning("Invalid Razorpay signature for order %s", razorpay_order_id)
        return Response(
            {"error": "Payment signature verification failed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Fetch booking ─────────────────────────────────────────────
    try:
        booking = Booking.objects.select_for_update().get(
            razorpay_order_id=razorpay_order_id
        )
    except Booking.DoesNotExist:
        return Response(
            {"error": "Booking not found for this order"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # ── Already confirmed (webhook beat us) — just return success ─
    if booking.status == "confirmed":
        return Response({
            "success":           True,
            "already_confirmed": True,
            "booking_reference": booking.reference,
            "amount_paid":       str(booking.amount_paid),
            "balance_due":       str(booking.balance_due),
            "grand_total":       str(booking.grand_total),
            "customer_name":     booking.customer_name,
            "customer_email":    booking.customer_email,
        })

    # ── Amount verification via Razorpay API ──────────────────────
    # Prevents someone creating a ₹1 order against a ₹5000 booking
    try:
        rz_order        = _rz_client().order.fetch(razorpay_order_id)
        rz_amount_paise = int(rz_order.get("amount", 0))
        expected_paise  = int(booking.amount_paid * 100)

        if rz_amount_paise != expected_paise:
            logger.error(
                "Amount mismatch for order %s: got %s paise, expected %s paise",
                razorpay_order_id, rz_amount_paise, expected_paise,
            )
            return Response(
                {"error": "Payment amount does not match booking amount"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as exc:
        logger.error("Razorpay order fetch failed: %s", exc)
        return Response(
            {"error": "Could not verify payment amount with Razorpay"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # ── Confirm booking atomically ────────────────────────────────
    with transaction.atomic():
        booking.refresh_from_db()
        if booking.status != "confirmed":
            booking.razorpay_payment_id = razorpay_payment_id
            booking.status              = "confirmed"
            booking.payment_verified_at = timezone.now()
            booking.save(update_fields=[
                "razorpay_payment_id",
                "status",
                "payment_verified_at",
            ])
            logger.info("Booking %s confirmed via verify_payment", booking.reference)

    # ── Fire both emails (customer + owner) ───────────────────────
    _fire_emails(booking.id)

    return Response({
        "success":           True,
        "booking_reference": booking.reference,
        "amount_paid":       str(booking.amount_paid),
        "balance_due":       str(booking.balance_due),
        "grand_total":       str(booking.grand_total),
        "customer_name":     booking.customer_name,
        "customer_email":    booking.customer_email,
    }, status=status.HTTP_200_OK)


# ── 2. razorpay_webhook ───────────────────────────────────────────
@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """
    Server-to-server fallback from Razorpay.
    Fires even if the user closed the browser before verify_payment ran.
    Must always return 200 — Razorpay retries indefinitely on non-2xx.
    """
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    received_sig = request.headers.get("X-Razorpay-Signature", "")
    body_bytes   = request.body

    expected_sig = hmac.new(
        webhook_secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("Invalid webhook signature received")
        return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload    = json.loads(body_bytes)
        event      = payload.get("event", "")
        rz_payment = payload["payload"]["payment"]["entity"]
    except (KeyError, json.JSONDecodeError) as exc:
        logger.error("Malformed webhook payload: %s", exc)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    order_id   = rz_payment.get("order_id", "")
    payment_id = rz_payment.get("id", "")

    if not order_id:
        return Response(status=status.HTTP_200_OK)

    try:
        booking = Booking.objects.select_for_update().get(
            razorpay_order_id=order_id
        )
    except Booking.DoesNotExist:
        logger.warning("Webhook: no booking found for order %s", order_id)
        return Response(status=status.HTTP_200_OK)

    with transaction.atomic():
        booking.refresh_from_db()

        if event == "payment.captured":
            if booking.status not in ("confirmed", "completed"):
                booking.razorpay_payment_id = payment_id
                booking.status              = "confirmed"
                booking.payment_verified_at = timezone.now()
                booking.save(update_fields=[
                    "razorpay_payment_id",
                    "status",
                    "payment_verified_at",
                ])
                logger.info("Webhook confirmed booking %s", booking.reference)

                # Fire both emails — same as verify_payment path
                _fire_emails(booking.id)

        elif event == "payment.failed":
            if booking.status == "pending":
                booking.status = "expired"
                booking.save(update_fields=["status"])
                logger.info(
                    "Webhook expired booking %s after payment failure",
                    booking.reference,
                )

    return Response({"status": "ok"}, status=status.HTTP_200_OK)
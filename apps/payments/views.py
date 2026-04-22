
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
"""
apps/payments/views.py

Two endpoints:
  POST /api/v1/payments/verify/   — frontend calls after Razorpay modal closes
  POST /api/v1/payments/webhook/  — Razorpay server→server fallback

Key guarantees:
  1. booking.status = 'confirmed' is written atomically (select_for_update)
  2. Emails are queued via transaction.on_commit() — they only fire AFTER
     the DB row is committed, so the Celery worker always sees 'confirmed'
  3. Both paths use the same _confirm_and_notify() function — no drift
  4. Idempotent: calling either endpoint twice is safe
"""

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
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.bookings.models import Booking

logger = logging.getLogger(__name__)


# ── Razorpay client ───────────────────────────────────────────────
def _rz_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ── Signature helpers ─────────────────────────────────────────────
def _verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """HMAC-SHA256 — Razorpay's documented verify method for payments."""
    body     = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_webhook_signature(body_bytes: bytes, received: str) -> bool:
    """HMAC-SHA256 — Razorpay webhook verification uses the webhook secret."""
    secret   = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    expected = hmac.new(
        secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received)


# ── Core: atomic confirm + email dispatch ─────────────────────────
def _confirm_and_notify(order_id: str, payment_id: str) -> tuple[Booking, bool]:
    """
    Atomically confirm a booking and schedule confirmation emails.

    Returns:
        (booking, was_already_confirmed)

    Raises:
        Booking.DoesNotExist  — no booking for this order_id
        ValueError            — amount mismatch (tamper attempt)

    Email dispatch uses transaction.on_commit() so emails are only
    queued AFTER the transaction commits. If the transaction rolls
    back for any reason, no emails are sent — correct behaviour.
    """
    with transaction.atomic():
        # select_for_update locks the row — prevents double-confirm race
        try:
            booking = Booking.objects.select_for_update().get(
                razorpay_order_id=order_id
            )
        except Booking.DoesNotExist:
            raise

        # ── Idempotent: already confirmed (other path beat us) ────
        if booking.status in ("confirmed", "completed"):
            return booking, True

        # ── Amount tamper check ───────────────────────────────────
        # Fetches the order from Razorpay and verifies the amount
        # matches what we stored. Prevents someone creating a ₹1
        # Razorpay order and replaying it against a ₹5000 booking.
        try:
            rz_order        = _rz_client().order.fetch(order_id)
            rz_amount_paise = int(rz_order.get("amount", 0))
            expected_paise  = int(booking.amount_paid * 100)

            if rz_amount_paise != expected_paise:
                logger.error(
                    "Amount mismatch order=%s got=%s expected=%s",
                    order_id, rz_amount_paise, expected_paise,
                )
                raise ValueError(
                    f"Payment amount mismatch: received {rz_amount_paise} paise, "
                    f"expected {expected_paise} paise"
                )
        except ValueError:
            raise
        except Exception as exc:
            # Razorpay API down — log but don't block; signature already verified
            logger.warning("Razorpay order fetch failed for %s: %s", order_id, exc)

        # ── Write confirmation ────────────────────────────────────
        booking.razorpay_payment_id = payment_id
        booking.status              = "confirmed"
        booking.payment_verified_at = timezone.now()
        booking.save(update_fields=[
            "razorpay_payment_id",
            "status",
            "payment_verified_at",
        ])
        logger.info("Booking %s confirmed (order %s)", booking.reference, order_id)

        # ── Queue emails AFTER commit ─────────────────────────────
        # on_commit fires _enqueue only when this transaction commits.
        # If the transaction rolls back, nothing is queued.
        # The 3-second countdown gives DB replicas time to catch up
        # before the Celery worker does its own Booking.objects.get().
        booking_id = booking.pk  # capture before leaving atomic block

        def _enqueue():
            from apps.notifications.tasks import send_confirmation_emails
            try:
                send_confirmation_emails.apply_async(
                    args=[booking_id],
                    countdown=3,  # 3s delay — lets DB replica settle
                )
                logger.info(
                    "Queued confirmation emails for booking %s", booking_id
                )
            except Exception as exc:
                # Celery/Redis down — fall back to synchronous send
                logger.warning(
                    "Celery unavailable, sending emails synchronously "
                    "for booking %s: %s", booking_id, exc
                )
                try:
                    from apps.notifications.tasks import send_confirmation_emails
                    send_confirmation_emails(booking_id)
                except Exception as mail_exc:
                    logger.error(
                        "Synchronous email fallback also failed for "
                        "booking %s: %s", booking_id, mail_exc
                    )

        transaction.on_commit(_enqueue)

    return booking, False


# ─────────────────────────────────────────────────────────────────
# ENDPOINT 1: verify_payment
# Called by the frontend Razorpay handler after modal success.
# ─────────────────────────────────────────────────────────────────
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    Frontend flow:
      1. User completes payment in Razorpay modal
      2. Razorpay calls handler(response) in the browser
      3. Frontend POSTs { razorpay_order_id, razorpay_payment_id, razorpay_signature }
      4. This view verifies, confirms booking, queues emails
      5. Returns booking data → frontend shows SuccessScreen

    Only after this returns 200 does the frontend show the success screen.
    """
    data                = request.data
    razorpay_order_id   = (data.get("razorpay_order_id")   or "").strip()
    razorpay_payment_id = (data.get("razorpay_payment_id") or "").strip()
    razorpay_signature  = (data.get("razorpay_signature")  or "").strip()

    # ── Field validation ──────────────────────────────────────────
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response(
            {"error": "razorpay_order_id, razorpay_payment_id and razorpay_signature are all required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Signature check ───────────────────────────────────────────
    if not _verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning("verify_payment: bad signature for order %s", razorpay_order_id)
        return Response(
            {"error": "Payment signature verification failed. Payment may be fraudulent."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Confirm + notify ──────────────────────────────────────────
    try:
        booking, was_already_confirmed = _confirm_and_notify(
            razorpay_order_id, razorpay_payment_id
        )
    except Booking.DoesNotExist:
        logger.error("verify_payment: no booking for order %s", razorpay_order_id)
        return Response(
            {"error": "Booking not found for this payment order."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        logger.exception("verify_payment: unexpected error for order %s: %s", razorpay_order_id, exc)
        return Response(
            {"error": "Internal error confirming booking. Payment was captured — reference saved."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Success response ──────────────────────────────────────────
    # All fields come from the DB — frontend must not calculate anything
    return Response({
        "success":           True,
        "already_confirmed": was_already_confirmed,
        "booking_reference": booking.reference,
        "amount_paid":       str(booking.amount_paid),   # 50% — paid now
        "balance_due":       str(booking.balance_due),   # 50% — due at arrival
        "grand_total":       str(booking.grand_total),
        "customer_name":     booking.customer_name,
        "customer_email":    booking.customer_email,
        "customer_phone":    booking.customer_phone,
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────
# ENDPOINT 2: razorpay_webhook
# Razorpay calls this server-to-server on payment.captured.
# Fires even when the user closes the browser before verify_payment runs.
# ─────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """
    Razorpay Dashboard setup:
      URL:    https://your-domain.com/api/v1/payments/webhook/
      Secret: RAZORPAY_WEBHOOK_SECRET in .env
      Events: ✅ payment.captured   ✅ payment.failed

    ALWAYS return 200 — Razorpay retries indefinitely on non-2xx.
    """
    # ── Config check ──────────────────────────────────────────────
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.critical(
            "RAZORPAY_WEBHOOK_SECRET not set — webhook endpoint is insecure and disabled"
        )
        return Response(
            {"error": "Webhook not configured"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Signature check ───────────────────────────────────────────
    received_sig = request.headers.get("X-Razorpay-Signature", "")
    if not _verify_webhook_signature(request.body, received_sig):
        logger.warning("razorpay_webhook: invalid signature")
        return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

    # ── Parse event ───────────────────────────────────────────────
    try:
        payload    = json.loads(request.body)
        event      = payload.get("event", "")
        rz_payment = payload["payload"]["payment"]["entity"]
        order_id   = rz_payment.get("order_id", "")
        payment_id = rz_payment.get("id", "")
    except (KeyError, json.JSONDecodeError, TypeError) as exc:
        logger.error("razorpay_webhook: malformed payload — %s", exc)
        return Response({"error": "Malformed payload"}, status=status.HTTP_400_BAD_REQUEST)

    if not order_id:
        # Not a booking-related event — ignore
        return Response({"status": "ignored"}, status=status.HTTP_200_OK)

    # ── Handle payment.captured ───────────────────────────────────
    if event == "payment.captured":
        try:
            booking, was_already = _confirm_and_notify(order_id, payment_id)
            if was_already:
                logger.info("razorpay_webhook: booking already confirmed for order %s", order_id)
            else:
                logger.info("razorpay_webhook: confirmed booking %s", booking.reference)
        except Booking.DoesNotExist:
            # Could be a non-booking Razorpay order (test, refund, etc.) — ignore
            logger.warning("razorpay_webhook: no booking for order %s", order_id)
        except ValueError as exc:
            # Amount mismatch — log for manual review but return 200
            # so Razorpay doesn't hammer us with retries
            logger.error(
                "razorpay_webhook: amount mismatch for order %s — %s", order_id, exc
            )
        except Exception as exc:
            # Unexpected error — log but return 200 (Razorpay must not retry)
            logger.exception(
                "razorpay_webhook: unexpected error for order %s — %s", order_id, exc
            )

    # ── Handle payment.failed ─────────────────────────────────────
    elif event == "payment.failed":
        try:
            with transaction.atomic():
                booking = Booking.objects.select_for_update().get(
                    razorpay_order_id=order_id
                )
                if booking.status == "pending":
                    booking.status = "expired"
                    booking.save(update_fields=["status"])
                    logger.info(
                        "razorpay_webhook: expired booking %s after payment.failed",
                        booking.reference,
                    )
        except Booking.DoesNotExist:
            pass
        except Exception as exc:
            logger.error(
                "razorpay_webhook: error handling payment.failed for order %s — %s",
                order_id, exc,
            )

    # Always 200 ──────────────────────────────────────────────────
    return Response({"status": "ok"}, status=status.HTTP_200_OK)
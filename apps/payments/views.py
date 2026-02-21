import hmac
import hashlib
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.models import Booking


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    POST /api/v1/payments/verify/
    Called by Next.js after Razorpay modal payment success.
    Verifies HMAC-SHA256 signature and confirms booking.
    """
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response({'error': 'Missing payment details'}, status=400)

    # HMAC-SHA256 signature verification
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        return Response({'error': 'Invalid payment signature'}, status=400)

    # Confirm booking
    booking = get_object_or_404(Booking, razorpay_order_id=razorpay_order_id)
    booking.razorpay_payment_id = razorpay_payment_id
    booking.razorpay_signature = razorpay_signature
    booking.status = 'confirmed'
    booking.save()

    # Fire confirmation emails
    from apps.notifications.tasks import send_booking_confirmation_email, send_owner_new_booking_alert
    send_booking_confirmation_email.delay(booking.id)
    send_owner_new_booking_alert.delay(booking.id)

    return Response({
        'status': 'confirmed',
        'booking_reference': booking.reference,
        'message': 'Booking confirmed! Check your email for details.'
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """
    POST /api/v1/payments/webhook/
    Razorpay server-to-server webhook — fallback safety net.
    """
    webhook_secret = settings.RAZORPAY_KEY_SECRET
    webhook_signature = request.headers.get('X-Razorpay-Signature', '')

    expected = hmac.new(
        webhook_secret.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, webhook_signature):
        return Response({'error': 'Invalid webhook signature'}, status=400)

    payload = json.loads(request.body)
    event = payload.get('event')

    if event == 'payment.captured':
        order_id = payload['payload']['payment']['entity']['order_id']
        payment_id = payload['payload']['payment']['entity']['id']
        try:
            booking = Booking.objects.get(razorpay_order_id=order_id)
            if booking.status == 'pending':
                booking.razorpay_payment_id = payment_id
                booking.status = 'confirmed'
                booking.save()
        except Booking.DoesNotExist:
            pass

    return Response({'status': 'ok'})

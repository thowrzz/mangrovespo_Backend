from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import Booking, BookingItem
from .serializers import BookingInitiateSerializer, BookingSerializer


# ─── PUBLIC ───────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_booking(request):
    """
    POST /api/v1/bookings/initiate/
    Creates a pending booking and returns Razorpay order_id.
    """
    serializer = BookingInitiateSerializer(data=request.data)
    if serializer.is_valid():
        booking, razorpay_order_id = serializer.save()
        return Response({
            'booking_reference': booking.reference,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_key_id': __import__('django.conf', fromlist=['settings']).settings.RAZORPAY_KEY_ID,
            'grand_total': str(booking.grand_total),
            'customer_name': booking.customer_name,
            'customer_email': booking.customer_email,
            'customer_phone': booking.customer_phone,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def lookup_booking(request):
    """
    GET /api/v1/bookings/lookup/?email=x&reference=MS-2026-XXXX
    Customer self-service lookup — no account required.
    """
    email = request.query_params.get('email')
    reference = request.query_params.get('reference')
    if not email or not reference:
        return Response({'error': 'email and reference are required'}, status=400)
    booking = get_object_or_404(
        Booking,
        customer_email__iexact=email,
        reference__iexact=reference,
        status__in=['confirmed', 'completed', 'cancelled']
    )
    return Response(BookingSerializer(booking).data)


# ─── ADMIN ────────────────────────────────────────────────────────

class AdminBookingListView(generics.ListAPIView):
    """GET /api/v1/admin/bookings/ with filters."""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'items__visit_date', 'items__activity']
    search_fields = ['customer_name', 'customer_phone', 'reference']

    def get_queryset(self):
        return Booking.objects.exclude(status='expired').prefetch_related('items__activity', 'items__slot')


class AdminBookingDetailView(generics.RetrieveAPIView):
    """GET /api/v1/admin/bookings/<reference>/"""
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    queryset = Booking.objects.prefetch_related('items__activity', 'items__slot')
    lookup_field = 'reference'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, reference):
    """POST /api/v1/admin/bookings/<reference>/cancel/"""
    booking = get_object_or_404(Booking, reference=reference, status='confirmed')
    booking.status = 'cancelled'
    booking.save()
    from apps.notifications.tasks import send_cancellation_email
    send_cancellation_email.delay(booking.id)
    return Response({'status': 'cancelled', 'reference': reference})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_booking(request, reference):
    """POST /api/v1/admin/bookings/<reference>/complete/"""
    booking = get_object_or_404(Booking, reference=reference, status='confirmed')
    booking.status = 'completed'
    booking.save()
    return Response({'status': 'completed', 'reference': reference})
class AdminBookingDetailView_ById(generics.RetrieveAPIView):
    """GET /api/v1/admin/bookings/<id>/  — frontend detail view"""
    permission_classes = [IsAuthenticated]
    serializer_class   = BookingSerializer
    queryset           = Booking.objects.prefetch_related('items__activity', 'items__slot')
    lookup_field       = 'pk'
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_booking_status(request, pk):
    """PATCH /api/v1/admin/bookings/<id>/status/"""
    booking = get_object_or_404(Booking, pk=pk)

    new_status = request.data.get('status')

    valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
    if not new_status:
        return Response({'error': 'status is required'}, status=400)
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Invalid status. Choose from: {valid_statuses}'},
            status=400
        )

    old_status = booking.status
    booking.status = new_status
    booking.save()

    # Fire notification tasks on specific transitions
    if new_status == 'cancelled' and old_status == 'confirmed':
        try:
            from apps.notifications.tasks import send_cancellation_email
            send_cancellation_email.delay(booking.id)
        except Exception:
            pass  # Don't break the response if Celery is not running

    return Response({
        'success':   True,
        'id':        booking.id,
        'reference': booking.reference,
        'status':    booking.status,
    })

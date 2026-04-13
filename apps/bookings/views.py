from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import Booking, BookingItem
from .serializers import BookingInitiateSerializer, BookingSerializer


# Helpers

def _safe_str(value, default='0'):
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _serialize_booking(b):
    first_item = b.items.first()
    amount_paid = (
        getattr(b, 'amount_paid', None)
        or getattr(b, 'paid_amount', None)
        or getattr(b, 'amount_to_pay', None)
    )
    items_data = []
    for item in b.items.all():
        activity = getattr(item, 'activity', None)
        price = (
            getattr(item, 'price', None)
            or getattr(item, 'subtotal', None)
            or getattr(item, 'total_price', None)
        )
        items_data.append({
            'activity_name':  activity.name              if activity else '',
            'activity_image': (activity.image_url or '') if activity else '',
            'num_adults':     getattr(item, 'num_adults',   0),
            'num_children':   getattr(item, 'num_children', 0),
            'price':          _safe_str(price),
        })
    return {
        'reference':      b.reference,
        'status':         b.status,
        'created_at':     b.created_at.strftime('%d %b %Y') if b.created_at else '',
        'visit_date':     str(first_item.visit_date)   if first_item and first_item.visit_date   else None,
        'arrival_time':   str(first_item.arrival_time) if first_item and first_item.arrival_time else None,
        'grand_total':    _safe_str(getattr(b, 'grand_total', None)),
        'amount_paid':    _safe_str(amount_paid),
        'balance_due':    _safe_str(getattr(b, 'balance_due', None)),
        'customer_name':  b.customer_name,
        'customer_email': b.customer_email,
        'items':          items_data,
    }


# PUBLIC

@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_booking(request):
    serializer = BookingInitiateSerializer(data=request.data)
    if serializer.is_valid():
        booking, razorpay_order_id = serializer.save()
        from django.conf import settings
        return Response({
            'booking_reference': booking.reference,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_key_id':   settings.RAZORPAY_KEY_ID,
            'grand_total':       str(booking.grand_total),
            'amount_to_pay':     str(booking.amount_paid),
            'balance_due':       str(booking.balance_due),
            'payment_mode':      booking.payment_mode,
            'customer_name':     booking.customer_name,
            'customer_email':    booking.customer_email,
            'customer_phone':    booking.customer_phone,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def lookup_booking(request):
    email     = request.query_params.get('email')
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


# CUSTOMER: My Bookings

class MyBookingsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        email = request.user.email
        if not email:
            return Response(
                {'detail': 'User account has no email address.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        bookings = (
            Booking.objects
            .filter(customer_email__iexact=email)
            .exclude(status='expired')
            .prefetch_related('items__activity')
            .order_by('-created_at')
        )
        return Response([_serialize_booking(b) for b in bookings])


# ADMIN

class AdminBookingListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = BookingSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['status', 'items__visit_date', 'items__activity']
    search_fields      = ['customer_name', 'customer_phone', 'reference']

    def get_queryset(self):
        return (
            Booking.objects
            .exclude(status='expired')
            .prefetch_related('items__activity', 'items__slot')
        )


class AdminBookingDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = BookingSerializer
    queryset           = Booking.objects.prefetch_related('items__activity', 'items__slot')
    lookup_field       = 'reference'


class AdminBookingDetailView_ById(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = BookingSerializer
    queryset           = Booking.objects.prefetch_related('items__activity', 'items__slot')
    lookup_field       = 'pk'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, status='confirmed')
    booking.status = 'cancelled'
    booking.save()
    from apps.notifications.tasks import send_cancellation_email
    send_cancellation_email.delay(booking.id)
    return Response({'status': 'cancelled', 'reference': reference})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, status='confirmed')
    booking.status = 'completed'
    booking.save()
    return Response({'status': 'completed', 'reference': reference})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    new_status     = request.data.get('status')
    valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
    if not new_status:
        return Response({'error': 'status is required'}, status=400)
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Invalid status. Choose from: {valid_statuses}'},
            status=400
        )
    old_status     = booking.status
    booking.status = new_status
    booking.save()
    if new_status == 'cancelled' and old_status == 'confirmed':
        try:
            from apps.notifications.tasks import send_cancellation_email
            send_cancellation_email.delay(booking.id)
        except Exception:
            pass
    return Response({
        'success':   True,
        'id':        booking.id,
        'reference': booking.reference,
        'status':    booking.status,
    })
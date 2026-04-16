from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, F, ExpressionWrapper, IntegerField
from django.utils import timezone
from datetime import timedelta, date
import csv
from django.http import HttpResponse

from apps.bookings.models import Booking, BookingItem
from apps.activities.models import Activity


# ── Helpers ───────────────────────────────────────────────────────


def _serialize_booking_for_list(booking):
    """Shared serializer for today/tomorrow booking list rows."""
    items = booking.items.select_related('activity', 'slot').all()
    activities = [item.activity.name for item in items]

    # ✅ FIX: filter out slot-less items BEFORE sorting, so sort key never hits None
    slotted = [item for item in items if item.slot]
    slots   = [item.slot.label for item in sorted(slotted, key=lambda i: i.slot.time)]

    return {
        'id':             booking.id,
        'reference':      booking.reference,
        'customer_name':  booking.customer_name,
        'customer_phone': booking.customer_phone,
        'customer_email': booking.customer_email,
        'activities':     activities,
        'earliest_slot':  slots[0] if slots else None,
        'grand_total':    str(booking.grand_total),
        'status':         booking.status,
    }


# ── Total persons helper ──────────────────────────────────────────

# ✅ FIX: num_persons no longer exists — use num_adults + num_children
_total_persons = ExpressionWrapper(
    F('num_adults') + F('num_children'),
    output_field=IntegerField(),
)


# ── Dashboard Stats ───────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    today     = date.today()
    tomorrow  = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    today_bookings_qs = Booking.objects.filter(
        items__visit_date=today,
        status__in=['confirmed', 'pending'],
    ).distinct().prefetch_related('items__activity', 'items__slot')

    today_revenue = Booking.objects.filter(
        items__visit_date=today,
        status='confirmed',
    ).distinct().aggregate(t=Sum('grand_total'))['t'] or 0

    yesterday_revenue = Booking.objects.filter(
        items__visit_date=yesterday,
        status='confirmed',
    ).distinct().aggregate(t=Sum('grand_total'))['t'] or 0

    yesterday_bookings_count = Booking.objects.filter(
        items__visit_date=yesterday,
        status__in=['confirmed', 'pending'],
    ).distinct().count()

    def pct_change(today_val, yesterday_val):
        if yesterday_val == 0:
            return 100 if today_val > 0 else 0
        return round((today_val - yesterday_val) / yesterday_val * 100)

    revenue_trend = pct_change(float(today_revenue), float(yesterday_revenue))
    booking_trend = pct_change(today_bookings_qs.count(), yesterday_bookings_count)

    month_start = today.replace(day=1)
    month_revenue = Booking.objects.filter(
        created_at__date__gte=month_start,
        status='confirmed',
    ).aggregate(t=Sum('grand_total'))['t'] or 0

    month_bookings = Booking.objects.filter(
        created_at__date__gte=month_start,
        status='confirmed',
    ).count()

    total_customers = Booking.objects.filter(
        status__in=['confirmed', 'completed']
    ).values('customer_email').distinct().count()

    tomorrow_bookings_qs = Booking.objects.filter(
        items__visit_date=tomorrow,
        status__in=['confirmed', 'pending'],
    ).distinct().prefetch_related('items__activity', 'items__slot')

    return Response({
        'today_revenue':         float(today_revenue),
        'today_bookings':        today_bookings_qs.count(),
        'revenue_trend':         revenue_trend,
        'booking_trend':         booking_trend,
        'month_revenue':         float(month_revenue),
        'month_bookings':        month_bookings,
        'total_customers':       total_customers,
        'today_booking_list':    [_serialize_booking_for_list(b) for b in today_bookings_qs],
        'tomorrow_booking_list': [_serialize_booking_for_list(b) for b in tomorrow_bookings_qs],
    })


# ── Revenue Chart ─────────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_chart(request):
    try:
        days = int(request.query_params.get('days', 7))
        days = min(max(days, 1), 90)
    except ValueError:
        days = 7

    today = date.today()
    data  = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        revenue = Booking.objects.filter(
            items__visit_date=d,
            status='confirmed',
        ).distinct().aggregate(t=Sum('grand_total'))['t'] or 0
        data.append({
            'date':    d.strftime('%b %d') if days > 7 else d.strftime('%a'),
            'revenue': float(revenue),
        })

    return Response({'data': data})


# ── Activity Breakdown ────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_breakdown(request):
    rows = (
        BookingItem.objects
        .filter(booking__status__in=['confirmed', 'completed'])
        .values('activity__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )
    data = [{'activity': r['activity__name'], 'count': r['count']} for r in rows]
    return Response({'data': data})


# ── Daily Report ──────────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_report(request):
    report_date = request.query_params.get('date', date.today().isoformat())
    bookings = Booking.objects.filter(
        items__visit_date=report_date,
        status='confirmed',
    ).distinct()

    by_activity = BookingItem.objects.filter(
        visit_date=report_date,
        booking__status='confirmed',
    ).values('activity__name').annotate(
        total_revenue=Sum('price_snapshot'),
        booking_count=Count('id'),
        total_persons=Sum(_total_persons),   # ✅ FIX: was Sum('num_persons')
    ).order_by('-total_revenue')

    return Response({
        'date':           report_date,
        'total_bookings': bookings.count(),
        'total_revenue':  bookings.aggregate(t=Sum('grand_total'))['t'] or 0,
        'by_activity':    list(by_activity),
    })


# ── Weekly Report ─────────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_report(request):
    today = date.today()
    days  = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        revenue = BookingItem.objects.filter(
            visit_date=d, booking__status='confirmed',
        ).aggregate(t=Sum('price_snapshot'))['t'] or 0
        count = Booking.objects.filter(
            items__visit_date=d, status='confirmed',
        ).distinct().count()
        days.append({'date': d.isoformat(), 'revenue': float(revenue), 'bookings': count})

    return Response({'days': days})


# ── CSV Export ────────────────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_bookings_csv(request):
    from_date = request.query_params.get('from', date.today().isoformat())
    to_date   = request.query_params.get('to',   date.today().isoformat())

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="mangrovespot_bookings_{from_date}_to_{to_date}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Reference', 'Customer', 'Phone', 'Email',
        'Activity', 'Date', 'Time Slot', 'Adults', 'Children', 'Amount', 'Status',
    ])

    items = BookingItem.objects.filter(
        visit_date__range=[from_date, to_date],
    ).select_related('booking', 'activity', 'slot').order_by('visit_date')

    for item in items:
        writer.writerow([
            item.booking.reference,
            item.booking.customer_name,
            item.booking.customer_phone,
            item.booking.customer_email,
            item.activity.name,
            item.visit_date,
            item.slot.label if item.slot else '',   # ✅ FIX: slot can be None
            item.num_adults,                         # ✅ FIX: was num_persons
            item.num_children,                       # ✅ FIX: added children column
            item.price_snapshot,
            item.booking.status,
        ])

    return response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, date
import csv
from django.http import HttpResponse

from apps.bookings.models import Booking, BookingItem
from apps.activities.models import Activity


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_report(request):
    """GET /api/v1/admin/reports/daily/?date=YYYY-MM-DD"""
    report_date = request.query_params.get('date', date.today().isoformat())
    bookings = Booking.objects.filter(
        items__visit_date=report_date,
        status='confirmed'
    ).distinct()

    by_activity = BookingItem.objects.filter(
        visit_date=report_date,
        booking__status='confirmed'
    ).values('activity__name').annotate(
        total_revenue=Sum('price_snapshot'),
        booking_count=Count('id'),
        total_persons=Sum('num_persons')
    ).order_by('-total_revenue')

    return Response({
        'date': report_date,
        'total_bookings': bookings.count(),
        'total_revenue': bookings.aggregate(t=Sum('grand_total'))['t'] or 0,
        'by_activity': list(by_activity),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_report(request):
    """GET /api/v1/admin/reports/weekly/ — last 7 days"""
    today = date.today()
    days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        revenue = BookingItem.objects.filter(
            visit_date=d, booking__status='confirmed'
        ).aggregate(t=Sum('price_snapshot'))['t'] or 0
        count = Booking.objects.filter(
            items__visit_date=d, status='confirmed'
        ).distinct().count()
        days.append({'date': d.isoformat(), 'revenue': float(revenue), 'bookings': count})

    return Response({'days': days})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_bookings_csv(request):
    """GET /api/v1/admin/reports/export/?from=YYYY-MM-DD&to=YYYY-MM-DD"""
    from_date = request.query_params.get('from', date.today().isoformat())
    to_date = request.query_params.get('to', date.today().isoformat())

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="mangrovespot_bookings_{from_date}_to_{to_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Reference', 'Customer', 'Phone', 'Email', 'Activity', 'Date', 'Time Slot', 'Persons', 'Amount', 'Status'])

    items = BookingItem.objects.filter(
        visit_date__range=[from_date, to_date]
    ).select_related('booking', 'activity', 'slot').order_by('visit_date')

    for item in items:
        writer.writerow([
            item.booking.reference,
            item.booking.customer_name,
            item.booking.customer_phone,
            item.booking.customer_email,
            item.activity.name,
            item.visit_date,
            item.slot.label,
            item.num_persons,
            item.price_snapshot,
            item.booking.status,
        ])
    return response

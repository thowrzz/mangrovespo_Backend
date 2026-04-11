from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from datetime import timedelta

from apps.bookings.models import Booking, BookingItem


# ── Paid statuses ─────────────────────────────────────────────────
PAID_STATUSES = ["confirmed", "completed"]


class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today       = timezone.localdate()
        yesterday   = today - timedelta(days=1)
        month_start = today.replace(day=1)

        # ── Today ─────────────────────────────────────────────
        today_revenue = Booking.objects.filter(
            created_at__date=today,
            status__in=PAID_STATUSES,
        ).aggregate(total=Sum("grand_total"))["total"] or 0

        today_bookings = Booking.objects.filter(
            created_at__date=today
        ).count()

        # ── Yesterday ─────────────────────────────────────────
        yesterday_revenue = Booking.objects.filter(
            created_at__date=yesterday,
            status__in=PAID_STATUSES,
        ).aggregate(total=Sum("grand_total"))["total"] or 0

        yesterday_bookings = Booking.objects.filter(
            created_at__date=yesterday
        ).count()

        def trend(today_val, yesterday_val):
            if yesterday_val == 0:
                return 100 if today_val > 0 else 0
            return round(((today_val - yesterday_val) / yesterday_val) * 100)

        # ── This month ────────────────────────────────────────
        month_revenue = Booking.objects.filter(
            created_at__date__gte=month_start,
            status__in=PAID_STATUSES,
        ).aggregate(total=Sum("grand_total"))["total"] or 0

        month_bookings = Booking.objects.filter(
            created_at__date__gte=month_start
        ).count()

        # ── Total unique customers ─────────────────────────────
        total_customers = Booking.objects.values(
            "customer_phone"
        ).distinct().count()

        # ── Today's booking list ───────────────────────────────
        today_list = (
            Booking.objects
            .filter(created_at__date=today)
            .prefetch_related("items__activity", "items__slot")
            .order_by("-created_at")
        )

        today_booking_list = []
        for b in today_list:
            items = b.items.all()

            activities = list({
                i.activity.name
                for i in items
                if i.activity
            })

            earliest = items.order_by("slot__time").first()

            today_booking_list.append({
                "id":                b.id,
                "booking_reference": b.reference,
                "customer_name":     b.customer_name,
                "customer_phone":    b.customer_phone,
                "activities":        activities,
                "item_count":        items.count(),
                "earliest_slot":     (
                    str(earliest.slot.time)
                    if earliest and earliest.slot
                    else None
                ),
                "grand_total":       str(b.grand_total),
                "status":            b.status,
            })

        return Response({
            "today_revenue":      float(today_revenue),
            "today_bookings":     today_bookings,
            "revenue_trend":      trend(today_revenue, yesterday_revenue),
            "booking_trend":      trend(today_bookings, yesterday_bookings),
            "month_revenue":      float(month_revenue),
            "month_bookings":     month_bookings,
            "total_customers":    total_customers,
            "today_booking_list": today_booking_list,
        })


class DashboardRevenueView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days  = min(int(request.query_params.get("days", 7)), 90)
        since = timezone.localdate() - timedelta(days=days - 1)

        rows = (
            Booking.objects
            .filter(
                created_at__date__gte=since,
                status__in=PAID_STATUSES,
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(revenue=Sum("grand_total"))
            .order_by("date")
        )

        data_map = {str(r["date"]): float(r["revenue"]) for r in rows}
        data = [
            {
                "date":    (since + timedelta(days=i)).strftime("%b %d"),
                "revenue": data_map.get(str(since + timedelta(days=i)), 0),
            }
            for i in range(days)
        ]

        return Response({"data": data})


class ActivityBreakdownView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        rows = (
            BookingItem.objects
            .filter(booking__status__in=PAID_STATUSES)
            .values("activity__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )

        data = [
            {
                "activity": r["activity__name"] or "Unknown",
                "count":    r["count"],
            }
            for r in rows
        ]

        return Response({"data": data})

from django.urls import path
from . import views

urlpatterns = [
    # ── Dashboard (used by admin frontend) ────────────────────────
    path('reports/dashboard/',views.dashboard_stats),
    path('reports/revenue-chart/', views.revenue_chart),
    path('reports/activity-breakdown/',views.activity_breakdown),

    # ── Existing reports ──────────────────────────────────────────
    path('reports/daily/',              views.daily_report),
    path('reports/weekly/',             views.weekly_report),
    path('reports/export/',             views.export_bookings_csv),
]
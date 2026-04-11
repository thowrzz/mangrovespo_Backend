from django.urls import path
from . import admin_views

urlpatterns = [
    path("dashboard/stats/",              admin_views.DashboardStatsView.as_view()),
    path("dashboard/revenue/",            admin_views.DashboardRevenueView.as_view()),
    path("dashboard/activity-breakdown/", admin_views.ActivityBreakdownView.as_view()),
]

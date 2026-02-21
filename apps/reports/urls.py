from django.urls import path
from . import views

urlpatterns = [
    path('reports/daily/', views.daily_report),
    path('reports/weekly/', views.weekly_report),
    path('reports/export/', views.export_bookings_csv),
]

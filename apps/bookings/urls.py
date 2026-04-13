from django.urls import path
from . import views
from .receipt import download_receipt
from .views import MyBookingsView  # add to existing imports

urlpatterns = [
    path('initiate/', views.initiate_booking, name='booking-initiate'),
    path('lookup/', views.lookup_booking, name='booking-lookup'),
    path('bookings/<str:reference>/receipt/', download_receipt, name='booking-receipt'),
    path('my-bookings/', MyBookingsView.as_view(), name='my-bookings'),
]

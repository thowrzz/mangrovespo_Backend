from django.urls import path
from . import views

urlpatterns = [
    path('initiate/', views.initiate_booking, name='booking-initiate'),
    path('lookup/', views.lookup_booking, name='booking-lookup'),
]

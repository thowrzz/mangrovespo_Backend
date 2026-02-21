from django.urls import path
from . import views

urlpatterns = [
    path('bookings/',                              views.AdminBookingListView.as_view()),
    path('bookings/<int:pk>/',                     views.AdminBookingDetailView_ById.as_view()),
    path('bookings/<int:pk>/status/',              views.update_booking_status),          # ← ADD
    path('bookings/<str:reference>/',              views.AdminBookingDetailView.as_view()),
    path('bookings/<str:reference>/cancel/',       views.cancel_booking),
    path('bookings/<str:reference>/complete/',     views.complete_booking),
]

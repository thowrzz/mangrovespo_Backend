from django.urls import path
from . import views

urlpatterns = [
    # ✅ FIX: was 'activities/check-date/' → now 'check-date/'
    path('check-date/',             views.check_date,                       name='check-date'),
    path('',                        views.ActivityListView.as_view(),        name='activity-list'),
    path('<int:pk>/',               views.ActivityDetailView.as_view(),      name='activity-detail'),
    path('<int:pk>/availability/',  views.activity_availability,             name='activity-availability'),
]
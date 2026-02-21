from django.urls import path
from . import views

urlpatterns = [
    path('blocked-dates/', views.BlockedDateListCreateView.as_view()),
    path('blocked-dates/<int:pk>/', views.BlockedDateDetailView.as_view()),
]

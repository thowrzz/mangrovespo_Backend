from django.urls import path
from . import views

urlpatterns = [
    path('', views.ActivityListView.as_view(), name='activity-list'),
    path('<int:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
    path('<int:pk>/availability/', views.activity_availability, name='activity-availability'),
]

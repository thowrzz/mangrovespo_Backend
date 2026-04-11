from django.urls import path
from . import views

urlpatterns = [
    # Activities
    path('activities/',            views.AdminActivityListCreateView.as_view()),
    path('activities/<int:pk>/',   views.AdminActivityDetailView.as_view()),
    path('activities/<int:pk>/upload-image/', views.upload_activity_image),

    # Slots
    path('activities/<int:activity_pk>/slots/', views.AdminSlotListCreateView.as_view()),
    path('slots/<int:pk>/',        views.AdminSlotDetailView.as_view()),

    # Rules
    path('activities/<int:activity_pk>/rules/',          views.AdminRuleListCreateView.as_view()),
    path('activities/<int:activity_pk>/rules/<int:pk>/', views.AdminRuleDetailView.as_view()),
]
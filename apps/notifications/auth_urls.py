# apps/notifications/auth_urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("token/",         TokenObtainPairView.as_view(),  name="admin_token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(),     name="admin_token_refresh"),
]

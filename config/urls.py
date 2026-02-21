from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # Public API — customer facing
    path('api/v1/activities/', include('apps.activities.urls')),
    path('api/v1/bookings/', include('apps.bookings.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),

    # Admin API — JWT protected
    path('api/v1/admin/', include('apps.activities.admin_urls')),
    path('api/v1/admin/', include('apps.bookings.admin_urls')),
    path('api/v1/admin/', include('apps.availability.urls')),
    path('api/v1/admin/', include('apps.reports.urls')),
    path('api/v1/admin/', include('apps.reports.admin_urls')),

    path('api/v1/admin/auth/', include('apps.notifications.auth_urls')),
]

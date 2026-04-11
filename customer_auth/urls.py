from django.urls import path
from . import views

urlpatterns = [
    path("otp/send/",    views.send_otp,    name="customer-otp-send"),
    path("otp/verify/",  views.verify_otp,  name="customer-otp-verify"),
    path("google/",      views.google_auth, name="customer-google-auth"),
]
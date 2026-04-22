from django.urls import path
from . import views

urlpatterns = [
    # Called by frontend after Razorpay modal success
    path("verify/",  views.verify_payment,  name="payment-verify"),

    # Called by Razorpay server-to-server (configure in Razorpay Dashboard)
    path("webhook/", views.razorpay_webhook, name="razorpay-webhook"),
]
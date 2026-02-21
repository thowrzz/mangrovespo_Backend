from django.db import models
from django.utils import timezone
from datetime import timedelta
from core.models import TimeStampedModel
from apps.activities.models import Activity, TimeSlot


class Booking(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    reference = models.CharField(max_length=20, unique=True, db_index=True)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=15)
    customer_email = models.EmailField(db_index=True)
    special_requests = models.TextField(blank=True)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    is_manual = models.BooleanField(default=False)  # walk-in / phone bookings

    def __str__(self):
        return f"{self.reference} — {self.customer_name}"

    class Meta:
        ordering = ['-created_at']


class BookingItem(TimeStampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT)
    visit_date = models.DateField()
    num_persons = models.PositiveIntegerField()
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    slot_hold_expires = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.slot_hold_expires:
            from django.conf import settings
            hold_mins = getattr(settings, 'SLOT_HOLD_MINUTES', 15)
            self.slot_hold_expires = timezone.now() + timedelta(minutes=hold_mins)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking.reference} — {self.activity.name} on {self.visit_date}"

    class Meta:
        ordering = ['visit_date', 'slot__time']

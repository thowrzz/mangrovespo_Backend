from django.db import models
from django.utils import timezone
from datetime import timedelta
from core.models import TimeStampedModel
from apps.activities.models import Activity, TimeSlot


# class Booking(TimeStampedModel):
#     STATUS_CHOICES = [
#         ('pending',   'Pending'),
#         ('confirmed', 'Confirmed'),
#         ('cancelled', 'Cancelled'),
#         ('completed', 'Completed'),
#         ('expired',   'Expired'),
#     ]

#     PAYMENT_MODE_CHOICES = [
#         # ('full', 'Full Payment'),
#         ('half', 'Half Now, Half at Arrival'),
#     ]

#     reference       = models.CharField(max_length=20, unique=True, db_index=True)
#     customer_name   = models.CharField(max_length=200)
#     customer_phone  = models.CharField(max_length=15)
#     customer_email  = models.EmailField(db_index=True)
#     special_requests = models.TextField(blank=True)

#     grand_total     = models.DecimalField(max_digits=10, decimal_places=2)

#     # Payment split tracking
#     payment_mode    = models.CharField(
#         max_length=10, choices=PAYMENT_MODE_CHOICES, default='half'
#     )
#     amount_paid     = models.DecimalField(
#         max_digits=10, decimal_places=2, default=0,
#         help_text="Amount collected online via Razorpay (50% at booking)"
#     )
#     balance_due     = models.DecimalField(
#         max_digits=10, decimal_places=2, default=0,
#         help_text="Amount to be collected at arrival (remaining 50%)"
#     )

#     status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     razorpay_order_id   = models.CharField(max_length=100, blank=True, db_index=True)
#     razorpay_payment_id = models.CharField(max_length=100, blank=True)
#     razorpay_signature  = models.CharField(max_length=200, blank=True)
#     is_manual           = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.reference} — {self.customer_name}"

#     class Meta:
#         ordering = ['-created_at']

from django.db import models
from django.utils import timezone
 
 
class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("expired",   "Expired"),
    ]
 
    PAYMENT_MODE_CHOICES = [
        ("half", "50% now, 50% at arrival"),
        ("full", "Full payment"),
    ]
 
    reference         = models.CharField(max_length=20, unique=True, db_index=True)
    customer_name     = models.CharField(max_length=200)
    customer_phone    = models.CharField(max_length=15)
    customer_email    = models.EmailField(db_index=True)
    special_requests  = models.TextField(blank=True)
 
    grand_total       = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid       = models.DecimalField(max_digits=10, decimal_places=2)
    balance_due       = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode      = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default="half")
 
    # ── Razorpay fields ───────────────────────────────────────────
    razorpay_order_id   = models.CharField(max_length=100, blank=True, null=True, db_index=True)
 
    # NEW: store payment_id once verified; unique=True prevents replay attacks
    razorpay_payment_id = models.CharField(
        max_length=100, blank=True, null=True,
        unique=True,
        db_index=True,
    )
 
    # NEW: timestamp when payment was verified
    payment_verified_at = models.DateTimeField(null=True, blank=True)
 
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"{self.reference} — {self.customer_name} ({self.status})"

class BookingItem(TimeStampedModel):
    booking     = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    activity    = models.ForeignKey(Activity, on_delete=models.PROTECT)

    # slot remains optional (kept for backward compat / fixed-slot activities)
    slot        = models.ForeignKey(
        TimeSlot, on_delete=models.PROTECT, null=True, blank=True,
        help_text="Only set for activities using fixed time slots"
    )

    # Free arrival time — visitor picks any time within operating hours
    arrival_time = models.TimeField(
        null=True, blank=True,
        help_text="Visitor-selected arrival time (used when slot is null)"
    )

    visit_date  = models.DateField()

    # Split persons into adults + children
    num_adults   = models.PositiveIntegerField(default=1)
    num_children = models.PositiveIntegerField(default=0)

    price_snapshot    = models.DecimalField(max_digits=10, decimal_places=2)
    slot_hold_expires = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.slot_hold_expires:
            from django.conf import settings
            hold_mins = getattr(settings, 'SLOT_HOLD_MINUTES', 15)
            self.slot_hold_expires = timezone.now() + timedelta(minutes=hold_mins)
        super().save(*args, **kwargs)

    @property
    def num_persons(self):
        """Backward-compat: total headcount used in reports/emails."""
        return self.num_adults + self.num_children

    def __str__(self):
        return f"{self.booking.reference} — {self.activity.name} on {self.visit_date}"

    class Meta:
        ordering = ['visit_date']
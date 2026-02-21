from django.db import models
from core.models import TimeStampedModel


class Activity(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('water', 'Water'),
        ('thrill', 'Thrill'),
        ('land', 'Land'),
        ('cultural', 'Cultural'),
        ('group_fun', 'Group Fun'),
        ('skill', 'Skill'),
    ]
    PRICING_TYPE_CHOICES = [
        ('per_person', 'Per Person'),
        ('per_group', 'Per Group'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    image_url = models.URLField(blank=True)          # Cloudinary CDN URL
    duration = models.CharField(max_length=50)       # "2 hrs", "30 min"
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='per_person')
    extra_person_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_persons = models.PositiveIntegerField(default=1)
    max_persons = models.PositiveIntegerField(default=10)
    rules_text = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    requires_prebooking = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class TimeSlot(TimeStampedModel):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='slots')
    label = models.CharField(max_length=100)         # "6:30 AM Sunrise"
    time = models.TimeField()
    capacity = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"{self.activity.name} — {self.label}"

    def available_capacity(self, date):
        """Returns remaining slots for a given date."""
        from apps.bookings.models import BookingItem
        from django.utils import timezone
        booked = BookingItem.objects.filter(
            slot=self,
            visit_date=date,
            booking__status__in=['pending', 'confirmed'],
            slot_hold_expires__gt=timezone.now()
        ).count()
        confirmed = BookingItem.objects.filter(
            slot=self,
            visit_date=date,
            booking__status='confirmed'
        ).count()
        total = max(booked, confirmed)
        return max(0, self.capacity - total)

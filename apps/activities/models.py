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
    image_url = models.URLField(blank=True)
    duration = models.CharField(max_length=50)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    # ── Child price (if None, use adult price logic)
    child_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Price per child. Leave blank if same as adult."
    )

    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='per_person')
    extra_person_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_persons = models.PositiveIntegerField(default=1)
    max_persons = models.PositiveIntegerField(default=10)

    # ── Operating hours for arrival time picker ───────────────────
    opening_time = models.TimeField(
        default='06:30',
        help_text="Earliest arrival time visitors can select when booking."
    )
    closing_time = models.TimeField(
        default='17:00',
        help_text="Latest arrival time visitors can select when booking."
    )

    # ── Kept for backward compat (use ActivityRule instead) ───────
    rules_text = models.TextField(blank=True)

    is_visible = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    requires_prebooking = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


# ── Structured rules per activity ────────────────────────────────
class ActivityRule(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='rules')
    rule = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.activity.name}: {self.rule[:60]}"


class TimeSlot(TimeStampedModel):
    """
    TimeSlot is OPTIONAL — only used by activities that need
    fixed-capacity slots. Activities using free arrival time selection
    do not need slots at all.
    """
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='slots')
    label = models.CharField(max_length=100)
    time = models.TimeField()
    capacity = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return f"{self.activity.name} — {self.label}"

    def available_capacity(self, date):
        from apps.bookings.models import BookingItem
        from django.utils import timezone
        from django.db.models import Q

        booked = BookingItem.objects.filter(
            slot=self,
            visit_date=date,
        ).filter(
            Q(booking__status='confirmed') |
            Q(booking__status='pending', slot_hold_expires__gt=timezone.now())
        ).aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F('num_adults') + models.F('num_children'),
                    output_field=models.IntegerField()
                )
            )
        )['total'] or 0

        return max(0, self.capacity - booked)
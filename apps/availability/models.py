from django.db import models
from core.models import TimeStampedModel
from apps.activities.models import Activity


class BlockedDate(TimeStampedModel):
    REASON_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('weather', 'Weather'),
        ('holiday', 'Holiday'),
        ('other', 'Other'),
    ]
    date = models.DateField(db_index=True)
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE,
        null=True, blank=True,
        help_text='Leave blank to block ALL activities on this date'
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        if self.activity:
            return f"{self.date} — {self.activity.name} blocked ({self.reason})"
        return f"{self.date} — All activities blocked ({self.reason})"

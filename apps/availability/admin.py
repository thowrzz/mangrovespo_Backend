from django.contrib import admin
from .models import BlockedDate


@admin.register(BlockedDate)
class BlockedDateAdmin(admin.ModelAdmin):
    list_display = ['date', 'activity', 'reason', 'note']
    list_filter = ['reason']

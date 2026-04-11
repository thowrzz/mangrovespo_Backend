# apps/activities/admin.py
from django.contrib import admin
from .models import Activity, TimeSlot, ActivityRule   # ← add ActivityRule


class TimeSlotInline(admin.TabularInline):
    model  = TimeSlot
    extra  = 1


# ── NEW: Rules inline ─────────────────────────────────────────────
class ActivityRuleInline(admin.TabularInline):
    model   = ActivityRule
    extra   = 1
    fields  = ['rule', 'order']
    ordering = ['order']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display   = ['name', 'category', 'base_price', 'pricing_type', 'is_visible', 'is_popular', 'is_deleted']
    list_filter    = ['category', 'is_visible', 'is_popular', 'pricing_type']
    search_fields  = ['name', 'tagline']
    list_editable  = ['is_visible', 'is_popular']
    inlines        = [TimeSlotInline, ActivityRuleInline]   # ← add ActivityRuleInline


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['activity', 'label', 'time', 'capacity', 'is_active']
    list_filter  = ['activity', 'is_active']
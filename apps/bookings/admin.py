from django.contrib import admin
from .models import Booking, BookingItem


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0
    readonly_fields = ['activity', 'slot', 'visit_date', 'num_persons', 'price_snapshot']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['reference', 'customer_name', 'customer_phone', 'grand_total', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'customer_name', 'customer_phone', 'customer_email']
    readonly_fields = ['reference', 'razorpay_order_id', 'razorpay_payment_id']
    inlines = [BookingItemInline]

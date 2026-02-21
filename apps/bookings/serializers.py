from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from .models import Booking, BookingItem
from apps.activities.models import Activity, TimeSlot
from core.utils import generate_booking_reference


class BookingItemInputSerializer(serializers.Serializer):
    """Input for each activity in the basket."""
    activity_id = serializers.IntegerField()
    slot_id = serializers.IntegerField()
    visit_date = serializers.DateField()
    num_persons = serializers.IntegerField(min_value=1)


class BookingInitiateSerializer(serializers.Serializer):
    """Input to initiate a booking and create a Razorpay order."""
    customer_name = serializers.CharField(max_length=200)
    customer_phone = serializers.CharField(max_length=15)
    customer_email = serializers.EmailField()
    special_requests = serializers.CharField(required=False, allow_blank=True)
    items = BookingItemInputSerializer(many=True, min_length=1)

    def validate_items(self, items):
        errors = []
        for i, item in enumerate(items):
            try:
                activity = Activity.objects.get(pk=item['activity_id'], is_visible=True, is_deleted=False)
                slot = TimeSlot.objects.get(pk=item['slot_id'], activity=activity, is_active=True)
                available = slot.available_capacity(item['visit_date'])
                if available == 0:
                    errors.append(f"Item {i+1}: Slot '{slot.label}' is full on {item['visit_date']}")
                if item['num_persons'] < activity.min_persons:
                    errors.append(f"Item {i+1}: Minimum {activity.min_persons} persons required")
                if item['num_persons'] > activity.max_persons:
                    errors.append(f"Item {i+1}: Maximum {activity.max_persons} persons allowed")
            except Activity.DoesNotExist:
                errors.append(f"Item {i+1}: Activity not found")
            except TimeSlot.DoesNotExist:
                errors.append(f"Item {i+1}: Slot not found")
        if errors:
            raise serializers.ValidationError(errors)
        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        grand_total = 0
        item_objects = []

        for item_data in items_data:
            activity = Activity.objects.get(pk=item_data['activity_id'])
            slot = TimeSlot.objects.select_for_update().get(pk=item_data['slot_id'])

            # Re-check availability with row lock
            available = slot.available_capacity(item_data['visit_date'])
            if available == 0:
                raise serializers.ValidationError(f"Slot '{slot.label}' just became full. Please choose another.")

            # Calculate price
            if activity.pricing_type == 'per_person':
                price = activity.base_price * item_data['num_persons']
            elif activity.pricing_type == 'per_group':
                extra = 0
                if activity.extra_person_charge and item_data['num_persons'] > activity.min_persons:
                    extra = activity.extra_person_charge * (item_data['num_persons'] - activity.min_persons)
                price = activity.base_price + extra
            else:
                price = activity.base_price

            grand_total += price
            item_objects.append({
                'activity': activity,
                'slot': slot,
                'visit_date': item_data['visit_date'],
                'num_persons': item_data['num_persons'],
                'price_snapshot': price,
            })

        # Create Razorpay order
        import razorpay
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        rz_order = client.order.create({
            'amount': int(grand_total * 100),  # paise
            'currency': 'INR',
            'receipt': generate_booking_reference(),
        })

        # Create booking
        booking = Booking.objects.create(
            reference=generate_booking_reference(),
            grand_total=grand_total,
            razorpay_order_id=rz_order['id'],
            **validated_data
        )

        hold_expires = timezone.now() + timedelta(minutes=settings.SLOT_HOLD_MINUTES)
        for item in item_objects:
            BookingItem.objects.create(
                booking=booking,
                slot_hold_expires=hold_expires,
                **item
            )

        return booking, rz_order['id']


class BookingItemSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    activity_image = serializers.CharField(source='activity.image_url', read_only=True)
    slot_label = serializers.CharField(source='slot.label', read_only=True)

    class Meta:
        model = BookingItem
        fields = [
            'id', 'activity_name', 'activity_image', 'slot_label',
            'visit_date', 'num_persons', 'price_snapshot'
        ]


class BookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'reference', 'customer_name', 'customer_phone',
            'customer_email', 'special_requests', 'grand_total',
            'status', 'razorpay_order_id', 'items', 'created_at'
        ]

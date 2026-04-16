# from rest_framework import serializers
# from django.db import transaction
# from django.utils import timezone
# from datetime import timedelta
# from django.conf import settings
# import uuid

# from .models import Booking, BookingItem
# from apps.activities.models import Activity, TimeSlot
# from core.utils import generate_booking_reference


# class BookingItemInputSerializer(serializers.Serializer):
#     """Input for each activity line in the basket."""
#     activity_id  = serializers.IntegerField()

#     # slot_id is fully optional — only needed for fixed-slot activities
#     slot_id      = serializers.IntegerField(required=False, allow_null=True)

#     # Free arrival time (HH:MM) — required when slot_id is not provided
#     arrival_time = serializers.TimeField(
#         required=False, allow_null=True,
#         help_text="Visitor-chosen arrival time, e.g. '10:30'. Required when slot_id is not given."
#     )

#     visit_date   = serializers.DateField()

#     # Adults & children counted separately
#     num_adults   = serializers.IntegerField(min_value=1)
#     num_children = serializers.IntegerField(min_value=0, default=0)


# class BookingInitiateSerializer(serializers.Serializer):
#     """Input to initiate a booking and create a Razorpay order for 50% of the total."""
#     customer_name    = serializers.CharField(max_length=200)
#     customer_phone   = serializers.CharField(max_length=15)
#     customer_email   = serializers.EmailField()
#     special_requests = serializers.CharField(required=False, allow_blank=True)
#     items            = BookingItemInputSerializer(many=True, min_length=1)

#     def validate_items(self, items):
#         errors = []
#         for i, item in enumerate(items):
#             try:
#                 activity = Activity.objects.get(
#                     pk=item['activity_id'], is_visible=True, is_deleted=False
#                 )

#                 num_adults   = item.get('num_adults', 1)
#                 num_children = item.get('num_children', 0)
#                 total_persons = num_adults + num_children

#                 if total_persons < activity.min_persons:
#                     errors.append(f"Item {i+1}: Minimum {activity.min_persons} person(s) required")
#                 if total_persons > activity.max_persons:
#                     errors.append(f"Item {i+1}: Maximum {activity.max_persons} persons allowed")

#                 # Require either a slot_id OR an arrival_time
#                 slot_id      = item.get('slot_id')
#                 arrival_time = item.get('arrival_time')

#                 if slot_id:
#                     slot = TimeSlot.objects.get(pk=slot_id, activity=activity, is_active=True)
#                     if slot.available_capacity(item['visit_date']) == 0:
#                         errors.append(f"Item {i+1}: Slot '{slot.label}' is full on {item['visit_date']}")
#                 elif not arrival_time:
#                     errors.append(
#                         f"Item {i+1}: Either a slot_id or an arrival_time must be provided"
#                     )

#             except Activity.DoesNotExist:
#                 errors.append(f"Item {i+1}: Activity not found")
#             except TimeSlot.DoesNotExist:
#                 errors.append(f"Item {i+1}: Slot not found")

#         if errors:
#             raise serializers.ValidationError(errors)
#         return items

#     @transaction.atomic
#     def create(self, validated_data):
#         items_data    = validated_data.pop('items')
#         grand_total   = 0
#         item_objects  = []

#         for item_data in items_data:
#             activity     = Activity.objects.get(pk=item_data['activity_id'])
#             num_adults   = item_data.get('num_adults', 1)
#             num_children = item_data.get('num_children', 0)
#             total_persons = num_adults + num_children

#             # Resolve slot (optional)
#             slot = None
#             if item_data.get('slot_id'):
#                 slot = TimeSlot.objects.select_for_update().get(pk=item_data['slot_id'])
#                 if slot.available_capacity(item_data['visit_date']) == 0:
#                     raise serializers.ValidationError(
#                         f"Slot '{slot.label}' just became full. Please choose another."
#                     )

#             # Price calculation
#             adult_price = activity.base_price
#             child_price = (
#                 activity.child_price
#                 if activity.child_price is not None
#                 else adult_price
#             )

#             if activity.pricing_type == 'per_person':
#                 price = (adult_price * num_adults) + (child_price * num_children)

#             elif activity.pricing_type == 'per_group':
#                 price = activity.base_price
#                 if activity.extra_person_charge and total_persons > activity.min_persons:
#                     extra_adults = max(0, num_adults - activity.min_persons)
#                     price += activity.extra_person_charge * extra_adults
#                     price += child_price * num_children
#             else:
#                 price = activity.base_price

#             grand_total += price
#             item_objects.append({
#                 'activity':    activity,
#                 'slot':        slot,
#                 'arrival_time': item_data.get('arrival_time'),
#                 'visit_date':  item_data['visit_date'],
#                 'num_adults':  num_adults,
#                 'num_children': num_children,
#                 'price_snapshot': price,
#             })

#         # ── 50 % charged now, 50 % at arrival ────────────────────
#         import math
#         amount_to_charge = math.ceil(grand_total / 2)   # round up to avoid underpayment
#         balance_due      = grand_total - amount_to_charge

#         # ── Create Razorpay order for the 50 % amount ─────────────
#         import razorpay
#         client = razorpay.Client(
#             auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#         )
#         rz_order = client.order.create({
#             'amount':   int(amount_to_charge * 100),  # paise — 50% only
#             'currency': 'INR',
#             'receipt': f"rcpt_{uuid.uuid4().hex[:12]}",

#             # 'receipt':  generate_booking_reference(),
#         })

#         # ── Create Booking record ─────────────────────────────────
#         booking = Booking.objects.create(
#             reference    = generate_booking_reference(),
#             grand_total  = grand_total,
#             payment_mode = 'half',
#             amount_paid  = amount_to_charge,
#             balance_due  = balance_due,
#             razorpay_order_id = rz_order['id'],
#             **validated_data
#         )

#         hold_expires = timezone.now() + timedelta(minutes=getattr(settings, 'SLOT_HOLD_MINUTES', 15))
#         for item in item_objects:
#             BookingItem.objects.create(
#                 booking=booking,
#                 slot_hold_expires=hold_expires,
#                 **item
#             )

#         return booking, rz_order['id']


# # ── Response serializers ──────────────────────────────────────────

# class BookingItemSerializer(serializers.ModelSerializer):
#     activity_name  = serializers.CharField(source='activity.name',      read_only=True)
#     activity_image = serializers.CharField(source='activity.image_url', read_only=True)
#     slot_label     = serializers.SerializerMethodField()

#     class Meta:
#         model  = BookingItem
#         fields = [
#             'id', 'activity_name', 'activity_image', 'slot_label',
#             'arrival_time', 'visit_date',
#             'num_adults', 'num_children', 'price_snapshot',
#         ]

#     def get_slot_label(self, obj):
#         if obj.slot:
#             return obj.slot.label
#         if obj.arrival_time:
#             return obj.arrival_time.strftime('%I:%M %p')
#         return None


# class BookingSerializer(serializers.ModelSerializer):
#     items = BookingItemSerializer(many=True, read_only=True)

#     class Meta:
#         model  = Booking
#         fields = [
#             'id', 'reference', 'customer_name', 'customer_phone',
#             'customer_email', 'special_requests',
#             'grand_total', 'amount_paid', 'balance_due', 'payment_mode',
#             'status', 'razorpay_order_id', 'items', 'created_at',
#         ]
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import uuid
import math
import razorpay

from .models import Booking, BookingItem
from apps.activities.models import Activity, TimeSlot
from core.utils import generate_booking_reference


# ── Shared price calculator ───────────────────────────────────────

def calculate_item_price(activity, num_adults: int, num_children: int) -> float:
    """
    Central price formula. Called from both validate and create so
    both paths always use the same logic.

    per_person:
        adults  → base_price each
        children → child_price each (falls back to base_price)
        extra charge → applied per person (adult or child) beyond min_persons

    per_group:
        base_price covers the whole group up to min_persons
        extra charge → applied per person (adult or child) beyond min_persons
        children beyond min_persons → extra_person_charge (not child_price)
        children within min_persons → already covered by base_price
    """
    base        = float(activity.base_price)
    extra       = float(activity.extra_person_charge or 0)
    min_persons = activity.min_persons
    child_rate  = float(activity.child_price) if activity.child_price else base

    total_persons  = num_adults + num_children
    extra_persons  = max(0, total_persons - min_persons)

    if activity.pricing_type == 'per_person':
        price  = base * num_adults
        price += child_rate * num_children
        price += extra * extra_persons          # extra charge for each person beyond min

    elif activity.pricing_type == 'per_group':
        price  = base                           # covers whole group up to min_persons
        price += extra * extra_persons          # each person beyond min pays extra

    else:
        price = base

    return price


class BookingItemInputSerializer(serializers.Serializer):
    """Input for each activity line in the basket."""
    activity_id  = serializers.IntegerField()
    slot_id      = serializers.IntegerField(required=False, allow_null=True)
    arrival_time = serializers.TimeField(
        required=False, allow_null=True,
        help_text="Visitor-chosen arrival time e.g. '10:30'. Required when slot_id is not given."
    )
    visit_date   = serializers.DateField()
    num_adults   = serializers.IntegerField(min_value=1)
    num_children = serializers.IntegerField(min_value=0, default=0)


class BookingInitiateSerializer(serializers.Serializer):
    customer_name    = serializers.CharField(max_length=200)
    customer_phone   = serializers.CharField(max_length=15)
    customer_email   = serializers.EmailField()
    special_requests = serializers.CharField(required=False, allow_blank=True)
    items            = BookingItemInputSerializer(many=True, min_length=1)

    def validate_items(self, items):
        errors = []
        for i, item in enumerate(items):
            try:
                activity = Activity.objects.get(
                    pk=item['activity_id'], is_visible=True, is_deleted=False
                )
                num_adults    = item.get('num_adults', 1)
                num_children  = item.get('num_children', 0)
                total_persons = num_adults + num_children

                if total_persons < activity.min_persons:
                    errors.append(f"Item {i+1}: Minimum {activity.min_persons} person(s) required")
                if total_persons > activity.max_persons:
                    errors.append(f"Item {i+1}: Maximum {activity.max_persons} persons allowed")

                slot_id      = item.get('slot_id')
                arrival_time = item.get('arrival_time')

                if slot_id:
                    slot = TimeSlot.objects.get(pk=slot_id, activity=activity, is_active=True)
                    if slot.available_capacity(item['visit_date']) == 0:
                        errors.append(f"Item {i+1}: Slot '{slot.label}' is full on {item['visit_date']}")
                elif not arrival_time:
                    errors.append(f"Item {i+1}: Either a slot_id or an arrival_time must be provided")

            except Activity.DoesNotExist:
                errors.append(f"Item {i+1}: Activity not found")
            except TimeSlot.DoesNotExist:
                errors.append(f"Item {i+1}: Slot not found")

        if errors:
            raise serializers.ValidationError(errors)
        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data   = validated_data.pop('items')
        grand_total  = 0
        item_objects = []

        for item_data in items_data:
            activity     = Activity.objects.get(pk=item_data['activity_id'])
            num_adults   = item_data.get('num_adults', 1)
            num_children = item_data.get('num_children', 0)

            # Resolve slot with row-lock to prevent race condition
            slot = None
            if item_data.get('slot_id'):
                slot = TimeSlot.objects.select_for_update().get(pk=item_data['slot_id'])
                if slot.available_capacity(item_data['visit_date']) == 0:
                    raise serializers.ValidationError(
                        f"Slot '{slot.label}' just became full. Please choose another."
                    )

            # ✅ Use shared calculator — same formula for validate + create
            price = calculate_item_price(activity, num_adults, num_children)

            grand_total += price
            item_objects.append({
                'activity':       activity,
                'slot':           slot,
                'arrival_time':   item_data.get('arrival_time'),
                'visit_date':     item_data['visit_date'],
                'num_adults':     num_adults,
                'num_children':   num_children,
                'price_snapshot': price,
            })

        # 50% charged now, 50% at arrival
        amount_to_charge = math.ceil(grand_total / 2)
        balance_due      = grand_total - amount_to_charge

        # Razorpay order
        client   = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rz_order = client.order.create({
            'amount':   int(amount_to_charge * 100),  # paise
            'currency': 'INR',
            'receipt':  f"rcpt_{uuid.uuid4().hex[:12]}",
        })

        booking = Booking.objects.create(
            reference         = generate_booking_reference(),
            grand_total       = grand_total,
            payment_mode      = 'half',
            amount_paid       = amount_to_charge,
            balance_due       = balance_due,
            razorpay_order_id = rz_order['id'],
            **validated_data
        )

        hold_expires = timezone.now() + timedelta(
            minutes=getattr(settings, 'SLOT_HOLD_MINUTES', 15)
        )
        for item in item_objects:
            BookingItem.objects.create(
                booking=booking,
                slot_hold_expires=hold_expires,
                **item
            )

        return booking, rz_order['id']


# ── Response serializers ──────────────────────────────────────────

class BookingItemSerializer(serializers.ModelSerializer):
    activity_name  = serializers.CharField(source='activity.name',      read_only=True)
    activity_image = serializers.CharField(source='activity.image_url', read_only=True)
    slot_label     = serializers.SerializerMethodField()

    class Meta:
        model  = BookingItem
        fields = [
            'id', 'activity_name', 'activity_image', 'slot_label',
            'arrival_time', 'visit_date',
            'num_adults', 'num_children', 'price_snapshot',
        ]

    def get_slot_label(self, obj):
        if obj.slot:
            return obj.slot.label
        if obj.arrival_time:
            return obj.arrival_time.strftime('%I:%M %p')
        return None


class BookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Booking
        fields = [
            'id', 'reference', 'customer_name', 'customer_phone',
            'customer_email', 'special_requests',
            'grand_total', 'amount_paid', 'balance_due', 'payment_mode',
            'status', 'razorpay_order_id', 'items', 'created_at',
        ]
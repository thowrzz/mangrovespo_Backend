from rest_framework import serializers
from .models import Activity, TimeSlot


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['id', 'label', 'time', 'capacity', 'is_active']


class ActivityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for homepage activity cards."""
    class Meta:
        model = Activity
        fields = [
            'id', 'name', 'tagline', 'category', 'image_url',
            'duration', 'base_price', 'pricing_type',
            'min_persons', 'max_persons',
            'is_popular', 'requires_prebooking', 'display_order',
        ]


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Full serializer for activity detail panel including time slots."""
    slots = TimeSlotSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'name', 'tagline', 'description', 'category',
            'image_url', 'duration', 'base_price', 'pricing_type',
            'extra_person_charge', 'min_persons', 'max_persons',
            'rules_text', 'is_popular', 'requires_prebooking', 'slots',
        ]


class ActivityAdminSerializer(serializers.ModelSerializer):
    """Full serializer for admin CRUD — all fields exposed."""
    slots = TimeSlotSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = '__all__'

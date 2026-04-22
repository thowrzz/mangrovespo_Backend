from rest_framework import serializers
from .models import Activity, TimeSlot, ActivityRule


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TimeSlot
        fields = ['id', 'label', 'time', 'capacity', 'is_active']


class ActivityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ActivityRule
        fields = ['id', 'rule', 'order']


class ActivityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for homepage activity cards."""
    children_allowed = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Activity
        fields = [
            'id', 'name', 'tagline', 'category', 'image_url',
            'duration', 'base_price', 'child_price',
            'extra_person_charge',
            'pricing_type', 'min_persons', 'max_persons',
            'opening_time', 'closing_time',
            'is_popular', 'requires_prebooking', 'display_order',
            'min_age',
            'children_allowed',
        ]


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Full serializer for activity detail panel."""
    slots            = TimeSlotSerializer(many=True, read_only=True)
    rules            = ActivityRuleSerializer(many=True, read_only=True)
    children_allowed = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Activity
        fields = [
            'id', 'name', 'tagline', 'description', 'category',
            'image_url', 'duration',
            'base_price', 'child_price', 'extra_person_charge',
            'pricing_type', 'min_persons', 'max_persons',
            'opening_time', 'closing_time',
            'is_popular', 'requires_prebooking',
            'slots', 'rules',
            'min_age',
            'children_allowed',
        ]


class ActivityAdminSerializer(serializers.ModelSerializer):
    slots            = TimeSlotSerializer(many=True, read_only=True)
    rules            = ActivityRuleSerializer(many=True, read_only=True)
    children_allowed = serializers.BooleanField(read_only=True)

    class Meta:
        model            = Activity
        fields           = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_deleted']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['description', 'category', 'duration']:
            self.fields[field].required    = False
            self.fields[field].allow_blank = True
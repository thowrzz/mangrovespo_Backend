from rest_framework import serializers
from .models import BlockedDate


class BlockedDateSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)

    class Meta:
        model = BlockedDate
        fields = ['id', 'date', 'activity', 'activity_name', 'reason', 'note']

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
import cloudinary.uploader

from .models import Activity, TimeSlot
from .serializers import (
    ActivityListSerializer, ActivityDetailSerializer, ActivityAdminSerializer,
    TimeSlotSerializer
)
from apps.availability.models import BlockedDate


# ─── PUBLIC VIEWS ─────────────────────────────────────────────────

class ActivityListView(generics.ListAPIView):
    serializer_class = ActivityListSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return Activity.objects.filter(is_visible=True, is_deleted=False)


class ActivityDetailView(generics.RetrieveAPIView):
    serializer_class = ActivityDetailSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return Activity.objects.filter(is_visible=True, is_deleted=False)


@api_view(['GET'])
@permission_classes([AllowAny])
def activity_availability(request, pk):
    activity = get_object_or_404(Activity, pk=pk, is_visible=True, is_deleted=False)
    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'date parameter required'}, status=400)
    try:
        from datetime import date
        visit_date = date.fromisoformat(date_str)
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    is_blocked = BlockedDate.objects.filter(
        date=visit_date
    ).filter(
        Q(activity__isnull=True) | Q(activity=activity)
    ).exists()

    if is_blocked:
        return Response({'date': date_str, 'blocked': True, 'slots': []})

    slots = activity.slots.filter(is_active=True)
    slot_data = []
    for slot in slots:
        available = slot.available_capacity(visit_date)
        slot_data.append({
            'id': slot.id,
            'label': slot.label,
            'time': slot.time.strftime('%H:%M'),
            'capacity': slot.capacity,
            'available': available,
            'is_full': available == 0,
        })
    return Response({'date': date_str, 'blocked': False, 'slots': slot_data})


# ─── ADMIN VIEWS ──────────────────────────────────────────────────

class AdminActivityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityAdminSerializer
    queryset = Activity.objects.filter(is_deleted=False)


class AdminActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityAdminSerializer
    queryset = Activity.objects.filter(is_deleted=False)
    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_visible = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_activity_image(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    image_file = request.FILES.get('image')
    if not image_file:
        return Response({'error': 'No image provided'}, status=400)
    result = cloudinary.uploader.upload(
        image_file,
        folder='mangrovespot/activities',
        public_id=f'activity_{pk}',
        overwrite=True,
        resource_type='image',
    )
    activity.image_url = result['secure_url']
    activity.save()
    return Response({'image_url': activity.image_url})


# ─── SLOT ADMIN VIEWS ─────────────────────────────────────────────

class AdminSlotListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer
    def get_queryset(self):
        return TimeSlot.objects.filter(activity_id=self.kwargs['activity_pk'])
    def perform_create(self, serializer):
        activity = get_object_or_404(Activity, pk=self.kwargs['activity_pk'])
        serializer.save(activity=activity)


class AdminSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer
    queryset = TimeSlot.objects.all()

    def perform_destroy(self, instance):
        from django.db.models import ProtectedError
        try:
            instance.delete()
        except ProtectedError:
            # Slot has bookings — soft delete by deactivating
            instance.is_active = False
            instance.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from django.db.models import ProtectedError
        try:
            instance.delete()
            return Response(status=204)
        except ProtectedError:
            instance.is_active = False
            instance.save()
            return Response(
                {"detail": "Slot has existing bookings and was deactivated instead of deleted."},
                status=200
            )

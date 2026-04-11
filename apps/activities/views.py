from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
import cloudinary.uploader

from .models import Activity, TimeSlot, ActivityRule
from .serializers import (
    ActivityListSerializer, ActivityDetailSerializer, ActivityAdminSerializer,
    TimeSlotSerializer, ActivityRuleSerializer,
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
    """
    GET /api/v1/activities/<pk>/availability/?date=YYYY-MM-DD

    - If activity has no active slots → returns blocked status only
      (visitor will select a free arrival time on frontend)
    - If activity has slots → returns slot capacity as before
    """
    activity = get_object_or_404(Activity, pk=pk, is_visible=True, is_deleted=False)
    date_str = request.query_params.get('date')

    if not date_str:
        return Response({'error': 'date parameter required'}, status=400)

    try:
        from datetime import date
        visit_date = date.fromisoformat(date_str)
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    # Check if date is globally or activity-specifically blocked
    is_blocked = BlockedDate.objects.filter(
        date=visit_date
    ).filter(
        Q(activity__isnull=True) | Q(activity=activity)
    ).exists()

    if is_blocked:
        return Response({'date': date_str, 'blocked': True, 'slots': [], 'has_slots': False})

    slots = activity.slots.filter(is_active=True)

    # ── No fixed slots → visitor picks arrival time freely ────────
    if not slots.exists():
        return Response({
            'date': date_str,
            'blocked': False,
            'has_slots': False,     # frontend shows time picker instead
            'slots': [],
        })

    # ── Fixed slots → return capacity info ────────────────────────
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

    return Response({
        'date': date_str,
        'blocked': False,
        'has_slots': True,          # frontend shows slot selector
        'slots': slot_data,
    })


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


# ─── RULES ADMIN VIEWS ────────────────────────────────────────────


class AdminRuleListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/admin/activities/<activity_pk>/rules/
    POST /api/v1/admin/activities/<activity_pk>/rules/
    Admin adds/lists individual rules for an activity.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityRuleSerializer

    def get_queryset(self):
        return ActivityRule.objects.filter(activity_id=self.kwargs['activity_pk'])

    def perform_create(self, serializer):
        activity = get_object_or_404(Activity, pk=self.kwargs['activity_pk'])
        serializer.save(activity=activity)


class AdminRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/admin/activities/<activity_pk>/rules/<pk>/
    PATCH  /api/v1/admin/activities/<activity_pk>/rules/<pk>/
    DELETE /api/v1/admin/activities/<activity_pk>/rules/<pk>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityRuleSerializer
    queryset = ActivityRule.objects.all()
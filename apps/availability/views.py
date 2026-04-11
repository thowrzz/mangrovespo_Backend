from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import BlockedDate
from .serializers import BlockedDateSerializer


class BlockedDateListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BlockedDateSerializer

    def get_queryset(self):
        qs = BlockedDate.objects.all()
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs


class BlockedDateDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BlockedDateSerializer
    queryset = BlockedDate.objects.all()

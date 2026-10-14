from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from workers.models import WorkerProfile

from .models import TrustScore


class TrustScoreView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        w = get_object_or_404(WorkerProfile, slug=slug, user__is_active=True)
        history = list(TrustScore.objects.filter(worker=w).order_by('-computed_at', '-id')[:30])
        latest = history[0] if history else None
        return Response({
            'worker': w.slug,
            'score': float(latest.value) if latest else None,
            'components': latest.components if latest else {},
            'badges': [b.code for b in w.badges.all()],
            'history': [{'value': float(h.value), 'computed_at': h.computed_at} for h in reversed(history)],
        })

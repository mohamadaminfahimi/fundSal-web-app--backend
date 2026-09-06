from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Endpoint وضعیت سلامت اپلیکیشن؛ برای ابزار Load Balancer و Health Check استفاده می‌شود."""
    return Response(
        {
            "success": True,
            "data": {
                "status": "ok",
                "service": "gold-app-backend",
            },
        }
    )

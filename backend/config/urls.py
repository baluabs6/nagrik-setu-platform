from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView

from core.internal_views import mark_attachment_verified


def healthz(request):
    """Used by the Docker HEALTHCHECK and the AWS/EKS/AKS load balancer probes."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz),
    path("api/v1/issues/", include("apps.issues.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # Internal-only: called by the upload-validation Lambda, not by clients.
    # Keep this off the public ALB listener rules where possible (see
    # infra/terraform/aws/upload-validation.tf).
    path("api/v1/internal/mark-attachment-verified/", mark_attachment_verified),
]

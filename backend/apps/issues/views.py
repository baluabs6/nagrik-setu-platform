import logging
import uuid

from django.core.cache import cache
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Issue
from .serializers import IssueSerializer
from .permissions import IsStaffForStatusChange

logger = logging.getLogger(__name__)

STATS_CACHE_KEY = "issue_stats_v1"
STATS_CACHE_TTL_SECONDS = 60


def _log_to_dynamodb(issue: Issue):
    """
    Fire-and-forget audit trail in DynamoDB, mirroring every state-changing
    event so ward-level dashboards can query recent activity without
    hitting Postgres. Never allowed to break the request if AWS is
    unreachable in local/dev.
    """
    try:
        import boto3

        table = boto3.resource("dynamodb", region_name=settings.AWS_REGION).Table(
            settings.AWS_DYNAMODB_TABLE
        )
        table.put_item(
            Item={
                "tracking_id": issue.tracking_id,
                "category": issue.category,
                "status": issue.status,
                "votes": issue.votes,
                "updated_at": issue.updated_at.isoformat(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("DynamoDB audit write skipped: %s", exc)


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    permission_classes = [IsStaffForStatusChange]

    def perform_create(self, serializer):
        issue = serializer.save()
        cache.delete(STATS_CACHE_KEY)
        _log_to_dynamodb(issue)

    @action(detail=True, methods=["patch"])
    def upvote(self, request, pk=None):
        issue = self.get_object()
        issue.votes += 1
        issue.save(update_fields=["votes", "updated_at"])
        _log_to_dynamodb(issue)
        return Response(IssueSerializer(issue).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Cached in Redis for STATS_CACHE_TTL_SECONDS to keep the
        dashboard's hero numbers cheap under load."""
        cached = cache.get(STATS_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        qs = Issue.objects.all()
        data = {
            "open": qs.exclude(status=Issue.Status.RESOLVED).count(),
            "resolved": qs.filter(status=Issue.Status.RESOLVED).count(),
            "total": qs.count(),
        }
        cache.set(STATS_CACHE_KEY, data, STATS_CACHE_TTL_SECONDS)
        return Response(data)

    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

    @action(detail=False, methods=["post"], url_path="presign-upload", permission_classes=[AllowAny])
    def presign_upload(self, request):
        """
        Returns a presigned S3 PUT URL so the browser uploads the photo
        directly to S3 (never through Django), plus the `attachment_key`
        to send back with the issue create/patch request.
        """
        content_type = request.data.get("content_type")
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            return Response(
                {"error": "unsupported_type", "message": "Only JPEG, PNG, or WebP photos are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = f"issue-attachments/{uuid.uuid4()}.{content_type.split('/')[-1]}"

        try:
            import boto3

            client = boto3.client("s3", region_name=settings.AWS_REGION)
            upload_url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=300,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Presigned URL generation failed: %s", exc)
            return Response(
                {"error": "upload_unavailable", "message": "Photo uploads are temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"upload_url": upload_url, "attachment_key": key, "max_bytes": self.MAX_UPLOAD_BYTES})

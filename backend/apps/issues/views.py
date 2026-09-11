import logging
import uuid

from django.core.cache import cache
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from core.ai_triage import triage_issue
from .models import Issue
from .serializers import IssueSerializer
from .permissions import IsStaffForStatusChange

logger = logging.getLogger(__name__)

STATS_CACHE_KEY = "issue_stats_v1"
STATS_CACHE_TTL_SECONDS = 60

# One vote per issue per client per day. Cheap, dependency-free abuse
# control against a single IP scripting repeated upvote calls; not a
# substitute for the ScopedRateThrottle below, which limits call *rate*
# regardless of target.
UPVOTE_DEDUPE_TTL_SECONDS = 24 * 60 * 60


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


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


def _run_ai_triage(issue: Issue) -> None:
    """Best-effort AI auto-triage agent (see core/ai_triage.py). Disabled
    unless ENABLE_AI_TRIAGE is set; never blocks or fails the request."""
    try:
        result = triage_issue(
            category_choices=[choice.value for choice in Issue.Category],
            category=issue.category,
            description=issue.description,
        )
        if result is None:
            return
        issue.ai_suggested_category = result.suggested_category
        issue.ai_urgency = result.urgency
        issue.ai_confidence = result.confidence
        issue.save(update_fields=["ai_suggested_category", "ai_urgency", "ai_confidence", "updated_at"])
    except Exception:  # noqa: BLE001
        logger.exception("AI triage post-processing failed for issue %s", issue.id)


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    permission_classes = [IsStaffForStatusChange]

    def perform_create(self, serializer):
        issue = serializer.save()
        cache.delete(STATS_CACHE_KEY)
        _log_to_dynamodb(issue)
        _run_ai_triage(issue)

    @action(detail=True, methods=["patch"], throttle_classes=[ScopedRateThrottle])
    def upvote(self, request, pk=None):
        issue = self.get_object()

        dedupe_key = f"upvote:{issue.id}:{_client_ip(request)}"
        if cache.get(dedupe_key):
            return Response(
                {"error": "already_voted", "message": "You've already upvoted this report recently."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        issue.votes += 1
        issue.save(update_fields=["votes", "updated_at"])
        cache.set(dedupe_key, True, UPVOTE_DEDUPE_TTL_SECONDS)
        _log_to_dynamodb(issue)
        return Response(IssueSerializer(issue).data, status=status.HTTP_200_OK)

    upvote.throttle_scope = "upvote"

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
            # A presigned PUT can't itself enforce a max size, and nothing
            # here verifies the bytes actually match `content_type` — a
            # client can declare "image/jpeg" and upload anything. The real
            # enforcement point is the S3-triggered upload-validation
            # Lambda (backend/lambda/upload_validation/handler.py, wired up
            # in infra/terraform/aws/upload-validation.tf), which sniffs
            # the real file type/size after upload, strips EXIF/GPS from
            # genuine images, and deletes anything that doesn't qualify.
            # `Issue.attachment_verified` only flips to True once that
            # Lambda has approved the object (see models.py, serializers.py).
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

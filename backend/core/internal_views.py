"""
Internal-only endpoints, never meant to be reachable by citizens or staff
through the normal API surface — only by trusted infra (the
upload-validation Lambda). Protected by a shared token (from Vault, see
INTERNAL_SERVICE_TOKEN in settings.py) rather than JWT, since the caller is
a Lambda, not a logged-in user.

Defense in depth beyond the token check: this path should also be blocked
at the network layer (ALB/security-group rule, or an internal-only ingress
path) so it's unreachable from the public internet even if the token were
ever leaked. See infra/terraform/aws/upload-validation.tf for the intended
network placement.
"""
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def mark_attachment_verified(request):
    expected = getattr(settings, "INTERNAL_SERVICE_TOKEN", "") or ""
    provided = request.headers.get("X-Internal-Token", "")

    if not expected or not hmac.compare_digest(expected, provided):
        logger.warning("Rejected internal callback: bad or missing token")
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body or b"{}")
        attachment_key = payload["attachment_key"]
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "bad_request"}, status=400)

    from apps.issues.models import Issue

    updated = Issue.objects.filter(attachment_key=attachment_key).update(attachment_verified=True)
    return JsonResponse({"updated": updated})

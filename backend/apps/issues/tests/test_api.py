import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.issues.models import Issue
from .factories import IssueFactory

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user():
    return User.objects.create_user(username="admin", password="pw", is_staff=True)


@pytest.fixture
def regular_user():
    return User.objects.create_user(username="citizen", password="pw")


def test_anonymous_can_list_issues(api_client):
    IssueFactory.create_batch(3)
    resp = api_client.get("/api/v1/issues/")
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 3


def test_anonymous_can_create_issue(api_client):
    payload = {"category": "water", "locality": "Sector 21", "description": "No water for 4 days"}
    resp = api_client.post("/api/v1/issues/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["tracking_id"].startswith("NS-")
    assert resp.data["status"] == "submitted"


def test_anonymous_can_upvote(api_client):
    issue = IssueFactory(votes=5)
    resp = api_client.patch(f"/api/v1/issues/{issue.id}/upvote/")
    assert resp.status_code == 200
    assert resp.data["votes"] == 6


def test_anonymous_cannot_change_status(api_client):
    # 401, not 403: JWTAuthentication advertises an auth header, so DRF
    # reports "not authenticated" rather than "authenticated but forbidden"
    # for a request with no token at all.
    issue = IssueFactory()
    resp = api_client.patch(f"/api/v1/issues/{issue.id}/", {"status": "resolved"}, format="json")
    assert resp.status_code == 401


def test_regular_user_cannot_change_status(api_client, regular_user):
    issue = IssueFactory()
    api_client.force_authenticate(user=regular_user)
    resp = api_client.patch(f"/api/v1/issues/{issue.id}/", {"status": "resolved"}, format="json")
    assert resp.status_code == 403


def test_staff_can_change_status(api_client, staff_user):
    issue = IssueFactory()
    api_client.force_authenticate(user=staff_user)
    resp = api_client.patch(f"/api/v1/issues/{issue.id}/", {"status": "resolved"}, format="json")
    assert resp.status_code == 200
    issue.refresh_from_db()
    assert issue.status == Issue.Status.RESOLVED


def test_stats_endpoint_counts_correctly(api_client):
    IssueFactory.create_batch(2, status=Issue.Status.SUBMITTED)
    IssueFactory.create_batch(1, status=Issue.Status.RESOLVED)
    resp = api_client.get("/api/v1/issues/stats/")
    assert resp.status_code == 200
    assert resp.data["open"] == 2
    assert resp.data["resolved"] == 1
    assert resp.data["total"] == 3


def test_presign_upload_rejects_unsupported_content_type(api_client):
    resp = api_client.post("/api/v1/issues/presign-upload/", {"content_type": "application/pdf"}, format="json")
    assert resp.status_code == 400


def test_presign_upload_accepts_anonymous_requests(api_client, monkeypatch):
    # boto3 isn't configured with real AWS creds in tests; patch the client
    # factory so we only assert on our own view logic, not AWS connectivity.
    class FakeS3:
        def generate_presigned_url(self, *args, **kwargs):
            return "https://example-bucket.s3.amazonaws.com/fake-presigned-url"

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    resp = api_client.post("/api/v1/issues/presign-upload/", {"content_type": "image/jpeg"}, format="json")
    assert resp.status_code == 200
    assert resp.data["upload_url"] == "https://example-bucket.s3.amazonaws.com/fake-presigned-url"
    assert resp.data["attachment_key"].startswith("issue-attachments/")
    assert resp.data["attachment_key"].endswith(".jpeg")


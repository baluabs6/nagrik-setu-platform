import pytest
from apps.issues.models import Issue
from .factories import IssueFactory

pytestmark = pytest.mark.django_db


def test_tracking_id_is_auto_generated():
    issue = IssueFactory()
    assert issue.tracking_id.startswith("NS-")
    assert len(issue.tracking_id) == 9  # "NS-" + 6 digits


def test_tracking_id_is_not_overwritten_on_resave():
    issue = IssueFactory()
    original_id = issue.tracking_id
    issue.description = "updated description"
    issue.save()
    issue.refresh_from_db()
    assert issue.tracking_id == original_id


def test_default_status_is_submitted():
    issue = IssueFactory()
    assert issue.status == Issue.Status.SUBMITTED


def test_default_votes_is_one():
    issue = IssueFactory()
    assert issue.votes == 1


def test_str_representation_includes_tracking_id():
    issue = IssueFactory(locality="Indiranagar")
    assert issue.tracking_id in str(issue)
    assert "Indiranagar" in str(issue)


def test_attachment_url_is_none_without_a_key():
    issue = IssueFactory()
    assert issue.attachment_url() is None


def test_attachment_url_generates_presigned_link(monkeypatch):
    issue = IssueFactory(attachment_key="issue-attachments/test.jpg")

    class FakeS3:
        def generate_presigned_url(self, *args, **kwargs):
            return "https://example-bucket.s3.amazonaws.com/issue-attachments/test.jpg?sig=abc"

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    url = issue.attachment_url()
    assert url is not None
    assert "issue-attachments/test.jpg" in url


def test_attachment_url_thumbnail_variant_swaps_the_prefix(monkeypatch):
    issue = IssueFactory(attachment_key="issue-attachments/test.jpg")
    captured = {}

    class FakeS3:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            captured["key"] = Params["Key"]
            return f"https://example-bucket.s3.amazonaws.com/{Params['Key']}?sig=abc"

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    issue.attachment_url(thumbnail=True)
    assert captured["key"] == "issue-attachments-thumbnails/test.jpg"

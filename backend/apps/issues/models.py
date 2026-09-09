import uuid
from django.db import models


class Issue(models.Model):
    class Category(models.TextChoices):
        ROADS = "roads", "Roads & Potholes"
        WATER = "water", "Water Supply"
        GARBAGE = "garbage", "Garbage & Sanitation"
        POWER = "power", "Power Outages"
        LIGHTING = "lighting", "Street Lighting"
        TRANSPORT = "transport", "Public Transport"
        POLLUTION = "pollution", "Air & Noise Pollution"
        GRIEVANCE = "grievance", "Corruption & Grievances"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        IN_PROGRESS = "progress", "In progress"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_id = models.CharField(max_length=16, unique=True, editable=False)
    category = models.CharField(max_length=20, choices=Category.choices)
    locality = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)
    votes = models.PositiveIntegerField(default=1)
    attachment_key = models.CharField(
        max_length=512, blank=True, default="",
        help_text="S3 object key for an uploaded photo, set after a successful presigned-URL upload.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "status"])]

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = f"NS-{uuid.uuid4().int % 900000 + 100000}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_id} · {self.category} · {self.locality}"

    def attachment_url(self, expires_in: int = 3600, thumbnail: bool = False) -> str | None:
        """Presigned GET URL for the uploaded photo (or its thumbnail, once
        the S3-triggered Lambda in backend/lambda/thumbnail/ has produced
        one — see infra/terraform/aws/thumbnail.tf), since the bucket has
        all public access blocked (see infra/terraform/aws/s3.tf)."""
        if not self.attachment_key:
            return None
        key = (
            self.attachment_key.replace("issue-attachments/", "issue-attachments-thumbnails/", 1)
            if thumbnail
            else self.attachment_key
        )
        try:
            import boto3
            from django.conf import settings

            client = boto3.client("s3", region_name=settings.AWS_REGION)
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception:  # noqa: BLE001 - never break a response over a missing photo
            return None

import bleach
from rest_framework import serializers
from .models import Issue

# Free text is stored and later rendered in the admin dashboard and public
# list — plain-text only. Stripping all tags (rather than trusting the
# frontend's escaping alone) means a stored-XSS payload can't survive even
# if some future view ever renders this field as raw HTML.
_ALLOWED_TAGS: list[str] = []


class IssueSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "tracking_id", "category", "locality", "description",
            "status", "votes", "attachment_key", "attachment_url", "thumbnail_url",
            "attachment_verified",
            "ai_suggested_category", "ai_urgency", "ai_confidence", "duplicate_of",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "tracking_id", "votes", "created_at", "updated_at",
            "attachment_verified", "ai_suggested_category", "ai_urgency",
            "ai_confidence", "duplicate_of",
        ]
        # `status` is writable at the serializer level; IsStaffForStatusChange
        # (see permissions.py) is what actually restricts who can set it.
        extra_kwargs = {"attachment_key": {"write_only": True, "required": False}}

    def validate_description(self, value: str) -> str:
        cleaned = bleach.clean(value, tags=_ALLOWED_TAGS, strip=True).strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError("Please provide a bit more detail (at least 10 characters).")
        return cleaned

    def validate_locality(self, value: str) -> str:
        return bleach.clean(value, tags=_ALLOWED_TAGS, strip=True).strip()

    def get_attachment_url(self, obj: Issue):
        return obj.attachment_url()

    def get_thumbnail_url(self, obj: Issue):
        return obj.attachment_url(thumbnail=True)

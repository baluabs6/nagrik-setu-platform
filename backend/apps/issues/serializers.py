from rest_framework import serializers
from .models import Issue


class IssueSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "tracking_id", "category", "locality", "description",
            "status", "votes", "attachment_key", "attachment_url", "thumbnail_url",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "tracking_id", "votes", "created_at", "updated_at"]
        # `status` is writable at the serializer level; IsStaffForStatusChange
        # (see permissions.py) is what actually restricts who can set it.
        extra_kwargs = {"attachment_key": {"write_only": True, "required": False}}

    def get_attachment_url(self, obj: Issue):
        return obj.attachment_url()

    def get_thumbnail_url(self, obj: Issue):
        return obj.attachment_url(thumbnail=True)

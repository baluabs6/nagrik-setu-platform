from django.contrib import admin
from .models import Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("tracking_id", "category", "locality", "status", "votes", "created_at")
    list_filter = ("category", "status")
    search_fields = ("tracking_id", "locality", "description")

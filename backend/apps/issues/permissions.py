from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffForStatusChange(BasePermission):
    """
    - Anyone (including anonymous) can list/retrieve/create/upvote a report.
    - Only staff accounts (municipal admins) can PATCH the `status` field,
      which is what moves a report from submitted -> in progress -> resolved.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if view.action in ("create", "upvote"):
            return True
        if view.action == "partial_update" and "status" in request.data:
            return bool(request.user and request.user.is_staff)
        return True

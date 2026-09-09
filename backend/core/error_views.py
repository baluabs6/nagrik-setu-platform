"""
Custom error handlers, wired up in config/settings.py (handler400/403/404/500).

Each renders a branded HTML page for normal browser requests and a clean
JSON body for API clients (anything sending Accept: application/json or
hitting a /api/ path), so the React SPA and the DRF backend degrade the
same way in production.
"""
from django.http import JsonResponse
from django.shortcuts import render


def _wants_json(request) -> bool:
    accept = request.headers.get("Accept", "")
    return request.path.startswith("/api/") or "application/json" in accept


def handler400(request, exception=None, *args, **kwargs):
    if _wants_json(request):
        return JsonResponse({"error": "bad_request", "message": "The request could not be understood."}, status=400)
    return render(request, "errors/400.html", status=400)


def handler403(request, exception=None, *args, **kwargs):
    if _wants_json(request):
        return JsonResponse({"error": "forbidden", "message": "You don't have permission to do that."}, status=403)
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None, *args, **kwargs):
    if _wants_json(request):
        return JsonResponse({"error": "not_found", "message": "That page or resource doesn't exist."}, status=404)
    return render(request, "errors/404.html", status=404)


def handler500(request, *args, **kwargs):
    if _wants_json(request):
        return JsonResponse({"error": "server_error", "message": "Something went wrong on our end."}, status=500)
    return render(request, "errors/500.html", status=500)


def handler503(request, *args, **kwargs):
    """Not a Django default handler; wire this in manually where you check
    a maintenance-mode flag (e.g. a middleware) since Django has no native
    503 hook."""
    if _wants_json(request):
        return JsonResponse({"error": "unavailable", "message": "The service is temporarily unavailable."}, status=503)
    return render(request, "errors/503.html", status=503)

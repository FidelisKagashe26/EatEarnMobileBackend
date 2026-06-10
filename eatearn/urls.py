from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(_request):
    """Lightweight health/info endpoint the mobile app pings on startup."""
    return JsonResponse(
        {
            "service": "EatEarn API",
            "status": "ok",
            "version": "1.0",
            "endpoints": [
                "/api/auth/",
                "/api/vendors/",
                "/api/menu-items/",
                "/api/orders/",
                "/api/notifications/",
                "/api/approvals/",
            ],
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api_root),
    path("api/", api_root),
    path("api/health/", api_root),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("approvals.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

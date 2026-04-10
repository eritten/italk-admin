from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def index(_request):
    return JsonResponse(
        {
            "name": "iTalkVoIP Admin API",
            "admin": "/admin/",
            "api": "/api/v1/",
        }
    )


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
]

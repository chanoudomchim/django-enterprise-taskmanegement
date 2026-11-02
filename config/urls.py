"""WorkFlow Enterprise URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.views import health_check, home_view
from config.api_v1 import api_router, AuthMeView, ReportSummaryView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("auth/", include("apps.accounts.urls")),
    path("orgs/", include("apps.organizations.urls")),
    path("", include("apps.departments.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.tasks.urls")),
    path("", include("apps.collaboration.urls")),
    path("", include("apps.approvals.urls")),
    path("", include("apps.time_tracking.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.ai_assistant.urls")),
    path("", include("apps.reports.urls")),

    # REST API v1
    path("api/v1/auth/me/", AuthMeView.as_view(), name="api_auth_me"),
    path("api/v1/reports/", ReportSummaryView.as_view(), name="api_reports_summary"),
    path("api/v1/", include(api_router.urls)),

    path("", home_view, name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


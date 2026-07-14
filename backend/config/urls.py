from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.ai_results.views import ai_bootstrap, dashboard_summary_view, health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/ai/bootstrap/", ai_bootstrap, name="ai-bootstrap"),
    path("api/dashboard/summary/", dashboard_summary_view, name="dashboard-summary"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("apps.users.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/employees/", include("apps.employees.urls")),
    path("api/cameras/", include("apps.cameras.urls")),
    path("api/zones/", include("apps.zones.urls")),
    path("api/events/", include("apps.events.urls")),
    path("api/attendance/", include("apps.attendance.urls")),
    path("api/ai-results/", include("apps.ai_results.urls")),
    path("api/alerts/", include("apps.ai_results.alert_urls")),
    path("api/face/", include("apps.face.urls")),
    path("api/reports/", include("apps.reports.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

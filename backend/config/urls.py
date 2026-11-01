from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.documentacion import EsquemaAPIView, SwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/pacientes/', include('pacientes.urls')),
    path('api/', include('informes.urls')),
    path('api/foro/', include('foro.urls')),
    # Documentación Swagger (decisión D-19); solo responde si DOCUMENTACION_API está activa.
    path('api/schema/', EsquemaAPIView.as_view(), name='api-schema'),
    path('api/docs/', SwaggerView.as_view(url_name='api-schema'), name='api-docs'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

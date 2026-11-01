"""
Documentación Swagger de la API (decisión D-19), con drf-spectacular.

- /api/schema/: el esquema OpenAPI 3 (YAML; con ?format=json, en JSON).
- /api/docs/: la página de Swagger, que lee ese esquema.

Solo responden si DOCUMENTACION_API está activa (por defecto, igual que DEBUG); si
no, dan 404, para no publicar el mapa de la API en producción. Se ven sin iniciar
sesión, pero los endpoints siguen pidiendo el token: en Swagger se pega en "Authorize".
"""

from django.conf import settings
from django.http import Http404
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


class _SoloSiEstaActiva:
    def get(self, request, *args, **kwargs):
        if not settings.DOCUMENTACION_API:
            raise Http404
        return super().get(request, *args, **kwargs)


# exclude=True: estas dos rutas no se documentan a sí mismas.
@extend_schema(exclude=True)
class EsquemaAPIView(_SoloSiEstaActiva, SpectacularAPIView):
    pass


@extend_schema(exclude=True)
class SwaggerView(_SoloSiEstaActiva, SpectacularSwaggerView):
    pass

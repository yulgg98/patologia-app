"""
Rechaza con 403 las peticiones a la API que llegan desde un origen no permitido
(decisión D-19).

CORS (django-cors-headers) solo le dice al navegador qué orígenes pueden leer la
respuesta: la petición igual llega a la API y se procesa. Este middleware la corta
antes: si la cabecera Origin no es la del propio servidor ni una de
CORS_ALLOWED_ORIGINS, responde 403 sin ejecutar la vista.

Las peticiones sin cabecera Origin (Postman, curl, otro servidor y las páginas del
mismo origen al pedir con GET) siguen pasando: el navegador es quien envía Origin, así
que esto protege del uso de la API desde páginas de otros sitios. El acceso a los datos
lo sigue protegiendo el token JWT.
"""

from django.conf import settings
from django.http import JsonResponse

PREFIJO_API = '/api/'


def _normalizar(origen):
    return origen.strip().rstrip('/').lower()


class OrigenPermitidoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origen = request.headers.get('Origin')
        if origen and request.path.startswith(PREFIJO_API) and not self._permitido(request, origen):
            mensaje = f'Origen no permitido: {origen}. La API solo acepta peticiones de los orígenes autorizados.'
            return JsonResponse({'detail': mensaje}, status=403, json_dumps_params={'ensure_ascii': False})
        return self.get_response(request)

    @staticmethod
    def _permitido(request, origen):
        origen = _normalizar(origen)
        # La propia API (por ejemplo, la página de Swagger en /api/docs/).
        if origen == _normalizar(f'{request.scheme}://{request.get_host()}'):
            return True
        return origen in {_normalizar(o) for o in settings.CORS_ALLOWED_ORIGINS}

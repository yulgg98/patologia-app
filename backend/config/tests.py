import importlib.util
import os
from pathlib import Path
from unittest import mock

import decouple
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

RUTA_SETTINGS = Path(__file__).resolve().parent / 'settings.py'


def cargar_settings(variables_entorno):
    """
    Carga config/settings.py como un módulo nuevo, simulando que NO existe el
    archivo .env y que el entorno solo tiene las variables indicadas.
    No afecta a la configuración con la que corren las demás pruebas.
    """
    sin_env = decouple.Config(decouple.RepositoryEmpty())
    entorno = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'DEBUG')}
    entorno.update(variables_entorno)
    with mock.patch.object(decouple, 'config', sin_env), mock.patch.dict(os.environ, entorno, clear=True):
        spec = importlib.util.spec_from_file_location('settings_prueba', RUTA_SETTINGS)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    return modulo


class ValoresPorDefectoSegurosTests(SimpleTestCase):
    """
    Hallazgo C-3 de docs/auditoria-inicial.md: si falta el .env, la app no debe
    arrancar con DEBUG=True ni con una SECRET_KEY escrita en el código.
    """

    def test_sin_secret_key_la_app_no_arranca(self):
        with self.assertRaises(Exception) as contexto:
            cargar_settings({})
        self.assertIn('SECRET_KEY', str(contexto.exception))

    def test_debug_es_false_si_no_se_define(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertFalse(settings.DEBUG)

    def test_sin_debug_no_se_permite_cors_desde_cualquier_origen(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)

    def test_usa_la_secret_key_del_entorno(self):
        # Control: si la variable existe, se usa tal cual.
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests', 'DEBUG': 'True'})
        self.assertEqual(settings.SECRET_KEY, 'clave-de-prueba-solo-para-tests')
        self.assertTrue(settings.DEBUG)


class EncabezadoLaboratorioTests(SimpleTestCase):
    """
    Tarea previa 2 de docs/plan-calidad-y-diseno.md: el encabezado del PDF se lee
    de backend/.env (LABORATORIO_NOMBRE, LABORATORIO_DIRECCION, LABORATORIO_TELEFONO).
    Sin esas variables queda el encabezado de demostración de siempre (P-9).
    """

    CLAVE = {'SECRET_KEY': 'clave-de-prueba-solo-para-tests'}

    def test_sin_variables_usa_el_encabezado_de_demostracion(self):
        settings = cargar_settings(self.CLAVE)
        self.assertEqual(settings.LABORATORIO_NOMBRE, 'PathoLab — Laboratorio de Patología (demostración)')
        self.assertEqual(settings.LABORATORIO_DIRECCION, 'Santiago de Cali, Colombia')
        self.assertEqual(settings.LABORATORIO_TELEFONO, '')

    def test_usa_las_variables_definidas(self):
        settings = cargar_settings(
            {
                **self.CLAVE,
                'LABORATORIO_NOMBRE': 'Laboratorio Ficticio de Prueba',
                'LABORATORIO_DIRECCION': 'Calle Falsa 123, Ciudad Ficticia',
                'LABORATORIO_TELEFONO': '000 000 0000',
            }
        )
        self.assertEqual(settings.LABORATORIO_NOMBRE, 'Laboratorio Ficticio de Prueba')
        self.assertEqual(settings.LABORATORIO_DIRECCION, 'Calle Falsa 123, Ciudad Ficticia')
        self.assertEqual(settings.LABORATORIO_TELEFONO, '000 000 0000')

    def test_lee_tildes_y_raya_del_archivo_env(self):
        # El .env se escribe a mano: las tildes y la raya (—) deben llegar intactas al PDF.
        import tempfile

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / '.env'
            ruta.write_text(
                'SECRET_KEY=clave-de-prueba-solo-para-tests\n'
                'LABORATORIO_NOMBRE=Laboratorio Ficticio — Anatomía Patológica\n'
                'LABORATORIO_DIRECCION=Carrera Ficticia 1 # 2-3, Bogotá\n',
                encoding='utf-8',
            )
            desde_archivo = decouple.Config(decouple.RepositoryEnv(str(ruta)))
            entorno = {k: v for k, v in os.environ.items() if not k.startswith('LABORATORIO_')}
            with mock.patch.object(decouple, 'config', desde_archivo), mock.patch.dict(os.environ, entorno, clear=True):
                spec = importlib.util.spec_from_file_location('settings_prueba_env', RUTA_SETTINGS)
                settings = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(settings)
        self.assertEqual(settings.LABORATORIO_NOMBRE, 'Laboratorio Ficticio — Anatomía Patológica')
        self.assertEqual(settings.LABORATORIO_DIRECCION, 'Carrera Ficticia 1 # 2-3, Bogotá')


class NumProxiesTests(SimpleTestCase):
    """
    Hallazgo O-17 de docs/auditoria-owasp.md: NUM_PROXIES dice cuántos proxies hay
    delante de Django. Sin definir vale 0: DRF usa la IP de la conexión y no la
    cabecera X-Forwarded-For, que el cliente puede inventar.
    """

    def test_num_proxies_vale_0_si_no_se_define(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertEqual(settings.REST_FRAMEWORK['NUM_PROXIES'], 0)

    def test_num_proxies_se_lee_del_entorno(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests', 'NUM_PROXIES': '1'})
        self.assertEqual(settings.REST_FRAMEWORK['NUM_PROXIES'], 1)


class LimitePeticionesUsuarioTests(SimpleTestCase):
    """
    Fase de Cypress: el límite de peticiones por usuario se puede subir con
    LIMITE_PETICIONES_USUARIO (solo lo hace npm run e2e, que va más rápido que una persona).
    El del login no cambia.
    """

    def test_sin_variable_es_120_por_minuto(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user'], '120/minute')

    def test_se_lee_del_entorno_y_no_cambia_el_del_login(self):
        settings = cargar_settings(
            {'SECRET_KEY': 'clave-de-prueba-solo-para-tests', 'LIMITE_PETICIONES_USUARIO': '2000/minute'}
        )
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user'], '2000/minute')
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'], '10/minute')


class ArchivoSqliteTests(SimpleTestCase):
    """
    Fase de Cypress: las pruebas de punta a punta usan su propia base SQLite
    (SQLITE_NOMBRE), para no tocar la base de desarrollo. Sin la variable, la de siempre.
    """

    def test_sin_variable_usa_db_sqlite3(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertEqual(settings.DATABASES['default']['NAME'], settings.BASE_DIR / 'db.sqlite3')

    def test_el_archivo_se_lee_del_entorno(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests', 'SQLITE_NOMBRE': 'e2e_db.sqlite3'})
        self.assertEqual(settings.DATABASES['default']['NAME'], settings.BASE_DIR / 'e2e_db.sqlite3')
        # Las pruebas del backend siguen usando su propio archivo.
        self.assertEqual(settings.DATABASES['default']['TEST']['NAME'], settings.BASE_DIR / 'test_db.sqlite3')


class RegistrosTests(SimpleTestCase):
    """
    Hallazgo O-21 de docs/auditoria-owasp.md: sin LOGGING, con DEBUG=False los errores 500
    iban a `mail_admins` con ADMINS vacío, es decir, a ningún lado. Ahora van a la consola
    (la recoge el servidor), igual que los registros de seguridad, sin depender de DEBUG.
    """

    def manejadores(self, settings, logger):
        configuracion = settings.LOGGING
        nombres = configuracion['loggers'][logger]['handlers']
        return [configuracion['handlers'][nombre] for nombre in nombres]

    def test_los_errores_500_van_a_la_consola_con_debug_false(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        self.assertFalse(settings.DEBUG)
        manejadores = self.manejadores(settings, 'django.request')
        self.assertTrue(any(m['class'] == 'logging.StreamHandler' for m in manejadores))
        # Sin el filtro require_debug_true, que los dejaría fuera en producción.
        self.assertTrue(all('require_debug_true' not in m.get('filters', []) for m in manejadores))

    def test_el_registro_de_seguridad_va_a_la_consola(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests'})
        manejadores = self.manejadores(settings, 'seguridad')
        self.assertTrue(any(m['class'] == 'logging.StreamHandler' for m in manejadores))
        self.assertEqual(settings.LOGGING['loggers']['seguridad']['level'], 'INFO')

    def test_el_nivel_se_lee_del_entorno(self):
        settings = cargar_settings({'SECRET_KEY': 'clave-de-prueba-solo-para-tests', 'LOG_LEVEL': 'WARNING'})
        self.assertEqual(settings.LOGGING['loggers']['seguridad']['level'], 'WARNING')


CLAVE = 'clave-de-prueba-solo-para-tests'
ORIGEN_FRONTEND = 'http://localhost:5173'
ORIGEN_AJENO = 'https://sitio-ajeno.example'


class ConfiguracionCorsTests(SimpleTestCase):
    """
    Decisión D-19: CORS solo acepta los orígenes de CORS_ALLOWED_ORIGINS, también con
    DEBUG=True. Antes, en desarrollo se aceptaba cualquier origen.
    """

    def test_con_debug_tampoco_se_permite_cualquier_origen(self):
        settings = cargar_settings({'SECRET_KEY': CLAVE, 'DEBUG': 'True'})
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)

    def test_sin_variable_solo_se_permite_el_frontend_de_desarrollo(self):
        settings = cargar_settings({'SECRET_KEY': CLAVE, 'DEBUG': 'True'})
        self.assertEqual(settings.CORS_ALLOWED_ORIGINS, ['http://localhost:5173', 'http://127.0.0.1:5173'])

    def test_los_origenes_se_leen_del_entorno(self):
        settings = cargar_settings({'SECRET_KEY': CLAVE, 'CORS_ALLOWED_ORIGINS': 'https://patolab.example'})
        self.assertEqual(settings.CORS_ALLOWED_ORIGINS, ['https://patolab.example'])

    def test_el_filtro_de_origenes_va_antes_que_cors(self):
        settings = cargar_settings({'SECRET_KEY': CLAVE})
        middleware = settings.MIDDLEWARE
        self.assertLess(
            middleware.index('config.origenes.OrigenPermitidoMiddleware'),
            middleware.index('corsheaders.middleware.CorsMiddleware'),
        )

    def test_la_documentacion_sigue_a_debug_si_no_se_define(self):
        self.assertTrue(cargar_settings({'SECRET_KEY': CLAVE, 'DEBUG': 'True'}).DOCUMENTACION_API)
        self.assertFalse(cargar_settings({'SECRET_KEY': CLAVE}).DOCUMENTACION_API)
        self.assertTrue(cargar_settings({'SECRET_KEY': CLAVE, 'DOCUMENTACION_API': 'True'}).DOCUMENTACION_API)


@override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_FRONTEND])
class OrigenesApiTests(APITestCase):
    """
    Decisión D-19: una petición del navegador desde un origen no permitido recibe 403
    sin llegar a la vista (config/origenes.py), y CORS no le da la cabecera
    Access-Control-Allow-Origin. Las de los orígenes permitidos y las que no traen
    Origin (Postman, curl) funcionan como antes.
    """

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='cors_prueba', password='Clave-Prueba-123', rol='patologo'
        )

    def test_un_origen_ajeno_recibe_403(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/opciones/', HTTP_ORIGIN=ORIGEN_AJENO)
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('Origen no permitido', respuesta.json()['detail'])
        self.assertNotIn('Access-Control-Allow-Origin', respuesta.headers)

    def test_un_origen_ajeno_no_puede_iniciar_sesion(self):
        respuesta = self.client.post(
            '/api/auth/login/',
            {'username': 'cors_prueba', 'password': 'Clave-Prueba-123'},
            format='json',
            HTTP_ORIGIN=ORIGEN_AJENO,
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotIn('access', respuesta.json())

    def test_la_consulta_previa_de_un_origen_ajeno_recibe_403(self):
        respuesta = self.client.options(
            '/api/informes/', HTTP_ORIGIN=ORIGEN_AJENO, HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotIn('Access-Control-Allow-Origin', respuesta.headers)

    def test_el_origen_permitido_recibe_la_cabecera_de_cors(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/opciones/', HTTP_ORIGIN=ORIGEN_FRONTEND)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['Access-Control-Allow-Origin'], ORIGEN_FRONTEND)

    def test_la_consulta_previa_del_origen_permitido_funciona(self):
        respuesta = self.client.options(
            '/api/informes/', HTTP_ORIGIN=ORIGEN_FRONTEND, HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['Access-Control-Allow-Origin'], ORIGEN_FRONTEND)

    def test_el_origen_permitido_puede_iniciar_sesion(self):
        respuesta = self.client.post(
            '/api/auth/login/',
            {'username': 'cors_prueba', 'password': 'Clave-Prueba-123'},
            format='json',
            HTTP_ORIGIN=ORIGEN_FRONTEND,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('access', respuesta.json())

    def test_el_propio_servidor_es_un_origen_permitido(self):
        # Por ejemplo, la página de Swagger (/api/docs/) probando un endpoint.
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/opciones/', HTTP_ORIGIN='http://testserver')
        self.assertEqual(respuesta.status_code, 200)

    def test_sin_cabecera_origin_no_se_bloquea(self):
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.get('/api/opciones/').status_code, 200)

    def test_sin_origin_la_api_sigue_pidiendo_el_token(self):
        # El filtro de orígenes no reemplaza la autenticación.
        self.assertEqual(self.client.get('/api/opciones/').status_code, 401)

    def test_no_afecta_las_rutas_fuera_de_la_api(self):
        respuesta = self.client.get('/admin/login/', HTTP_ORIGIN=ORIGEN_AJENO)
        self.assertEqual(respuesta.status_code, 200)


class DocumentacionApiTests(APITestCase):
    """Decisión D-19: documentación Swagger en /api/docs/ y esquema OpenAPI en /api/schema/."""

    @override_settings(DOCUMENTACION_API=True)
    def test_la_pagina_de_swagger_carga_sin_iniciar_sesion(self):
        respuesta = self.client.get('/api/docs/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('swagger-ui', respuesta.content.decode())

    @override_settings(DOCUMENTACION_API=True)
    def test_el_esquema_documenta_todos_los_grupos_de_la_api(self):
        respuesta = self.client.get('/api/schema/', {'format': 'json'})
        self.assertEqual(respuesta.status_code, 200)
        esquema = respuesta.json()
        self.assertEqual(esquema['info']['title'], 'API de PathoLab')
        rutas = esquema['paths']
        for ruta in (
            '/api/auth/login/',
            '/api/auth/logout/',
            '/api/auth/cambiar-password/',
            '/api/opciones/',
            '/api/informes/',
            '/api/informes/{id}/finalizar/',
            '/api/pacientes/',
            '/api/foro/publicaciones/',
        ):
            self.assertIn(ruta, rutas)
        # El token JWT se documenta como esquema de seguridad, para el botón "Authorize".
        self.assertIn('jwtAuth', esquema['components']['securitySchemes'])

    @override_settings(DOCUMENTACION_API=False)
    def test_sin_documentacion_activa_responde_404(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 404)
        self.assertEqual(self.client.get('/api/schema/').status_code, 404)

from datetime import timedelta
from pathlib import Path

from decouple import Csv, UndefinedValueError, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Core / seguridad general ----------
# SECRET_KEY, DEBUG y ALLOWED_HOSTS se leen de variables de entorno (.env).
# No hay SECRET_KEY por defecto: el código es público y con esa clave se podrían
# falsificar tokens JWT. Si falta, la app no arranca (auditoría C-3).
try:
    SECRET_KEY = config('SECRET_KEY')
except UndefinedValueError:
    raise ImproperlyConfigured(
        'Falta la variable SECRET_KEY. Copia backend/.env.example como backend/.env '
        'y pon una clave propia (ver README).'
    ) from None

# Si no se define, DEBUG queda desactivado (modo seguro para producción).
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ---------- Applications ----------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # lista negra de tokens (decisión D-6)
    'corsheaders',
    'drf_spectacular',  # documentación Swagger / OpenAPI (decisión D-19)
    'drf_spectacular_sidecar',  # archivos de Swagger UI servidos por Django, sin CDN (D-19)
    # Local
    'accounts',
    'informes',
    'pacientes',
    'foro',
]

# ---------- Middleware ----------
MIDDLEWARE = [
    # Va antes que CORS: corta con 403 las peticiones a /api/ de orígenes no permitidos (D-19).
    'config.origenes.OrigenPermitidoMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------- Database (persistencia) ----------
# En desarrollo usa SQLite. En producción, definiendo DB_NAME en el .env
# se conecta automáticamente a Postgres (persistencia real, no efímera).
if config('DB_NAME', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            # SQLITE_NOMBRE elige otro archivo: npm run e2e (Cypress) usa e2e_db.sqlite3
            # para no tocar la base de desarrollo.
            'NAME': BASE_DIR / config('SQLITE_NOMBRE', default='db.sqlite3'),
            # Si otro usuario está escribiendo, espera hasta 20 s en lugar de fallar
            # con "database is locked" (número de petición, decisión D-7).
            'OPTIONS': {'timeout': 20},
            # Las pruebas usan un archivo y no la base en memoria: la prueba de
            # concurrencia escribe desde varios hilos, y la base en memoria falla
            # con "table is locked" en vez de esperar. *.sqlite3 está en .gitignore.
            'TEST': {'NAME': BASE_DIR / 'test_db.sqlite3'},
        }
    }

# ---------- Auth ----------
AUTH_USER_MODEL = 'accounts.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------- REST Framework ----------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'config.paginacion.PaginacionEstandar',  # admite ?page_size= (máx. 1000)
    'PAGE_SIZE': 20,
    # Esquema OpenAPI para la documentación Swagger (decisión D-19).
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ---- Anti-SPAM / seguridad de la API REST ----
    # Limita cuántas peticiones puede hacer un cliente en una ventana de tiempo,
    # para frenar fuerza bruta en login y flood de publicaciones/comentarios.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    # Cuántos proxies hay delante de Django (hallazgo O-17). Con 0, los límites usan la IP
    # de la conexión y no la cabecera X-Forwarded-For, que el cliente puede inventar.
    # Detrás de un Nginx que agrega la IP real, NUM_PROXIES=1 en el .env.
    'NUM_PROXIES': config('NUM_PROXIES', default=0, cast=int),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        # npm run e2e (Cypress) lo sube para su backend: las pruebas van más rápido que
        # una persona. El del login no se puede cambiar (O-16).
        'user': config('LIMITE_PETICIONES_USUARIO', default='120/minute'),
        'login': '10/minute',
        'registro': '5/minute',
        'foro_publicacion': '10/minute',
        'foro_comentario': '20/minute',
    },
}

# Las pruebas no acumulan los límites de peticiones entre sí (ver config/test_runner.py).
TEST_RUNNER = 'config.test_runner.PathoLabTestRunner'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    # Al renovar, el token de renovación anterior queda invalidado (decisión D-6).
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------- CORS (decisión D-19) ----------
# Solo los orígenes listados en CORS_ALLOWED_ORIGINS pueden llamar a la API desde un
# navegador, también en desarrollo: ya no se permite cualquier origen con DEBUG=True.
# Por defecto, el frontend de desarrollo (Vite, puerto 5173). Además de CORS,
# config/origenes.py responde 403 a las peticiones de cualquier otro origen.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173', cast=Csv())

# ---------- Documentación de la API: Swagger (decisión D-19) ----------
# /api/schema/ (OpenAPI) y /api/docs/ (Swagger), en config/documentacion.py. Por defecto
# solo con DEBUG=True, para no publicar el mapa de la API en producción (si no, 404).
DOCUMENTACION_API = config('DOCUMENTACION_API', default=DEBUG, cast=bool)
SPECTACULAR_SETTINGS = {
    'TITLE': 'API de PathoLab',
    'DESCRIPTION': (
        'API REST de PathoLab: informes histopatológicos, pacientes, plantillas y foro. '
        'Para probar los endpoints, obtén un token en POST /api/auth/login/ y pégalo en "Authorize". '
        'Solo se aceptan peticiones de navegador desde los orígenes de CORS_ALLOWED_ORIGINS.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # La documentación se ve sin iniciar sesión; los endpoints siguen pidiendo el token.
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
    'SWAGGER_UI_SETTINGS': {'persistAuthorization': True},
    # Swagger UI desde drf-spectacular-sidecar: funciona sin internet y con una versión fija.
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# ---------- Seguridad general adicional ----------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    # Solo se activan en producción real (detrás de HTTPS) para no romper
    # el entorno de desarrollo local.
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------- Archivos subidos (imágenes del foro) ----------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Tamaño máximo de cada imagen del foro. Lo comprueba foro/views.py (auditoría I-6).
# El frontend (ForoPage.jsx) usa el mismo valor para avisar antes de publicar.
FORO_MAX_TAMANO_IMAGEN = 10 * 1024 * 1024
# DATA_UPLOAD_MAX_MEMORY_SIZE limita el cuerpo de la petición SIN contar los archivos,
# así que no sirve para limitar imágenes. Para FILE_UPLOAD_MAX_MEMORY_SIZE se deja el
# valor por defecto de Django (2,5 MB): los archivos más grandes van a disco temporal
# en vez de ocupar RAM.
# En producción, el servidor web debe cortar las peticiones enormes antes de que
# lleguen a Django (por ejemplo, en Nginx: client_max_body_size 60m;).
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ---------- Encabezado del PDF de los informes ----------
# Datos del laboratorio que imprime el encabezado del PDF. Sin .env queda el
# encabezado de demostración (respuesta P-9), que no copia los datos de ningún
# laboratorio real. La dirección es una sola línea (dirección completa y ciudad);
# si el teléfono está vacío, el PDF no imprime su línea.
LABORATORIO_NOMBRE = config('LABORATORIO_NOMBRE', default='PathoLab — Laboratorio de Patología (demostración)')
LABORATORIO_DIRECCION = config('LABORATORIO_DIRECCION', default='Santiago de Cali, Colombia')
LABORATORIO_TELEFONO = config('LABORATORIO_TELEFONO', default='')

# ---------- Registros (logging) ----------
# Hallazgo O-21 de docs/auditoria-owasp.md. Sin LOGGING, con DEBUG=False Django mandaba
# los errores 500 a mail_admins y, con ADMINS vacío, no quedaban en ningún lado. Todo va
# a la consola, que recoge el servidor (systemd, Docker…), con o sin DEBUG:
# - django.request: solo los errores 500 (los 4xx son errores del cliente);
# - seguridad: inicios de sesión correctos (INFO) y fallidos (WARNING), con el usuario y
#   la IP (accounts/signals.py). Nunca se registran contraseñas, tokens ni datos de pacientes.
# LOG_LEVEL (backend/.env) es el nivel del registro de seguridad.
LOG_LEVEL = config('LOG_LEVEL', default='INFO').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'consola': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'django.request': {'handlers': ['consola'], 'level': 'ERROR', 'propagate': False},
        'seguridad': {'handlers': ['consola'], 'level': LOG_LEVEL, 'propagate': False},
    },
}

# ---------- i18n ----------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ---------- Static ----------
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auditoría de seguridad OWASP Top 10:2025

**Fecha:** 2026-10-11
**Rama:** `fase-3-auditoria-owasp` (fase 3 de `docs/plan-calidad-y-diseno.md`).
**Alcance:**
- `backend/` y `frontend/src/` completos;
- la configuración (`settings.py`, `.env.example`, `vite.config.js`);
- las dependencias de npm (raíz y frontend) y de Python.

**Importante:** en esta fase **no se modificó ningún archivo de código**.
- Las comprobaciones de comportamiento se hicieron con pruebas temporales fuera del proyecto. Usaban la base de pruebas (`test_db.sqlite3`), no la de desarrollo.
- `pip-audit` se ejecutó en un entorno virtual temporal, fuera del proyecto. No se instaló en el venv del backend.
- Las correcciones se eligen y se hacen en la fase 4.

---

## Cómo leer este informe

Cada hallazgo nuevo tiene un identificador `O-N` y una prioridad:

| Prioridad | Qué significa |
|---|---|
| **Alta** | Rompe una regla del sistema o abre un ataque realista. Conviene corregirla al empezar la fase 4. |
| **Media** | Es un riesgo real, pero con alcance limitado o que exige otra condición (por ejemplo, un XSS previo o un despliegue concreto). Conviene corregirla en la fase 4 o antes de publicar la app. |
| **Baja** | Mejora de defensa en profundidad, de despliegue o de higiene. Se puede dejar para después con su motivo anotado. |

**Comprobado** quiere decir que el fallo se ejecutó y se vio ocurrir. **Deducido del código** quiere decir que se razonó leyendo el código (de PathoLab o de la librería), sin ejecutarlo.

Los códigos C-x, I-x y M-x remiten a `docs/auditoria-inicial.md`, y los D-x a `docs/decisiones.md`.

---

## Resumen

- **Hallazgos:** 23 (`O-1` a `O-23`): 5 de prioridad alta, 13 de prioridad media y 5 de prioridad baja.
  - **Comprobados:** 6. Son O-1, O-2, O-13, O-16, O-22 y O-23.
- **Lo más urgente:**
  1. **O-1.** Cualquier patólogo puede pasar su informe a "finalizado" con un `PATCH {"estado": "finalizado"}`. Así se salta los requisitos de D-8, y el informe queda sin firma ni datos congelados (D-10, D-15) y ya no se puede corregir más que con adendas.
  2. **O-16.** El login y el registro **no tienen ningún límite de intentos**. El README dice 10/min y 5/min, pero `ScopedRateThrottle` no se activa porque las vistas no definen `throttle_scope`. Además, al poner `throttle_classes` se pierde también el límite global de anónimos. Se puede probar contraseñas sin fin.
  3. **O-13.** El foro acepta un archivo `ataque.html` que también es un PNG válido y lo guarda con extensión `.html`. Si se sirve desde el mismo dominio que la app, es un XSS almacenado que puede robar los tokens de `localStorage` (O-19).
  4. **O-9.** **Django 4.2 ya no tiene soporte** (terminó en abril de 2026). `pip-audit` encuentra 8 avisos que solo se corrigen en 5.2 o 6.0. Ninguno afecta hoy a PathoLab, pero los próximos no tendrán parche para 4.2.
  5. **O-4 (D-14, ya decidida).** En `/admin/` un informe finalizado se puede modificar y borrar.
- **Lo que ya está bien protegido:** C-1, C-2, C-3, I-3, I-5, I-6, I-8, I-11 y las decisiones D-2, D-3 (en la API), D-6, D-7, D-9, D-10, D-11, D-12 y D-15. El detalle está en cada categoría.

### Tabla de hallazgos

| ID | Categoría | Hallazgo | Prioridad | Comprobado |
|---|---|---|---|---|
| O-1 | A01, A08 | `estado` se puede escribir por la API: se finaliza sin requisitos ni datos congelados | Alta | Sí |
| O-2 | A01, A07 | `Usuario.activo` no hace nada: un usuario "inactivo" sigue entrando | Media | Sí |
| O-3 | A01, A08 | En `/admin/`, un borrador se pasa a finalizado sin requisitos ni datos congelados | Media | Deducido |
| O-4 | A01, A08 | En `/admin/`, un finalizado se modifica y se borra (**D-14, ya decidida**) | Alta | Deducido (D-14) |
| O-5 | A01 | `/media/` (imágenes del foro) sin autenticación en producción, con rutas previsibles | Media | Deducido |
| O-6 | A02 | Sin política de seguridad de contenido (CSP) ni cabeceras para el frontend; un ajuste obsoleto | Media | Deducido |
| O-7 | A02, A04 | `.env.example` desactiva la redirección a HTTPS y su `SECRET_KEY` de ejemplo se acepta | Baja | `check --deploy` |
| O-8 | A02 | Nombre o documento del paciente en la dirección (`?q=`) | Baja | Ya conocido |
| O-9 | A03 | Django 4.2 sin soporte; 8 avisos de `pip-audit` | Alta | `pip-audit` |
| O-10 | A03, A08 | Dependencias de Python sin versiones fijas ni archivo de bloqueo; `pip` y `setuptools` viejos en el venv | Media | `pip-audit` |
| O-11 | A03 | I-9c: 2 avisos moderados de `react-router` 6 (no afectan) | Baja | `npm audit` |
| O-12 | A04 | Clave antigua en el historial de git (C-3) | Baja | Ya conocido |
| O-13 | A05 | Subida de imágenes: se acepta un `.html` que también es una imagen válida (XSS almacenado) | Alta | Sí |
| O-14 | A06, A08 | Edición concurrente: gana el último guardado, y un `PUT` puede colarse al finalizar | Media | Deducido |
| O-15 | A06 | Extracción masiva: `?page_size=1000` para cualquier usuario autenticado | Baja | Deducido |
| O-16 | A07 | Login y registro sin límite de intentos | Alta | Sí |
| O-17 | A07 | Los límites se saltan cambiando la cabecera `X-Forwarded-For` | Media | Deducido del código de DRF |
| O-18 | A07 | `/admin/` sin límite de intentos de login | Media | Deducido |
| O-19 | A07 | Tokens en `localStorage` y token de acceso de 8 horas | Media | Deducido |
| O-20 | A09 | No hay registro de accesos a pacientes, informes y PDF | Media | Deducido |
| O-21 | A09 | Sin `LOGGING`: con `DEBUG=False` los errores 500 y los intentos fallidos no se registran | Media | Deducido |
| O-22 | A10 | Filtros con valores no válidos responden 500 (8 rutas) | Media | Sí |
| O-23 | A10 | `datos_ingresados` que no es un objeto: 500, y el informe queda guardado a medias | Media | Sí |

---

## A01: Control de acceso roto

### Qué aplica a PathoLab

Los roles (admin, patólogo, auditor), la regla del autor (D-2), los informes finalizados (D-3, D-14), los permisos de pacientes y catálogos (D-11), el PDF de borrador (D-12), el foro, `/admin/` y los archivos subidos (`/media/`).

### Qué ya está protegido

- **C-1:** nadie se cambia el rol, `activo`, `username` ni el registro médico desde `/api/auth/perfil/` (`read_only_fields` en `accounts/serializers.py`).
- **C-2, D-2:** `EsAutorOAdminOSoloLectura` (`accounts/permissions.py:31`). Solo el autor o un admin edita, borra o finaliza un informe, y el auditor no escribe.
- **D-3:** en la API, un finalizado responde 400 a `PUT`, `PATCH` y `DELETE`, también para un admin (`InformeViewSet._rechazar_si_finalizado`).
- **D-11:** solo el admin borra pacientes (`EsPatologoOAdminYSoloAdminBorra`).
- **D-12:** el PDF de un borrador es solo para su autor o un admin (`exportar_pdf`, `informes/views.py:281`).
- **I-8:** en el foro, solo un admin fija publicaciones y un comentario no se mueve a otra publicación.
- **Adendas (D-9):** solo en finalizados, autor o admin, sin `PUT`, `PATCH` ni `DELETE`, y de solo lectura en `/admin/` (`AdendaInline`).
- El registro de usuarios y la lista de usuarios son solo del admin (`EsAdmin`).
- El historial del paciente (`/api/pacientes/{id}/informes/`) lo ven todos los roles autenticados, como los informes. Es coherente con D-11 y D-2.

**Observación, no hallazgo.** Por D-2, todos los roles leen todos los informes por la API, también los borradores ajenos y el auditor. D-12 solo restringe el **PDF** del borrador. Es lo decidido, pero queda como pregunta para el usuario (ver "Preguntas para el usuario").

### O-1. `estado` se puede escribir por la API: un informe se finaliza sin requisitos ni datos congelados (Alta, comprobado)

> **Estado: corregido el 2026-10-11** (fase 4, grupo 1). `estado` es de solo lectura en `InformeSerializer`. Prueba: `EstadoSoloLecturaTests`.

- **Dónde:** `backend/informes/serializers.py:197` y `:205-213`. `estado` está en `fields`, pero no en `read_only_fields`.
- **Qué pasa:** `POST /api/informes/{id}/finalizar/` comprueba los requisitos de D-8, fija `fecha_informe` y guarda `datos_finalizacion` (D-10, D-15). Pero el mismo cambio se hace con `PATCH /api/informes/{id}/` y `{"estado": "finalizado"}`, y entonces no se comprueba ni se guarda nada de eso. También se puede **crear** un informe ya finalizado con `POST /api/informes/` y `"estado": "finalizado"`.
- **Cómo se reproduce (comprobado):**
  1. Un patólogo sin registro médico crea un informe sin diagnósticos ni microscópica.
  2. Envía `PATCH {"estado": "finalizado"}`: **200**, y el informe queda finalizado con `fecha_informe = None` y `datos_finalizacion = None`.
  3. `requisitos_faltantes()` devuelve 3 requisitos sin cumplir.
  4. `POST /api/informes/` con `"estado": "finalizado"` responde **201** con el informe ya finalizado.
- **Por qué importa:**
  - Rompe D-8: un informe sin diagnóstico ni firma queda finalizado.
  - Rompe D-10 y D-15: sin `datos_finalizacion`, `datos_impresos()` usa los datos **actuales**. Si después se corrige el paciente o cambia el `.env`, el PDF de un informe "finalizado" cambia.
  - Por D-3, ese informe ya no se puede arreglar: solo admite adendas.
  - En la base de desarrollo hoy no hay ningún finalizado sin datos congelados (6 de 6 están bien), así que no hay datos que reparar.
- **Corrección propuesta:**
  - agregar `estado` a `read_only_fields` de `InformeSerializer`, para que solo `finalizar` lo cambie (el frontend no lo envía nunca);
  - pruebas: `PATCH` y `POST` con `estado` no lo cambian.
  - Opcional: una comprobación (prueba o comando) de que ningún finalizado tiene `datos_finalizacion` o `fecha_informe` vacíos.

### O-2. `Usuario.activo` no hace nada: un usuario "inactivo" sigue entrando (Media, comprobado)

- **Dónde:** `backend/accounts/models.py:24` (campo `activo`) y `backend/accounts/admin.py:40`, que lo muestra en "Datos de PathoLab". Ningún código lo consulta.
- **Qué pasa:**
  - Django y SimpleJWT solo miran `is_active`, el campo estándar.
  - Un admin que desmarca "activo" en `/admin/` cree que desactivó la cuenta, pero no cambia nada.
  - `is_active` también está en la ficha (sección "Permisos" de `UserAdmin`), así que hay dos casillas parecidas y solo una funciona.
- **Cómo se reproduce (comprobado):** un usuario con `activo=False` hace login y recibe **200** con sus tokens.
- **Por qué importa:** la forma prevista de dar de baja a alguien (por ejemplo, un patólogo que deja el laboratorio) no le quita el acceso a datos de pacientes.
- **Corrección propuesta** (**la elige el usuario**):
  - **Opción A (recomendada):** usar solo `is_active`. Una migración copia `activo` en `is_active` y borra `activo`; la API muestra `is_active` con el nombre `activo`. Django y SimpleJWT ya rechazan a los usuarios inactivos, también con un token de acceso vigente.
  - **Opción B:** mantener `activo` y sincronizarlo con `is_active` en `Usuario.save()`.
  - En las dos: una prueba de que un usuario desactivado no hace login, no renueva su token y no usa un token de acceso que ya tenía.

### O-3. En `/admin/`, un borrador se pasa a finalizado sin requisitos ni datos congelados (Media, deducido del código)

> **Estado: corregido el 2026-10-11** (fase 4, grupo 1). `estado` es de solo lectura en `InformeAdmin`. Prueba: `AdminInformeFinalizadoTests.test_un_borrador_no_se_finaliza_desde_admin`.

- **Dónde:** `backend/informes/admin.py:56-81`. `estado` es un campo editable de `InformeAdmin`.
- **Qué pasa:** D-14 cubre los informes **ya** finalizados. Un **borrador** sigue siendo editable en `/admin/`, incluido su `estado`. Pasarlo ahí a "Finalizado" tiene el mismo efecto que O-1: sin requisitos (D-8), sin `fecha_informe` ni `datos_finalizacion` (D-10, D-15).
- **Por qué importa:** es la misma ruptura de O-1, aunque solo la puede hacer un usuario con acceso a `/admin/` (`is_staff`).
- **Corrección propuesta:**
  - en `InformeAdmin`, `estado` siempre de solo lectura: un informe solo se finaliza con `POST /api/informes/{id}/finalizar/`;
  - hacerlo junto con O-4 (D-14), en la misma rama y con las mismas pruebas de `/admin/`.
  - Si el usuario quiere finalizar también desde `/admin/`, la alternativa es una acción de admin que llame a la misma lógica que `finalizar`.

### O-4. En `/admin/`, un informe finalizado se modifica y se borra (Alta; ya decidida en D-14)

> **Estado: corregido el 2026-10-11** (fase 4, grupo 1). Un finalizado no tiene permiso de cambio ni de borrado en `/admin/`, y sus diagnósticos son de solo lectura. Prueba: `AdminInformeFinalizadoTests`.

- **Dónde:** `backend/informes/admin.py:56-81` (`InformeAdmin` y `DiagnosticoInline`).
- **Qué pasa:** hoy se pueden cambiar el contenido, los diagnósticos y el estado de un finalizado, y también borrarlo, sin dejar rastro en el informe.
- **Estado:** **ya decidido (D-14, 2026-10-08).** La corrección y sus pruebas están descritas en la fase 4 del plan. Este informe solo la registra con un identificador para seguirla.

### O-5. `/media/` sin autenticación en producción, con rutas previsibles (Media, deducido del código)

- **Dónde:**
  - `backend/config/urls.py:14-15`: Django sirve `/media/` solo con `DEBUG=True`;
  - `backend/foro/models.py:5-6`: la ruta es `foro/publicaciones/<id>/<nombre original del archivo>`;
  - README, "Seguridad": pide servir `media/` con el servidor web.
- **Qué pasa:**
  - La API exige sesión, pero los archivos no: cualquiera que tenga la dirección de una imagen la descarga sin iniciar sesión. Esto vale para Django en desarrollo y para el servidor web en producción.
  - La dirección es fácil de adivinar: un número consecutivo y el nombre que el archivo tenía en el equipo del usuario (por ejemplo, `IMG_0001.jpg`).
  - Las imágenes conservan sus metadatos EXIF (fecha, equipo y, en fotos de celular, la ubicación).
- **Por qué importa:** el foro tiene un tema "Casos clínicos". Una imagen de un caso puede llevar datos del paciente (una etiqueta en la lámina, una foto clínica), y la Ley 1581 los considera datos sensibles.
- **Corrección propuesta:**
  1. Nombre aleatorio (UUID) en `ruta_imagen_publicacion`. Se combina con O-13.
  2. Volver a codificar la imagen con Pillow al subirla: quita EXIF y cualquier contenido extra (O-13).
  3. A más largo plazo, servir las imágenes por una vista que exija sesión, por ejemplo con `X-Accel-Redirect` de Nginx o `FileResponse` en desarrollo. El frontend tendría que pedirlas con el token, como el PDF (I-5).
  - La prioridad sube a **alta** si el foro se va a usar con imágenes de casos reales.

---

## A02: Configuración de seguridad incorrecta

### Qué aplica a PathoLab

`DEBUG`, `SECRET_KEY`, CORS, HTTPS y HSTS, las cabeceras, `/admin/`, `.env.example` y lo que dice `manage.py check --deploy`.

### Qué ya está protegido

- **C-3:** sin `SECRET_KEY` la app no arranca, y `DEBUG` es `False` si no se define (`settings.py:13-22`). Lo vigila `config/tests.py`.
- Con `DEBUG=False`:
  - CORS solo acepta los orígenes de `CORS_ALLOWED_ORIGINS`;
  - se activan la redirección a HTTPS, las cookies seguras y HSTS de un año con subdominios y `preload` (`settings.py:159-176`).
- `X_FRAME_OPTIONS = 'DENY'` y `SECURE_CONTENT_TYPE_NOSNIFF`.
- `/media/` solo lo sirve Django en desarrollo.
- **`check --deploy`** con `DEBUG=False` y una clave propia da un solo aviso, W008 (`SECURE_SSL_REDIRECT`). Sale porque el `.env` local, copiado de `.env.example`, la pone en `False` (O-7). No hay ningún otro aviso.
- El `CORS_ALLOW_ALL_ORIGINS` de desarrollo es poco peligroso: la API se autentica por cabecera, no por cookies, así que otra página no puede usar la sesión del usuario. *(Actualización 2026-11-01, D-19: ya no existe; CORS solo acepta `CORS_ALLOWED_ORIGINS` también en desarrollo, y `config/origenes.py` responde 403 a los demás orígenes.)*

### O-6. Sin política de seguridad de contenido (CSP) ni cabeceras para el frontend; un ajuste obsoleto (Media, deducido)

- **Dónde:**
  - el frontend (Vite en desarrollo, el servidor web en producción): no hay `Content-Security-Policy`, `Referrer-Policy` ni `Permissions-Policy`;
  - `backend/config/settings.py:165`: `SECURE_BROWSER_XSS_FILTER`.
- **Qué pasa:**
  - Los tokens están en `localStorage` (O-19), así que cualquier XSS en el dominio de la app los puede robar. Una CSP estricta (`script-src 'self'`) es la defensa que bloquearía ese script.
  - `SECURE_BROWSER_XSS_FILTER` se eliminó en Django 4.0 y ya no hace nada: da una falsa sensación de protección.
- **Corrección propuesta:**
  - documentar en el README la configuración del servidor web con estas cabeceras: `Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'`, `Referrer-Policy: same-origin` y `X-Content-Type-Options: nosniff`, también en `/media/`. React no necesita `unsafe-inline` para los scripts;
  - quitar `SECURE_BROWSER_XSS_FILTER`.
  - La CSP también reduce el riesgo de O-13.

### O-7. `.env.example` desactiva la redirección a HTTPS y su `SECRET_KEY` de ejemplo se acepta (Baja, `check --deploy`)

- **Dónde:** `backend/.env.example:6` (`SECRET_KEY=django-insecure-change-this-secret-key-in-production`) y `:22` (`SECURE_SSL_REDIRECT=False`); `backend/config/settings.py:171`.
- **Qué pasa:**
  - Si alguien copia `.env.example` en el servidor y solo cambia `DEBUG`, la app arranca con una clave **pública**. Con ella se pueden falsificar tokens JWT de cualquier usuario. `check --deploy` lo avisa (W009), pero la app arranca igual.
  - El mismo archivo deja `SECURE_SSL_REDIRECT=False`.
  - Además, falta `SECURE_PROXY_SSL_HEADER`. Detrás de un proxy que termina HTTPS (por ejemplo, Nginx), Django cree que la petición llegó por HTTP. Con la redirección activada, eso produce un bucle de redirecciones, y la tentación es desactivarla.
- **Corrección propuesta:**
  - en `settings.py`, con `DEBUG=False`, negarse a arrancar si la clave empieza por `django-insecure-` o tiene menos de 50 caracteres, con un mensaje como el de C-3;
  - en `.env.example`, dejar la clave vacía o con un comentario, y explicar `SECURE_SSL_REDIRECT`;
  - `SECURE_PROXY_SSL_HEADER` configurable desde `.env` y documentado.

### O-8. Nombre o documento del paciente en la dirección (`?q=`) (Baja, ya conocido)

- **Dónde:** `GET /api/pacientes/?q=` y `GET /api/informes/?q=`.
- **Estado:** el usuario lo aprobó en la etapa 3 con una condición: que en producción los registros del servidor web no guarden esos parámetros o se protejan como datos sensibles. Está en el README ("Seguridad") y en "Pendientes" de `docs/progreso.md`.
- **Corrección propuesta:** ninguna en el código por ahora. Si se quiere eliminar el riesgo, la búsqueda podría pasar a `POST` (cambia la API y el frontend).

---

## A03: Fallos en la cadena de suministro de software

### Qué aplica a PathoLab

Las dependencias de npm (raíz y frontend) y de Python, la forma de fijar sus versiones y las versiones con soporte.

### Resultado de los análisis (2026-10-11)

| Dónde | Herramienta | Resultado |
|---|---|---|
| Raíz (`package-lock.json`) | `npm audit` | **0** vulnerabilidades. `shell-quote` y `concurrently` ya se corrigieron el 2026-10-08 (`npm-audit-fix`) |
| Frontend (`frontend/package-lock.json`) | `npm audit` | **2 moderadas**, las de `react-router` 6.30.6 (I-9c, ver O-11). `source-map-js` ya se corrigió el 2026-10-08 |
| Backend, lo que resuelve hoy `requirements.txt` | `pip-audit -r` | **8** avisos, todos de Django 4.2.30 (ver O-9) |
| Backend, lo instalado en el venv | `pip-audit` sobre `pip freeze` | Los mismos 8 de Django. Aparte, `pip` 24.0 (6 avisos) y `setuptools` 65.5.0 (4), que son herramientas de instalación (O-10) |

**Paquetes de Python instalados:** Django 4.2.30, djangorestframework 3.17.2, djangorestframework-simplejwt 5.5.1, PyJWT 2.15.0, django-cors-headers 4.9.0, Pillow 12.3.0, reportlab 5.0.1, psycopg2-binary 2.9.13, python-decouple 3.8, asgiref 3.12.1, sqlparse 0.6.0, tzdata 2026.4, ruff 0.16.10 (solo desarrollo). Python 3.11.9.

### Los 8 avisos de Django 4.2.30: ¿afectan a PathoLab?

Todos se corrigen en 5.2.15–5.2.17 o 6.0.6–6.0.8. Los avisos dicen que las series sin soporte, como la 4.2, **no se evaluaron**.

| Aviso | Qué afecta | ¿Afecta a PathoLab? |
|---|---|---|
| PYSEC-2026-198 | `has_vary_header()` con espacios: lectura de respuestas en caché | No: no hay caché de respuestas (`UpdateCacheMiddleware` ni `cache_page`) |
| PYSEC-2026-199 | `get_signed_cookie()`: sal no inyectiva | No: no se usan cookies firmadas |
| PYSEC-2026-201 | `UpdateCacheMiddleware` y `Cache-Control` con mayúsculas | No: no hay caché de respuestas |
| PYSEC-2026-2090 | `UpdateCacheMiddleware` y `cache_page()` con cookies | No: no hay caché de respuestas |
| PYSEC-2026-2091 | `GDALRaster` (GeoDjango) | No: no se usa GeoDjango |
| PYSEC-2026-2092 | `DomainNameValidator` con saltos de línea | No: no se usa ese validador |
| PYSEC-2026-3717 | `GEOSGeometry` (GeoDjango) | No: no se usa GeoDjango |
| PYSEC-2026-4035 | Búsquedas espaciales (GeoDjango) | No: no se usa GeoDjango |

### O-9. Django 4.2 ya no tiene soporte (Alta, `pip-audit`)

- **Dónde:** `backend/requirements.txt:1` (`Django>=4.2,<5.0`).
- **Qué pasa:**
  - El soporte de seguridad de Django 4.2 LTS terminó en abril de 2026. La versión instalada (4.2.30) ya no recibe parches.
  - Los 8 avisos de la tabla anterior no afectan hoy a PathoLab, pero muestran el problema: los fallos nuevos ya no se corrigen ni se evalúan para 4.2.
- **Por qué importa:** la app guarda datos de salud. Una vulnerabilidad nueva en el ORM, en `/admin/` o en la subida de archivos se quedaría sin parche.
- **Corrección propuesta:**
  - pasar a **Django 5.2 LTS** (con soporte hasta abril de 2028) en una rama propia;
  - revisar las notas de las versiones 5.0, 5.1 y 5.2, la compatibilidad de DRF, SimpleJWT y django-cors-headers (las versiones instaladas ya son compatibles con 5.2), y pasar todas las pruebas.
  - 6.0 no es LTS y obligaría a cambiar de versión otra vez pronto.

### O-10. Dependencias de Python sin versiones fijas ni archivo de bloqueo (Media, `pip-audit`)

- **Dónde:** `backend/requirements.txt` (todas las líneas tienen rangos, como `djangorestframework>=3.14`) y el venv (`pip` 24.0, `setuptools` 65.5.0).
- **Qué pasa:**
  - Dos instalaciones en fechas distintas pueden traer versiones distintas. Una versión nueva rota o comprometida de una dependencia, o de una dependencia de una dependencia, entraría sin aviso.
  - No hay *hashes* que comprueben que cada paquete descargado es el esperado.
  - Del lado de npm sí hay `package-lock.json` con *hashes* de integridad, así que la diferencia está solo en Python.
  - `pip` 24.0 y `setuptools` 65.5.0 tienen avisos conocidos de instalación de paquetes (por ejemplo, el manejo de archivos `tar`). Solo afectan al instalar paquetes, no a la app en marcha.
- **Corrección propuesta:**
  - `requirements.in` con las dependencias directas y `requirements.txt` generado con `pip-compile --generate-hashes` (pip-tools), con versiones exactas y *hashes*. Instalar con `pip install --require-hashes -r requirements.txt`;
  - agregar `pip-audit` a `requirements-dev.txt` y, si el usuario quiere, una comprobación en `npm run check` o un comando aparte (`npm run audit`) que ejecute `npm audit` y `pip-audit`;
  - actualizar `pip` en el venv (README: `python -m pip install --upgrade pip` al crearlo).

### O-11. I-9c: 2 avisos moderados de `react-router` 6 (Baja, `npm audit`)

- **Dónde:** `frontend/package.json` (`react-router-dom` 6.30.6). Solo se corrigen en React Router 7.
- **Nueva comprobación** (lo pedía el plan, porque desde D-13 `App.jsx` usa `createBrowserRouter`):
  - **GHSA-337j-9hxr-rhxg** (inyección de constructor en `deserializeErrors()`): solo se ejecuta al **hidratar** datos que vienen del servidor, `window.__staticRouterHydrationData` o la opción `hydrationData`, que se usan con renderizado en el servidor (SSR). `App.jsx:187` llama a `createBrowserRouter(rutas)` sin `hydrationData`, y PathoLab no tiene SSR. **No afecta.** La conclusión de I-9a sigue siendo válida, aunque el motivo ya no es "usa `BrowserRouter`", sino "no hidrata datos del servidor".
  - **GHSA-wrjc-x8rr-h8h6** (redirección abierta con una barra invertida en `<Link>` y `useNavigate`): solo afecta si la ruta de destino sale de un dato que controla el usuario. Todos los `navigate()` y `<Link>` de `src/` van a rutas fijas (`/`, `/foro`, `/salir`) o con un `id` numérico que devuelve la API. Por ejemplo, el login no redirige a una dirección que venga en la URL. **No afecta.**
- **Corrección propuesta:** pasar a React Router 7 cuando convenga, por ejemplo junto con el rediseño de las fases 5 a 7. Es un cambio con riesgo, porque D-13 depende de `useBlocker`. Mientras tanto, no usar destinos que vengan de la URL o del usuario. Se corrige la frase de `CHANGELOG.md` (I-9a) con una entrada nueva que remita aquí, sin reescribir la antigua.

---

## A04: Fallos criptográficos

### Qué aplica a PathoLab

Los JWT (firma, duración y rotación), `SECRET_KEY`, HTTPS y el almacenamiento de contraseñas.

### Qué ya está protegido

- **JWT:** HS256 firmado con `SECRET_KEY`, que es obligatoria (C-3). La renovación rota el token y la lista negra (`token_blacklist`) invalida el anterior (D-6). Cerrar sesión y cambiar la contraseña invalidan los tokens de renovación.
- **Contraseñas:** se guardan con el PBKDF2 de Django (también las creadas en `/admin/`, desde el arreglo del 2026-10-05) y pasan por los validadores (I-11).
- **HTTPS:** con `DEBUG=False`, redirección, cookies seguras y HSTS (ver A02). El token viaja siempre en la cabecera, nunca en la URL (I-5).
- No hay más secretos en el código: las contraseñas de `seed_data` son de prueba y están documentadas.

La duración del token de acceso (8 horas) y su lugar en `localStorage` se tratan en A07 (O-19), porque son un problema de sesión más que de criptografía. La clave de ejemplo de `.env.example` está en O-7.

### O-12. Clave antigua en el historial de git (Baja, ya conocido)

- **Dónde:** el historial de `backend/config/settings.py` hasta el commit `455cff0` (C-3), que tenía `default='django-insecure-patologia-dev-key-change-in-production-!@#$%'`.
- **Qué pasa:** el repositorio es público. Cualquier instalación que haya funcionado sin `.env` usó esa clave, y con ella se pueden falsificar tokens JWT y sesiones de `/admin/` de esa instalación.
- **Corrección propuesta:** no hay nada que cambiar en el código. Basta con lo que ya dice "Pendientes" de `docs/progreso.md` (producción): no reutilizarla y cambiarla en cualquier servidor que la haya usado. Reescribir el historial de git no sirve, porque la clave ya es pública.

---

## A05: Inyección

### Qué aplica a PathoLab

Las consultas a la base de datos, el PDF (ReportLab interpreta etiquetas), el HTML de React, los nombres de archivo y la subida de imágenes.

### Qué ya está protegido

- **SQL:** todo pasa por el ORM. No hay `raw()`, `extra()`, `cursor()` ni `RawSQL` en el código (búsqueda en `backend/`, sin migraciones ni venv). Los filtros `?q=` usan `icontains` con parámetros.
- **PDF (I-3):** todo el texto del usuario pasa por `texto_seguro()` (`informes/utils.py:30`), también el encabezado del `.env`, la firma, las adendas y los diagnósticos.
- **Cabecera del PDF (I-5):** el nombre del archivo se limpia con una expresión regular y nunca lleva datos del paciente.
- **React:** no hay `dangerouslySetInnerHTML`, `innerHTML` ni `eval`, y no hay enlaces `href` armados con datos del usuario. React escapa todo el texto.
- **`/admin/`:** no se usan `mark_safe` ni `format_html` con datos del usuario.
- **Imágenes (I-6):** se comprueban el tamaño y que Pillow las pueda abrir. **Pero ver O-13.**

### O-13. Subida de imágenes: se acepta un `.html` que también es una imagen válida (Alta, comprobado)

- **Dónde:** `backend/foro/views.py:104-125` (`subir_imagenes`) y `backend/foro/models.py:5-6`.
- **Qué pasa:**
  - `forms.ImageField().to_python(archivo)` comprueba que Pillow pueda abrir el contenido, pero **no** revisa la extensión: ese validador (`validate_image_file_extension`) solo se ejecuta en `clean()`.
  - `ImagenPublicacion.objects.create()` tampoco valida el modelo.
  - Resultado: el archivo se guarda con el nombre y la extensión que mandó el usuario.
- **Cómo se reproduce (comprobado):**
  1. Se arma un PNG válido de 2×2 píxeles y se le agrega al final `<html><script>alert(document.domain)</script></html>`.
  2. Se sube con el nombre `ataque.html`.
  3. La respuesta es **201** con `"imagen": "http://testserver/media/foro/publicaciones/1/ataque.html"`.
- **Por qué importa:**
  - El servidor (Django en desarrollo, Nginx en producción) entrega ese archivo como `text/html`, porque decide el tipo por la extensión. El navegador ejecuta el script.
  - Si `/media/` se sirve en el **mismo dominio** que el frontend, como propone el README cuando `VITE_API_URL` está vacía, el script se ejecuta con el origen de la app. Puede leer `access_token` y `refresh_token` de `localStorage` (O-19) y actuar como la víctima.
  - Basta con que un patólogo o un admin abra el enlace de la imagen. El atacante puede ser cualquier patólogo.
- **Corrección propuesta:**
  1. Aceptar solo `.jpg`, `.jpeg`, `.png`, `.gif` y `.webp`, comprobando a la vez la extensión y el formato que detecta Pillow (`Image.format`).
  2. Guardar con un nombre nuevo, un UUID con la extensión del formato real, sin usar el nombre original (también ayuda con O-5).
  3. Volver a codificar la imagen con Pillow al guardarla: elimina cualquier contenido agregado y los metadatos EXIF (O-5).
  4. En producción, servir `/media/` con `X-Content-Type-Options: nosniff` y `Content-Security-Policy: sandbox` (O-6).
  - Pruebas: un `.html`, un `.svg` y un PNG con contenido extra se rechazan o se limpian, y una imagen normal sigue funcionando.

---

## A06: Diseño inseguro

### Qué aplica a PathoLab

Los límites de peticiones, el tratamiento de datos sensibles (Ley 1581), la edición concurrente y el volumen de datos que se puede sacar.

### Qué ya está protegido

- **Datos mínimos:** solo se guardan los datos del paciente que aparecen en el informe (sin dirección, teléfono ni correo), los ejemplos son siempre ficticios y hay una política de privacidad.
- **D-13:** no se guarda ninguna copia del informe en el navegador.
- **D-7:** número de petición sin repetir aunque dos usuarios creen informes a la vez (contador con `UPDATE` atómico y prueba de concurrencia).
- **D-9, D-10, D-15:** un finalizado se corrige con adendas y conserva los datos con que se imprimió.
- **Límites de peticiones globales** (`anon` y `user`) y del foro. **Pero los de login y registro no funcionan: ver O-16.**

### O-14. Edición concurrente: gana el último guardado, y un `PUT` puede colarse al finalizar (Media, deducido)

- **Dónde:** `backend/informes/views.py:178-181` (`update`) y `:294-321` (`finalizar`).
- **Qué pasa:**
  1. **Último guardado gana** (anotado por el usuario el 2026-10-05). Si el mismo informe está abierto en dos pestañas o equipos, el segundo guardado borra los cambios del primero sin aviso. Con el autoguardado de D-13 es más probable.
  2. **Carrera al finalizar.** `update()` comprueba que el informe no esté finalizado **antes** y **fuera** de la transacción en la que guarda. Si un `PUT` (por ejemplo, el autoguardado de otra pestaña) y `finalizar` llegan casi a la vez, el `PUT` puede guardar después de que `finalizar` congeló los datos. Quedaría un finalizado con contenido distinto del que se revisó al finalizar. `finalizar` sí bloquea la fila, pero `update` no la bloquea.
- **Corrección propuesta:**
  - **Conflicto:** el frontend envía la `fecha_actualizacion` que cargó (o una cabecera `If-Unmodified-Since` o `If-Match`). El backend responde **409** si no coincide con la guardada, y `InformePage` avisa y ofrece recargar. Es la propuesta ya anotada en `docs/progreso.md`.
  - **Carrera:** en `update`, dentro de `transaction.atomic()`, volver a leer el informe con `select_for_update()` y comprobar ahí que siga en borrador.
  - Pruebas: dos `PUT` con la misma versión (el segundo responde 409) y un `PUT` sobre un informe que pasó a finalizado.

### O-15. Extracción masiva con `?page_size=1000` (Baja, deducido)

- **Dónde:** `backend/config/paginacion.py` (`max_page_size = 1000`), en todos los listados, también `/api/pacientes/`.
- **Qué pasa:** cualquier usuario autenticado, también el auditor, puede bajar 1000 pacientes o informes por petición. Con el límite de 120 peticiones por minuto, se saca toda la base en segundos.
- **Por qué es baja:** todos los roles ya tienen permiso para ver esos datos (D-11), así que no es un acceso indebido. El riesgo real es una cuenta robada (O-16, O-19), y lo que más ayuda ahí es poder detectarlo (O-20).
- **Corrección propuesta:** dejar el `page_size` grande solo en los catálogos (EPS, servicios, patologías, categorías), que lo necesitan para los menús desplegables. En pacientes e informes, como mucho 100. Y registrar los listados en O-20.

---

## A07: Fallos de identificación y autenticación

### Qué aplica a PathoLab

El login (`/api/auth/login/`), la renovación y el cierre de sesión, el login de `/admin/`, las contraseñas y el lugar donde se guardan los tokens.

### Qué ya está protegido

- **Contraseñas (I-11):** el registro y el cambio de contraseña aplican los 4 validadores de Django.
- **Sesión (D-6):** cerrar sesión, cambiar la contraseña y renovar invalidan el token de renovación anterior.
- **Sin enumeración de usuarios:** el login responde lo mismo si el usuario no existe o si la contraseña es incorrecta (mensaje de SimpleJWT).
- **Registro:** solo lo puede usar un admin (`EsAdmin`).
- **`is_active`:** un usuario con `is_active=False` no entra ni usa tokens vigentes, porque SimpleJWT lo comprueba. **Pero ver O-2:** el campo que muestra la app es `activo`.

### O-16. El login y el registro no tienen límite de intentos (Alta, comprobado)

> **Estado: corregido el 2026-10-11** (fase 4, grupo 2). `CustomTokenView` y `RegistroView` definen `throttle_scope` y conservan el límite global; se borró `accounts/throttles.py`. Prueba: `LimitesLoginTests`.

- **Dónde:** `backend/accounts/views.py:33-42` (`CustomTokenView` y `RegistroView`) y `backend/accounts/throttles.py`.
- **Qué pasa:**
  - `LoginRateThrottle` y `RegistroRateThrottle` heredan de `ScopedRateThrottle` y definen `scope = 'login'`. Pero `ScopedRateThrottle.allow_request()` **sobrescribe** `self.scope` con el atributo `throttle_scope` de la **vista** (`rest_framework/throttling.py`, `scope_attr = 'throttle_scope'`). Si la vista no lo tiene, deja pasar todas las peticiones.
  - Ni `CustomTokenView` ni `RegistroView` definen `throttle_scope`.
  - Además, `throttle_classes = [...]` **reemplaza** los límites globales, así que el login tampoco tiene el de 30/min para anónimos.
  - Resultado: el login no tiene ningún límite.
  - El foro sí funciona, porque `get_throttles()` asigna `self.throttle_scope`.
- **Cómo se reproduce (comprobado):** con una caché real conectada al throttle (las pruebas del proyecto usan `DummyCache`, que no cuenta nada), 12 intentos fallidos seguidos desde la misma IP responden **12 veces 401** y ninguna 429.
- **Por qué no lo detectaron las pruebas:** `config/test_runner.py` desactiva la caché para que los límites no se acumulen entre pruebas. Ninguna prueba comprueba que el límite de login funcione.
- **Por qué importa:**
  - permite probar contraseñas sin límite contra cualquier usuario, también los admin;
  - el README (sección "Seguridad") dice "Login 10/min" y "Registro 5/min", y no es cierto.
- **Corrección propuesta:**
  - en `CustomTokenView`, `throttle_scope = 'login'` y `throttle_classes = [AnonRateThrottle, ScopedRateThrottle]`. En `RegistroView`, lo mismo con `'registro'`. Así `accounts/throttles.py` sobra;
  - una prueba con la caché real (`override_settings` de `CACHES` o un `LocMemCache` en el throttle) que compruebe el 429 al intento 11.
  - Con O-17 y O-18.

### O-17. Los límites se saltan cambiando la cabecera `X-Forwarded-For` (Media, deducido del código de DRF)

> **Estado: corregido el 2026-10-11** (fase 4, grupo 2). `NUM_PROXIES` se lee de `backend/.env` y vale 0 por defecto. Pruebas: `LimitesLoginTests.test_cambiar_x_forwarded_for_no_reinicia_la_cuenta` y `NumProxiesTests`.

- **Dónde:** `REST_FRAMEWORK` en `backend/config/settings.py:122-142`, que no define `NUM_PROXIES`; `rest_framework/throttling.py`, `BaseThrottle.get_ident()`.
- **Qué pasa:** sin `NUM_PROXIES`, DRF identifica al cliente anónimo por la cabecera `X-Forwarded-For` completa, si existe, en lugar de por `REMOTE_ADDR`. El cliente puede poner cualquier valor en esa cabecera: con uno distinto en cada petición, cada intento cuenta como una "IP" nueva y nunca llega al límite.
- **Por qué importa:** cuando se corrija O-16, el atacante se lo podría saltar así. Afecta a todos los límites de anónimos, incluido el login.
- **Corrección propuesta:**
  - `NUM_PROXIES` configurable en `.env`: `0` si Django recibe las peticiones directamente, `1` detrás de un Nginx que agrega la IP real;
  - documentarlo en el README;
  - una prueba de que cambiar `X-Forwarded-For` no reinicia la cuenta con `NUM_PROXIES=0`.

### O-18. `/admin/` sin límite de intentos de login (Media, deducido)

- **Dónde:** `backend/config/urls.py:7`. Es el `admin.site` de Django en la ruta por defecto `/admin/`.
- **Qué pasa:** el formulario de login de `/admin/` no pasa por DRF, así que no lo cubre ningún límite (ni siquiera después de corregir O-16). Los usuarios con `is_staff` (como `admin`) tienen ahí acceso total, también a borrar pacientes y a O-3 y O-4.
- **Corrección propuesta** (elegir una o combinarlas):
  - **django-axes:** bloquea por usuario e IP después de N intentos fallidos y registra los intentos (ayuda con O-21);
  - en producción, limitar `/admin/` por IP o VPN en el servidor web;
  - cambiar la ruta (`ADMIN_URL` en `.env`). Por sí sola no protege, pero reduce los ataques automáticos.

### O-19. Tokens en `localStorage` y token de acceso de 8 horas (Media, deducido)

- **Dónde:**
  - `frontend/src/context/AuthContext.jsx:25-27`, `frontend/src/api/client.js` y `PerfilPage.jsx:73-74`: `access_token`, `refresh_token` y `user_data` en `localStorage`;
  - `backend/config/settings.py:147-154`: `ACCESS_TOKEN_LIFETIME = 8 horas` y `REFRESH_TOKEN_LIFETIME = 7 días`.
- **Qué pasa:**
  - Cualquier script que se ejecute en el origen de la app puede leer los dos tokens. Puede venir de un XSS como O-13 o de una dependencia comprometida (A03).
  - Con el de renovación, el atacante obtiene tokens nuevos durante 7 días. La rotación de D-6 no lo impide: el atacante también rota.
  - El token de acceso dura 8 horas y no se puede revocar: ni cerrar sesión ni cambiar la contraseña lo invalidan (es una limitación de JWT, ya aceptada en D-6).
  - `user_data` guarda nombre, correo, teléfono y registro médico del usuario. No son datos de pacientes, así que no contradice D-13.
- **Por qué es media y no alta:** hace falta primero un XSS. React escapa todo y no se encontró ninguno en el frontend; el único camino encontrado es O-13.
- **Corrección propuesta**, de menor a mayor esfuerzo:
  1. **Token de acceso más corto** (15 a 30 minutos). `client.js` ya lo renueva solo, así que el usuario no lo nota. Reduce el tiempo en que sirve un token robado y el desfase de D-6.
  2. **CSP (O-6)** y **corregir O-13**: quitan la forma de ejecutar el script.
  3. **El token de renovación en una cookie `HttpOnly; Secure; SameSite=Strict`** limitada a `/api/auth/`, y el de acceso solo en memoria. Es el cambio más seguro, pero toca el login, la renovación, el cierre de sesión, CORS y las pruebas, y necesita protección CSRF para esas rutas. Conviene evaluarlo aparte.
  - **Recomendación:** 1 y 2 en la fase 4; 3 como decisión del usuario.

**Otros puntos de A07, sin identificador:**
- No hay autenticación de dos factores. Es una idea futura razonable para el admin; no se propone ahora.
- El cambio de contraseña tiene solo el límite general (120/min) para probar la contraseña actual. Exige un token válido, así que el riesgo es bajo.

---

## A08: Fallos de integridad de software o datos

### Qué aplica a PathoLab

La integridad del informe clínico (número de petición, finalización, datos congelados, adendas) y la de las dependencias.

### Qué ya está protegido

- **D-7:** el número de petición es único, no se reutiliza y no se modifica (de solo lectura en la API y en `/admin/`; el contador es de solo lectura en `/admin/`). Prueba de concurrencia `NumeroPeticionConcurrenciaTests`.
- **D-3:** la API no deja editar ni borrar un finalizado.
- **D-9:** las adendas no se modifican ni se borran (sin `PUT`, `PATCH` ni `DELETE`, y de solo lectura en `/admin/`). `informe` y `autor` son `PROTECT`, y la firma se congela.
- **D-10, D-15:** `finalizar` congela el paciente, la EPS, el servicio, la firma y el encabezado en la misma transacción. `fecha_informe` y `datos_finalizacion` son `editable=False`.
- **Dependencias de npm:** `package-lock.json` con *hashes* de integridad en la raíz y en el frontend.

### Lo que falta (ya listado en otras categorías)

- **O-1** y **O-3:** se puede llegar a "finalizado" sin pasar por `finalizar`, y así se saltan D-8, D-10 y D-15.
- **O-4 (D-14):** `/admin/` deja cambiar o borrar un finalizado.
- **O-14:** último guardado gana, y un `PUT` puede colarse al finalizar.
- **O-10:** dependencias de Python sin versiones fijas ni *hashes*.

---

## A09: Fallos en el registro y las alertas de seguridad

### Qué aplica a PathoLab

Qué queda registrado cuando alguien consulta o cambia datos de pacientes e informes, cuando falla un login o cuando hay un error del servidor.

### Qué existe hoy

- **`/admin/`:** Django guarda en `LogEntry` quién creó, cambió o borró cada objeto y cuándo ("Historial" de cada ficha). Solo cubre lo que se hace en `/admin/`.
- **En el informe:**
  - `autor`, `fecha_creacion`, `fecha_actualizacion` y `fecha_informe`;
  - cada adenda guarda autor, fecha y firma.
  - No se sabe **quién** hizo la última modificación de un borrador (admin o autor), ni qué cambió.
- **Servidor de desarrollo:** `runserver` muestra cada petición en la consola, pero no es un registro: no se guarda en ningún archivo.

### O-20. No hay registro de accesos a pacientes, informes y PDF (Media, deducido)

- **Dónde:** toda la API. No existe ningún modelo ni middleware de auditoría.
- **Qué pasa:**
  - no queda constancia de quién consultó qué paciente o informe, quién descargó qué PDF, quién buscó qué (`?q=`) ni quién cambió qué dato de un paciente;
  - un acceso indebido con una cuenta válida, por ejemplo una cuenta robada (O-16, O-19) o una extracción masiva (O-15), no se puede detectar ni investigar después.
- **Por qué es media:** no es un ataque por sí mismo, pero en un sistema con datos de salud es **un requisito antes de un uso real**. La Ley 1581 de 2012 exige demostrar medidas de seguridad sobre datos sensibles, y la Resolución 1995 de 1999 trata la custodia de la historia clínica. Ya está en "Pendientes" de `docs/progreso.md` y en la hoja de ruta del README.
- **Corrección propuesta:**
  - un modelo `RegistroAcceso` (usuario, acción, tipo y `id` del objeto, fecha, IP, sin datos del paciente en el texto), que se agregue y no se pueda modificar ni borrar desde la app ni desde `/admin/`;
  - registrar: ver el detalle de un paciente o de un informe, descargar un PDF, buscar pacientes (sin guardar el texto buscado, o guardándolo como dato sensible), crear o editar pacientes e informes, finalizar, agregar una adenda y entrar o fallar el login;
  - una pantalla o un filtro en `/admin/` para el admin.
  - **El alcance lo decide el usuario:** qué acciones se registran, cuánto tiempo se guardan y si el auditor lo puede consultar.

### O-21. Sin `LOGGING`: con `DEBUG=False`, los errores 500 y los intentos fallidos no se registran (Media, deducido)

- **Dónde:** `backend/config/settings.py`. No hay `LOGGING` ni `ADMINS`.
- **Qué pasa:**
  - Con la configuración por defecto de Django, los errores de `django.request` solo van a la consola si `DEBUG=True`, y con `DEBUG=False` van a `mail_admins`. Como `ADMINS` está vacío, **no van a ningún lado**.
  - En producción, un 500 como los de O-22 y O-23 no deja rastro.
  - Tampoco se registran los logins fallidos: SimpleJWT usa `authenticate()`, que emite la señal `user_login_failed`, pero nadie la escucha.
- **Corrección propuesta:**
  - `LOGGING` con un manejador a consola (lo recoge el servidor o el contenedor), con nivel configurable desde `.env`;
  - un receptor de `user_login_failed` y `user_logged_in` que registre usuario e IP, sin la contraseña, como base para alertas (muchos fallos seguidos);
  - cuidar que los registros nunca guarden datos de pacientes ni tokens.

---

## A10: Mal manejo de condiciones excepcionales

### Qué aplica a PathoLab

Las respuestas a datos inesperados, los errores 500, lo que revelan los mensajes de error y si una operación que falla deja datos a medias.

### Qué ya está protegido

- Con `DEBUG=False`, un 500 muestra la página genérica de Django, sin detalles internos.
- Borrar algo en uso (patología, EPS, servicio, paciente) responde 400 con un mensaje claro en lugar de un 500 (I-1).
- Los mensajes de validación están en español y no revelan detalles internos.
- El informe y sus diagnósticos se guardan en la misma transacción (`InformeSerializer.create` y `update`).
- `finalizar` y las adendas usan transacciones y bloqueo de la fila.

### O-22. Filtros con valores no válidos responden 500 (Media, comprobado)

- **Dónde:**
  - `backend/informes/views.py:62-64` (`?categoria=`), `:99-101` (`?patologia=` en plantillas) y `:216-234` (`?fecha_desde=`, `?fecha_hasta=`, `?patologia=`, `?paciente=` en informes y estadísticas);
  - `backend/foro/views.py:75-77` (`?tema=`) y `:162-164` (`?publicacion=`).
  - Los valores pasan sin validar a `filter()`, y el ORM lanza `ValueError` o `ValidationError`.
- **Cómo se reproduce (comprobado):** todas estas peticiones responden **500**:
  - `/api/informes/?fecha_desde=abc`
  - `/api/informes/?patologia=abc`
  - `/api/informes/?paciente=abc`
  - `/api/informes/estadisticas/?fecha_hasta=2026-13-45`
  - `/api/patologias/?categoria=abc`
  - `/api/plantillas/?patologia=abc`
  - `/api/foro/publicaciones/?tema=abc`
  - `/api/foro/comentarios/?publicacion=abc`
- **Por qué importa:**
  - no hay fuga de datos, pero un error del cliente aparece como error del servidor;
  - sin registro (O-21) no se distingue un ataque de un fallo real;
  - cualquier usuario autenticado, también el auditor, puede generar errores 500 a voluntad.
- **Corrección propuesta:**
  - una función común en `config/` que lea un parámetro entero o de fecha y responda **400** con un mensaje en español si no es válido;
  - usarla en todos esos filtros (o pasar a `django-filter`, que valida los tipos, si el usuario prefiere agregar la dependencia);
  - una prueba por filtro.

### O-23. `datos_ingresados` que no es un objeto: 500, y el informe queda guardado a medias (Media, comprobado)

- **Dónde:**
  - `backend/informes/serializers.py:299-319` (`_validar_campos_obligatorios`), que usa `datos.get(...)`;
  - `backend/informes/views.py:238-250` (`perform_create` y `perform_update`), que guardan el informe y **después** generan `texto_generado` fuera de una transacción;
  - `backend/informes/utils.py` (`generar_descripcion_macroscopica`).
- **Qué pasa:** `datos_ingresados` es un `JSONField` que acepta cualquier JSON (lista, número, texto), pero el código supone un objeto.
  - Si la patología tiene campos obligatorios, la validación falla con `AttributeError`: es un 500, aunque no guarda nada.
  - Si no los tiene, el informe **se guarda**, gasta un número de petición (D-7) y luego falla al generar la descripción: es un 500 y queda un informe con datos no válidos.
- **Cómo se reproduce (comprobado):** `POST /api/informes/` con `"datos_ingresados": [1, 2]` responde **500**, y en la base queda el informe `P-2026-00001` con `datos_ingresados = [1, 2]`.
- **Corrección propuesta:**
  - `validate_datos_ingresados` en `InformeSerializer`: debe ser un objeto, cada valor un texto, número, booleano o nulo, y con un tamaño máximo razonable;
  - generar `texto_generado` dentro de la misma transacción del guardado, en `create` y `update` del serializer, en lugar de `perform_create` y `perform_update`. Así, si algo falla, no queda nada guardado;
  - pruebas: una lista, un número y un objeto con valores anidados responden 400, y no se crea ningún informe.

**Otro punto de A10, sin identificador:** los campos de texto largo (microscópica, comentarios, diagnósticos, adendas, foro) no tienen tamaño máximo. El límite real es el cuerpo de la petición (10 MB, `DATA_UPLOAD_MAX_MEMORY_SIZE`). Un PDF con 10 MB de texto tardaría mucho en generarse. El riesgo es bajo, porque solo lo puede hacer un usuario con permiso de escritura sobre su propio informe. Se puede revisar junto con O-23 si el usuario quiere.

---

## Propuesta de orden para la fase 4

La decide el usuario. Esta es una propuesta, de lo más urgente y pequeño a lo más grande:

| Grupo | Hallazgos | Por qué juntos |
|---|---|---|
| 1. Integridad del informe | O-1, O-3, O-4 (D-14) | Todos tratan de cómo un informe llega a finalizado y de que no cambie después. Los tres son cambios pequeños en `serializers.py` y `admin.py`, con pruebas |
| 2. Login | O-16, O-17 y, si se elige, O-18 | La misma zona (`accounts/views.py`, `settings.py`). Hay que corregir también el README |
| 3. Imágenes del foro | O-13 y los puntos 1 y 2 de O-5 | El mismo código (`subir_imagenes`, `ruta_imagen_publicacion`) |
| 4. Django 5.2 LTS | O-9 y O-10 | Conviene hacerlo en una rama propia, con todas las pruebas, y fijar las versiones de una vez |
| 5. Errores y registros | O-22, O-23, O-21 | Respuestas 400 en lugar de 500, y que los errores que queden se registren |
| 6. Cuentas y sesiones | O-2, O-19 (puntos 1 y 2), O-6, O-7 | Dependen de decisiones: `activo` frente a `is_active`, la duración de los tokens y la CSP |
| 7. Concurrencia | O-14 | Toca el backend y `InformePage` (aviso de conflicto) |
| 8. Antes de producción | O-20, O-15, O-5 (punto 3), O-18 (servidor web), O-8, O-11, O-12, O-19 (punto 3) | Requieren definir el despliegue o son cambios grandes; algunos pueden quedar anotados con su motivo |

---

## Preguntas para el usuario

1. **¿Qué hallazgos se corrigen en la fase 4, y en qué orden?** La tabla anterior es una propuesta. ¿Una rama por grupo o una sola?
2. **O-2:** ¿opción A (usar solo `is_active`, recomendada) u opción B (mantener `activo` y sincronizarlo)?
3. **O-19:** ¿se acorta el token de acceso (por ejemplo, a 15 o 30 minutos)? ¿Se estudia pasar el token de renovación a una cookie `HttpOnly`?
4. **O-20:** ¿qué acciones se registran, cuánto tiempo se guardan y quién puede consultar el registro (solo el admin o también el auditor)?
5. **O-18:** ¿se agrega `django-axes` (una dependencia nueva) o basta con limitar `/admin/` en el servidor web al publicar?
6. **Borradores (observación de A01):** hoy el auditor y los demás patólogos leen por la API el contenido de los borradores ajenos (D-2), aunque no pueden descargar su PDF (D-12). ¿Se mantiene así o se restringe como el PDF? Si cambia, sería una decisión nueva.

---

## Respuestas del usuario (2026-10-11)

1. **Fase 4:** una rama por grupo de la tabla "Propuesta de orden para la fase 4".
   - **2026-10-11 y 2026-10-12**, en este orden: grupo 1 (O-1, O-3, O-4), grupo 2 (O-16, O-17), grupo 3 (O-13 y los puntos 1 y 2 de O-5) y grupo 5 (O-22, O-23, O-21).
   - **Desde el martes 2026-10-13:** una fase nueva de pruebas con Cypress, que el usuario presenta el viernes 2026-10-16. Empieza ese día aunque la fase 4 no haya terminado.
   - **Después del 2026-10-16:** los grupos 4, 6 y 7.
   - **Antes de producción:** el grupo 8.
2. **O-2:** opción A, usar solo `is_active` (grupo 6).
3. **O-19:** token de acceso de **30 minutos**, en el grupo 6. Pasar el token de renovación a una cookie `HttpOnly` queda como estudio antes de producción (grupo 8).
4. **O-20:** queda para antes de producción (grupo 8). Cuando se llegue, hay que presentar una propuesta concreta: qué se registra, cuánto tiempo se guarda y quién lo consulta.
5. **O-18:** por ahora, restringir `/admin/` en el servidor web al publicar (grupo 8). `django-axes` se reconsidera entonces.
6. **Borradores ajenos:** se mantiene como está (D-2). Queda como pregunta para consultar con el patólogo y el profesor (ver "Pendientes" de `docs/progreso.md`).

### Estado de los hallazgos

| Hallazgo | Estado |
|---|---|
| O-1, O-3, O-4 | **Corregidos el 2026-10-11** (fase 4, grupo 1, rama `fase-4-integridad-informe`). Pruebas: `EstadoSoloLecturaTests` (3) y `AdminInformeFinalizadoTests` (13) |
| O-16, O-17 | **Corregidos el 2026-10-11** (fase 4, grupo 2, rama `fase-4-limites-login`). Pruebas: `LimitesLoginTests` (4) y `NumProxiesTests` (2) |
| O-13 (puntos 1 a 3), O-5 (puntos 1 y 2) | **Corregidos el 2026-10-12** (fase 4, grupo 3, rama `fase-4-imagenes-foro`). Pruebas: `SeguridadImagenesForoTests` (11) y `AdminImagenesForoTests` (3) en el backend, y 2 en `ForoPage.test.jsx`. También cubre `/admin/`. El punto 4 de O-13 (cabeceras de `/media/`) va con O-6 en el grupo 6, y el punto 3 de O-5, en el grupo 8 |
| O-22, O-23, O-21 | **Corregidos el 2026-10-12** (fase 4, grupo 5, rama `fase-4-errores-registros`), junto con `/admin/` y `datos_ingresados = {}`. Pruebas: `FiltrosNoValidosTests` (2), `DatosIngresadosTests` (6) y `AdminDatosIngresadosTests` (2) en `informes`, `FiltrosNoValidosForoTests` (2), `RegistroDeAccesosTests` (4) y `RegistrosTests` (3). El tamaño máximo de los textos largos (otro punto de A10) queda para el grupo 8, por decisión del usuario |
| O-9, O-10 | Fase 4, grupo 4 (después del 2026-10-16) |
| O-2 (opción A), O-19 (punto 1: 30 minutos), O-6, O-7 | Fase 4, grupo 6 (después del 2026-10-16) |
| O-14 | Fase 4, grupo 7 (después del 2026-10-16) |
| O-20, O-15, O-5 (punto 3), O-18 (servidor web), O-8, O-11, O-12, O-19 (punto 3: cookie `HttpOnly`), tamaño máximo de los textos largos (A10) | Antes de producción (grupo 8) |

Al corregir cada hallazgo, se anota aquí su fecha y su commit.

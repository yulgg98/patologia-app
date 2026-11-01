# CORS y documentación Swagger de la API

Decisión D-19 (2026-11-01). Esta guía explica qué hace cada parte y cómo mostrarla en una revisión.

## 1. Qué es CORS

Un navegador no deja que una página de un origen (esquema, dominio y puerto, por ejemplo `https://sitio-ajeno.example`) lea las respuestas de una API de otro origen (`http://localhost:8000`), salvo que la API lo autorice con la cabecera `Access-Control-Allow-Origin`. Antes de una petición «no simple» (un `POST` con JSON, una con `Authorization`), el navegador hace primero una **consulta previa** (`OPTIONS`, *preflight*) para preguntar si el origen tiene permiso.

CORS lo aplica el navegador: Postman, `curl` u otro servidor no lo respetan. Por eso no reemplaza la autenticación; en PathoLab, la API sigue pidiendo el token JWT.

## 2. Cómo está protegida la API de PathoLab

1. **Lista de orígenes permitidos** (`CORS_ALLOWED_ORIGINS` en `backend/.env`). Por defecto, solo el frontend de desarrollo: `http://localhost:5173` y `http://127.0.0.1:5173`. Rige **también con `DEBUG=True`**: antes, en desarrollo se permitía cualquier origen (`CORS_ALLOW_ALL_ORIGINS = DEBUG`), y eso ya no existe.
2. **CORS** (`django-cors-headers`): solo los orígenes de la lista reciben `Access-Control-Allow-Origin`.
3. **Bloqueo con 403** (`backend/config/origenes.py`, `OrigenPermitidoMiddleware`): si una petición a `/api/` trae una cabecera `Origin` que no es la del propio servidor ni una de la lista, la API responde **403** con `{"detail": "Origen no permitido: …"}` sin ejecutar la vista. Va antes que el middleware de CORS. Con CORS solo, la petición llegaba a la API y se procesaba; el navegador escondía la respuesta. Con el 403, no se procesa.

Qué pasa en cada caso:

| Petición | Resultado |
|---|---|
| Desde el frontend (`localhost:5173`) | Funciona normal |
| Desde la página de Swagger (`localhost:8000/api/docs/`, el mismo origen de la API) | Funciona normal |
| Desde otra página web (otro origen) | 403 y el navegador muestra «blocked by CORS policy» |
| Sin cabecera `Origin` (Postman, `curl`) | Pasa al siguiente control: sin token, 401 |

El frontend no se afecta: en desarrollo, Vite reenvía `/api/` al backend con su proxy (`frontend/vite.config.js`). `npm run e2e` le pasa a su backend el origen de su propio frontend (puerto 5174).

En producción, `CORS_ALLOWED_ORIGINS` debe tener la dirección real del frontend (por ejemplo, `https://patolab.example`). No se usa `*`.

## 3. Documentación Swagger

Con `drf-spectacular` (y `drf-spectacular-sidecar`, que sirve los archivos de Swagger UI desde Django, sin internet):

- **`http://localhost:8000/api/docs/`**: la página de Swagger, con todos los endpoints agrupados (auth, informes, pacientes, foro…), sus parámetros y sus respuestas.
- **`http://localhost:8000/api/schema/`**: el esquema OpenAPI 3 (YAML; `?format=json` para JSON). Se puede importar en Postman.

La documentación se ve sin iniciar sesión, pero los endpoints siguen pidiendo el token. Para probarlos desde Swagger:

1. Abrir `POST /api/auth/login/` → **Try it out**, escribir `{"username": "patologo1", "password": "patologo1234"}` y **Execute**.
2. Copiar el valor de `access` de la respuesta.
3. Pulsar **Authorize** (arriba a la derecha), pegar el token y **Authorize**. Desde ahí, cualquier endpoint se puede probar con **Try it out**.

La documentación responde solo si `DOCUMENTACION_API` está activa. Si no se define, sigue a `DEBUG`: activa en desarrollo y apagada (404) en producción, para no publicar el mapa de la API. En producción, con `DOCUMENTACION_API=True`, hay que servir los archivos estáticos (`collectstatic`).

## 4. Cómo mostrarlo en la revisión

Antes: backend arrancado (`npm run dev` en la raíz, o `python manage.py runserver` en `backend/`).

**a) Swagger.** Abrir `http://localhost:8000/api/docs/` y seguir los pasos de la sección 3.

**b) Un origen no permitido queda bloqueado (en el navegador).**

1. Abrir cualquier página de otro sitio, por ejemplo `https://example.com`.
2. Abrir la consola del navegador (`F12` → pestaña **Console**).
3. Pegar y ejecutar:
   ```js
   fetch('http://localhost:8000/api/auth/login/', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ username: 'patologo1', password: 'patologo1234' }),
   }).then((r) => r.json()).then(console.log).catch(console.error);
   ```
4. Sale en rojo *«Access to fetch … from origin 'https://example.com' has been blocked by CORS policy»* y `TypeError: Failed to fetch`. En la pestaña **Network** se ve la consulta previa (`OPTIONS`) con estado **403**.

   Chrome puede pedir permiso para que una página pública acceda a `localhost` (acceso a la red local). Si se acepta, el resultado es el mismo bloqueo de CORS.

**c) Un origen permitido sí funciona.** Con la app abierta en `http://localhost:5173`, el mismo `fetch` en la consola, con la dirección relativa `'/api/auth/login/'`, responde con los tokens.

**d) La respuesta 403 (en PowerShell).** `curl.exe` permite poner a mano la cabecera `Origin` (un navegador no lo deja):

```powershell
curl.exe -i http://localhost:8000/api/opciones/ -H "Origin: https://sitio-ajeno.example"
```

Responde `HTTP/1.1 403 Forbidden` y `{"detail": "Origen no permitido: https://sitio-ajeno.example. …"}`: la API ni siquiera revisa el token. Con el origen del frontend:

```powershell
curl.exe -i http://localhost:8000/api/opciones/ -H "Origin: http://localhost:5173"
```

responde `401 Unauthorized` (falta el token, como cualquier petición sin sesión) y trae la cabecera `Access-Control-Allow-Origin: http://localhost:5173`, que es la autorización de CORS.

**e) Las pruebas automáticas.** En `backend/`: `python manage.py test config` (clases `ConfiguracionCorsTests`, `OrigenesApiTests` y `DocumentacionApiTests`).

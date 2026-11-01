# Registro de cambios

Todos los cambios de código del proyecto se documentan aquí, del más reciente al más antiguo.
Cada entrada indica la fecha, qué se cambió y por qué. Los códigos como "C-1" remiten a `docs/auditoria-inicial.md`.

## 2026-11-01

### Plantillas según el manual de procesamiento macroscópico y muestreo para histología (D-18)

**Qué se cambió:**
- **Plantillas:** las 14 se revisaron con el «Manual de procesamiento macroscópico de patología quirúrgica» (HUV – Univalle, 2.ª ed.). La matriz de correspondencia, los campos de cada una y lo pendiente de validar están en `docs/plantillas-manual.md`.
  - `backend/informes/definiciones_manual.py` (nuevo): campos, secciones, condiciones, ayudas y guía de muestreo de cada plantilla. De 124 campos se pasa a 260; no se borró ninguno.
  - `python manage.py actualizar_plantillas` (nuevo, `--simular` para probar): aplica las definiciones a una base existente. Es idempotente, solo agrega opciones a las listas, deja juntos los campos de cada sección y no toca los informes. `seed_data` lo llama al final.
- **Modelos (migración `informes/0014`, solo agrega):**
  - `Plantilla.seccion`, `Plantilla.condicion` (`{"campo": ..., "valores": [...]}`) y `Plantilla.ayuda`;
  - `Patologia.guia_muestreo`;
  - modelo nuevo `Canastilla` (`informe`, `orden`, `codigo` único por informe, `region`, `lesion_margen`, `descripcion`, `cantidad`, `entintado`, `motivo`, `observaciones`).
- **Validación** (`backend/informes/reglas.py`, nuevo): `InformeSerializer` exige solo los obligatorios que aplican al procedimiento elegido, rechaza números negativos o no numéricos y valores que no están en la lista. Un valor de lista ya guardado se conserva aunque la opción se haya quitado (como D-4). `PlantillaSerializer` valida el formato de `condicion`.
- **Canastillas en la API:** `canastillas` va anidado en `InformeSerializer` como `diagnosticos`: si se envía, reemplaza la lista en la misma transacción; si no, no cambia. Identificación obligatoria y sin repetir (sin importar mayúsculas), al menos región, lesión o descripción, cantidad de 0 o más (antes de este arreglo un negativo respondía 500), máximo `MAX_CANASTILLAS` (200). Se cargan con `prefetch_related` solo en el detalle. En un finalizado no cambian (D-3); en `/admin/`, `CanastillaInline` es de solo lectura para un finalizado (D-14).
- **Descripción macroscópica** (`backend/informes/utils.py`): omite los campos que no aplican; redacta `0` y «No» (antes se omitían); usa la etiqueta real en lugar del nombre técnico; y usa la frase del `mapeo` solo si la etiqueta nombra ese concepto (`RAICES_MAPEO`). Así, en Vesícula Biliar ya no dice «La consistencia es 3 mm», sino «Pared (espesor): 3 mm.». Las canastillas no se mencionan.
- **PDF:** sección «MUESTREO PARA HISTOLOGÍA» después de la macroscópica, en una tabla en negro, solo si hay canastillas. El texto pasa por `texto_seguro()`.
- **Frontend:**
  - `InformePage.jsx`: campos agrupados por sección, solo los que aplican, con su texto de ayuda; se exige solo lo que aplica; un `0` guardado ya se ve (antes salía vacío) y cuenta como respuesta; tarjeta «Muestreo para histología» cuando hay patología elegida.
  - `components/informe/MuestreoHistologia.jsx` (nuevo): agregar (con la letra libre sugerida), editar y quitar canastillas con confirmación; guía del manual desplegable; errores por fila como los de DRF; solo lectura en un finalizado.
  - `utils/reglas.js` (nuevo): `camposAplicables()` (la misma regla que `reglas.py`), `agruparPorSeccion()` y `esVacio()`.
  - `index.css`: estilos de las secciones, la ayuda, la guía y las canastillas.
- **Ruff:** `ruff.toml` exime `informes/definiciones_manual.py` de E501, como `seed_data.py` (es una tabla de datos).
- **Pruebas:**
  - Backend: 55 nuevas (reglas, comando, validación por procedimiento, canastillas, descripción, PDF y `/admin/`). Total: 377, todas en verde.
  - Frontend: 20 nuevas (`utils/reglas.test.js`, `MuestreoHistologia.test.jsx` y un bloque en `InformePage.test.jsx`).
- **Documentación:** `docs/plantillas-manual.md` (nuevo), D-18 en `docs/decisiones.md`, `README.md`, `CLAUDE.md` y `docs/progreso.md`.

**Por qué:** las plantillas exigían datos que no corresponden a todos los procedimientos, les faltaban datos que el manual pide y no había dónde registrar el muestreo para histología. La descripción redactaba algunos campos con un significado que no tenían.

## 2026-10-14

### Fase de Cypress: modo presentación y advertencias de la terminal

**Qué se cambió:**
- **Modo presentación:** `npm run e2e:presentacion` abre la interfaz de Cypress con una pausa después de cada acción, para que el público pueda seguirla.
  - La pausa es de 500 ms por defecto y se cambia con `-- --pausa=N`. Admite hasta 3000 ms, porque los borradores se autoguardan a los 5 s (D-13) y una pausa mayor haría fallar "Guardar y salir". Un valor no válido se rechaza con un mensaje.
  - `scripts/e2e.mjs`: `leerArgumentos()` devuelve también la pausa, que solo se usa en la presentación. `argumentosCypress()` la pasa a Cypress con `--expose pausa=N`.
  - `frontend/cypress/support/e2e.js`: si recibe una pausa, reemplaza las acciones (`visit`, `reload`, `click`, `type`, `clear`, `select`, `check`, `uncheck`) por otras que esperan después. Sin pausa no cambia nada.
  - Comprobado: `npm run e2e` sigue tardando lo mismo (29 s), y un mismo archivo pasa de 8 s a 14 s con 500 ms. Con 1000 ms pasan las 25 pruebas.
- **Chrome:** `e2e:abrir` y `e2e:presentacion` abren Chrome (`--browser chrome`) en lugar de Electron, que se cerró de golpe en el computador del usuario.
- **Advertencia de `allowCypressEnv`:** `allowCypressEnv: false` en `frontend/cypress.config.js`. Cypress avisaba que `Cypress.env()` deja que el código del navegador lea esos valores, que es inseguro y que lo quitará. Las pruebas no lo usaban (Testing Library tampoco).
- **Tildes rotas en la terminal** ("Inicio de sesi�n"): `entornoPython()` en `scripts/entorno.mjs` da `PYTHONIOENCODING=utf-8` al backend de `npm run dev` y de `npm run e2e`. Cuando la salida de Python pasa por concurrently, Windows usaba su codificación antigua.
- **`exited with code 1` al terminar:** no se quita, porque es Windows informando que los servidores se apagaron a la fuerza. Solo se podría ocultar quitando también las etiquetas `[backend]` y `[frontend]`, que sirven para encontrar problemas. Ahora el script avisa antes de apagarlos que es normal.
- **Se dejan como están:**
  - `WARNING seguridad: Inicio de sesión fallido`: es el registro de seguridad (O-21) anotando la contraseña incorrecta que la prueba usa a propósito;
  - `Re-optimizing dependencies because lockfile has changed`, de Vite: sale una vez después de instalar paquetes.
- **Pruebas:** 5 nuevas en `scripts/` (UTF-8, Chrome, modo presentación, pausa por defecto y configurable, pausa no válida o mayor de 3000), que fallaron antes del cambio. Total: 23 de la raíz, 322 del backend, 137 del frontend y 25 de Cypress, todas en verde. `npm run check` termina sin errores ni avisos.
- **Documentación:** `README.md`, `CLAUDE.md`, la sección "Fase de Cypress" del plan y `docs/progreso.md`.

**Por qué:** el usuario pidió quitar las advertencias de la terminal y explicarlas, y un modo más lento para la presentación del viernes que no haga más lentas las pruebas normales. También pidió abrir Chrome directamente, porque Electron se le cerró de golpe.

### Fase de Cypress: ajuste a los requisitos de la presentación

**Qué se cambió:**
- **Flujos críticos:** pasan de 4 a 6 archivos y de 22 a 25 pruebas en `frontend/cypress/e2e/`.
  - `login-y-roles.cy.js`: el admin, un patólogo y el auditor entran **por la pantalla**, ven el menú de su rol y cierran la sesión. Antes solo entraba `patologo1`.
  - `adendas.cy.js` (nuevo): la adenda pasa a ser su propio flujo, sobre un informe finalizado preparado por la API. También comprueba que un borrador no admite adendas y que la firma queda guardada. Sale de `informe-completo.cy.js`.
  - `auditor.cy.js` (nuevo): el auditor no ve "Nuevo Informe" ni "+ Paciente". Si abre `/informes/nuevo` directamente, los campos están deshabilitados y no hay "Guardar Informe". La API le responde 403 al crear un informe.
- **Selectores:** todas las pruebas buscan con `@testing-library/cypress` 10.1 (nueva dependencia de desarrollo de `frontend/`): `cy.findByRole`, `cy.findByLabelText` y `cy.findByText`. Ya no queda ningún `cy.get` ni `cy.contains` con clases CSS o ids (antes había unos 50), así que las pruebas sobreviven al rediseño de las fases 5 a 7.
- **Accesibilidad en la app,** necesaria para buscar por rol:
  - `frontend/src/components/FormularioPaciente.jsx`: el formulario es un `role="dialog"` con su título como nombre, igual que el aviso de cambios sin guardar.
  - `frontend/src/pages/LoginPage.jsx` e `InformePage.jsx`: `role="alert"` en los mensajes de error, para que los lectores de pantalla los anuncien.
  - Pruebas: `LoginPage.test.jsx` (nueva, 1), y una comprobación más en `InformePage.test.jsx` y en `SelectorPaciente.test.jsx`. Fallaron antes del cambio.
- **Video:** `npm run e2e:video` corre todo y graba un video por archivo en `frontend/cypress/videos/` (ignorada por git).
  - `scripts/e2e.mjs`: `leerArgumentos()` y `argumentosCypress(modo)`, con los modos `correr`, `abrir` y `video`. Una prueba nueva en `scripts/e2e.test.mjs`.
  - `frontend/cypress.config.js`: `video: false` pasa a la raíz de la configuración. Dentro de `e2e` pesaba más que `--config video=true`, y no se grababa nada.
- **Pruebas:** 19 de la raíz, 322 del backend, 137 del frontend y 25 de Cypress, todas en verde. `npm run check` termina sin errores ni avisos.
- **Documentación:**
  - sección "Fase de Cypress" en `docs/plan-calidad-y-diseno.md`, con los requisitos, los flujos, cómo se hace y cuándo se da por terminada;
  - `README.md`, `CLAUDE.md` y `docs/progreso.md`.

**Por qué:** el usuario fijó 5 requisitos para la presentación del viernes 2026-10-16. La revisión encontró que faltaban:
- el login por la pantalla de cada rol;
- la adenda como flujo propio;
- comprobar que el auditor no puede crear un informe;
- que las pruebas no dependieran de clases CSS;
- el video de respaldo;
- la documentación en el plan.

### Fase de Cypress: pruebas de punta a punta (decisión D-17)

**Qué se cambió:**
- **Cypress 15** (dependencia de desarrollo de `frontend/`):
  - `frontend/cypress.config.js`: dirección `http://localhost:5174`, ventana de 1280 × 800 y sin videos.
  - `frontend/cypress/support/commands.js`:
    - `cy.entrarComo(usuario)` abre la sesión por la API y la reutiliza con `cy.session`;
    - `cy.api()` hace peticiones con el token del usuario;
    - `cy.crearInforme({ listo, finalizar })` crea un paciente ficticio y un informe de "Biopsia de Piel".
- **4 archivos de pruebas** en `frontend/cypress/e2e/`, con 22 pruebas en total:
  - `login-y-roles.cy.js` (6):
    - login correcto e incorrecto;
    - sin sesión, una página protegida lleva al login;
    - "Salir";
    - el auditor no ve "Nuevo Informe" ni "+ Paciente", y el patólogo sí.
  - `informe-completo.cy.js` (5), todo por la pantalla:
    1. paciente nuevo desde el informe;
    2. borrador con su número de petición;
    3. lista de requisitos al intentar finalizar (D-8);
    4. microscópica y diagnóstico (con el CIE-10 normalizado) y finalización con firma;
    5. descarga del PDF (se comprueba que empieza con `%PDF`) y adenda (D-9), que sigue ahí al recargar.
  - `permisos.cy.js` (6):
    - D-2: patologo2 ve el borrador de patologo1 en solo lectura y sin vista previa del PDF (D-12); la API le responde 403, y al autor 200;
    - D-3: un finalizado no se edita en la pantalla, y la API responde 400 al autor y al admin.
  - `cambios-sin-guardar.cy.js` (5): sin cambios no hay aviso; "Seguir editando", "Salir sin guardar" y "Guardar y salir" (que guarda el borrador); "Salir" del menú también avisa (D-13).
- **`scripts/e2e.mjs`** (nuevo): `npm run e2e` y `npm run e2e:abrir` en `package.json` de la raíz.
  - Pasos: crea desde cero `backend/e2e_db.sqlite3` con `migrate` y `seed_data`, arranca el backend (8001) y el frontend (5174), corre Cypress y espera a que los servidores se cierren antes de salir (si no, en Windows quedaban vivos y con la base abierta).
  - Los argumentos extra pasan a Cypress (`-- --spec ...`).
  - Le quita a Cypress `ELECTRON_RUN_AS_NODE`, que definen las terminales de VS Code y con la que Cypress no arranca.
- **`scripts/e2e.test.mjs`** (nuevo, 6 pruebas): base aparte, límite, pasos, puertos, entorno de Cypress y argumentos.
- **`backend/config/settings.py`**:
  - `SQLITE_NOMBRE` elige el archivo SQLite (`db.sqlite3` por defecto);
  - `LIMITE_PETICIONES_USUARIO` el límite `user` (`120/minute` por defecto). Corriendo todo junto, `patologo1` pasaba de 120 peticiones por minuto y el backend respondía 429. El límite del login sigue fijo.
  - Pruebas: `ArchivoSqliteTests` y `LimitePeticionesUsuarioTests` en `config/tests.py` (4). Antes del cambio fallaba una de cada clase; las otras dos son de control.
- **`frontend/vite.config.js`**: el destino del proxy se lee de `API_PROXY_DESTINO` (`http://localhost:8000` por defecto).
- **ESLint, Prettier y git:**
  - `frontend/eslint.config.js`: globals de Cypress y Mocha en `cypress/**`; las carpetas de salida se ignoran.
  - `.gitignore` y `frontend/.prettierignore`: `frontend/cypress/downloads/`, `screenshots/` y `videos/`.
- **`backend/.env.example`**: explica las dos variables nuevas.
- **`npm audit`**: Cypress no agrega vulnerabilidades. Quedan solo las 2 moderadas de `react-router` (I-9c).
- **Pruebas:** 18 de la raíz, 322 del backend, 136 del frontend y 22 de Cypress, todas en verde. `npm run check` termina sin errores ni avisos.
- **Documentación:** `README.md` (estructura y pruebas), `CLAUDE.md` (comandos y configuración), `docs/decisiones.md` (D-17), el plan y `docs/progreso.md`.

**Por qué:** el usuario presenta las pruebas de punta a punta el viernes 2026-10-16. Las pruebas unitarias simulan la API. Las de Cypress comprueban que la aplicación real, con backend y frontend juntos, cumple los flujos y las decisiones más importantes (D-2, D-3, D-8, D-9, D-12, D-13). La base aparte evita ensuciar la de desarrollo y gastar números de petición (D-7).

## 2026-10-12

### Fase 4, grupo 5: errores y registros (O-22, O-23, O-21)

**Qué se cambió:**
- `backend/config/filtros.py` (nuevo): `parametro_entero()` y `parametro_fecha()` leen un filtro de la URL y responden 400 con un mensaje en español (`{"patologia": "Debe ser un número entero positivo."}`) si no es válido. Un valor vacío cuenta como sin filtro.
  - Se usan en `?categoria=` (patologías), `?patologia=` (plantillas), `?fecha_desde=`, `?fecha_hasta=`, `?patologia=` y `?paciente=` (informes y estadísticas), `?tema=` y `?publicacion=` (foro). Antes respondían 500 con un texto, una fecha imposible o un número demasiado grande (**O-22**).
- `backend/informes/models.py`: `validar_datos_ingresados` en `Informe.datos_ingresados`. Debe ser un objeto con textos, números, booleanos o nulos, de máximo 100 campos y 5000 caracteres por valor. Como está en el modelo, DRF lo aplica en la API y Django en `/admin/` (**O-23**). El campo pasa a `blank=True`: en `/admin/`, un informe con `{}` ya se puede guardar.
- `backend/informes/migrations/0013_datos_ingresados_validados.py`: solo cambia la definición del campo; no toca datos.
- `backend/informes/serializers.py` y `views.py`: `texto_generado` se genera en `InformeSerializer.create` y `update` (`_generar_texto`), dentro de la misma transacción que el informe y sus diagnósticos. Antes se generaba en `perform_create` y `perform_update`, después de guardar: si fallaba, quedaba un informe a medias con su número de petición gastado (**O-23**).
- Registros (**O-21**):
  - `backend/config/settings.py`: `LOGGING` manda a la consola los errores 500 (`django.request`) y el logger `seguridad`, también con `DEBUG=False`. Antes, con `DEBUG=False` y `ADMINS` vacío, no iban a ningún lado. `LOG_LEVEL` (`INFO` por defecto) se lee de `backend/.env`; `.env.example` lo explica.
  - `backend/accounts/signals.py` (nuevo) y `accounts/apps.py` (nuevo, conecta las señales): registran los logins fallidos (aviso) y los correctos de `/admin/`, con el usuario y la IP (como los límites, respetando `NUM_PROXIES`). El usuario se recorta y va en una sola línea, para que no se puedan inventar líneas en el registro.
  - `backend/accounts/views.py`: `CustomTokenView.post` registra los logins correctos de la API, porque SimpleJWT no emite `user_logged_in`.
  - Nunca se registran contraseñas, tokens ni datos de pacientes.
  - `backend/config/test_runner.py`: silencia la salida a la consola durante las pruebas; `assertLogs()` sigue funcionando.
- Pruebas nuevas (19): `FiltrosNoValidosTests` (2), `DatosIngresadosTests` (6) y `AdminDatosIngresadosTests` (2) en `informes/tests.py`; `FiltrosNoValidosForoTests` (2) en `foro/tests.py`; `RegistroDeAccesosTests` (4) en `accounts/tests.py`; `RegistrosTests` (3) en `config/tests.py`. Antes del arreglo fallaban 14 de las 17 primeras (las otras 3 son de control); las 2 últimas de `RegistroDeAccesosTests` se agregaron con el arreglo.
- **Pruebas:** 12 de la raíz, 318 del backend y 136 del frontend, todas en verde; `npm run check` sin errores ni avisos.
- **Documentación:** `README.md` (estructura, filtros y `datos_ingresados` en la API, seguridad, publicación), `CLAUDE.md`, `docs/auditoria-owasp.md`, el plan y `docs/progreso.md`.
- **No incluido, por decisión del usuario:** el tamaño máximo de los textos largos (microscópica, comentarios, diagnósticos, adendas, foro) queda para el grupo 8. Que `/admin/` no regenere `texto_generado` al guardar (ya pasaba antes) queda anotado en los pendientes.

**Por qué:** la auditoría OWASP comprobó que cualquier usuario con sesión podía provocar errores 500 con un filtro mal escrito, que un `datos_ingresados` que no era un objeto dejaba un informe guardado a medias, y que con `DEBUG=False` ni esos errores ni los logins fallidos quedaban registrados.

### Fase 4, grupo 3: imágenes del foro (O-13, O-5 puntos 1 y 2)

**Qué se cambió:**
- `backend/foro/imagenes.py` (nuevo): `preparar_imagen(archivo)` revisa y limpia cada imagen antes de guardarla.
  - Rechaza (400) un archivo que supera `FORO_MAX_TAMANO_IMAGEN`, cuya extensión no sea `.jpg`, `.jpeg`, `.png`, `.gif` o `.webp`, o cuyo formato real, según Pillow, no sea JPEG, PNG, GIF o WEBP. Un `ataque.html` que también es un PNG válido ya no se acepta (**O-13**). Tampoco un SVG ni un BMP.
  - Vuelve a codificar la imagen con Pillow. Se pierde todo lo agregado después de la imagen (por ejemplo, HTML) y los metadatos EXIF (fecha, equipo, ubicación) (**O-5**, punto 2). Antes se aplica la orientación del EXIF, para que las fotos de celular no queden giradas. Los GIF y WEBP animados conservan sus cuadros. Los JPEG se guardan con calidad 90.
  - La extensión guardada es la del formato real: un JPEG llamado `.png` se guarda como `.jpg`.
- `backend/foro/models.py`: `ruta_imagen_publicacion` usa un nombre aleatorio (`uuid4`) con la extensión, sin el nombre original: `foro/publicaciones/<id>/<uuid>.<ext>` (**O-5**, punto 1). Sin migración, porque la función es la misma.
- `backend/foro/views.py`: `subir_imagenes` usa `preparar_imagen()` en lugar de su propia revisión. Sigue revisando todos los archivos antes de guardar ninguno.
- `backend/foro/admin.py`: `ImagenPublicacionForm` en el `ImagenInline`, para que las imágenes subidas en `/admin/` pasen por la misma revisión y limpieza. Lo aprobó el usuario junto con el resto.
- `frontend/src/pages/ForoPage.jsx`: el selector de archivos ofrece solo `.jpg,.jpeg,.png,.gif,.webp` (`EXTENSIONES_IMAGEN`), y la revisión previa a publicar rechaza las demás extensiones con "no es una imagen permitida. Use JPG, PNG, GIF o WEBP".
- Pruebas nuevas:
  - `SeguridadImagenesForoTests` (11, `backend/foro/tests.py`). Antes del arreglo fallaban 9; las del SVG y el GIF animado ya pasaban y quedan para que no se rompan;
  - `AdminImagenesForoTests` (3): el inline usa el formulario, un BMP se rechaza y se guarda una copia limpia con nombre aleatorio;
  - 2 en `ForoPage.test.jsx`: los formatos no permitidos no se publican y el `accept` del selector.
- **Pruebas:** 12 de la raíz, 299 del backend y 136 del frontend, todas en verde; `npm run check` sin errores ni avisos.
- **Documentación:** `README.md` (estructura, endpoint de imágenes, características y seguridad), `CLAUDE.md` (imágenes del foro), `docs/auditoria-owasp.md` (estado de O-13 y O-5), el plan y `docs/progreso.md`.
- **No incluido:** las imágenes ya guardadas conservan su nombre y su EXIF (hoy solo hay datos de prueba). El punto 4 de O-13 (cabeceras de `/media/`) va con O-6 en el grupo 6, y servir las imágenes con sesión (O-5, punto 3), en el grupo 8.

**Por qué:** la auditoría OWASP comprobó que el foro guardaba el archivo con el nombre y la extensión que enviaba el usuario. Un PNG válido con HTML al final, llamado `ataque.html`, quedaba servido como página web en el origen de la app (XSS almacenado que podía leer los tokens). Además, la dirección de cada imagen era fácil de adivinar y las fotos conservaban su EXIF.

## 2026-10-11

### Fase 4, grupo 2: límites del login (O-16, O-17)

**Qué se cambió:**
- `backend/accounts/views.py`:
  - `CustomTokenView` define `throttle_scope = 'login'` y usa `AnonRateThrottle` y `ScopedRateThrottle`. El login vuelve a tener su límite de 10 intentos por minuto y el general de 30 por minuto para anónimos.
  - `RegistroView`, lo mismo con `'registro'` (5 por minuto) y `UserRateThrottle`.
  - Antes, `ScopedRateThrottle` tomaba el scope de la vista, que no lo tenía, así que el login no tenía ningún límite (**O-16**).
- `backend/accounts/throttles.py`: **borrado**. Sus clases definían `scope`, que DRF ignora, y daban la impresión de que había un límite.
- `backend/config/settings.py`: `NUM_PROXIES` en `REST_FRAMEWORK`, leído de `backend/.env`, con 0 por defecto. Los límites usan la IP de la conexión y ya no se saltan cambiando `X-Forwarded-For` (**O-17**). `backend/.env.example` lo explica: detrás de Nginx, `NUM_PROXIES=1`.
- Pruebas nuevas:
  - `LimitesLoginTests` (4, en `accounts/tests.py`), con una caché real: el login da 429 al intento 11, otra IP sí entra, cambiar `X-Forwarded-For` no reinicia la cuenta y el registro da 429 a la petición 6;
  - `NumProxiesTests` (2, en `config/tests.py`): vale 0 sin `.env` y se lee del entorno.
  - Antes del arreglo fallaban 5 de las 6; la sexta es de control.
- **Pruebas:** 12 de la raíz, 285 del backend y 134 del frontend, todas en verde; `npm run check` sin errores ni avisos.
- **Documentación:**
  - `README.md`: sin el aviso de O-16 y sin `throttles.py` en la estructura, con `NUM_PROXIES` en "Para publicar";
  - `CLAUDE.md`: el párrafo de rate limiting y cómo probar un límite con caché real;
  - `docs/auditoria-owasp.md` (O-16 y O-17 corregidos), el plan y `docs/progreso.md`.
  - Además se anota en el grupo 5 el problema de `/admin/` con `datos_ingresados` vacío, a pedido del usuario.

**Por qué:** la auditoría OWASP comprobó que el login no tenía ningún límite de intentos, aunque el README decía 10 por minuto, y que con la cabecera `X-Forwarded-For` se podía saltar cualquier límite por IP.

### Fase 4, grupo 1: integridad del informe (O-1, O-3, O-4 / D-14)

**Qué se cambió:**
- `backend/informes/serializers.py`: `estado` pasa a `read_only_fields` de `InformeSerializer`. Un `PATCH`, un `PUT` o un `POST` con `"estado": "finalizado"` ya no finalizan el informe: el campo se ignora y el informe sigue en borrador. Solo lo cambia `POST /api/informes/{id}/finalizar/` (**O-1**). El frontend no enviaba ese campo, así que no cambia nada en la pantalla.
- `backend/informes/admin.py`:
  - `estado` es de solo lectura en `InformeAdmin`, también en los borradores. Un borrador ya no se finaliza desde `/admin/` sin requisitos ni datos congelados (**O-3**).
  - `InformeAdmin.has_change_permission` y `has_delete_permission` devuelven `False` para un informe finalizado. Su ficha se ve en solo lectura, cualquier envío responde 403 y no se borra ni desde su página ni con la acción en lote, tenga o no adendas (**O-4**, decisión **D-14**).
  - `DiagnosticoInline`: en un finalizado no deja agregar, cambiar ni borrar diagnósticos.
  - Los borradores se siguen editando y borrando como antes.
- `backend/informes/tests.py`: `EstadoSoloLecturaTests` (3) y `AdminInformeFinalizadoTests` (13), con la función `datos_formulario_admin()`, que arma lo que el navegador enviaría al guardar una ficha de `/admin/`. Antes del arreglo fallaban 11 de las 15 primeras. Las otras 4 ya pasaban: las 3 de borradores y la del finalizado con adendas, que `PROTECT` ya impedía borrar. La prueba 16 comprueba que la ficha de un finalizado se ve sin el botón de guardar.
- **Pruebas:** 12 de la raíz, 279 del backend y 134 del frontend, todas en verde; `npm run check` sin errores ni avisos.
- **Documentación:**
  - `docs/decisiones.md` (D-14 implementada), `README.md` (sin el "Pendiente" de D-14 y con la regla del estado), `CLAUDE.md` y `docs/propuesta-informe-v2.md`;
  - `docs/auditoria-owasp.md` (O-1, O-3 y O-4 corregidos), el plan y `docs/progreso.md`.
  - En el plan, la decisión de la guía de diseño (fase 5) ya no tiene reservado el número D-16, que se usó para las cuentas: llevará el siguiente libre.

**Por qué:** la auditoría OWASP comprobó que un informe podía quedar finalizado sin diagnóstico, sin firma y sin datos congelados (D-8, D-10, D-15), y que en `/admin/` un finalizado se podía modificar y borrar, contra D-14.

### Respuestas del usuario a la auditoría OWASP

**Qué se cambió** (solo documentación):
- `docs/auditoria-owasp.md`: sección "Respuestas del usuario" con el estado y el grupo de cada hallazgo.
- `docs/plan-calidad-y-diseno.md`:
  - la fase 3 queda terminada;
  - la fase 4 se define con una rama por grupo y su calendario;
  - se anota la fase nueva de Cypress (desde el 2026-10-13, presentación el 2026-10-16).
- `docs/decisiones.md`: D-16 (solo `is_active` y token de acceso de 30 minutos). Se implementa en el grupo 6 de la fase 4.
- `docs/progreso.md`: siguiente paso, pendientes de producción (O-20, O-18, cookie `HttpOnly`) y la pregunta de los borradores ajenos para el patólogo y el profesor.

**Por qué:** el usuario leyó el informe de la fase 3 y respondió sus 6 preguntas.

### Fase 3: auditoría OWASP Top 10:2025

**Qué se cambió** (solo documentación; no se tocó código):
- `docs/auditoria-owasp.md` (nuevo): el informe de seguridad de las 10 categorías de OWASP Top 10:2025.
  - Para cada categoría: qué aplica a PathoLab, qué ya está protegido y qué falta.
  - Las dependencias de npm (raíz y frontend) y de Python, con `npm audit` y `pip-audit`.
  - 23 hallazgos (`O-1` a `O-23`): 5 de prioridad alta, 13 media y 5 baja, cada uno con dónde está, cómo se reproduce y la corrección propuesta. 6 se comprobaron con pruebas temporales fuera del proyecto.
  - Una propuesta de orden para la fase 4 y las preguntas para el usuario.
- **I-9a:** el análisis decía que GHSA-337j-9hxr-rhxg no afecta porque la app usa `BrowserRouter`. Desde D-13 usa `createBrowserRouter`. Se volvió a comprobar y sigue sin afectar, ahora porque no hidrata datos del servidor (sin `hydrationData` ni SSR). El detalle está en O-11.
- `README.md`:
  - enlace al informe en "Seguridad" y en la tabla de documentación;
  - un aviso bajo la tabla de límites: hoy los de login y registro no se aplican (O-16).
- `docs/plan-calidad-y-diseno.md` y `docs/progreso.md`: estado de la fase 3.

**Por qué:** fase 3 de `docs/plan-calidad-y-diseno.md`. Las correcciones se eligen después de que el usuario lea el informe y se hacen en la fase 4.

## 2026-10-08

### Regla de comprobar antes de cada commit

**Qué se cambió** (solo documentación):
- `CLAUDE.md`, regla de trabajo 7 (nueva): antes de cada commit que toque código se ejecutan `npm run check` y todas las pruebas (raíz, backend y frontend), y si algo falla no se hace el commit hasta corregirlo. En los commits que solo cambian documentación no hace falta ejecutar las pruebas.
- `docs/progreso.md`: el mismo paso en la "Forma de trabajar". Además se completa la lista de lo terminado, que no mencionaba la fase 2 ni la tarea previa 2.

**Por qué:** pedido del usuario. Así ningún commit deja el código con errores de formato, avisos de los linters o pruebas rotas.

### Fase 2, parte 4: arreglos a mano de ESLint y Ruff

**Qué se cambió** (cada arreglo lo aprobó el usuario; ninguno cambia el comportamiento):
- **`react-hooks/exhaustive-deps` (11):**
  - `useCallback` en `VisorImagenes.jsx` (`cerrar`, `mover`), `CatalogosPage.jsx` (`cargar`), `ForoPage.jsx` y `PatologiasPage.jsx` (`fetchData`) y `PublicacionDetallePage.jsx` (`fetchPublicacion`). Los efectos dependen de esas funciones y se repiten en los mismos casos que antes.
  - `InformePage.jsx`: se agregan `isEditing` y `navigate`, que no cambian mientras la pantalla está abierta (nuevo y edición son rutas distintas).
  - Regla desactivada solo en esa línea, con su motivo: la búsqueda inicial de `BuscarPage.jsx` y el cierre de sesión de `CerrarSesionPage.jsx`, que deben correr una sola vez al abrir.
  - **Autoguardado (D-13):** el temporizador llama a `autoguardarRef.current()`, como ya se hacía con `versionRef`. Se reinicia solo cuando cambia lo escrito, no cuando cambia el indicador "guardando…", y ESLint lo sigue vigilando. Lo eligió el usuario en lugar de desactivar la regla.
- **Errores de ESLint (9):**
  - `catch` sin variable (4);
  - `&quot;` en lugar de comillas sueltas en `SelectorPaciente.jsx` y `PoliticaPrivacidadPage.jsx`, que se ven igual;
  - un escape de más en el nombre del PDF (`InformePage.jsx`).
- **Ruff (4):**
  - `raise ... from None` en `config/settings.py`: sin `SECRET_KEY`, la consola ya no muestra antes el error interno de decouple;
  - `raise ... from error` en `accounts/serializers.py`;
  - una `lambda` pasa a `def` en `informes/tests.py`.
- `scripts/check.mjs`: con `shell: true`, `npm` recibe el comando en un solo texto, y desaparece el aviso DEP0190 de Node.
- **Pruebas:** no hay nuevas, porque no cambia el comportamiento. Pasan las 21 de D-13 y todas las demás: 12 de la raíz, 134 del frontend y 263 del backend. `npm run build` compila y `npm run check` termina con las cuatro comprobaciones en OK.
- **Documentación:** `CLAUDE.md` (autoguardado), el plan y `docs/progreso.md`.

**Por qué:** cierre de la fase 2 de `docs/plan-calidad-y-diseno.md`: el código queda sin errores ni avisos de los linters.

### Fase 2, partes 2 y 3: formato automático e imports ordenados

**Qué se cambió**
- **Parte 2, commit `836257b`, solo formato:**
  - `prettier --write` en `frontend/`: 43 archivos de `src/`, `index.html` y `vite.config.js`;
  - `ruff format` en `backend/`: 27 archivos, sin las migraciones.

  Sobre todo se parten las líneas de más de 120 caracteres, se juntan en una las expresiones que cabían, y se agregan comas finales y comillas uniformes. No cambia el comportamiento: pasaron todas las pruebas (12 de la raíz, 134 del frontend y 263 del backend) y `npm run build`.
- **Parte 3, `ruff check --select I --fix`:** Ruff ordena los imports de 27 archivos del backend (38 bloques): primero la biblioteca estándar, luego los paquetes instalados y al final los del proyecto.
- `.git-blame-ignore-revs` (nuevo): lleva el commit `836257b`, para que `git blame` lo salte. El README explica cómo activarlo en local.
- **Pendiente (parte 4):** los arreglos a mano de ESLint (11 `exhaustive-deps`, 4 variables sin usar, 4 comillas en JSX y 1 escape) y de Ruff (3 B904 y 1 `lambda`). Se muestran al usuario antes de aplicarlos.

**Por qué:** fase 2 de `docs/plan-calidad-y-diseno.md`. El formateo va en su propio commit, sin nada más, para poder revisarlo y saltarlo en `git blame`.

### Fase 2, parte 1: herramientas de formato y linter

**Qué se cambió** (sin tocar todavía el código de la aplicación):
- **Frontend**, dependencias de desarrollo:
  - Prettier 3.9.9, con versión exacta;
  - ESLint 9.39 con `@eslint/js`, `eslint-plugin-react`, `eslint-plugin-react-hooks` 7, `globals` y `eslint-config-prettier`.
- **Frontend**, archivos nuevos:
  - `.prettierrc`: comillas simples, punto y coma, 120 caracteres y `endOfLine: "auto"`;
  - `.prettierignore`;
  - `eslint.config.js`: reglas recomendadas de JavaScript y React, solo `rules-of-hooks` y `exhaustive-deps` de los hooks, sin `prop-types`, globales de Vitest en las pruebas y `eslint-config-prettier` al final.
- **Frontend**, scripts nuevos: `format`, `format:check` y `lint` (con `--max-warnings 0`).
- **Backend**:
  - `requirements-dev.txt`: `-r requirements.txt` más `ruff==0.16.10`;
  - `ruff.toml`: 120 caracteres, comillas simples, `py310`, `line-ending = "auto"`, sin las migraciones, reglas E, W, F, I, B y DJ, con E501 desactivada solo en las tablas de `seed_data.py`.
- **Raíz:**
  - `npm run check` (`scripts/check.mjs`): corre las cuatro comprobaciones sin cambiar archivos y termina con error si alguna falla;
  - 4 pruebas en `scripts/check.test.mjs`. La raíz pasa de 8 a 12 pruebas.
- **VS Code:**
  - `.vscode/settings.json`: formato al guardar con el Prettier de `frontend/node_modules` (solo donde hay `.prettierrc`) y el Ruff del venv;
  - `.vscode/extensions.json`: Prettier, ESLint y Ruff;
  - `.gitignore` ignora el resto de `.vscode/`.
- **Documentación:**
  - README: sección nueva "Formato y Linter", tecnologías, estructura, instalación con `requirements-dev.txt` y VS Code;
  - `CLAUDE.md`: comandos; desaparece "No hay linter configurado";
  - el plan y `docs/progreso.md`.

**Por qué:** fase 2 de `docs/plan-calidad-y-diseno.md`. Hasta ahora el formato dependía de cada persona y no había linter (auditoría inicial, sección 1). El formateo del código va en el commit siguiente, solo, para que no se mezcle con cambios reales.

### El encabezado del PDF se congela al finalizar (decisión D-15)

**Qué se cambió**
- `backend/informes/models.py`: `Informe.datos_para_congelar()` agrega `laboratorio` (`nombre`, `direccion`, `telefono`), con los valores de `settings` del momento. Al finalizar queda guardado en `datos_finalizacion`, y `datos_impresos()` lo devuelve congelado en los finalizados y actual en los borradores.
- `backend/informes/utils.py`: `_encabezado()` recibe `datos['laboratorio']` en lugar de leer `settings`.
- Migración nueva `backend/informes/migrations/0012_encabezado_congelado.py` (solo datos):
  - agrega el encabezado de demostración a los informes finalizados que no tienen `laboratorio`;
  - lo escribe la propia migración, para no depender del `.env` del equipo;
  - no toca los borradores ni los que ya lo tienen;
  - usa `update()` para no cambiar `fecha_actualizacion`;
  - la reversa quita la clave.
- **Pruebas:** 6 nuevas.
  - En `PdfInformeTests`, 4:
    - al finalizar se congela el encabezado;
    - un finalizado conserva su encabezado aunque cambie la configuración;
    - un borrador usa el encabezado actual (resguardo: ya pasaba);
    - una adenda no cambia el encabezado congelado.
  - En `MigracionEncabezadoCongeladoTests`, 2: completa los finalizados, y la reversa lo quita.
  - Las 5 primeras fallaban antes del cambio. El backend pasa de 257 a 263 pruebas.
- **Documentación:**
  - `docs/decisiones.md` (D-15);
  - README: tabla de variables, "Integridad del informe" y la lista de decisiones;
  - `CLAUDE.md`;
  - el plan: la guía de diseño pasa a ser D-16;
  - `docs/progreso.md`.

**Por qué:** al probar la tarea previa 2, el usuario cambió el encabezado en el `.env` y vio que también cambiaba el PDF de un informe finalizado. Un informe entregado no debe cambiar (D-3, D-10).

### Encabezado del PDF configurable (tarea previa 2 del plan)

**Qué se cambió**
- `backend/config/settings.py` lee de `backend/.env` tres variables nuevas, todas opcionales:

  | Variable | Valor por defecto |
  |---|---|
  | `LABORATORIO_NOMBRE` | "PathoLab — Laboratorio de Patología (demostración)" |
  | `LABORATORIO_DIRECCION` | "Santiago de Cali, Colombia" |
  | `LABORATORIO_TELEFONO` | vacío |

  Sin `.env`, el PDF queda igual que antes.
- `backend/informes/utils.py`:
  - se eliminan las constantes `ENCABEZADO_LABORATORIO` y `ENCABEZADO_CIUDAD`;
  - `_encabezado()` imprime el nombre (en negrita) y la dirección, que es una sola línea con la dirección completa y la ciudad;
  - si hay teléfono, imprime una tercera línea, "Teléfono: …";
  - los tres valores pasan por `texto_seguro()` (I-3).
- `backend/.env.example`: sección comentada con las tres variables y un ejemplo ficticio.
- **Pruebas:** 6 nuevas.
  - En `config/tests.py` (`EncabezadoLaboratorioTests`), 3:
    - valores por defecto;
    - valores del entorno;
    - tildes y raya leídas de un archivo `.env` en UTF-8.
  - En `PdfInformeTests`, 3:
    - encabezado configurado, con el teléfono en su línea;
    - sin teléfono no hay línea;
    - valores con `<` y `&` escapados.
  - Las 6 fallaban antes del cambio. `test_los_titulos_van_en_negrita_y_en_negro` ahora lee el nombre de `settings`. El backend pasa de 251 a 257 pruebas.
- **Documentación:**
  - README: "Características", tabla de las variables en la instalación y hoja de ruta (hecho);
  - `CLAUDE.md`;
  - `docs/propuesta-informe-v2.md`, sección 5.1;
  - el plan y `docs/progreso.md`, también la lista de lugares con "PathoLab".

**Por qué:** el usuario prevé que el encabezado de demostración no se quede así (2026-10-08), y ya estaba en la hoja de ruta. Así cada instalación pone los datos de su laboratorio en `.env`, sin tocar el código. Las opciones (teléfono en una línea aparte, una sola variable de dirección) las eligió el usuario.

### D-14 también impide borrar un informe finalizado desde `/admin/`

**Qué se cambió** (solo documentación):
- `docs/decisiones.md`, D-14: un informe finalizado tampoco se puede borrar desde `/admin/`, tenga o no adendas. Si se finalizó por error, se deja constancia con una adenda.
- `docs/plan-calidad-y-diseno.md`, fase 4: `has_delete_permission()` y la acción de borrado en lote. Se agregan las pruebas de borrado de un finalizado con y sin adendas, y la de que un borrador sí se borra.
- `docs/progreso.md`: idea futura de un estado "Anulado".
- README y `CLAUDE.md`: mencionan el borrado en D-14.

**Por qué:** el usuario respondió el 2026-10-08 la pregunta que el plan dejaba para la fase 4. D-3 ya impedía borrar un finalizado por la API, y un finalizado con adendas no se borraba (`PROTECT`), pero uno sin adendas sí se podía borrar desde `/admin/`.

### `npm audit fix`: avisos crítico y alto de las herramientas de desarrollo

**Qué se cambió** (rama `npm-audit-fix`): se ejecutó `npm audit fix`, sin `--force`, en la raíz y en `frontend/`. Solo cambiaron los `package-lock.json`; ningún `package.json` cambió.
- **Raíz:** `concurrently` 10.0.5 → 10.0.6, que trae `shell-quote` 1.9.0 → 1.12.0. Cierra el aviso **crítico** [GHSA-pqg4-j6r4-53mv](https://github.com/advisories/GHSA-pqg4-j6r4-53mv) (inyección de comandos en `quote()`). `npm audit` en la raíz: de 2 críticas a **0**.
- **Frontend:** `source-map-js` 1.2.1 → 1.2.2, que usa Vite a través de PostCSS. Cierra el aviso **alto** [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) (bloqueo del proceso con mapas de código manipulados). `npm audit` en el frontend: de 3 (1 alta, 2 moderadas) a **2 moderadas**.
- Además, npm quitó una marca `"peer": true` de los metadatos de una dependencia de desarrollo en `frontend/package-lock.json`. No cambia ninguna versión.
- **Siguen las 2 moderadas de `react-router`** (I-9c). Solo se cierran con React Router 7. Se evalúan en la fase 3 del plan, con el análisis de I-9a revisado.
- **Comprobación:**
  - pasan todas las pruebas: 8 de la raíz, 251 del backend y 134 del frontend;
  - `npm run build` compila;
  - `concurrently` lanza y termina dos procesos de prueba;
  - no hay prueba nueva, porque es una actualización de dependencias sin cambio de comportamiento.

**Por qué:** el inventario de pendientes del 2026-10-08 encontró estos dos avisos nuevos, que no existían en I-9. Los dos estaban en herramientas de desarrollo (`npm run dev` y Vite) y no llegaban a la aplicación publicada. El usuario pidió corregirlos ya, antes de la tarea previa 2 del plan, porque el arreglo no cambia de versión principal.

### Inventario de pendientes, decisión D-14 y documentación corregida

**Qué se cambió** (solo documentación, rama `docs-pendientes`):
- `docs/progreso.md`: sección "Pendientes" nueva, ordenada y sin duplicados, con origen y destino de cada punto:
  - del plan;
  - decisiones del usuario, con la lista de lugares donde aparece "PathoLab" para el posible cambio de nombre;
  - producción;
  - ideas futuras;
  - contradicciones.

  También se actualizaron "Dónde estamos" y "Siguiente paso".
- `docs/plan-calidad-y-diseno.md`:
  - tarea previa 2 (encabezado del PDF configurable desde `backend/.env`);
  - puntos conocidos que debe evaluar la fase 3;
  - la implementación de D-14 en la fase 4, con sus pruebas;
  - la guía de diseño pasa a ser D-15.
- `docs/decisiones.md`: **D-14**. Un informe finalizado tampoco se modifica desde `/admin/` (campos, diagnósticos y estado de solo lectura); se corrige siempre con adendas. Reemplaza la excepción de `/admin/` de D-3, sin borrar D-3. **Todavía no está implementada** (fase 4).
- `README.md`:
  - D-14 en la lista de decisiones y en "Roles y Permisos", con el aviso de que falta implementarla;
  - `docs/plan-calidad-y-diseno.md` en la tabla de documentación;
  - "Pruebas Automáticas" incluye D-13 y el visor de imágenes;
  - la imagen de la firma (etapa 10) en la hoja de ruta.
- `CLAUDE.md`:
  - de la auditoría inicial solo queda I-9c, y los pendientes están en `progreso.md`;
  - D-14 y su estado.
- `docs/auditoria-inicial.md`:
  - estado de I-13 (corregido) e I-7 (README corregido);
  - columna "Hoy" en la tabla de la sección 5.
- `docs/propuesta-informe-v2.md`:
  - estado (etapas 8 y 9 hechas);
  - sección 8: registro de `patologo2` y la excepción aprobada de `?q=` en la URL;
  - nota de D-14 en la sección 7.

**Por qué:**
- El usuario pidió un inventario de todo lo pendiente antes de seguir con el plan.
- Al hacerlo aparecieron contradicciones entre documentos. La más seria: D-3 permitía corregir en `/admin/` un informe finalizado, y `InformeAdmin` deja cambiar su contenido y su estado sin rastro. Eso contradice D-9 y el README. El usuario la resolvió con D-14.
- Queda sin corregir, por decisión del usuario, el análisis de React Router en la entrada de I-9a: se vuelve a comprobar en la fase 3.


### Segundo patólogo de prueba (`patologo2`) en `seed_data`

**Qué se cambió**
- `backend/informes/management/commands/seed_data.py` crea `patologo2` / `patologo2345`:
  - "Dra. Ana Ficticia", Patología Quirúrgica;
  - registro médico ficticio `RM-PRUEBA-0002`, para que pueda finalizar sus propios informes.
- Si `patologo2` ya existe, no se cambia: ni la contraseña ni el registro.
- **Pruebas:** 3 nuevas en `RegistroMedicoTests` (`accounts/tests.py`):
  - lo crea con su rol, su registro y su contraseña;
  - ejecutar `seed_data` dos veces no lo duplica;
  - no cambia un `patologo2` que ya existía.

  Las dos primeras fallaban antes del cambio.
- **Documentación:**
  - README: tabla de usuarios de prueba, y que `seed_data` no cambia usuarios existentes;
  - `CLAUDE.md`: usuarios de `seed_data`;
  - Postman: descripción del login;
  - `docs/plan-calidad-y-diseno.md` y `docs/progreso.md`.

**Por qué:** es la tarea previa de `docs/plan-calidad-y-diseno.md`, aprobada por el usuario el 2026-10-08.
- Para probar la decisión D-2 (un patólogo no modifica, borra ni finaliza los informes de otro) hace falta un segundo patólogo.
- Hasta ahora había que crearlo a mano (así se hizo para la prueba manual del 2026-10-05), y el README no lo mencionaba.

### PDF en negro (Bloque B, punto 4)

**Qué se cambió**
- `backend/informes/utils.py`: las constantes `AZUL_OSCURO`, `AZUL`, `GRIS_TEXTO`, `GRIS_SUAVE` y `GRIS_LINEA` se reemplazan por una sola, `NEGRO`.
  - Todo el texto va en negro: encabezado, título, tabla de datos, secciones, firma, adendas y pie de página. También las líneas: tabla, bajo cada sección y de firma.
  - `ROJO` queda solo en el aviso de adendas y en la marca de agua BORRADOR, porque son alertas.
- Los estilos `TituloInforme` y `Subtitulo` declaran `fontName='Helvetica-Bold'`. Ya eran negrita por herencia de los estilos de ReportLab; ahora queda escrito.
- La línea bajo el encabezado del laboratorio pasa de 2 puntos en azul a 0.75 en negro.
- **Pruebas:** 3 nuevas en `PdfInformeTests` (`informes/tests.py`), que espían el lienzo al generar el PDF:
  - el PDF, finalizado con adenda o borrador, solo usa negro y el rojo de las alertas;
  - los títulos van en negrita y en negro;
  - el encabezado lleva una línea fina negra.

**Por qué:** observación del usuario en la prueba manual del 2026-10-05: el informe debe verse sobrio, como un documento clínico impreso, sin azul y con los títulos en negrita.

## 2026-10-05

### Botones del aviso "Tienes cambios sin guardar"

**Qué se cambió**
- `frontend/src/pages/InformePage.jsx` y `frontend/src/index.css`: el aviso de D-13 usa clases propias (`.aviso-salir` y `.aviso-salir-acciones`) en lugar de `.modal-card-sm` y `.form-actions`.
  - El recuadro mide hasta 520 px y los tres botones caben en una fila.
  - Si no caben, pasan a otra línea. En pantallas de 480 px o menos se apilan a todo el ancho, con "Guardar y salir" arriba.
  - Sin el margen inferior de 2rem de `.form-actions`, ya no sobra espacio debajo de los botones.
- `.form-actions`, que usan los demás formularios, no cambia. Los bordes y la tipografía se cambiarán en el rediseño del Bloque B.
- **Pruebas:** no hay prueba automática nueva. Es un cambio solo de CSS, y jsdom (el entorno de las pruebas) no calcula tamaños ni posiciones. Se comprueba en la prueba manual anotada en `docs/progreso.md`. Las 134 pruebas del frontend siguen pasando.

**Por qué:** el usuario vio en el navegador que los tres botones no cabían en el recuadro de 380 px. La fila no permitía pasar a otra línea y estaba alineada a la derecha, así que "Seguir editando" quedaba cortado por la izquierda, y sobraba espacio debajo.

### Finalizar, vista previa y cerrar sesión con cambios sin guardar (ampliación de D-13)

**Qué se cambió**
- **Finalizar** (`frontend/src/pages/InformePage.jsx`): si hay cambios sin guardar, primero se guardan (`guardarCambiosPendientes()`). Si la validación falla o el servidor los rechaza, no se finaliza y se muestra qué falta. Antes se finalizaba lo que estaba en el servidor: lo escrito en los últimos segundos (o con datos no válidos) se perdía, y la pantalla quedaba en solo lectura mostrándolo como si estuviera guardado.
- **Vista previa del PDF de un borrador:** con la misma regla, el PDF muestra lo que hay en pantalla.
- **Cerrar sesión:**
  - "Salir" (`Navbar.jsx`) ya no cierra la sesión: navega a la ruta nueva `/salir` (`pages/CerrarSesionPage.jsx`), que la cierra y lleva a `/login`.
  - Si hay un informe con cambios sin guardar, el aviso de D-13 aparece antes, con la sesión todavía abierta, así que "Guardar y salir" funciona.
  - Antes, cerrar sesión borraba la sesión primero y el aviso no podía aparecer.
- **Pruebas:**
  - 8 nuevas en `InformePage.test.jsx`: finalizar sin cambios, con cambios, con cambios no válidos y con rechazo del servidor; vista previa con cambios y con cambios no válidos; cerrar sesión con "Salir sin guardar" y con "Guardar y salir".
  - `Navbar.test.jsx` (1) y `CerrarSesionPage.test.jsx` (2), los dos nuevos.
  - El frontend pasa de 123 a 134 pruebas.
- **Documentación:** `docs/decisiones.md` (ampliación de D-13), `CLAUDE.md`, `README.md` y `docs/progreso.md`.

**Por qué:** se encontró al hacer el punto 3 de "Pendientes", y el usuario aprobó el arreglo el 2026-10-05. También pidió que cerrar sesión mostrara el mismo aviso si era sencillo, y lo era.

### Aviso al salir con cambios sin guardar y autoguardado de borradores (decisión D-13, Pendientes, punto 3)

**Qué se cambió**
- **Aviso al salir** (`frontend/src/pages/InformePage.jsx`):
  - En un informe que se puede editar, si hay cambios sin guardar, salir por el menú, "Cancelar" o un enlace muestra el aviso "Tienes cambios sin guardar" con tres botones: **Seguir editando**, **Salir sin guardar** y **Guardar y salir**.
  - "Guardar y salir" valida primero. Si falta algo (por ejemplo, el paciente) o el servidor rechaza los datos, no se sale y la página muestra qué falta.
  - Al cerrar la pestaña o recargar, el navegador muestra su propio aviso (`beforeunload`).
  - No se frena la salida hacia `/login` (cerrar sesión), porque para entonces la sesión ya se cerró.
- **Autoguardado:** solo en un borrador que ya existe y que el usuario puede editar. Se guarda en el servidor 5 segundos después del último cambio (`ESPERA_AUTOGUARDADO_MS`), y solo si el formulario pasa la validación. Un informe nuevo no se autoguarda, para no gastar números de petición (D-7). Nada se guarda en el navegador.
- **Indicador** junto al título: "Cambios sin guardar", "Cambios sin guardar: hay datos obligatorios o incompletos", "Guardando…" o "Guardado automáticamente a las hh:mm". Lo anuncian los lectores de pantalla (`role="status"`).
- **Organización de `InformePage`:**
  - `calcularErrores()` separa la validación de mostrar los errores (la usa el autoguardado);
  - `armarPayload()` y `guardarEnServidor()` son comunes al botón, al autoguardado y a "Guardar y salir";
  - `erroresDeRespuesta()` convierte los errores de la API.
  - Los códigos CIE-10 normalizados por el backend solo se copian al formulario si no hubo cambios mientras se guardaba.
- **Error que ya existía:** el error del backend sobre `datos_ingresados` ("Faltan campos obligatorios: …") no se mostraba en ninguna parte. Ahora aparece en la alerta de errores.
- **Router** (`frontend/src/App.jsx`): pasa de `<BrowserRouter>` a `createBrowserRouter` y `RouterProvider` (router de datos), que es lo que exige `useBlocker`. Las rutas y las pantallas no cambian, y React Router sigue en la versión 6.
- **Pruebas:**
  - `InformePage.test.jsx` usa `createMemoryRouter`.
  - 13 pruebas nuevas: autoguardado a los 5 s y la espera que se reinicia, sin autoguardar si no es válido, informe nuevo sin autoguardado, nada en el navegador, salir sin cambios, los tres botones, "Guardar y salir" con validación fallida y con rechazo del servidor, salir después del autoguardado, crear un informe sin aviso y `beforeunload`.
  - El frontend pasa de 110 a 123 pruebas.
- **Documentación:** `docs/decisiones.md` (D-13), `CLAUDE.md`, `README.md` y `docs/progreso.md`, con dos casos anotados: finalizar con cambios sin guardar (falta la confirmación del usuario) y cerrar sesión con cambios sin guardar (limitación conocida). También el conflicto entre dos pestañas, para más adelante.

**Por qué:** en la prueba manual del 2026-10-05 el usuario notó que al salir del formulario sin guardar se perdía todo lo escrito. El usuario eligió la opción B el 2026-10-05 (decisión D-13).

### Visor de imágenes del foro (Pendientes, punto 2)

**Qué se cambió**
- `frontend/src/components/VisorImagenes.jsx` (nuevo): miniaturas de las imágenes de una publicación y visor para verlas ampliadas.
  - **Miniaturas:** cada una es un botón ("Ampliar imagen 2 de 3"), de 220 px de alto en lugar de 160.
  - **Visor:** fondo oscuro, la imagen completa sin recortar (hasta el 90 % del ancho y el 80 % del alto de la pantalla), su descripción si la tiene y el contador "2 de 3".
  - **Navegación:** "Imagen anterior" y "Imagen siguiente", también con las flechas del teclado. Con una sola imagen no aparecen.
  - **Cerrar:** botón "Cerrar", la tecla Escape o un clic fuera de la imagen.
- `frontend/src/pages/PublicacionDetallePage.jsx` usa el visor en lugar de las `<img>` sueltas. `index.css` tiene los estilos de las miniaturas y del visor.
- **Pruebas:** 4 nuevas en `PublicacionDetallePage.test.jsx` (abrir una miniatura, anterior y siguiente con botones y teclado, las tres formas de cerrar, una sola imagen sin flechas). El frontend pasa de 106 a 110 pruebas.

**Por qué:** en la prueba manual del 2026-10-05 el usuario vio que las imágenes del foro eran pequeñas (recortadas a 160 px) y no se podían abrir en grande. No se agrega ninguna librería.

### Datos del paciente separados de su etiqueta en el informe (Pendientes, punto 1)

**Qué se cambió**
- `frontend/src/components/informe/SelectorPaciente.jsx`: en la tarjeta "Paciente" del informe, los cuatro datos (paciente, identificación, edad y sexo) pasan a ser una lista de definiciones: la etiqueta en un `<dt>` y el valor en un `<dd>`. Antes eran dos `<span>` seguidos.
- `frontend/src/index.css`: clase `.datos-paciente`, con la etiqueta pequeña y gris encima del valor, en columnas.
- **Pruebas:** nueva en `SelectorPaciente.test.jsx`, que comprueba que cada etiqueta y su valor van separados. El frontend pasa de 105 a 106 pruebas.

**Por qué:** en la prueba manual del 2026-10-05 el usuario vio los datos pegados a su etiqueta ("Nombreluis"). Pasaba solo en pantalla: el PDF arma el texto de otra forma y se veía bien. Con `<dt>`/`<dd>` la separación está en la estructura, no solo en el aspecto, y los lectores de pantalla anuncian bien cada dato.

### Documentación: pendientes de la prueba manual

**Qué se cambió:** `docs/progreso.md` tiene una sección nueva, "Pendientes", con las observaciones del usuario en la prueba manual. Están divididas en Bloque A (funcional: datos del paciente pegados a su etiqueta, imágenes del foro sin ampliar, pérdida de lo escrito al salir del informe) y Bloque B (estética: colores del PDF y rediseño general). La rama de trabajo pasa a ser `ajustes-prueba-manual`, creada desde `main`.

**Por qué:** a pedido del usuario, para registrar las observaciones antes de trabajar el Bloque A.

### Documentación: `docs/progreso.md` resumido y al día

**Qué se cambió** (solo documentación; el código no cambia)
- **"Dónde estamos":** se resume en pocas líneas con el estado actual: proyecto, rama de trabajo, informe v2 terminado y unido a `main`, forma de trabajar y cantidad de pruebas. Se quitan el historial de uniones a `main` y el detalle de cada etapa, que ya están en la tabla "Hecho", en este CHANGELOG y en git (commits "docs: registrar la unión…").
- **Tabla "Hecho":** dos filas nuevas con datos que solo estaban en el párrafo que se resumió: la prueba manual final del 2026-10-05 (`420b91f`) y la unión de `informe-v2` a `main` (`64c6e22`).
- **"Siguiente paso":**
  - la numeración saltaba del 3 al 5; ahora va de 1 a 5, y la referencia "(punto 6)" pasa a "(punto 5)";
  - las ideas de la hoja de ruta coinciden con la del README; ya no menciona la descripción microscópica, que existe desde la etapa 5 del informe v2;
  - las instrucciones para unir a `main` dicen ahora que se hace con fast-forward, sin pull request, porque `gh` no está instalado. Ese dato estaba antes en el historial de uniones.
- Se revisó que el README siga coherente con `progreso.md` (hoja de ruta y pendientes de producción); no necesitó cambios.
- "Dónde estamos" deja solo la ubicación actual del proyecto: se quita el dato de su traslado de Descargas al Escritorio (2026-10-03), a pedido del usuario.

**Por qué:** a pedido del usuario. "Dónde estamos" se había vuelto un historial largo y difícil de leer, y "Siguiente paso" tenía la numeración rota y una idea ya hecha.

### Usuarios en /admin/ con el UserAdmin de Django

**Qué se cambió**
- `backend/accounts/admin.py`: `Usuario` se registra con el `UserAdmin` de Django en lugar de un `ModelAdmin` común. `UsuarioCreationForm` y `UsuarioChangeForm` adaptan los formularios de Django al modelo `Usuario`.
  - **Al crear un usuario** se piden la contraseña dos veces (con los validadores de Django), el rol, el nombre completo, la especialidad y el registro médico. La contraseña se guarda cifrada.
  - **En la ficha** de un usuario, la contraseña se ve en solo lectura y se cambia con el formulario de Django. Hay una sección "Datos de PathoLab" con rol, nombre completo, teléfono, especialidad, registro médico y activo.
  - Se mantienen la lista, los filtros y la búsqueda de antes.
- **Pruebas:** nueva `AdminUsuariosTests` en `backend/accounts/tests.py` (3): crear un usuario cifra la contraseña y guarda el rol y el registro médico, ese usuario puede iniciar sesión, y la ficha no muestra la contraseña en un campo de texto. El backend pasa de 242 a 245 pruebas.
- **Documentación:** `CLAUDE.md`, `README.md` (usuarios de prueba) y `docs/progreso.md`.

**Por qué:** al preparar la prueba manual final se vio que crear un usuario en `/admin/` guardaba la contraseña tal cual. Django esperaba un hash, así que ese usuario no podía iniciar sesión. Además, la ficha de cualquier usuario mostraba el hash de su contraseña en un campo de texto editable. El usuario aprobó el arreglo el 2026-10-05.

### Enlaces legales en el login y en las páginas legales sin sesión

**Qué se cambió**
- `frontend/src/pages/LoginPage.jsx`: la pantalla de login muestra el pie de página (`Footer`) con "Política de Privacidad" y "Términos y Condiciones", debajo del formulario y con colores claros sobre el fondo oscuro (`index.css`).
- `frontend/src/App.jsx` (`LegalRoute`): sin sesión, las páginas legales muestran también el pie y un enlace "← Volver al inicio de sesión". Antes solo se llegaba a ellas escribiendo la dirección, y no había forma de volver al login.
- **Pruebas:** nuevo `frontend/src/App.test.jsx` (3): el login muestra los dos enlaces, desde el login se abre la política, y una página legal sin sesión tiene el pie y el enlace de vuelta. El frontend pasa de 102 a 105 pruebas.
- **Documentación:** `CLAUDE.md` (rutas) y `docs/progreso.md`. En `progreso.md` también se corrige el paso de preparación de la prueba manual (`patologo2` se crea con `create_user` y no en `/admin/`) y se anota el hallazgo de las contraseñas en `/admin/`.

**Por qué:** en la prueba manual final el usuario no encontró los enlaces legales en el login. La política de privacidad debe poder leerse antes de iniciar sesión, sobre todo ahora que la aplicación guarda datos de salud de pacientes.

### Informe v2, etapa 9: cierre

**Qué se cambió**
- **Política de privacidad** (`frontend/src/pages/PoliticaPrivacidadPage.jsx`):
  - Lista los datos de los pacientes (documento, nombres, fecha de nacimiento, sexo y EPS) y aclara qué no se guarda.
  - Lista el contenido clínico del informe (solicitud, macroscópica, microscópica, diagnósticos CIE-10, comentarios y adendas) y el registro médico de los usuarios.
  - Secciones nuevas: "Datos sensibles" (Ley 1581 de 2012, art. 5; Resolución 1995 de 1999) e "Integridad de los informes" (adendas, datos congelados y PDF de borrador sin validez).
  - El responsable del tratamiento pasa a ser la institución que opera la plataforma. Dice "contraseñas almacenadas con hash" en lugar de "cifrado de contraseñas", y "anatomía patológica" en lugar de "patología clínica".
- **"Última actualización"** en la política de privacidad y en los términos (`TerminosCondicionesPage.jsx`): es una fecha fija (5 de octubre de 2026). Antes mostraba la fecha del día en que se abría la página, así que siempre parecía recién actualizada.
- **Nombre del producto:** "Patología Clínica" → "Anatomía Patológica" en `LoginPage.jsx`, en `frontend/index.html` (descripción y título de la pestaña) y en el título del README. La patología clínica es el laboratorio clínico; esta aplicación hace informes de anatomía patológica, como dice el título del PDF.
- **README, revisión completa:**
  - el diagrama de arquitectura incluye la app `pacientes`, los diagnósticos y las adendas;
  - la estructura menciona `ConsecutivoPeticion`, `Adenda` y `admin.py`, y el paso de `seed_data` dice todo lo que crea;
  - los permisos mencionan D-8, D-9 y D-12, y la nota de `/admin/` dice que la vía normal de corrección es la adenda;
  - el flujo incluye la vista previa del borrador;
  - Seguridad: integridad del informe, nombre del PDF sin datos del paciente y enlace a la política de privacidad;
  - Documentación: enlace a `docs/propuesta-informe-v2.md`;
  - hoja de ruta: registro de accesos.
- **Postman** (`PathoLab_API.postman_collection.json`):
  - variable `refresh_token`, que guarda el login;
  - peticiones nuevas "Renovar token" (guarda el `refresh` rotado, D-6), "Cerrar sesión", "Editar paciente" y "Editar informe (borrador)";
  - descripción general actualizada.
  - Se comprobaron contra una copia de la base: renovar (el `refresh` viejo deja de servir), editar paciente, crear y editar informe (el CIE-10 se normaliza), editar un finalizado (400) y cerrar sesión (el `refresh` deja de servir).
- **D-7 a D-11:** se revisó el código y ya las cumple; no hubo cambios.
- **Documentación:** `docs/propuesta-informe-v2.md` (etapa 9 hecha) y `docs/progreso.md`, con la lista de comprobación de la prueba manual final, que reemplaza las pruebas de navegador que estaban sueltas.

**Por qué:** es la etapa 9 de `docs/propuesta-informe-v2.md`. La aplicación ahora guarda datos de salud de pacientes, y la política de privacidad debía decirlo; el README y Postman debían quedar al día con las etapas 1 a 8. El usuario aprobó los seis puntos el 2026-10-05, incluido el cambio de nombre.

### PDF de un borrador: vista previa solo para su autor o un admin (decisión D-12)

**Qué se cambió**
- **API** (`backend/informes/views.py`): `GET /api/informes/{id}/pdf/` de un borrador responde 403 si quien lo pide no es su autor ni un admin. El archivo de un borrador se llama `informe_P-AAAA-NNNNN_borrador.pdf`. El PDF de un informe finalizado no cambia: lo descargan todos los roles.
- **PDF** (`backend/informes/utils.py`): `CanvasNumerado` recibe `marca_agua` y, en un borrador, dibuja "BORRADOR" grande, en diagonal y casi transparente en cada página.
- **Frontend** (`InformePage.jsx`): en un borrador el botón dice "Vista previa (borrador)" y solo lo ven el autor y el admin. El archivo descargado lleva el sufijo `_borrador`. En un informe finalizado sigue diciendo "Exportar PDF".
- **Pruebas:**
  - Backend, de 235 a 242: `PdfBorradorTests` (7: autor, admin, otro patólogo, auditor, finalizado para todos y marca de agua en cada página o en ninguna).
  - Se ajustan `DescargaPdfTests` (el auditor descarga un informe finalizado; el nombre del borrador lleva `_borrador`) y `NumeroPeticionTests`.
  - Frontend, de 100 a 102: el botón de vista previa, el de un finalizado y que el borrador ajeno no ofrezca el PDF.
- **Documentación:** `docs/decisiones.md` (D-12), `docs/propuesta-informe-v2.md` (5.2), `README.md`, `CLAUDE.md` y la descripción de "Descargar PDF" en Postman.

**Por qué:** en la prueba manual el usuario notó que cualquier usuario podía descargar el PDF de un borrador. Aunque decía "sin validez", una hoja suelta podía imprimirse y circular. Se conserva la vista previa para el autor, que puede revisar el PDF antes de finalizar, y la marca de agua hace imposible confundirla con un informe definitivo. Decisión del usuario del 2026-10-05.

### Informe v2, etapa 8: adendas

**Qué se cambió**
- **Modelo `Adenda`** (`backend/informes/models.py`, migración `informes/0011_adenda`). Campos:
  - `informe` y `autor` (los dos `PROTECT`);
  - `numero` (1, 2, 3... dentro de cada informe; único por `informe` + `numero`);
  - `motivo` (máximo 300 caracteres) y `texto`;
  - `fecha` (`auto_now_add`) y `firma` (JSON con nombre, especialidad y registro médico de quien la crea, congelados).
  - La firma sale de la función nueva `firma_de(usuario)`, que ahora también usa `Informe.firma_actual()` (antes armaba el mismo diccionario por su cuenta).
- **API** (`backend/informes/views.py`, `serializers.py`):
  - `GET /api/informes/{id}/adendas/` (todos los roles) y `POST /api/informes/{id}/adendas/` (autor del informe o admin; el auditor y los demás patólogos reciben 403).
  - El POST responde 400 si el informe es un borrador o si quien crea la adenda no tiene registro médico, aunque sea admin. No hay PUT, PATCH ni DELETE (405).
  - El número se calcula con el informe bloqueado (`select_for_update`). Si aun así choca con la restricción única, responde 400 "intente de nuevo" en lugar de un error 500.
  - Agregar una adenda no cambia el informe: ni su contenido, ni `fecha_actualizacion`, ni `fecha_informe`, ni los datos congelados.
  - `AdendaSerializer` solo acepta `motivo` y `texto`. `InformeSerializer` devuelve la lista `adendas` (solo lectura), cargada con `prefetch_related` solo en las rutas de detalle. El listado no cambia.
- **`/admin/`** (`backend/informes/admin.py`): `AdendaInline` en el informe, de solo lectura (no se agregan, cambian ni borran).
- **PDF** (`backend/informes/utils.py`):
  - Si el informe tiene adendas, bajo el título va el aviso en rojo "Este informe tiene N adenda(s); ver al final." (en singular con 1).
  - Después de la firma va la sección "ADENDAS", con número, fecha (hora de Bogotá), motivo, texto y la firma de cada una, todo escapado con `texto_seguro()` (I-3). Cada adenda va entera en una página si cabe, y el título de la sección va con la primera.
  - Las líneas de la firma pasan a `_lineas_firma()`, que comparten la firma del informe y la de las adendas.
- **Frontend:**
  - `components/informe/SeccionAdendas.jsx` (nuevo): tarjeta "Adendas", solo en informes finalizados. Muestra la lista. Al autor y al admin les ofrece "+ Agregar adenda", con motivo y texto, y pide confirmación antes de guardar ("Las adendas no se pueden modificar ni borrar"). Muestra los errores del backend, como la falta de registro médico.
  - `InformePage.jsx` la dibuja después de la Firma y fuera de su `<form>`, porque la adenda se guarda con su propia petición. La adenda nueva se agrega a la lista sin recargar.
  - `SeccionFirma.jsx` exporta `LineasFirma` y `formatoFechaHora` para reutilizarlos. `index.css` tiene los estilos de las adendas.
- **Pruebas:**
  - Backend, de 212 a 235: `AdendaTests` (19) y 4 en `PdfInformeTests` (orden, aviso en singular, sin adendas no hay aviso, texto escapado).
  - Frontend, de 89 a 100: `SeccionAdendas.test.jsx` (8) y 3 en `InformePage.test.jsx`.
- **Documentación:** `README.md` (características, permisos, API, pruebas, flujo), `CLAUDE.md`, `docs/propuesta-informe-v2.md`, `docs/progreso.md` y la colección de Postman ("Agregar adenda" y "Ver adendas").

**Por qué:** es la etapa 8 de `docs/propuesta-informe-v2.md` y aplica la decisión D-9. D-3 no permite modificar un informe finalizado, y las adendas permiten corregirlo sin perder lo que se entregó, dejando constancia de quién corrigió qué y cuándo. El usuario aprobó el plan el 2026-10-05, incluido que un admin necesite su propio registro médico para firmar una adenda.

## 2026-10-04

### Informe v2, etapa 7: PDF nuevo

**Qué se cambió**
- **PDF** (`backend/informes/utils.py`): `generar_pdf_informe` se reescribe con la estructura de la sección 5 de `docs/propuesta-informe-v2.md` y se divide en funciones pequeñas (`_estilos`, `_encabezado`, `_tabla_datos`, `_titulo`, `_seccion` y `_firma`). En orden, el PDF tiene:
  - **Encabezado fijo de demostración:** "PathoLab — Laboratorio de Patología (demostración)" y "Santiago de Cali, Colombia", sin teléfono (respuesta P-9), en las constantes `ENCABEZADO_LABORATORIO` y `ENCABEZADO_CIUDAD`. No se lee de la configuración (ver "Por qué").
  - **Tabla de datos en dos columnas:** paciente e identificación, edad y sexo, médico tratante y EPS, servicio y número de petición, fecha de ingreso y fecha de informe. Después, a todo el ancho, la orden externa (solo si existe) y los estudios solicitados. Los datos salen de `datos_impresos()`, así que un informe finalizado imprime los datos congelados (D-10). Un dato vacío se imprime "—", y un informe antiguo sin paciente también genera el PDF.
  - Título **"INFORME DE ANATOMÍA PATOLÓGICA"**, el tipo de estudio y, debajo y en letra más pequeña, la patología y el tipo de muestra.
  - Descripción macroscópica, descripción microscópica, diagnósticos y comentarios. El título de una sección no queda solo al final de una página (`CondPageBreak` de 4 cm).
  - **Firma**, solo en los informes finalizados: línea, nombre, especialidad y "Registro médico N.º …". No se parte entre dos páginas.
  - **Pie en cada página:** "N.º de petición P-AAAA-NNNNN · Página X de Y · Generado el dd/mm/aaaa hh:mm", con la hora de Bogotá (M-10). Lo dibuja `CanvasNumerado`, el `canvasmaker`, al final, cuando ya se sabe el total de páginas.
  - **Borrador:** no lleva firma y dice "BORRADOR — SIN VALIDEZ" en la celda de fecha de informe y al principio del pie de cada página.
  - **Se quitan** la sección "DATOS CLÍNICOS", que imprimía `datos_ingresados` en bruto (esos datos ya están redactados en la macroscópica), el título "INFORME DE PATOLOGÍA CLÍNICA" y la tabla de metadatos anterior.
  - Todo el texto del usuario sigue pasando por `texto_seguro()` (I-3), incluidos el nombre del paciente, el médico tratante y los estudios solicitados.
- **`Informe.edad_paciente(paciente)`** (`backend/informes/models.py`): calcula la edad a la fecha de ingreso (o a la de creación, en informes antiguos). Antes ese cálculo estaba en `InformeSerializer.get_paciente_datos`, que ahora la usa. Así la API y el PDF no repiten el cálculo, y la API devuelve lo mismo que antes.
- **Pruebas** (de 204 a 212 en el backend):
  - Nueva `PdfInformeTests` (11): tabla en dos columnas, fila de orden externa, datos congelados, texto escapado en la tabla, informe sin paciente, borrador sin firma y sin validez, orden de las partes, sin "DATOS CLÍNICOS", encabezado de demostración, pie en cada página y pie del borrador.
  - `PdfConTextoDelUsuarioTests`: el marcado que estaba en `datos_ingresados` pasa a la descripción microscópica. Se elimina la prueba de la hora del pie, que ahora cubre `PdfInformeTests`.
  - `FinalizacionTests`: se eliminan las dos pruebas que leían la tabla anterior del PDF ("Patólogo:"). Las reemplazan las de `PdfInformeTests`.
- **Documentación:** `README.md` (descripción del PDF y hoja de ruta), `CLAUDE.md`, `docs/propuesta-informe-v2.md` y `docs/progreso.md`. El frontend no cambia.

**Por qué:** es la etapa 7 de `docs/propuesta-informe-v2.md`: el PDF tiene el orden y los datos de un informe real de anatomía patológica, y una hoja suelta se puede identificar por su pie. El 2026-10-04 el usuario decidió dejar el encabezado fijo y no agregar por ahora `LABORATORIO_NOMBRE`, `LABORATORIO_DIRECCION` ni `LABORATORIO_TELEFONO`; hacerlo configurable queda como propuesta futura. También aprobó poner "BORRADOR — SIN VALIDEZ" en el pie de cada página de un borrador, para que no circule una hoja que parezca definitiva.

### Informe v2, etapa 6: firma y finalización

**Qué se cambió**
- **Usuario** (`backend/accounts/models.py`, migración `accounts/0002_registro_medico`): campo nuevo `registro_medico` (texto, opcional).
  - `UsuarioSerializer` lo devuelve (perfil, login y lista de usuarios), pero es de **solo lectura**, como el rol (C-1). Con un registro falso se podrían firmar informes (decisión D-8).
  - `RegistroSerializer` lo acepta: solo un admin crea usuarios. También se edita en `/admin/`, donde además aparece en la lista y en la búsqueda.
- **Informe** (`backend/informes/models.py`, migración `informes/0010_finalizacion`): campos nuevos `fecha_informe` y `datos_finalizacion` (JSON). Los dos son `editable=False`: no se escriben por la API ni en `/admin/`, donde se ven en solo lectura.
  - `requisitos_faltantes()`: lo que falta para finalizar (D-8): paciente, al menos un diagnóstico, descripción microscópica si el estudio es de histología y registro médico **del autor**.
  - `datos_para_congelar()`: paciente (nombre, documento, fecha de nacimiento y sexo), nombres de la EPS y del servicio, y firma del autor (nombre, especialidad y registro médico).
  - `datos_impresos()`: los datos congelados si el informe está finalizado y los actuales si es borrador.
  - **Migración de datos:** en los informes que ya estaban finalizados, `fecha_informe` toma el valor de `fecha_actualizacion` (la mejor aproximación disponible) y `datos_finalizacion` se llena con los datos actuales. Usa `update()` para no cambiar `fecha_actualizacion` y tiene función de reversa.
- **`pacientes/models.py`:** el cálculo de la edad pasa a la función `edad_en_texto(nacimiento, fecha)`, que usan `Paciente.edad_en()` y los datos congelados. El resultado no cambia.
- **`POST /api/informes/{id}/finalizar/`** (`backend/informes/views.py`):
  - Bloquea el informe con `select_for_update` dentro de una transacción, para que dos peticiones a la vez no lo finalicen dos veces.
  - Si faltan requisitos, responde 400 con todos a la vez: `{"detail": "No se puede finalizar el informe. …", "requisitos": [...]}`. Antes finalizaba cualquier borrador.
  - Si todo está bien, en la misma transacción cambia el estado, fija `fecha_informe` y guarda `datos_finalizacion`.
- **`InformeSerializer`:** campos nuevos `fecha_informe` (solo lectura) y `firma` (`{nombre, especialidad, registro_medico}` del autor). En un informe finalizado, `paciente_datos`, `eps_nombre`, `servicio_nombre` y `firma` salen de los datos congelados; corregir después el paciente, la EPS, el servicio o el usuario ya no cambia el informe (D-10). La edad se sigue calculando a la fecha de ingreso.
- **PDF** (`backend/informes/utils.py`): la fila "Patólogo" usa la firma de `datos_impresos()` (la congelada si está finalizado), y se agregan las filas "Registro médico" y, si está finalizado, "Fecha de informe" (hora de Bogotá). La estructura completa sigue en la etapa 7.
- **`seed_data`:** `patologo1` recibe el registro médico ficticio `RM-PRUEBA-0001`. Si `patologo1` ya existía sin registro, se le asigna; un registro ya asignado no se cambia.
- **Frontend:**
  - `components/informe/SeccionFirma.jsx` (nuevo): tarjeta "Firma" al final de un informe guardado, de solo lectura. En un informe finalizado muestra la firma y la fecha de informe; en un borrador, quién firmará o, si el autor no tiene registro médico, un aviso.
  - `InformePage.jsx`: si no se puede finalizar, muestra la lista de requisitos que faltan.
  - `PerfilPage.jsx`: muestra el registro médico en solo lectura (no se envía al guardar) y avisa a un patólogo sin registro que no podrá finalizar informes.
  - `index.css`: estilos `.alert-warning`, `.alert-lista` y `.firma-informe`.
- **Pruebas:**
  - 25 nuevas en el backend (de 179 a 204): `RegistroMedicoTests` (6), `FinalizacionTests` (18) y `MigracionFinalizacionTests` (1).
  - El ayudante de `PermisosInformeTests` crea informes completos (paciente, diagnóstico, microscópica y autor con registro médico), para que sus pruebas de finalizar sigan siendo válidas.
  - `MigracionNumeroPeticionTests` y `MigracionContenidoTests` vuelven también `accounts` a `0001_initial`: con la columna `registro_medico` el modelo histórico de `Usuario` no podía crear usuarios.
  - 10 nuevas en el frontend (de 79 a 89): `SeccionFirma.test.jsx` (4), 3 en `InformePage.test.jsx` y 3 en `PerfilPage.test.jsx`.
- **Documentación:** `README.md`, `CLAUDE.md`, `docs/propuesta-informe-v2.md`, `docs/progreso.md` y la colección de Postman ("Ver mi perfil" y "Finalizar informe").

**Por qué:** es la etapa 6 de `docs/propuesta-informe-v2.md` y cumple las decisiones D-8 (registro médico, firma del autor y requisitos para finalizar) y D-10 (datos congelados al finalizar). El usuario aprobó el 2026-10-04 dar el registro ficticio a `patologo1` en `seed_data` (si no, en una base existente no se podría finalizar ningún informe) y usar ya en el PDF actual la firma congelada, para que un PDF finalizado no cambie si después se corrige el nombre del autor.

### Informe v2, etapa 5: contenido del informe

**Qué se cambió**
- **Modelo** (`backend/informes/models.py`, migración `0009_contenido`, escrita a mano porque `makemigrations` pregunta de forma interactiva por el cambio de nombre):
  - `Informe.notas` pasa a llamarse `Informe.comentarios` (`RenameField`). Lo que ya estaba escrito se conserva; lo comprueba `MigracionContenidoTests`.
  - Campo nuevo `Informe.descripcion_microscopica` (texto, opcional).
  - Modelo nuevo `Diagnostico`: `informe` (`CASCADE`), `orden`, `descripcion` y `codigo_cie10` (opcional). Restricción única `informe` + `orden`.
- **`InformeSerializer`** (`backend/informes/serializers.py`):
  - Devuelve y acepta `descripcion_microscopica`, `comentarios` y `diagnosticos`. **`notas` ya no existe en la API.**
  - `diagnosticos` es una lista anidada (`DiagnosticoSerializer`). Si se envía, reemplaza a la anterior en la misma transacción que el informe; si no se envía, no cambia. Una lista vacía los quita todos. El orden es el de la lista.
  - Máximo 20 diagnósticos. La descripción no puede estar vacía ("Escriba la descripción del diagnóstico.").
  - El código CIE-10 se pasa a mayúsculas, sin espacios, y se le agrega el punto que falte (`c443` → `C44.3`, `M8090` → `M80.90`). Si no es una letra, dos cifras y, de forma opcional, un punto con uno o dos caracteres, responde 400.
  - Un borrador se puede guardar sin diagnósticos. La regla de "al menos uno para finalizar" es de la etapa 6.
- **`InformeViewSet`:** en las rutas de detalle (ver, editar, PDF, finalizar) carga los diagnósticos en una sola consulta (`prefetch_related`). El listado no los pide.
- **PDF** (`backend/informes/utils.py`):
  - Después de la descripción macroscópica imprime "DESCRIPCIÓN MICROSCÓPICA", "DIAGNÓSTICOS" (numerados: `1. Carcinoma basocelular nodular (CIE-10: C44.3)`) y "COMENTARIOS", que reemplaza a "NOTAS ADICIONALES".
  - Todo el texto nuevo pasa por `texto_seguro()` (I-3).
  - Las secciones usan una función auxiliar `seccion()` en lugar de repetir el título y la línea.
  - La estructura completa del PDF sigue para la etapa 7.
- **`/admin/`:** los diagnósticos se ven y se editan dentro del informe (`DiagnosticoInline`).
- **Frontend:**
  - `components/informe/ListaDiagnosticos.jsx` (nuevo): tarjeta "Diagnósticos" con una fila por diagnóstico (descripción y CIE-10 opcional) y botones para agregar, quitar, subir y bajar. Muestra los errores del backend junto a cada fila. En solo lectura no muestra botones.
  - `InformePage.jsx`:
    - tarjetas nuevas "Descripción microscópica", "Diagnósticos" y "Comentarios" (antes "Notas adicionales"), en el orden del informe real;
    - el texto generado pasa a la tarjeta "Descripción macroscópica";
    - no deja guardar un diagnóstico sin descripción;
    - después de guardar muestra los códigos CIE-10 ya normalizados por el backend;
    - los errores por fila de los diagnósticos ya no se aplanan a texto.
  - `index.css`: estilos de las filas de diagnósticos y del título del texto generado.
- **Pruebas:**
  - 17 nuevas en el backend (de 162 a 179): `ContenidoInformeTests` (16) y `MigracionContenidoTests` (1). Las pruebas que usaban `notas` ahora usan `comentarios`.
  - 9 nuevas en el frontend (de 70 a 79): `ListaDiagnosticos.test.jsx` (4) y 5 en `InformePage.test.jsx`.
- **Documentación:** `README.md`, `CLAUDE.md`, `docs/propuesta-informe-v2.md`, `docs/progreso.md` y la colección de Postman ("Crear informe" con microscópica, diagnósticos y comentarios).

**Por qué:** es la etapa 5 de `docs/propuesta-informe-v2.md`. El informe real tiene descripción microscópica, diagnósticos y comentarios, y el cambio de nombre de `notas` a `comentarios` lo aprobó el usuario (P-5). El usuario confirmó el 2026-10-04 tres detalles:
- el PDF actual ya muestra las secciones nuevas, para que los diagnósticos no falten en el PDF hasta la etapa 7;
- los diagnósticos se reordenan con botones de subir y bajar;
- la búsqueda no incluye los diagnósticos por ahora.

### Informe v2, etapa 4: datos de la solicitud

**Qué se cambió**
- **Campos nuevos en `Informe`** (`backend/informes/models.py`, migración `0008_datos_solicitud`):
  - `paciente`: `PROTECT`, admite `null` solo por los informes de antes de esta etapa.
  - `medico_tratante` y `estudios_solicitados`: texto libre.
  - `fecha_ingreso`.
  - `eps`, que es la del momento del estudio y no cambia si el paciente cambia de EPS, y `servicio`. Los dos son `PROTECT` y opcionales.
  - `tipo_estudio`: por defecto, histología.
  - Los informes antiguos quedan sin paciente y se muestran como "No registrado".
- **`Paciente`** tiene ahora las propiedades `nombre_completo` y `documento` ("CC PRUEBA0001").
- **`InformeSerializer`**:
  - Al crear, el paciente es obligatorio ("Seleccione un paciente."). Un informe antiguo sin paciente se puede seguir editando, pero a un informe que ya tiene paciente no se le puede quitar.
  - Si no se envía `fecha_ingreso`, se usa la fecha local de hoy. No puede estar en el futuro ni ser anterior al nacimiento del paciente. Esto también se comprueba al cambiar de paciente.
  - Si un informe nuevo no envía `eps`, toma la EPS actual del paciente, siempre que siga activa (decisión del usuario en la etapa 4). Si se envía `eps: null`, el informe queda sin EPS.
  - No se puede asignar una EPS ni un servicio desactivados, pero el informe que ya los tenía los conserva. Es la misma regla que se aplica a los pacientes.
  - Devuelve `paciente_datos` (nombre, documento, fecha de nacimiento, sexo y **edad a la fecha de ingreso**), `eps_nombre` y `servicio_nombre`.
  - El código de validación se dividió en dos métodos: `_validar_paciente_y_fecha_ingreso` y `_validar_campos_obligatorios`, que es el de I-2 sin cambios.
- **`InformeListSerializer`** agrega `paciente`, `paciente_nombre`, `paciente_documento` y `tipo_estudio`.
- **`InformeViewSet`**:
  - Hace `select_related` de `paciente`, `eps` y `servicio`, para que el listado no haga una consulta por fila (M-4).
  - `?q=` busca también por el nombre y el documento del paciente. Cada palabra debe aparecer en algún campo, así que "ficticio uno" encuentra a "Paciente Ficticio Uno".
  - Filtro nuevo `?paciente=`.
- **Endpoint nuevo `GET /api/pacientes/{id}/informes/`** (acción `informes` de `PacienteViewSet`): historial paginado del paciente, con los campos del listado de informes.
- **Borrados que ahora responden 400** en lugar de un error 500 (como I-1):
  - un paciente con informes;
  - un servicio en uso por algún informe (`ServicioViewSet.destroy`, que pide desactivarlo);
  - una EPS en uso. El mensaje de la EPS ahora cuenta pacientes e informes.
- **`/admin/` de informes:** muestra paciente y tipo de estudio, busca por paciente y elige el paciente con búsqueda (`autocomplete_fields`).
- **Ejecutor de pruebas** (`backend/config/test_runner.py`, `TEST_RUNNER` en `settings.py`):
  - Durante las pruebas usa `DummyCache`, así que los límites de peticiones no se acumulan de una prueba a otra.
  - Antes, como SQLite repite los ids de usuario, todas las peticiones de un minuto se sumaban al mismo usuario. Con las pruebas nuevas se pasaba de 120 por minuto y aparecían fallos 429 que no tenían que ver con lo probado.
  - Ninguna prueba depende de esos límites.
- **Frontend:**
  - `InformePage.jsx` se reorganiza con el orden del informe real:
    - **Paciente**: `components/informe/SelectorPaciente.jsx`, que busca por documento o nombre, permite crear el paciente ("Nuevo paciente") y muestra su nombre, identificación, edad y sexo.
    - **Datos de la solicitud**: `components/informe/DatosSolicitud.jsx`, con médico tratante, fecha de ingreso (hoy por defecto), EPS, servicio, orden externa y estudios solicitados.
    - **Estudio**: tipo de estudio (de `/api/opciones/`), patología y tipo de muestra.
    - Al elegir el paciente se precarga su EPS si sigue activa. Una EPS o un servicio desactivados se ven como "(desactivada)" y se conservan.
    - No deja guardar sin paciente. Al pulsar Enter en la búsqueda del paciente se busca y no se envía el informe.
  - `components/FormularioPaciente.jsx` (nuevo): el formulario de paciente que estaba dentro de `PacientesPage`, ahora compartido con el selector. Se dibuja con un portal en `document.body`, porque el informe ya es un `<form>`.
  - `utils/formularios.js` (nuevo): `hoyISO()` y `conOpcionActual()`, que antes estaba repetido en el código.
  - `PacientesPage.jsx`: botón "Informes" en cada fila, para todos los roles, que abre el historial del paciente con enlaces a cada informe.
  - `pages/CatalogosPage.jsx` (nuevo, ruta `/catalogos`, enlace "Catálogos" en el Navbar):
    - administra las EPS y los servicios: agregar, renombrar, activar o desactivar y eliminar;
    - si el backend no deja borrar porque el elemento está en uso, muestra el motivo;
    - el auditor solo lee.
  - `BuscarPage.jsx`:
    - columnas N.º de petición, Paciente, Tipo de estudio, Patología, Autor, Fecha y Estado;
    - el texto de ayuda menciona la búsqueda por paciente.
  - `DashboardPage.jsx` agrega la columna Paciente.
  - `components/CeldaPaciente.jsx` dibuja esa celda: nombre y documento, o "No registrado".
  - `hooks/useOpciones.js`:
    - un componente que se monta después de recibir las opciones las tiene desde el primer render;
    - antes, el formulario de paciente abría con los menús vacíos durante un instante y el navegador bloqueaba el envío por los campos `required`.
- **Pruebas:**
  - 28 nuevas en el backend (de 134 a 162):
    - `DatosSolicitudTests` (19);
    - `BorrarCatalogosEnUsoPorInformesTests` (3);
    - `ConsultasListadoInformesTests` (1);
    - `HistorialYBorradoConInformesTests` (5).
  - Las pruebas que crean informes por la API ahora envían un paciente ficticio.
  - 24 nuevas en el frontend (de 46 a 70):
    - `SelectorPaciente.test.jsx` (7);
    - `CatalogosPage.test.jsx` (7);
    - 5 en `InformePage.test.jsx`, 2 en `PacientesPage.test.jsx`, 2 en `BuscarPage.test.jsx` y 1 en `DashboardPage.test.jsx`.
- **Documentación:** `README.md`, `CLAUDE.md`, `docs/propuesta-informe-v2.md`, `docs/progreso.md` y la colección de Postman ("Crear informe" con paciente y datos de la solicitud, "Historial de informes del paciente" y el filtro `paciente`).

**Por qué:** es la etapa 4 de `docs/propuesta-informe-v2.md`, aprobada por el usuario el 2026-10-04 junto con tres detalles:
- la pantalla de catálogos va en `/catalogos`;
- la EPS del paciente se copia si el informe no la envía;
- toda la etapa va en un solo commit.

El informe real lleva en su encabezado al paciente y los datos de la solicitud. La EPS se guarda en el informe porque el paciente puede cambiar de EPS y el informe debe mostrar la que tenía en el momento del estudio. La edad se calcula a la fecha de ingreso para que no cambie al reimprimir el informe. Todos los datos de prueba son ficticios.

### Informe v2, etapa 3: pacientes

**Qué se cambió**
- **Modelo `Paciente`** en `backend/pacientes/models.py`, con la migración `0002_paciente`:
  - Campos: tipo y número de documento, nombres, apellidos, fecha de nacimiento, sexo y EPS (opcional, `PROTECT`).
  - El tipo y el número de documento no se repiten (`paciente_documento_unico`).
  - Se ordena por apellidos y nombres. Tiene admin con búsqueda.
  - **La edad no se guarda.** `edad_en(fecha)` la da como texto: en años cumplidos ("45 años"), en meses si el paciente es menor de 1 año ("8 meses") y en días si es menor de 1 mes ("28 días"). Quien nace un 29 de febrero cumple años el 1 de marzo en los años no bisiestos. La propiedad `edad` la calcula a la fecha de hoy.
- **`PacienteSerializer`** en `pacientes/serializers.py`:
  - Normaliza el número de documento: lo guarda sin espacios ni puntos y en mayúsculas.
  - Si el documento se repite, responde 400 con un mensaje en español. Por eso desactiva el validador automático de DRF (`validators = []`).
  - Rechaza una fecha de nacimiento en el futuro o de hace más de 130 años.
  - Quita los espacios sobrantes de nombres y apellidos.
  - No deja asignar una EPS desactivada, pero el paciente que ya la tenía la conserva (confirmado por el usuario).
  - Devuelve `edad` y `eps_nombre`.
- **`PacienteViewSet`** en `/api/pacientes/` y `/api/pacientes/{id}/`:
  - `?q=` busca por documento, nombres y apellidos. Cada palabra debe aparecer en alguno de ellos, así que "ficticio uno" encuentra a "Paciente Ficticio Uno". Usa `select_related('eps')`.
  - Solo acepta ids numéricos (`lookup_value_regex`), y en `pacientes/urls.py` la ruta `eps` se registra antes, para que `/api/pacientes/eps/` siga funcionando.
- **Permiso nuevo** `EsPatologoOAdminYSoloAdminBorra` en `accounts/permissions.py`: todos leen, patólogo y admin crean y editan, y solo el admin borra (decisión D-11).
- **Borrar una EPS que usa un paciente** (`EPSViewSet.destroy`) responde 400 en lugar de un error 500: "No se puede eliminar: esta EPS tiene N paciente(s) asociado(s). Desactívela en su lugar." Es lo mismo que I-1 hizo con las patologías.
- **`seed_data`** crea 2 pacientes ficticios (`PRUEBA0001` y `PRUEBA0002`) y no los duplica si se ejecuta otra vez.
- **Frontend:**
  - `src/hooks/useOpciones.js` (nuevo): pide `/api/opciones/` una sola vez por sesión del navegador. Si la petición falla, se vuelve a intentar la próxima vez. `etiquetaDe()` da la etiqueta de un valor. `reiniciarOpciones()` se usa en las pruebas.
  - `src/pages/PacientesPage.jsx` (nuevo, ruta `/pacientes`):
    - Búsqueda y tabla paginada de 20 en 20, con documento, nombre, edad, sexo y EPS.
    - Formulario para crear y editar, con los errores del backend junto a cada campo. El calendario no ofrece fechas futuras.
    - Si la EPS del paciente está desactivada, aparece como "(desactivada)" y se conserva.
    - "Editar" se ve para patólogo y admin; "Eliminar", con confirmación, solo para el admin.
  - `App.jsx` (ruta `/pacientes`) y `Navbar.jsx` (enlace "Pacientes", visible para todos los roles).
- **Pruebas:**
  - 26 nuevas en el backend (de 108 a 134): `EdadTests` (6), `PacienteAPITests` (18: permisos, edad, validaciones, documento repetido, EPS desactivada, búsqueda y `seed_data`) y `BorrarEPSConPacientesTests` (2).
  - 8 nuevas en el frontend (de 38 a 46), en `PacientesPage.test.jsx`.
- **Documentación:**
  - `README.md`: características, permisos, estructura, API, datos de prueba, pruebas y seguridad.
  - `CLAUDE.md`, `docs/propuesta-informe-v2.md` y `docs/progreso.md`.
  - Colección de Postman: carpeta nueva "3. Pacientes" y variable `{{paciente_id}}`.

**Qué queda para la etapa 4**
- El historial `GET /api/pacientes/{id}/informes/` y la respuesta 400 al borrar un paciente con informes. Los dos necesitan `Informe.paciente`, que se agrega en esa etapa. Por ahora un admin puede borrar cualquier paciente, porque ninguno tiene informes todavía.

**Por qué:** es la etapa 3 de `docs/propuesta-informe-v2.md`. El informe real lleva el nombre, el documento, la edad, el sexo y la EPS del paciente, y un mismo paciente puede tener varios informes. La edad se calcula y no se guarda, para que siempre sea correcta y el informe pueda mostrarla a su fecha de ingreso. Solo se guardan los datos que aparecen en el informe, porque los datos de salud son sensibles (Ley 1581 de 2012). Todos los datos de prueba son ficticios.

### Informe v2, etapa 2: catálogos de EPS y servicios, tipo de estudio y `GET /api/opciones/`

**Qué se cambió**
- **App nueva `backend/pacientes/`** (rutas en `/api/pacientes/`). Por ahora tiene solo:
  - el modelo `EPS` (`nombre` único, `activa`), con su admin, y `EPSViewSet` en `/api/pacientes/eps/` (filtro `?activa=true`/`false` y `?search=`);
  - las listas fijas `TipoDocumento` (CC, TI, RC, CE, PA, PPT, MS, AS) y `Sexo` (Femenino, Masculino, Indeterminado), como `TextChoices`.
  - El modelo `Paciente` llega en la etapa 3. La migración `0001_initial` crea solo `EPS`.
- **`backend/informes/`:**
  - Modelo `Servicio` (`nombre` único, `activo`), con su admin, y `ServicioViewSet` en `/api/servicios/` (filtro `?activo=true`/`false` y `?search=`). Migración `0007_servicio`.
  - `Informe.TipoEstudio` (`TextChoices`): Histología, Citología no ginecológica, Citología cérvico-vaginal, Inmunohistoquímica, Estudio intraoperatorio por congelación y Revisión de láminas. Por ahora es solo la lista; el campo `tipo_estudio` se agrega en la etapa 4.
  - `OpcionesView` en `GET /api/opciones/`: devuelve `{sexos, tipos_documento, tipos_estudio}`, cada elemento con `valor` y `etiqueta`, sacados de los `TextChoices`. Cualquier usuario con sesión la lee; no acepta escritura (405).
  - `seed_data` carga 7 servicios y 12 EPS: "Particular", "Otra" y una lista corta de EPS reales. Se puede ejecutar varias veces sin duplicar.
- **`backend/config/catalogos.py` (nuevo):** piezas comunes de los dos catálogos.
  - `NombreCatalogoMixin`: rechaza un nombre repetido aunque cambien las mayúsculas o haya espacios de más ("Sura" y " SURA "), y guarda el nombre sin espacios sobrantes.
  - `filtrar_por_activo()`: aplica el filtro `?activa=` o `?activo=`.
- **Permisos:** los dos catálogos usan `EsPatologoOAdmin`: todos leen y solo patólogo y admin escriben (decisión D-11). Se desactivan en lugar de borrarse (D-4). Mientras nada los use se pueden borrar; la respuesta 400 "en uso" llega en las etapas 3 y 4.
- **`config/settings.py` y `config/urls.py`:** se registra la app `pacientes` y su ruta `/api/pacientes/`.
- **Pruebas:** 18 nuevas en el backend (de 90 a 108).
  - `OpcionesTests` (6): contenido de cada lista, sesión obligatoria y solo lectura.
  - `CatalogoServiciosTests` (6) y `CatalogoEPSTests` (6, en `pacientes/tests.py`): permisos por rol, filtro de activos, desactivar, nombre repetido y `seed_data` sin duplicados.
- **Documentación:** `README.md` (estructura, referencia de la API y pruebas), `CLAUDE.md`, la colección de Postman (Listar servicios, Listar EPS y Opciones), `docs/propuesta-informe-v2.md` y `docs/progreso.md`.

**Por qué:** es la etapa 2 de `docs/propuesta-informe-v2.md`. El informe necesita estas listas para registrar la EPS, el servicio, el sexo, el documento y el tipo de estudio (etapas 3 y 4). Las listas fijas salen de un solo lugar del backend para que el frontend no tenga copias que haya que mantener iguales. Los filtros se llaman como su campo (`activa` en EPS, `activo` en servicios), como `?activa=` en patologías. Los nombres repetidos se rechazan sin importar mayúsculas para no tener dos veces la misma EPS en el menú.

### Informe v2, etapa 1: número de petición automático (decisión D-7)

**Qué se cambió**
- **`backend/informes/models.py`:**
  - Nuevo modelo `ConsecutivoPeticion`: guarda el último número usado en cada año.
  - Nueva función `siguiente_numero_peticion()`: devuelve `P-AÑO-NNNNN` (5 cifras; el consecutivo vuelve a 1 cada año, con el año en hora de Bogotá).
  - `Informe.save()` asigna el número al crear el informe, en la misma transacción que lo guarda. Así también se numeran los informes creados desde `/admin/` o con el ORM.
  - `Informe` pierde `numero_caso` y gana `numero_peticion` (único, no editable) y `numero_orden_externa` (opcional, no único).
- **Migraciones:**
  - `0004_numero_peticion`: contador y campos nuevos.
  - `0005_numerar_informes_existentes`: numera los informes que ya existían, en orden de creación y por año, y deja el contador al día.
  - `0006_quitar_numero_caso`: hace obligatorio y único el número de petición y elimina `numero_caso`. Si se deshace, `numero_caso` vuelve con el número de petición; el valor original no se recupera.
- **`serializers.py`, `views.py`, `admin.py` y `utils.py`:**
  - `numero_peticion` es de solo lectura en la API.
  - La búsqueda `q` incluye el número de petición y la orden externa.
  - El PDF muestra "N.º de petición" (y la orden externa, si existe) y el archivo se llama `informe_P-AÑO-NNNNN.pdf`.
  - En `/admin/`, el número es de solo lectura y el contador solo se puede consultar.
- **`backend/config/settings.py`** (SQLite):
  - Espera hasta 20 s si la base está ocupada (`timeout`).
  - Las pruebas usan el archivo `test_db.sqlite3` (ya cubierto por `*.sqlite3` en `.gitignore`).
- **Frontend:**
  - `InformePage.jsx` ya no pide número de caso; tiene el campo "N.º de orden externa (opcional)" y el título muestra el número de petición, que también da nombre al PDF.
  - `DashboardPage.jsx` y `BuscarPage.jsx` muestran la columna "N.º de petición", y el buscador explica que se puede buscar por él.
  - `PoliticaPrivacidadPage.jsx` describe los datos nuevos.
- **Pruebas:**
  - Backend: 13 nuevas.
    - `NumeroPeticionTests` (11): formato, consecutivo, reinicio por año, no se elige ni se cambia, no se reutiliza, `unique`, orden externa, búsqueda y PDF.
    - `NumeroPeticionConcurrenciaTests`: 10 hilos crean informes a la vez.
    - `MigracionNumeroPeticionTests`: numeración de los informes existentes, incluido un informe del 31/12 a las 23:30 de Bogotá.
    - Se quitó `numero_caso` de las pruebas que ya existían. La prueba del nombre de archivo con caracteres peligrosos se mantiene como defensa.
  - Frontend: 7 nuevas o ajustadas en `InformePage.test.jsx`, `DashboardPage.test.jsx` y `BuscarPage.test.jsx` (nuevo).
- **Documentación:** `README.md`, `CLAUDE.md`, la colección de Postman, `docs/propuesta-informe-v2.md` y `docs/progreso.md`.

**Por qué**
- El número de caso lo escribía el usuario: permitía errores y obligaba a inventar un consecutivo.
- Se usa un contador con `UPDATE` atómico y no "el mayor número + 1". Se comprobó poniendo por un momento esa versión ingenua: la prueba de concurrencia falló las 3 veces que se corrió ("database is locked"). Con el contador pasó las 5 veces.
- Base local: el único informe ("Prueba claudio") quedó como `P-2026-00001`. Se hizo una copia de seguridad antes de migrar. También se comprobó que las migraciones se pueden deshacer y volver a aplicar.

### Se elimina `iniciar_y_probar.ps1`

**Qué se cambió**
- Se borró el script `iniciar_y_probar.ps1` de la raíz y sus menciones en `README.md` y `CLAUDE.md`. Las entradas anteriores de este CHANGELOG y de la auditoría lo siguen nombrando porque describen cómo estaba el proyecto en su momento.

**Por qué**
- A pedido del autor: no se usaba. Para el día a día está `npm run dev`. Para la primera instalación, el README explica paso a paso cómo crear el entorno virtual y el `.env` (con el comando para generar la `SECRET_KEY`), migrar y cargar los datos de prueba.

### Desarrollo: arrancar backend y frontend con un solo comando (`npm run dev`)

**Qué se cambió**
- `package.json` (nuevo, en la raíz): scripts `npm run dev` y `npm test`, con `concurrently` como única dependencia de desarrollo.
- `scripts/entorno.mjs` (nuevo): comprueba que existan el entorno virtual de Python, `backend/.env` y `frontend/node_modules`. Si falta algo, explica el comando para resolverlo. La ruta de Python cambia según el sistema operativo.
- `scripts/dev.mjs` (nuevo):
  - Hace esas comprobaciones y avisa si hay migraciones sin aplicar (`migrate --check`).
  - Arranca Django (8000) y Vite (5173) en la misma terminal, con la salida etiquetada.
  - Si uno de los dos se detiene, detiene también el otro.
  - Si falta el `npm install` de la raíz, también lo explica.
- `scripts/entorno.test.mjs` (nuevo): 8 pruebas con el ejecutor de pruebas que trae Node (`node --test`).
- Documentación: nueva sección **Arrancar el Proyecto** en el `README.md` (también la estructura, la instalación y las pruebas) y comandos en `CLAUDE.md`.

**Por qué**
- Para ver la app había que abrir dos terminales y arrancar el backend y el frontend por separado.
- Se eligió un script de Node en lugar de archivos `.bat` porque funciona en Windows, Mac y Linux, no depende de rutas de un computador concreto, usa una sola terminal y explica qué falta en vez de fallar sin aviso.
- Verificado arrancando `npm run dev`: frontend 200 y login a través del proxy 200. Al detener el backend a la fuerza, el frontend también se detuvo y los dos puertos quedaron libres.

### Corrección: al editar una patología se ven su descripción y su protocolo

**Qué se cambió**
- `frontend/src/pages/PatologiasPage.jsx`: el botón "Editar" pide la patología completa (`GET /api/patologias/{id}/`) antes de abrir el formulario. Si falla, muestra un aviso.
- `frontend/src/pages/PatologiasPage.test.jsx`: prueba nueva. Las pruebas de D-4 se adaptaron a que el formulario se abre después de recibir la respuesta.

**Por qué**
- Fallo encontrado al hacer M-5; no estaba en la auditoría. El formulario se llenaba con los datos del listado, que no incluyen `descripcion` ni `protocolo_medico`. Esos campos aparecían vacíos aunque tuvieran contenido, y al escribir algo se reemplazaba un texto que no se veía.
- No se añadieron esos campos al listado porque también alimenta el selector de "Nuevo informe" (hasta 1000 patologías): se enviarían todos los protocolos sin necesidad.

### Seguridad: cerrar sesión y cambiar la contraseña invalidan el token de renovación (M-11, decisión D-6)

**Qué se cambió**
- `backend/config/settings.py`:
  - Se instaló `rest_framework_simplejwt.token_blacklist`, que añade 12 migraciones con sus tablas.
  - `BLACKLIST_AFTER_ROTATION = True`: al renovar, el token de renovación anterior queda invalidado.
- `backend/accounts/views.py` y `urls.py`:
  - Nuevo `POST /api/auth/logout/` (`LogoutView`), que invalida el `refresh` recibido. No procesa la autenticación (`authentication_classes = []`), para que funcione aunque el token de acceso haya vencido.
  - `CambiarPasswordView` invalida todos los tokens de renovación del usuario y devuelve un par nuevo (`access`, `refresh`), para que la sesión actual siga abierta.
- `frontend/src/api/client.js`: al renovar el token, el interceptor guarda también el `refresh` nuevo. Sin esto, la lista negra habría cerrado la sesión en la segunda renovación.
- `frontend/src/context/AuthContext.jsx`: `logout()` avisa al backend antes de borrar los tokens del navegador.
- `frontend/src/pages/PerfilPage.jsx`: guarda los tokens nuevos al cambiar la contraseña.
- Pruebas:
  - Backend: `CierreDeSesionTests`, 5 pruebas (logout, token inválido, token de acceso vencido, reutilizar un token renovado y cambio de contraseña con dos sesiones abiertas).
  - Frontend: 3 pruebas (interceptor, `logout` y perfil).
- Documentación: tabla de la API y sección de Seguridad del `README.md`, y el frontend en `CLAUDE.md`.

**Por qué**
- Antes, cerrar sesión solo borraba los tokens del navegador. Un token de renovación robado seguía sirviendo hasta 7 días, incluso después de cambiar la contraseña.
- Verificado de punta a punta a través del proxy de Vite. Login; renovar devuelve un `refresh` nuevo; reutilizar el viejo da 401; `logout` con un token de acceso vencido da 200; usar el `refresh` después del logout da 401.
- **En otros computadores** hay que ejecutar `python manage.py migrate`. En el del autor ya se aplicó, después de guardar una copia de seguridad de `db.sqlite3`.

### La hora del pie del PDF usa la zona horaria configurada (M-10)

**Qué se cambió**
- `backend/informes/utils.py`: el pie *"Generado el …"* usa `timezone.localtime()` de Django en lugar de `datetime.now()`.
- `backend/informes/tests.py`: una prueba fija la hora en 03:30 UTC del 4 de octubre y comprueba que el PDF diga "03/10/2026 22:30" (hora de Bogotá).

**Por qué**
- `datetime.now()` devuelve la hora del sistema operativo, no la de `TIME_ZONE = 'America/Bogota'`. En Linux, Django ajusta la zona horaria de todo el proceso y el resultado coincidía; en Windows no puede hacerlo, y en un servidor con otra zona la hora del PDF salía corrida.

### Los errores se muestran en pantalla, no solo en la consola (M-9)

**Qué se cambió**
- `frontend/src/pages/DashboardPage.jsx`: si falla la carga del panel, se muestra *"No se pudo cargar el panel…"*; si falla el borrado de un borrador, se muestra el motivo que devuelve la API.
- `frontend/src/pages/InformePage.jsx`: avisos si no se pueden cargar las patologías o los campos de la patología elegida. Se quitó el último `console.error`, porque ese error ya se mostraba en pantalla.
- Pruebas: `DashboardPage.test.jsx` (nuevo, 2) y 2 nuevas en `InformePage.test.jsx`.

**Por qué**
- Con el backend apagado o ante un error del servidor, el panel se quedaba vacío y el formulario de informe sin opciones, sin ningún aviso. El error solo aparecía en la consola del navegador, que el usuario no ve.

### Foro: el auditor ya no ve el formulario para comentar (M-7)

**Qué se cambió**
- `frontend/src/pages/PublicacionDetallePage.jsx`: el formulario de comentarios solo se muestra si el usuario puede escribir (`canWrite`).
- `frontend/src/pages/PublicacionDetallePage.test.jsx` (nuevo): 2 pruebas, una para el auditor y otra para el patólogo.

**Por qué**
- El auditor tiene solo lectura y la API le rechaza los comentarios (403). Aun así veía el formulario, y al usarlo recibía un error.

### Foro: temas iniciales y botón para crear temas (M-6, decisión D-5)

**Qué se cambió**
- `backend/informes/management/commands/seed_data.py`: crea 4 temas del foro: *Casos clínicos*, *Técnicas de laboratorio*, *Investigación* y *Dudas y consultas*. Usa `get_or_create`, así que ejecutarlo varias veces no duplica nada.
- `frontend/src/pages/ForoPage.jsx`: botón **"+ Tema"** (solo para patólogos y administradores, según D-1) con un formulario de nombre y descripción.
- Pruebas: `TemasInicialesTests` (2, backend) y una nueva en `ForoPage.test.jsx`.
- `README.md`: `seed_data` y la descripción del foro.

**Por qué**
- El foro empezaba sin temas, y la app no tenía forma de crearlos: solo se podía desde `/admin/`.
- Para tener los temas en una base de datos que ya existe, basta con volver a ejecutar `python manage.py seed_data`.

### Las patologías se pueden desactivar en lugar de borrarse (M-5, decisión D-4)

**Qué se cambió**
- `backend/informes/views.py`: `GET /api/patologias/` acepta `?activa=true` o `?activa=false`.
- `frontend/src/pages/InformePage.jsx`: al **crear** un informe, el selector pide solo las patologías activas. Al **editar** pide todas, para que se vea la patología de un informe viejo aunque esté desactivada.
- `frontend/src/pages/PatologiasPage.jsx`: casilla **"Activa"** en el formulario de patologías; las nuevas se crean activas.
- Pruebas: `PatologiasActivasTests` (3, backend), `PatologiasPage.test.jsx` (2, frontend, nuevo) y 2 en `InformePage.test.jsx`.
- `README.md`: nuevo filtro `?activa=` y una frase en las características.

**Por qué**
- El selector de "Nuevo informe" ofrecía también las patologías desactivadas, y la app no tenía forma de activarlas o desactivarlas (solo desde `/admin/`).
- Una patología con informes no se puede borrar (I-1): desactivarla permite retirarla sin perder el historial.

### Corrección: los menús desplegables muestran todos los elementos, no solo los primeros 20

**Qué se cambió**
- `backend/config/paginacion.py` (nuevo): clase `PaginacionEstandar`, que sigue paginando de 20 en 20 pero admite `?page_size=` hasta 1000. Se configura en `settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']`.
- `frontend/src/api/client.js`: constante `LISTA_COMPLETA` (`{ page_size: 1000 }`). Se usa en el selector de patologías de "Nuevo informe", en los temas del foro y en las categorías y patologías de la pantalla Patologías.
- Pruebas: `TamanoDePaginaTests` (3, backend) y una nueva en `InformePage.test.jsx`.
- Documentación: `CLAUDE.md` y la nota de paginación de la API en el `README.md`.

**Por qué**
- Fallo encontrado durante la limpieza; no estaba en la auditoría. Los listados vienen de 20 en 20 y esas pantallas solo leían la primera página. Con más de 20 patologías, las demás no se podían elegir al crear un informe, ni se veían en la tabla de Patologías.

### Rendimiento: los listados ya no hacen una consulta por fila (M-4)

**Qué se cambió**
- `backend/informes/views.py` y `backend/foro/views.py`: los listados de categorías, temas y publicaciones cuentan sus totales en la misma consulta, con `annotate(Count(...))`. El de publicaciones ya no precarga los comentarios completos, solo las imágenes, que se usan para la portada.
- `backend/informes/serializers.py` y `backend/foro/serializers.py`:
  - `total_patologias` y `total_publicaciones` usan el valor contado y, si no existe (al crear o editar un solo elemento), cuentan aparte.
  - La portada del listado se toma de las imágenes ya precargadas; antes `.first()` hacía una consulta por publicación.
- Se indica el orden de forma explícita (`order_by`) en esos tres listados. Al usar `annotate(Count)`, Django ignora el `Meta.ordering` del modelo: sin esto, el foro habría dejado de mostrar primero las publicaciones fijadas.
- `backend/informes/tests.py`: nueva clase `ConsultasPorListadoTests` con 4 pruebas:
  - el número de consultas no crece al pasar de 5 a 20 elementos;
  - crear una categoría o un tema devuelve su total;
  - los totales y la portada son correctos;
  - los listados conservan su orden.

**Por qué**
- Medido con 20 elementos, los listados de categorías y temas hacían 22 consultas y el de publicaciones 25. Ahora hacen 2, 2 y 3.

### Limpieza: código duplicado y comentarios en español (M-3, M-13)

**Qué se cambió**
- Backend:
  - Nueva propiedad `Usuario.nombre_visible` (nombre completo o, si está vacío, el nombre de usuario). Reemplaza la expresión `nombre_completo or username`, que estaba repetida en 8 lugares: 5 serializers (que ahora usan `CharField(source='autor.nombre_visible')`), el PDF, el token del login y `Usuario.__str__`. La API responde igual.
  - Se tradujeron al español 52 docstrings, comentarios y el texto de ayuda de `seed_data`, en 11 archivos. También se corrigió el docstring de `Patologia`, que todavía mencionaba el campo borrado en M-1.
- Frontend:
  - `src/constants.js` (nuevo): `ROL_LABELS` (antes copiado en 3 archivos) y `ESTADOS_INFORME`.
  - `src/components/EstadoBadge.jsx` (nuevo): la etiqueta de estado del informe, que se repetía en el Dashboard, el Buscador y la página del informe. Antes, cualquier estado distinto de "borrador" se mostraba como "Finalizado"; ahora un estado desconocido se muestra tal cual.
  - `api/client.js`: nueva función `resultados(data)`, que reemplaza `data.results || data` (7 apariciones en 5 páginas).
  - Se tradujeron 11 comentarios.
- Pruebas: `NombreVisibleAutorTests` (2, backend) y `EstadoBadge.test.jsx` (3, frontend). Los mocks de `InformePage.test.jsx` y `ForoPage.test.jsx` ahora conservan las funciones reales del módulo `api/client`.
- Documentación: `CLAUDE.md` (dónde está el código compartido) y una corrección en la auditoría (ver M-13).

**Por qué**
- Con el código repetido, un cambio (por ejemplo, el nombre de un rol) había que hacerlo en varios sitios, y era fácil olvidar alguno.
- La regla 4 de `CLAUDE.md` pide comentarios y documentación en español.

### Limpieza: código y archivos sin usar (M-1, M-2)

**Qué se cambió**
- Backend:
  - Importaciones sin usar: `status` y `permissions` en `accounts/views.py`, `os` en `config/settings.py`, y `inch` y `TA_LEFT` en `informes/utils.py`.
  - Se borró la clase `LoginSerializer` (`accounts/serializers.py`), que no se usaba.
  - Se quitó el campo **`Patologia.campos_requeridos`** del modelo y del serializer, con la migración `informes/migrations/0003_quitar_campos_requeridos.py`. La API ya no devuelve ese campo.
- Frontend:
  - `LoginPage.jsx`: se quitaron `ROL_LABELS` y la variable `user`, que no se usaban.
  - `AuthContext.jsx`: se quitaron `isPatologo` e `isAuditor`. `canWrite` ahora compara directamente el rol.
  - `InformePage.jsx`: se quitaron dos `console.log` de depuración.
- Archivos borrados: `frontend/public/favicon.svg`, `frontend/public/icons.svg`, `frontend/src/assets/hero.png`, `typescript.svg` y `vite.svg` (restos de la plantilla de Vite que nadie usaba). También se borró la carpeta local `frontend/dist/`, que no está en git.
- `frontend/src/context/AuthContext.test.jsx` (nuevo): 3 pruebas que comprueban qué roles pueden escribir.

**Por qué**
- El código que no se usa confunde a quien lee el proyecto. `campos_requeridos` parecía definir los campos obligatorios, pero nunca se leía ni se llenaba (estaba vacío en las 14 patologías). Los obligatorios se definen en `Plantilla.obligatorio`.
- `frontend/dist/` tenía compilada una versión vieja del frontend, todavía con el token en la URL del PDF (I-5). Se regenera con `npm run build`.
- Al quitar `isPatologo` se detectó que `canWrite` dependía de él. Sin el ajuste, los patólogos habrían perdido el permiso de escritura en la interfaz. La prueba nueva de `AuthContext` cubre ese caso: se comprobó que falla si se reintroduce el error.
- **En otros computadores** hay que ejecutar `python manage.py migrate` para aplicar la migración 0003. En el del autor ya se aplicó, después de guardar una copia de seguridad de `db.sqlite3`.

### Corrección: los campos obligatorios de los informes se validan siempre (I-2)

**Qué se cambió**
- `backend/informes/serializers.py`:
  - `InformeSerializer.validate()` valida los campos obligatorios de la plantilla aunque `datos_ingresados` llegue vacío o no llegue. Si un `PATCH` no trae `datos_ingresados` (por ejemplo, porque solo cambia las notas), valida los datos ya guardados.
  - Nueva función `esta_vacio()`: solo cuenta como vacío `None`, un texto en blanco o una lista o diccionario vacíos. **`0` y `false` son respuestas válidas.**
- `backend/informes/tests.py`: nueva clase `CamposObligatoriosTests` con 7 pruebas.
- `README.md`: vuelve a indicar que los campos obligatorios se validan en el backend; la frase se había quitado en I-12 porque no era cierta.

**Por qué**
- La condición `if patologia and datos:` saltaba toda la validación si `datos_ingresados` venía vacío. Desde la API se podía crear un informe sin ningún campo obligatorio.
- `if not valor` trataba el número `0` como "vacío", así que un informe con "Número de ganglios: 0" (un dato clínico real) se rechazaba si llegaba como número por la API.
- La colección de Postman y `iniciar_y_probar.ps1` siguen funcionando: envían todos los campos obligatorios.

### Documentación: README reescrito y colección de Postman actualizada (I-12)

**Qué se cambió**
- `README.md`, reescrito por completo:
  - Se eliminaron las líneas con caracteres de control dañados y los bloques de código rotos.
  - Nueva sección **Roles y Permisos**, con una tabla según las decisiones D-1, D-2 y D-3. Corrige que el administrador no es el único que gestiona el catálogo.
  - Referencia de la API completa, sacada de las rutas reales: autenticación, catálogo (con categorías), informes (con estadísticas) y foro.
  - Nuevas secciones de **Pruebas Automáticas**, **Seguridad** y **Documentación del Proyecto**.
  - Estructura del proyecto actualizada (foro, pruebas, `docs/`).
  - Se corrigieron afirmaciones que no eran ciertas: el PDF no lleva "firma del patólogo", sino su nombre; la búsqueda no es "en tiempo real"; las pruebas exigen Node 22.12+, no Node 18; y `GET /api/plantillas/` lo puede leer cualquier usuario autenticado.
- `PathoLab_API.postman_collection.json`, rehecha:
  - 14 peticiones en 4 carpetas: autenticación, catálogo, informes y foro.
  - El token se configura a nivel de colección y el login lo guarda automáticamente.
  - "Crear informe" y "Crear publicación" guardan su `id` para las peticiones siguientes.
  - El número de caso usa `{{$timestamp}}` para no repetirse.

**Por qué**
- El README tenía 15 líneas dañadas (por ejemplo, "dmin" en lugar de `admin`), no mencionaba el foro ni las categorías, y su tabla de la API estaba incompleta.
- En la colección de Postman, "Listar patologías" no enviaba el token y siempre respondía 401, "Descargar PDF" usaba el informe 1 escrito a mano y "Crear informe" fallaba la segunda vez por repetir el número de caso.
- La colección nueva se ejecutó completa contra una copia de la base de datos: las 14 peticiones respondieron 200 o 201.

### Corrección: la dirección del backend ya no está fija en el código del frontend (I-10)

**Qué se cambió**
- `frontend/src/api/client.js`: `API_URL` deja de ser `'http://localhost:8000/api'` y pasa a ser `VITE_API_URL + '/api'` (se quita una posible barra final). Con `VITE_API_URL` vacía, el frontend llama a `/api/...` en el mismo sitio que la página; en desarrollo esas peticiones las reenvía el proxy de `vite.config.js` al backend. La renovación del token usa la misma dirección.
- `frontend/.env.example`: `VITE_API_URL` vacía, con comentarios sobre cuándo darle valor.
- El `frontend/.env` local del usuario también se dejó con `VITE_API_URL` vacía, con su permiso. Ese archivo no está en git.
- `frontend/src/api/client.test.js` (nuevo): 3 pruebas (sin variable, con variable y con barra final).
- Documentación: pasos de instalación del frontend en el `README.md` (incluido crear el `.env`, y una nota corregida sobre el proxy) y sección del frontend en `CLAUDE.md`.

**Por qué**
- Con la dirección fija en `localhost:8000`, la app solo funcionaba en el computador del desarrollador. Publicada en un servidor, el navegador de cada visitante buscaría el backend en su propio equipo.
- `VITE_API_URL` y el proxy de Vite ya existían, pero el código no los usaba.
- Verificado con las 11 pruebas del frontend, con `vite build` (el resultado ya no contiene `localhost:8000`) y con un login real a través del proxy (Vite en 5199 → Django en 8000: respuesta 200 con token).

### Seguridad: Vite 5 → 6.4 y Vitest 3 → 5 (I-9, parte b)

**Qué se cambió**
- `frontend/package.json` y `package-lock.json`: `vite` ^5.4.0 → ^6.4.3 y `vitest` ^3.2.7 → ^5.0.3. `@vitejs/plugin-react` 4.7 ya era compatible con Vite 6 y no cambió. `vite.config.js` no necesitó cambios.
- `README.md` (insignia y lista de tecnologías) y `CLAUDE.md`: versión de Vite actualizada.

**Por qué**
- Las vulnerabilidades de las herramientas de desarrollo (Vite, esbuild ≤ 0.24.2 y la de Vitest 3, GHSA-82fw-gwwq-j7x9) solo se corregían con versiones principales nuevas. `npm audit` (todo) pasa de 6 vulnerabilidades (1 alta) a **2 moderadas**, que son las de `react-router` ya analizadas en I-9a.
- Se eligió Vite 6.4 en lugar de 7: es el salto más pequeño que cierra todas las vulnerabilidades de desarrollo. Ninguno de los cambios incompatibles de Vite 6 (Sass, `resolve.conditions`, `json.stringify`, modo librería) afecta a la configuración de PathoLab.
- Verificado con las 8 pruebas del frontend, `vite build` y arrancando el servidor de desarrollo, que sirvió la página y transformó `main.jsx` y `App.jsx` sin errores.

### Seguridad: actualización de dependencias del frontend sin cambiar de versión principal (I-9, parte a)

**Qué se cambió**
- `frontend/package-lock.json`: se ejecutó `npm audit fix` (sin `--force`). `package.json` no cambió. Versiones de producción actualizadas: `axios` 1.13.6 → 1.20.0, `react-router-dom` y `react-router` 6.30.3 → 6.30.6, `@remix-run/router` 1.23.2 → 1.23.4, `follow-redirects` 1.15.11 → 1.16.1 y `form-data` 4.0.5 → 4.0.6, además de dependencias internas de estos paquetes. También se actualizaron versiones menores de herramientas de desarrollo (Babel, PostCSS, nanoid, browserslist).

**Por qué**
- `npm audit --omit=dev`, que solo cuenta lo que llega a la app publicada, pasó de **6 vulnerabilidades (2 altas)** a **2 moderadas**. Las altas estaban en `axios` y `form-data`.
- Las 2 que quedan son de `react-router` y solo se corrigen con React Router 7 (cambio de versión principal). Se revisó que **no afectan a PathoLab**:
  - [GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6), redirección abierta en `<Link>`/`useNavigate`: la app solo navega a rutas fijas o con ids numéricos que devuelve la API, nunca a rutas escritas por el usuario.
  - [GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg): solo afecta a renderizado en servidor (SSR) con `createBrowserRouter`. PathoLab usa `BrowserRouter` sin SSR.
- Verificado con las 8 pruebas del frontend y con `vite build`.

### Seguridad: el registro y el cambio de contraseña aplican los validadores de Django (I-11)

**Qué se cambió**
- `backend/accounts/serializers.py`:
  - Nueva función `validar_contrasena()`, que llama a `validate_password()` de Django y convierte su error en un 400 de DRF.
  - `CambiarPasswordSerializer` la usa en `validate_new_password()`.
  - `RegistroSerializer` la usa en `validate()`, con un `Usuario` temporal sin guardar para poder detectar contraseñas parecidas al usuario. Los errores salen en el campo `password`.
- `backend/accounts/tests.py`: nueva clase `ValidacionContrasenasTests` con 5 pruebas.
- Documentación: nota en `CLAUDE.md` sobre los usuarios de `seed_data`.

**Por qué**
- `settings.py` define 4 validadores (longitud mínima, contraseñas comunes, solo números y parecido al usuario), pero ningún serializer los aplicaba. Se aceptaban contraseñas como `12345678` o `password123`.
- Los mensajes salen en español (`LANGUAGE_CODE = 'es'`), y la página de perfil ya los muestra sin cambios en el frontend.

### Seguridad: en el foro solo un admin fija publicaciones y los comentarios no se pueden mover (I-8)

**Qué se cambió**
- `backend/foro/serializers.py`:
  - `PublicacionSerializer.get_fields()` vuelve `fijado` de solo lectura si quien hace la petición no es admin.
  - `ComentarioSerializer.get_fields()` vuelve `publicacion` de solo lectura al editar un comentario existente.
  - Como en C-1, los valores no permitidos se ignoran en silencio (comportamiento estándar de DRF).
- `backend/foro/tests.py`: nueva clase `CamposProtegidosForoTests` con 5 pruebas.
- Documentación: sección de permisos de `CLAUDE.md`.

**Por qué**
- El modelo dice que "los administradores pueden fijar publicaciones importantes", pero cualquier patólogo podía crear o editar su publicación con `"fijado": true` y dejarla siempre arriba del foro.
- El autor de un comentario podía cambiar su campo `publicacion` con un `PATCH` y moverlo a otra publicación.
- El frontend no necesitó cambios: no tiene botón para fijar y solo envía `publicacion` al crear un comentario.

### Seguridad: límite real de tamaño y validación de las imágenes del foro (I-6)

**Qué se cambió**
- `backend/config/settings.py`:
  - Nuevo ajuste `FORO_MAX_TAMANO_IMAGEN = 10 MB`.
  - Se corrigió el comentario que decía que `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` limitaban la subida; no lo hacen.
  - Se quitó `FILE_UPLOAD_MAX_MEMORY_SIZE` para usar el valor por defecto de Django (2,5 MB), así los archivos grandes van a disco y no a RAM.
  - Se añadió una nota: en producción, el servidor web debe limitar el tamaño de las peticiones (por ejemplo, `client_max_body_size` en Nginx).
- `backend/foro/views.py` (`subir_imagenes`): antes de guardar nada revisa todos los archivos. Si alguno supera el límite o **no es una imagen real** (se abre con Pillow mediante `forms.ImageField().to_python()`), responde 400. Las imágenes se guardan dentro de `transaction.atomic()`.
- `frontend/src/pages/ForoPage.jsx`:
  - Revisa el tipo y el tamaño de las imágenes **antes** de crear la publicación.
  - Los errores del formulario se muestran dentro del modal; antes quedaban ocultos detrás.
  - Si la publicación se crea pero el backend rechaza las imágenes, cierra el formulario y lo avisa, para que reintentar no cree una publicación duplicada.
- Pruebas: `backend/foro/tests.py` (nuevo, 5 pruebas; las imágenes se guardan en una carpeta temporal) y `frontend/src/pages/ForoPage.test.jsx` (nuevo, 4 pruebas).
- Documentación: `CLAUDE.md` (ajuste `FORO_MAX_TAMANO_IMAGEN`).

**Por qué**
- El "límite de 10 MB" no existía: los ajustes usados no limitan el tamaño de los archivos subidos, y se podía llenar el disco del servidor.
- Durante el arreglo se descubrió algo más grave: `ImagenPublicacion.objects.create()` no valida el `ImageField`, así que el foro aceptaba cualquier archivo con extensión de imagen. Por ejemplo, un HTML con `<script>` llamado `foto.png`.
- En el frontend, una imagen rechazada dejaba una publicación sin imágenes, y al reintentar se creaba otra duplicada.

### Seguridad: el token de sesión ya no viaja en la URL al descargar el PDF (I-5)

**Qué se cambió**
- `backend/informes/views.py` y `backend/informes/urls.py`: se eliminaron la vista `descargar_pdf` (`/api/descargar-pdf/<id>/<filename>?token=...`), su ruta y el `import csrf_exempt` que solo ella usaba. El PDF se descarga únicamente por `GET /api/informes/{id}/pdf/`, que exige el token en la cabecera `Authorization`.
- `backend/informes/views.py`: en `exportar_pdf`, el nombre del archivo se limpia con `re.sub(r'[^A-Za-z0-9\-]', '_', ...)`. Antes solo se reemplazaban los espacios, y unas comillas en el número de caso rompían la cabecera `Content-Disposition`.
- `frontend/src/pages/InformePage.jsx`: `downloadPDF` pide el PDF con Axios (`responseType: 'blob'`) y lo guarda con un enlace temporal `blob:`. Ya no crea un formulario oculto con el token. Si la descarga falla, muestra *"No se pudo descargar el PDF."* (antes fallaba sin avisar).
- Pruebas: `DescargaPdfTests` (5 pruebas del backend) y `frontend/src/pages/InformePage.test.jsx` (1 prueba del frontend).
- Documentación: sección de PDF de `CLAUDE.md`.

**Por qué**
- Una URL con `?token=` queda guardada en el historial del navegador y en los registros del servidor y de los proxies. Cualquiera que la viera podía usar la cuenta durante las 8 horas de vida del token.
- Había dos endpoints que hacían lo mismo. Ahora queda uno, autenticado igual que el resto de la API.

### Corrección: la página de perfil ya no queda en blanco si falla la carga (M-8) y primeras pruebas del frontend

**Qué se cambió**
- `frontend/src/pages/PerfilPage.jsx`: la carga del perfil pasa a la función `cargarPerfil()` y tiene `.catch`. Si falla, se muestra *"No se pudo cargar tu perfil. Intenta de nuevo."* con un botón **Reintentar**, en lugar de dibujar el formulario con `perfil = null`.
- Herramientas de prueba del frontend, instaladas solo como `devDependencies`: `vitest` 3.2, `@testing-library/react` 16, `@testing-library/dom` 10, `@testing-library/jest-dom` 6 y `jsdom` 26.
- `frontend/package.json`: scripts `npm test` (`vitest run`) y `npm run test:watch`.
- `frontend/vite.config.js`: sección `test` (entorno `jsdom`, archivo de preparación `src/test/setup.js`).
- `frontend/src/test/setup.js` (nuevo): añade las comprobaciones de jest-dom y limpia el DOM entre pruebas.
- `frontend/src/pages/PerfilPage.test.jsx` (nuevo): 3 pruebas que simulan la API con `vi.mock`. Cubren el error de carga, el botón Reintentar y la carga correcta.
- Documentación: comandos de prueba en el `README.md` y en `CLAUDE.md`.

**Por qué**
- Si `GET /auth/perfil/` fallaba (backend caído, error 500), la página leía `perfil.nombre_completo` con `perfil = null`. React lanzaba `TypeError` y, como la app no tiene un Error Boundary, toda la pantalla quedaba en blanco.
- El frontend no tenía forma de probar errores como este. Ahora tiene Vitest, que también servirá para los próximos hallazgos del frontend.
- **Nota de seguridad:** `npm audit` marca una vulnerabilidad moderada en Vitest 3 (GHSA-82fw-gwwq-j7x9). Solo afecta al ejecutar las pruebas en local y no llega a la app publicada. La corrige Vitest 5, que exige Vite 6 o superior, así que se resolverá junto con I-9. Las vulnerabilidades de producción no cambiaron (siguen las 6 de I-9).

### Corrección: estadísticas reales en el dashboard y paginación en el buscador (I-4)

**Qué se cambió**
- `backend/informes/views.py`: nuevo endpoint `GET /api/informes/estadisticas/` (acción `estadisticas` de `InformeViewSet`). Devuelve `{total, borradores, finalizados}` contando todos los informes en una sola consulta (`Count` agrupado por estado) y respeta los mismos filtros que el listado.
- `frontend/src/pages/DashboardPage.jsx`: las tarjetas de totales usan el endpoint nuevo. "Informes recientes" sigue mostrando los 10 más nuevos del listado.
- `frontend/src/pages/BuscarPage.jsx`: paginación con botones "Anterior" y "Siguiente", el texto "Mostrando X–Y de Z" y el total real en el título. Al cambiar de página se conservan los filtros de la última búsqueda.
- `frontend/src/index.css`: estilo `.paginacion`.
- `backend/informes/tests.py`: nueva clase `EstadisticasYPaginacionTests` con 5 pruebas sobre los totales, los permisos, la segunda página y los filtros.
- Documentación: endpoint nuevo en la tabla de la API del README y en `CLAUDE.md`.

**Por qué**
- La API devuelve los informes de 20 en 20, pero el dashboard contaba solo la primera página. Con 25 informes mostraba "Total 20" y "Finalizados 10" en lugar de 25 y 15. El buscador mostraba "Resultados (20)" y no permitía ver el resto.

### Corrección: el PDF muestra literal el texto del usuario y respeta los saltos de línea (I-3)

**Qué se cambió**
- `backend/informes/utils.py`: nueva función `texto_seguro()`. Escapa `<`, `>` y `&` con `xml.sax.saxutils.escape` y convierte los saltos de línea en `<br/>`. Se aplica a todo el texto del usuario que va a un `Paragraph` del PDF: nombres y valores de los datos clínicos, descripción macroscópica y notas.
- `backend/informes/tests.py`: nueva clase `PdfConTextoDelUsuarioTests` con 3 pruebas. Comprueban que el PDF se genera con textos como `<i>H. pylori` o `<b>grande`, que etiquetas como `<font size=40>` no cambian el formato y que las notas conservan sus saltos de línea.

**Por qué**
- ReportLab interpreta el texto de `Paragraph` como marcado. Un texto como `ver <i>H. pylori` hacía fallar la generación del PDF con un error 500. Con etiquetas válidas como `<font size=40>`, un usuario podía cambiar el aspecto del informe oficial.
- Mejora pedida por el usuario: antes, las notas escritas en varias líneas se juntaban en un solo párrafo.

### Corrección: borrar una patología con informes ya no da error 500 (I-1)

**Qué se cambió**
- `backend/informes/views.py`: `PatologiaViewSet.destroy()` captura `ProtectedError` y responde **400** con el mensaje *"No se puede eliminar: esta patología tiene N informe(s) asociado(s)."*. Antes la petición fallaba con un error 500. Los informes siguen protegidos por `on_delete=PROTECT`.
- `backend/informes/tests.py`: nueva clase `BorrarPatologiaTests` con 2 pruebas. Una comprueba que con informes se responde 400 y la patología no se borra; la otra, que sin informes se borra normalmente (204).

**Por qué**
- Al borrar desde la pantalla de Patologías una patología que ya tenía informes, el servidor fallaba con un error interno y el usuario veía un mensaje genérico. `PatologiasPage.jsx` ya mostraba el campo `detail` de la respuesta, así que el frontend no necesitó cambios.

### Seguridad: SECRET_KEY obligatoria y DEBUG desactivado por defecto (C-3)

**Qué se cambió**
- `backend/config/settings.py`: se eliminó la `SECRET_KEY` de respaldo escrita en el código. Si falta la variable, la app no arranca y lanza `ImproperlyConfigured` con un mensaje en español que dice qué hacer. `DEBUG` vale `False` si no se define (antes era `True`).
- `backend/config/tests.py` (nuevo): 4 pruebas que cargan `settings.py` simulando que no hay `.env`.
- `iniciar_y_probar.ps1`: si no existe `backend/.env`, lo crea desde `.env.example` con una `SECRET_KEY` aleatoria (`secrets.token_urlsafe(50)`). Si el `.env` ya existe, no lo toca.
- `backend/.env.example`: comentario que explica que `SECRET_KEY` es obligatoria y cómo generar una.
- `README.md`: el paso 4 de la instalación (crear el `.env`) pasa a ser obligatorio y explica cómo generar la clave.
- `backend/accounts/permissions.py`: se borró la clase `EsSoloLectura`, que ya no usaba ninguna vista desde el arreglo de C-2.
- Documentación: `CLAUDE.md` (configuración y regla 6), `docs/progreso.md` (nuevo) y C-3 marcado como corregido en la auditoría.

**Por qué**
- La clave de respaldo era pública en GitHub. Si la app se publicaba sin `.env`, cualquiera podía firmar tokens JWT de administrador. Además quedaba con `DEBUG=True`, que muestra detalles internos en los errores y permite CORS desde cualquier origen.
- `docs/progreso.md` registra en qué punto quedó el trabajo, para poder retomarlo aunque la conversación se corte.

### Seguridad: informes finalizados bloqueados y solo el autor o un admin puede modificarlos (C-2)

**Qué se cambió**
- `backend/accounts/permissions.py`: ahora contiene `EsAutorOAdminOSoloLectura`, que se movió desde `backend/foro/permissions.py` (archivo eliminado) para que lo compartan informes y foro. El comportamiento del foro no cambia; solo cambia el `import` en `backend/foro/views.py`.
- `backend/informes/views.py`: `InformeViewSet` usa `EsAutorOAdminOSoloLectura` en lugar de `EsSoloLectura`. Solo el autor o un admin puede editar, borrar o finalizar un informe; los demás reciben 403. Además, `update()` y `destroy()` responden 400 si el informe está finalizado, también para el admin.
- `backend/informes/serializers.py`: `InformeListSerializer` incluye el campo `autor` (id), que el frontend necesita.
- `frontend/src/pages/InformePage.jsx`: los campos y los botones "Actualizar" y "Finalizar" solo se habilitan para el autor o un admin. También se muestran los mensajes de error `detail` de la API, que antes no aparecían.
- `frontend/src/pages/DashboardPage.jsx`: el botón de eliminar borrador solo aparece para el autor o un admin.
- `backend/informes/tests.py` (nuevo): 12 pruebas de permisos y del bloqueo de informes finalizados.
- Documentación: decisión D-3 en `docs/decisiones.md`; tabla de la API del README; sección de permisos de `CLAUDE.md`; C-2 marcado como corregido en la auditoría.

**Por qué**
- Un informe finalizado se podía seguir editando y borrando, aunque el README dice que finalizar "bloquea edición".
- Cualquier patólogo podía editar, borrar o finalizar informes de otro. Esto va contra las decisiones D-2 (solo el autor o un admin) y D-3 (el bloqueo de un informe finalizado también aplica al admin).

### Seguridad: un usuario ya no puede cambiarse el rol, el estado ni el username (C-1)

**Qué se cambió**
- `backend/accounts/serializers.py`: en `UsuarioSerializer`, los campos `username`, `rol` y `activo` pasan a ser de solo lectura (`read_only_fields`). Se siguen mostrando en las respuestas, pero se ignoran si llegan en un `PATCH` o `PUT` a `/api/auth/perfil/`.
- `backend/accounts/tests.py` (nuevo): primeras pruebas automáticas del proyecto (`PerfilCamposProtegidosTests`). Comprueban que un usuario no puede cambiar su `rol`, `activo` ni `username`, y que sí puede editar sus datos personales.

**Por qué**
- Cualquier usuario autenticado, incluso un auditor, podía enviar `{"rol": "admin"}` a `/api/auth/perfil/` y convertirse en administrador. Eso anulaba todo el control de acceso por roles.
- El registro de usuarios (`RegistroSerializer`, solo para admin) y el panel `/admin/` de Django no usan este serializer, así que siguen pudiendo asignar roles.

# Estado del trabajo

Este archivo dice **en qué quedamos**. Se actualiza al terminar cada tarea para poder retomar el trabajo si la conversación se corta.
- **Qué se cambió y por qué:** `CHANGELOG.md`.
- **Decisiones tomadas:** `docs/decisiones.md`.
- **Lista completa de problemas:** `docs/auditoria-inicial.md`.

**Última actualización:** 2026-11-12

---

## Dónde estamos

- **Proyecto:** `C:\Users\yulia_z9mxe\patologia-app` (desde el 2026-11-01; antes `C:\Users\salam\Desktop\patolab-app-actualizado\patologia-app`).
- **Repositorio:** `origin` es `https://github.com/yulgg98/patologia-app.git` (donde se hace `push`); `upstream` es el repositorio original, `https://github.com/juansalamanca01-glitch/patologia-app.git`. Comprobado el 2026-11-12: `main` local y `origin/main` están en `6612d73` (D-19).
- **Herramienta:** desde el 2026-11-12 el trabajo se hace con Claude Code en una terminal del computador del usuario, abierta en la carpeta del proyecto, para poder correr las pruebas y `git` en cada paso.
- **Plan vigente:** `docs/plan-calidad-y-diseno.md`, aprobado el 2026-10-08. Cada fase va en su propia rama desde `main`.
- **Trabajo en curso (2026-11-12):** mejoras de PathoLab para cumplir los objetivos del proyecto de investigación (OE2 y OE3). Las instrucciones completas del usuario están en `docs/mejoras-objetivos-investigacion.md`: 8 tareas, en orden, con reglas obligatorias (no borrar nada sin autorización escrita, migraciones solo aditivas, no inventar contenido clínico, una rama por tarea desde `main`). Línea base tomada el 2026-11-12 sobre `main` (`348ce48`): `npm run check` sin errores ni avisos; 24 pruebas de la raíz, 395 del backend y 157 del frontend, todas en verde. La **tarea 1 está hecha y aprobada** por el usuario el 2026-11-12: el commit `d3fdcfd` se unió a `main` con fast-forward y se subió a `origin`. Sigue la **tarea 2**, que no empieza a escribir código hasta que el usuario responda las preguntas sobre la fijación y el rotulado.
- **Trabajo anterior (2026-11-01):** CORS estricto, bloqueo con 403 de los orígenes no permitidos y documentación Swagger (D-19, `docs/cors-y-swagger.md`), pedido para la clase de Programación Web 2. Hecho en `main`, commit `6612d73`, ya subido a GitHub (`origin`). En la sesión de trabajo pasaron las 395 del backend, las 24 de la raíz y Ruff, y se comprobó en Chromium que Swagger carga y que una página de otro origen queda bloqueada. La línea base de la tarea 1 confirma que también pasan en el computador del usuario.
- **Trabajo anterior a ese (2026-11-01):** plantillas según el manual de procesamiento macroscópico y muestreo para histología (D-18, `docs/plantillas-manual.md`), hecho directamente en `main` (sin rama propia, por elección del usuario el 2026-11-01). El usuario ejecutó en su computador `npm run check` y todas las pruebas (23 de la raíz, 377 del backend y 157 del frontend, todas en verde), hizo el commit `aa1e2ba` y lo subió a GitHub. Falta la prueba manual en el navegador y la revisión del patólogo (siguiente paso 0). Nota: las pruebas del backend fallan con Python 3.14, porque Django 4.2 no es compatible con esa versión; el entorno virtual (`venv`) se debe crear con Python 3.12 (`py -3.12 -m venv venv`).
- **Rama de trabajo anterior:** ninguna abierta. Todo está en `main`, que es la única rama (las ramas viejas, ya unidas, se borraron el 2026-10-14). La fase de Cypress se unió a `main` el 2026-10-14, después de que el usuario probara `npm run e2e:presentacion` en Chrome y grabara los videos de respaldo. Lo siguiente es la presentación del viernes 2026-10-16; después, los grupos 4, 6 y 7 de la fase 4.
- **Estado:**
  - Están terminados y en `main`:
    - la auditoría inicial (salvo I-9c);
    - el informe de anatomía patológica v2 (etapas 1 a 9 y D-12);
    - los Bloques A y B (punto 4) de la prueba manual;
    - las fases 1, 2 y 3 y las tareas previas 1 y 2 del plan.
  - El detalle está en la tabla "Hecho" y en `CHANGELOG.md`.
- **Forma de trabajar con cada hallazgo** (ver las reglas en `CLAUDE.md`):
  1. Escribir una prueba que demuestre el fallo y mostrar que falla.
  2. Explicar el arreglo y esperar confirmación.
  3. Aplicar el arreglo y mostrar que la prueba pasa.
  4. Registrar el cambio en `CHANGELOG.md` y actualizar la documentación.
  5. Antes del commit, si el cambio toca código, ejecutar `npm run check` y todas las pruebas (raíz, backend y frontend). Si algo falla, no se hace el commit hasta corregirlo. Si el commit solo cambia documentación, no hace falta ejecutar las pruebas (regla 7 de `CLAUDE.md`).
  6. Hacer el commit.
  7. Hacer `git push` de la rama de trabajo después de cada commit, como respaldo. El usuario lo autorizó el 2026-10-03 y lo volvió a confirmar el 2026-11-12 (reemplaza el "preguntar antes del push" de `docs/mejoras-objetivos-investigacion.md`). Unir la rama a `main` requiere preguntar aparte. Nunca `git push --force`.
- **Pruebas:** desde la tarea 1 (2026-11-12), 414 del backend y 168 del frontend. Antes: 24 de la raíz desde D-19 (`npm test`, comprobaciones de `npm run dev`, `npm run check` y `npm run e2e`), 395 del backend desde D-19 (377 con D-18) (`cd backend` y luego `python manage.py test`; con SQLite usan el archivo `backend/test_db.sqlite3`) y 157 del frontend desde D-18 (antes 137; `cd frontend` y luego `npm test`). Además, 25 de Cypress (`npm run e2e` en la raíz, cerca de un minuto; no son obligatorias antes de cada commit, D-17). Con D-18 el usuario comprobó que todas pasan (2026-11-01). Las de D-19 se confirman con la línea base de la tarea 1 (2026-11-12).

## Hecho

| Hallazgo | Qué se hizo | Commit |
|---|---|---|
| — | Auditoría inicial (`docs/auditoria-inicial.md`) | `bf42ff9` |
| C-1 | Un usuario ya no puede cambiarse el rol, `activo` ni `username` | `bf42ff9` |
| I-7 | Resuelto por decisión D-1 (los patólogos sí administran el catálogo) | `945affb` |
| C-2 | Informes finalizados bloqueados; solo el autor o un admin los modifica (D-2, D-3) | `e56174d` |
| C-3 | `SECRET_KEY` obligatoria, `DEBUG=False` por defecto; el script crea el `.env` | `455cff0` |
| — | Borrada la clase `EsSoloLectura`, que ya no se usaba | `455cff0` |
| I-1 | Borrar una patología con informes responde 400 en vez de un error 500 | `bd35f2f` |
| I-3 | El PDF escapa el texto del usuario (sin error 500 ni etiquetas inyectadas) y respeta los saltos de línea | `8ebf17b` |
| I-4 | Endpoint `/api/informes/estadisticas/` para el dashboard y paginación en el buscador | `4938f2d` |
| M-8 | El perfil muestra un error con "Reintentar" en lugar de quedar en blanco; se instala Vitest en el frontend | `958c2f0` |
| I-5 | PDF descargado con Axios (token en la cabecera); se eliminó `/api/descargar-pdf/?token=` | `7886e0c` |
| I-6 | Límite real de 10 MB y validación de que el archivo sea una imagen (backend); revisión previa y sin publicaciones duplicadas (frontend) | `2bf50e6` |
| I-8 | Foro: solo un admin fija publicaciones; un comentario no se puede mover a otra publicación | `8c8dac3` |
| I-11 | El registro y el cambio de contraseña aplican los validadores de Django | `3d5e5cf` |
| I-9a | `npm audit fix`: producción pasa de 6 vulnerabilidades (2 altas) a 2 moderadas que no afectan a la app | `ee92a38` |
| I-9b | Vite 5 → 6.4 y Vitest 3 → 5: quedan solo las 2 vulnerabilidades moderadas de react-router | `da69796` |
| I-10 | `client.js` usa `VITE_API_URL` (vacía en desarrollo → proxy de Vite) en lugar de `localhost:8000` fijo | `1a1822e` |
| I-12 | README reescrito (permisos, API completa, pruebas, seguridad) y colección de Postman rehecha y probada | `e3743c2` |
| I-2 | Los campos obligatorios se validan aunque `datos_ingresados` llegue vacío; `0` y `false` cuentan como respuesta | `0d94a56` |
| M-1, M-2 | Limpieza: imports, `LoginSerializer`, campo `campos_requeridos` (migración 0003), `isPatologo`/`isAuditor`, `console.log`, imágenes sobrantes y `dist/` | `f944dd7` |
| M-3, M-13 | `nombre_visible`, `constants.js`, `EstadoBadge`, `resultados()`; 63 comentarios traducidos | `3dd9c49` |
| M-4 | Listados de categorías, temas y publicaciones: de 22/22/25 a 2/2/3 consultas, conservando el orden | `6af05d9` |
| Nuevo | Menús desplegables y tabla de Patologías con todos los elementos (`?page_size=`, máx. 1000) | `78d306c` |
| M-5 / D-4 | Filtro `?activa=`, solo activas al crear informes, casilla "Activa" en Patologías | `b99d9f1` |
| M-6 / D-5 | `seed_data` crea 4 temas del foro; botón "+ Tema" para patólogos y admin | `91cea02` |
| M-7 | El auditor ya no ve el formulario de comentarios del foro | `563fb85` |
| M-9 | Errores de carga y borrado visibles en el Dashboard y en InformePage | `1c28a66` |
| M-10 | El pie del PDF usa la hora de Bogotá (`timezone.localtime()`) | `df4ab5f` |
| M-11 / D-6 | Lista negra de tokens, `POST /api/auth/logout/`, cambio de contraseña cierra otras sesiones, el interceptor guarda el `refresh` rotado | `ced62eb` |
| M-12 | Resuelto con documentación (README, sección Seguridad); sin cambios de código | — |
| — | README sin emojis (salvo el título), a pedido del usuario | `f6ccaa7` |
| Nuevo | "Editar" en Patologías pide la patología completa (antes no se veían la descripción ni el protocolo) | `dac13ef` |
| — | `npm run dev` en la raíz: comprueba el entorno y arranca backend y frontend juntos (rama `desarrollo-un-comando`) | `c44d7ec` |
| — | Se borra `iniciar_y_probar.ps1` (no se usaba; lo reemplaza `npm run dev`) | `b1ef010` |
| D-7 | Informe v2, etapa 1: número de petición `P-AÑO-NNNNN` automático (contador con `UPDATE` atómico, prueba de concurrencia), orden externa opcional, se elimina `numero_caso` | `6ca1727` |
| D-11 | Informe v2, etapa 2: catálogos `EPS` (app nueva `pacientes`) y `Servicio`, `Informe.TipoEstudio`, `GET /api/opciones/`, `seed_data` con 7 servicios y 12 EPS, nombres sin repetir sin importar mayúsculas | `c44bb4f` |
| D-11 | Informe v2, etapa 3: modelo `Paciente` (edad calculada, documento único y normalizado), `/api/pacientes/` con búsqueda `?q=`, solo el admin borra, 400 al borrar una EPS en uso, 2 pacientes ficticios en `seed_data`, `useOpciones` y `PacientesPage` (`/pacientes`) | `19c92ce` |
| — | Informe v2, etapa 4: paciente y datos de la solicitud en el informe (migración 0008), edad a la fecha de ingreso, EPS del momento del estudio, búsqueda y filtro por paciente, historial `/api/pacientes/{id}/informes/`, 400 al borrar paciente/EPS/servicio en uso, `SelectorPaciente`, `DatosSolicitud`, `FormularioPaciente` compartido, `CatalogosPage` (`/catalogos`), columnas de los listados y ejecutor de pruebas sin throttles acumulados | `f1cda29` |
| — | Informe v2, etapa 5: `descripcion_microscopica`, `notas` → `comentarios` (migración 0009, conserva los datos), modelo `Diagnostico` anidado en el informe (reemplazo de la lista, máx. 20, CIE-10 validado y normalizado), `prefetch` solo en el detalle, microscópica, diagnósticos y comentarios en el PDF actual, `DiagnosticoInline` en `/admin/`, `ListaDiagnosticos` (agregar, quitar, subir y bajar) y tarjetas nuevas en `InformePage` | `f1994e8` |
| D-8, D-10 | Informe v2, etapa 6: `Usuario.registro_medico` (solo lo asigna un admin), requisitos para finalizar con la lista de lo que falta, `fecha_informe`, datos congelados (`datos_finalizacion`, migración que completa los ya finalizados), firma del autor en la API y en el PDF actual, `seed_data` con `RM-PRUEBA-0001`, `SeccionFirma` y registro médico en el perfil | `5033c6b` |
| — | Informe v2, etapa 7: PDF con la estructura del informe real (encabezado fijo de demostración, tabla de datos en dos columnas, título, tipo de estudio, secciones, firma), "Página X de Y" en cada página con `CanvasNumerado`, borrador sin firma y con "BORRADOR — SIN VALIDEZ" en la fecha y en el pie, sin "DATOS CLÍNICOS", `Informe.edad_paciente()` compartida con la API | `f6f7f8f` |
| D-9 | Informe v2, etapa 8: modelo `Adenda` (migración 0011), `GET`/`POST /api/informes/{id}/adendas/` (solo en finalizados, autor o admin, quien la crea necesita registro médico, número por informe con bloqueo, sin PUT/PATCH/DELETE), firma congelada con `firma_de()`, `adendas` en el detalle, `AdendaInline` de solo lectura, aviso y sección "ADENDAS" en el PDF, `SeccionAdendas` con confirmación, Postman | `0f834ad` |
| D-12 | El PDF de un borrador es una vista previa solo para su autor o un admin (403 para los demás), con marca de agua "BORRADOR" en cada página y archivo `…_borrador.pdf`; botón "Vista previa (borrador)". Lo notó el usuario en la prueba manual de las etapas 7 y 8, que ya hizo | `90d6958` |
| — | Informe v2, etapa 9 (cierre): D-7 a D-11 revisadas (ya se cumplen); política de privacidad con los datos de pacientes, datos sensibles, integridad del informe y fecha fija (también en los términos); "Patología Clínica" → "Anatomía Patológica"; revisión completa del README; Postman con Renovar token, Cerrar sesión, Editar paciente y Editar informe; lista de comprobación para la prueba manual final | `4b9525a` |
| — | Pie de página (Política de Privacidad, Términos) en el login y en las páginas legales sin sesión, con "← Volver al inicio de sesión". Lo notó el usuario en la prueba manual final | `99c4b36` |
| — | `/admin/` de usuarios con el `UserAdmin` de Django: la contraseña se cifra al crear un usuario y ya no se muestra el hash en un campo editable. Lo encontramos al preparar la prueba manual final | `ad97f70` |
| — | Prueba manual final del flujo completo, hecha por el usuario el 2026-10-05 con `patologo1`, `patologo2`, `auditor1` y `admin`: todo salió bien. Reemplazó las pruebas de navegador que estaban pendientes (etapas 3, 4 y 6, Catálogos, C-2 e I-4) | `420b91f` |
| — | Unión de `informe-v2` a `main` (fast-forward, con todas las pruebas en verde) | `64c6e22` |
| — | Pendientes, punto 1: los datos del paciente en el informe ya no salen pegados a su etiqueta (`<dt>`/`<dd>` en `SelectorPaciente`) | `a31c5e1` |
| — | Pendientes, punto 2: miniaturas del foro más grandes y visor para ampliarlas (anterior y siguiente, teclado, Escape, clic fuera) | `ee28886` |
| D-13 | Pendientes, punto 3: aviso al salir con cambios sin guardar (Seguir editando, Salir sin guardar, Guardar y salir) y autoguardado a los 5 s de los borradores existentes, con indicador de estado; `App.jsx` pasa a `createBrowserRouter` para usar `useBlocker`; se muestran los errores de `datos_ingresados` del backend | `0c05b68` |
| D-13 | Ampliación: finalizar y la vista previa del PDF guardan primero los cambios pendientes (si no son válidos, no siguen y muestran qué falta); "Salir" pasa por `/salir`, así que cerrar sesión con cambios sin guardar también avisa. Encontrado al hacer el punto 3 y aprobado por el usuario | `a9b648d` |
| — | Acomodo del aviso "Tienes cambios sin guardar": los tres botones caben dentro del recuadro (pasan a otra línea o se apilan en pantallas angostas) y no sobra espacio debajo. Solo CSS; los bordes y la tipografía quedan para el Bloque B | commit "fix: botones del aviso de cambios sin guardar" |
| — | Prueba manual del Bloque A hecha por el usuario: todo salió bien. Se une `ajustes-prueba-manual` a `main` y el Bloque B sigue en la rama `bloque-b-estetica` | `4a9284d` |
| — | Fase 1 del plan (Bloque B, punto 4): el PDF va todo en negro (el rojo solo en el aviso de adendas y en la marca de agua), con los títulos en negrita y una línea fina negra bajo el encabezado. El usuario lo confirmó el 2026-10-08 | `8021597` |
| — | Plan de calidad, seguridad y diseño (`docs/plan-calidad-y-diseno.md`), aprobado el 2026-10-08 | `43a40e7` |
| — | Tarea previa del plan: `seed_data` crea `patologo2` (`patologo2345`, `RM-PRUEBA-0002`) para probar D-2; si ya existe, no lo cambia | `7ea0125` |
| — | Inventario de pendientes (sección "Pendientes"), tarea previa 2 en el plan, decisión D-14 (un finalizado tampoco se modifica en `/admin/`; se implementa en la fase 4) y corrección de las contradicciones entre documentos | `dd38439` |
| — | `npm audit fix`: `shell-quote` (crítico, raíz) y `source-map-js` (alto, frontend), los dos de herramientas de desarrollo. Quedan solo las 2 moderadas de `react-router` (I-9c, fase 3) | `fadac1d` |
| — | D-14 ampliada: un informe finalizado tampoco se borra desde `/admin/`, tenga o no adendas; idea futura de un estado "Anulado" | `8c084e8` |
| — | Tarea previa 2 del plan: el encabezado del PDF (nombre, dirección y teléfono del laboratorio) se lee de `backend/.env`, con el de demostración por defecto; el teléfono va en su propia línea y solo si existe | `539a88d` |
| D-15 | El encabezado se congela al finalizar (`datos_finalizacion['laboratorio']`); la migración 0012 da el de demostración a los finalizados existentes. Lo encontró el usuario al probar la tarea previa 2 | `c0f08c8` |
| — | Fase 2 del plan: Prettier 3.9, ESLint 9 y Ruff 0.16, `npm run check`, `.vscode` (formato al guardar y extensiones), formato automático (`836257b`, en `.git-blame-ignore-revs`), imports ordenados y arreglos a mano aprobados por el usuario (el autoguardado usa `autoguardarRef`) | `6f2e3c3`, `836257b`, `602810e` y `e10ee5f` |
| — | Regla 7 de `CLAUDE.md`: antes de cada commit que toque código, `npm run check` y todas las pruebas; si algo falla, no hay commit. En los de solo documentación no hace falta ejecutar las pruebas | `19c02fb` |
| — | Fase 3 del plan: informe `docs/auditoria-owasp.md` (OWASP Top 10:2025, dependencias de npm y Python), con 23 hallazgos `O-1` a `O-23` (5 altos, 13 medios, 5 bajos; 6 comprobados). Sin cambios de código. Falta que el usuario elija las correcciones | commit "docs: auditoría OWASP Top 10:2025 (fase 3)" |
| O-1, O-3, O-4 / D-14 | Fase 4, grupo 1: `estado` de solo lectura en la API y en `/admin/` (solo `finalizar` lo cambia); en `/admin/`, un finalizado no se modifica ni se borra (tampoco en lote) y sus diagnósticos son de solo lectura. 16 pruebas nuevas | commit "fix(seguridad): integridad del informe (fase 4, grupo 1)" |
| O-16, O-17 | Fase 4, grupo 2: el login y el registro vuelven a tener límite de intentos (`throttle_scope` en la vista, sin perder los globales; se borra `accounts/throttles.py`) y `NUM_PROXIES` (0 por defecto) impide saltarlos con `X-Forwarded-For`. 6 pruebas nuevas | commit "fix(seguridad): límites del login (fase 4, grupo 2)" |
| O-13, O-5 (1 y 2) | Fase 4, grupo 3: solo se aceptan JPG, PNG, GIF y WEBP (extensión y formato real); cada imagen se vuelve a codificar (sin EXIF ni contenido agregado, con su orientación y animación) y se guarda con un nombre aleatorio; igual en `/admin/`. `foro/imagenes.py` nuevo; 16 pruebas nuevas (14 del backend, 2 del frontend) | commit "fix(seguridad): imágenes del foro (fase 4, grupo 3)" |
| D-17 | Fase de Cypress: Cypress 15 con base aparte (`backend/e2e_db.sqlite3`, `seed_data` en cada corrida), `npm run e2e` y `npm run e2e:abrir` (puertos 8001 y 5174), `SQLITE_NOMBRE` y `LIMITE_PETICIONES_USUARIO` en `settings.py`, proxy configurable. 22 pruebas: login y roles, informe completo (paciente, borrador, requisitos, finalizar, PDF, adenda), permisos D-2 y D-3, cambios sin guardar (D-13) | `fb454e6` |
| D-17 | Fase de Cypress ajustada a los requisitos del usuario: 6 flujos (login con cada rol, informe con PDF, adendas, el auditor no crea informes, cambios sin guardar, permisos), 25 pruebas que buscan por rol, etiqueta o texto (`@testing-library/cypress`), `role="dialog"` en el formulario de paciente y `role="alert"` en los errores, `npm run e2e:video` y la sección "Fase de Cypress" del plan | `976b682` |
| D-17 | Modo presentación (`npm run e2e:presentacion`, pausa de 500 ms configurable hasta 3000) y `e2e:abrir` en Chrome; sin la advertencia `allowCypressEnv` (`Cypress.expose()`); tildes del registro en UTF-8 también en `npm run dev`; aviso de que `exited with code 1` al apagar es normal | `230ea3b` |
| — | Unión de `fase-cypress` a `main` (fast-forward), con la aprobación del usuario tras probar el modo presentación en Chrome | `162e05b` |
| — | Limpieza de ramas: se borran `fase-cypress` y otras 17 ramas viejas, en el computador y en GitHub. Antes se comprobó que ninguna tenía commits fuera de `main`, así que no se pierde nada: los commits citados en esta tabla siguen en `main`. Solo queda `main`. Lo pidió el usuario el 2026-10-14 | commit "docs: ramas viejas borradas" |
| O-22, O-23, O-21 | Fase 4, grupo 5: filtros de la URL con 400 en vez de 500 (`config/filtros.py`); `datos_ingresados` validado en el modelo (objeto, valores simples, límites) y `{}` se guarda en `/admin/` (migración 0013); `texto_generado` en la misma transacción; `LOGGING` y registro de logins (logger `seguridad`, `LOG_LEVEL`). 19 pruebas nuevas | commit "fix(seguridad): errores y registros (fase 4, grupo 5)" |
| D-18 | Plantillas según el manual de procesamiento macroscópico (secciones, campos que aplican según el procedimiento, 124 → 260 campos sin borrar ninguno, `actualizar_plantillas`), muestreo para histología con canastillas (modelo `Canastilla`, migración 0014, API, `/admin/`, PDF y `MuestreoHistologia`) y descripción fiel a lo registrado. 55 pruebas nuevas del backend y 20 del frontend | `aa1e2ba` |
| D-19 | CORS solo con `CORS_ALLOWED_ORIGINS` también en desarrollo, 403 a los orígenes no permitidos (`config/origenes.py`) y documentación Swagger en `/api/docs/` y `/api/schema/` (`drf-spectacular`), para la clase de Programación Web 2. 18 pruebas nuevas del backend y 1 de la raíz | `6612d73` (subido a `origin`) |
| — | `docs/progreso.md` puesto al día (D-19 ya tenía commit) y plan de mejoras para los objetivos de investigación (`docs/mejoras-objetivos-investigacion.md`), con las decisiones del usuario del 2026-11-12. Solo documentación | `348ce48` |
| Tarea 1 (OE2) | Descripción macroscópica editable. Campos `descripcion_macroscopica_final` y `descripcion_macroscopica_base` (migración aditiva 0015); el PDF y la API usan el texto vigente; `POST /api/informes/vista-previa-macroscopica/`, que no guarda nada; tarjeta con texto sugerido, área editable, Restaurar, Copiar y aviso si el sugerido cambia. 19 pruebas nuevas del backend y 11 del frontend; `MigracionEncabezadoCongeladoTests` ajustada con autorización. Aprobada por el usuario y unida a `main` | `d3fdcfd` |

## Siguiente paso

0. **Mejoras para los objetivos de investigación (2026-11-12),** en el orden de `docs/mejoras-objetivos-investigacion.md`. Al terminar cada tarea se para, se entrega el resumen de la sección 4 de ese documento y se espera la aprobación del usuario antes de la siguiente.

   | # | Tarea | Rama | Estado |
   |---|---|---|---|
   | — | Línea base: `npm run check` y todas las pruebas sobre `main` | — | hecha (2026-11-12): check OK; 24 raíz, 395 backend, 157 frontend |
   | 1 | Descripción macroscópica editable | `texto-macroscopico-editable` | hecha, aprobada y unida a `main` (`d3fdcfd`, 2026-11-12). Falta correr `npm run e2e` (opcional, D-17) |
   | 2 | Estado de fijación y rotulado | por definir | antes de escribir código, preguntar al usuario tipo, opciones, obligatoriedad y frase |
   | 3 | Plantilla de placenta | por definir | bloqueada: espera el contenido del manual o la lista del patólogo |
   | 4 | Revisión de la gástrica endoscópica (solo documento) | por definir | espera los textos de ejemplo del usuario |
   | 5 | Indicador de completitud | por definir | pendiente |
   | 6 | Tiempo de diligenciamiento | — | primero una propuesta; no se registra nada sin aprobación (consentimiento) |
   | 7 | Instancia de prueba (PostgreSQL y documentación) | por definir | pendiente; no se despliega nada |
   | 8 | Seguridad: grupos 4, 6 y 7 de la fase 4 | una por grupo | grupo 6: borrar `activo` autorizado (abajo); O-19 y O-14 requieren propuesta |

   Para la revisión del profesor de D-19, seguir la sección 4 de `docs/cors-y-swagger.md`.
1. **D-18 (2026-11-01):** commit `aa1e2ba` hecho y subido a GitHub, con todas las pruebas en verde. Falta probar a mano un informe de Tiroides y uno de Mama (campos que aparecen según el procedimiento, canastillas y PDF). Después, pedir al patólogo que revise la sección 6 de `docs/plantillas-manual.md`. En una base existente, aplicar `python manage.py migrate` y `python manage.py actualizar_plantillas`.

1. **Fase 3 terminada** y unida a `main` el 2026-10-11. El usuario respondió el informe el mismo día (`docs/auditoria-owasp.md`, "Respuestas del usuario").
2. **Fase 4, una rama por grupo** (tabla en la fase 4 del plan). El 2026-10-11 y el 2026-10-12, en orden:
   1. grupo 1, integridad del informe (O-1, O-3, O-4/D-14): **hecho** y unido a `main` el 2026-10-11;
   2. grupo 2, límites del login (O-16, O-17), **hecho** y unido a `main` el 2026-10-11;
   3. grupo 3, imágenes del foro (O-13, O-5 puntos 1 y 2), rama `fase-4-imagenes-foro`: **hecho** y unido a `main` el 2026-10-12 (también en `/admin/`, aprobado por el usuario);
   4. grupo 5, errores y registros (O-22, O-23, O-21), rama `fase-4-errores-registros`: **hecho** el 2026-10-12. El tamaño máximo de los textos largos queda para el grupo 8 (decisión del usuario). Incluye el problema de `/admin/` con `datos_ingresados` vacío, ya resuelto (`blank=True` y el mismo validador de O-23). Unido a `main` el 2026-10-12.
3. **Fase de Cypress**, que el usuario presenta el viernes 2026-10-16: **hecha** el 2026-10-14 en la rama `fase-cypress` (D-17). Ajustada el mismo día a los 5 requisitos del usuario (sección "Fase de Cypress" del plan). El usuario probó `npm run e2e:presentacion` en Chrome y grabó los videos de respaldo (`npm run e2e:video`). **Unida a `main` el 2026-10-14.**
4. **Después del 2026-10-16:** grupos 4 (Django 5.2), 6 (cuentas y sesiones, D-16) y 7 (concurrencia) de la fase 4; luego las fases 5 a 8.
4. **Para arrancar la aplicación:** `npm run dev` en la raíz y abrir http://localhost:5173. Se detiene con Ctrl + C (en Windows, responder `S` si pregunta "¿Desea terminar el trabajo por lotes?").

Para unir una rama a `main` (con fast-forward desde la terminal, sin pull request, porque `gh` no está instalado):
1. Comprobar que todas las pruebas pasan.
2. Ejecutar `git switch main`, luego `git merge --ff-only <rama de trabajo>` y `git push origin main`.
3. Volver con `git switch <rama de trabajo>`.

Siempre se pregunta antes al usuario.

## Pendientes

Inventario del 2026-10-08: todo lo pendiente, sin terminar o anotado para después en la documentación. En el código no hay comentarios `TODO` ni `FIXME`. Cada punto aparece una sola vez, con su origen.

### 1. Del plan (`docs/plan-calidad-y-diseno.md`), en orden

| # | Qué | Origen |
|---|---|---|
| 4 | **Fase 4:** correcciones de la auditoría OWASP, una rama por grupo. Grupos 1, 2, 3 y 5 el 2026-10-11 y 12; grupos 4, 6 (D-16) y 7 después del 2026-10-16. El grupo 1 incluye D-14. Los puntos conocidos que evaluó la fase 3 (I-9c, versiones de Python, D-14, conflicto entre pestañas, registro de accesos, clave antigua, `?q=`, `localStorage`) tienen ahora su hallazgo `O-x` y su grupo en `docs/auditoria-owasp.md` | Plan; `docs/auditoria-owasp.md` |
| — | **Fase de Cypress** (nueva): **hecha** y unida a `main` el 2026-10-14 (D-17); el usuario la presenta el viernes 2026-10-16 | Pedido del usuario, 2026-10-11 |
| 5 | **Fase 5:** guía de diseño. La aprueban el usuario, el equipo y el profesor | Plan; Bloque B, punto 5 |
| 6 | **Fase 6:** pantalla del informe. La aprueban el usuario, el equipo y el profesor | Plan; Bloque B, punto 5 |
| 7 | **Fase 7:** resto de pantallas | Plan; Bloque B, punto 5 |
| 8 | **Fase 8:** cierre. Incluye volver a buscar contradicciones entre documentos (sección 5) | Plan |

### 2. Necesitan una decisión del usuario

- **Nombre del proyecto.** El equipo probablemente cambiará "PathoLab", y el nombre nuevo no está decidido. No se cambia nada hasta que lo esté; entonces se cambia de una sola vez en todos estos lugares:

  | Dónde | Archivo y lugar |
  |---|---|
  | Pantallas | `frontend/src/components/Navbar.jsx:20` (marca del menú), `frontend/src/components/Footer.jsx:6` ("© año PathoLab"), `frontend/src/pages/LoginPage.jsx:37` (título del login) |
  | Pestaña del navegador | `frontend/index.html:7-8` (`<meta name="description">` y `<title>`) |
  | Textos legales | `frontend/src/pages/PoliticaPrivacidadPage.jsx:23`, `frontend/src/pages/TerminosCondicionesPage.jsx:19` y `:66` |
  | PDF | el valor por defecto de `LABORATORIO_NOMBRE` en `backend/config/settings.py` (sección "Encabezado del PDF"); en una instalación basta con cambiarlo en `backend/.env`. **Los informes finalizados conservan su encabezado congelado (D-15)**, y el cambio de nombre no los modifica. También `ENCABEZADO_DEMOSTRACION` de la migración `informes/0012`, que no se cambia porque es historia. Lo comprueban `backend/config/tests.py` (`EncabezadoLaboratorioTests`) y `backend/informes/tests.py` (`test_el_encabezado_es_el_de_demostracion_sin_telefono` y la lista de `test_las_partes_salen_en_el_orden_del_informe_real`) |
  | `/admin/` | `backend/accounts/admin.py:36` (sección "Datos de PathoLab") |
  | Código interno | `backend/config/settings.py:148` y `backend/config/test_runner.py:14` (`PathoLabTestRunner`), `backend/foro/tests.py:15` (prefijo `patolab-media-pruebas-`), `frontend/src/index.css:2` (comentario), `scripts/dev.mjs:16` y `:48` (mensajes de `npm run dev`) |
  | Nombres de paquete | `package.json` y `package-lock.json` de la raíz (`patolab` y la descripción), `frontend/package.json` y `frontend/package-lock.json` (`patholab-frontend`) |
  | Ejemplos de dominio | `frontend/.env.example:9`, `frontend/src/api/client.js:7` y `frontend/src/api/client.test.js:24-30` (`api.patolab.com`) |
  | Postman | `PathoLab_API.postman_collection.json`: el nombre del archivo y las líneas 4 y 5 (nombre y descripción de la colección) |
  | Documentación | `README.md` (título, línea 9, línea 40, líneas 207 y 505 con el nombre del archivo de Postman, línea 593), `CLAUDE.md:5` y `:50`, `docs/auditoria-inicial.md:1`, `docs/propuesta-informe-v2.md:304` y `:485` (P-9), `docs/plan-calidad-y-diseno.md` (varias). `CHANGELOG.md` (7 líneas) es historial: no se reescribe, se agrega una entrada |
  | Repositorio y carpetas | el repositorio `github.com/juansalamanca01-glitch/patologia-app` (no lleva "PathoLab"); la carpeta local `patolab-app-actualizado`, que también aparece en `docs/progreso.md:14` y en la memoria de Claude Code |

  Esta lista es del 2026-10-08. Antes de hacer el cambio, se vuelve a buscar con `git grep -i "patholab\|patolab"`.
- **Ya decidido el 2026-10-08:**
  - informes finalizados de solo lectura en `/admin/` (D-14). **Hecho** el 2026-10-11 (fase 4, grupo 1);
  - corregir ya los avisos de `npm audit`. **Hecho** el mismo día.
- **Ya decidido el 2026-10-11** (respuestas a la auditoría OWASP): D-16 (solo `is_active` y token de acceso de 30 minutos, grupo 6 de la fase 4) y el orden de la fase 4 (ver el plan).
- **Para consultar con el patólogo (D-18):** lo pendiente de validar de las plantillas del manual, en la sección 6 de `docs/plantillas-manual.md`: apartados incompletos del manual («COMPLEMENTAR», «(corregir)», capítulo de biopsias pequeñas), procedimientos sin protocolo (biopsia de próstata por aguja, gástrica endoscópica, bronquiales, lipomas y quistes), las categorías de «Márgenes quirúrgicos», los obligatorios condicionales nuevos y la frase final de la descripción.
- **Para consultar con el patólogo y el profesor:** hoy el auditor y los demás patólogos leen por la API el contenido de los borradores ajenos (D-2), aunque no pueden descargar su PDF (D-12). El usuario decidió el 2026-10-11 mantenerlo así hasta consultarlo (observación de A01 en `docs/auditoria-owasp.md`).

### 3. Para producción (al publicar la aplicación)

- Definir `SECRET_KEY` propia, `DEBUG=False`, `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS`. No reutilizar la clave antigua, que quedó en el historial de git (C-3).
- Migrar de SQLite a **PostgreSQL**: `settings.py` ya lo permite con `DB_NAME`. Hay que pasar los datos y correr todas las pruebas contra PostgreSQL, en especial la de concurrencia del número de petición.
- Configurar en el servidor web un límite de tamaño de petición, por ejemplo `client_max_body_size 60m;` en Nginx (nota de I-6 en `settings.py`).
- Servir la carpeta `media/`, porque Django solo la sirve en desarrollo (M-12).
- Configurar los registros del servidor web para que no guarden los parámetros de `GET /api/pacientes/?q=`, que llevan el nombre o el documento, o protegerlos como datos sensibles. Lo aprobó así el usuario en la etapa 3.
- Revisión legal antes de un uso real con pacientes (Ley 1581 de 2012, Resolución 1995 de 1999), como dicen el README y la propuesta v2, sección 8.

Además, de la auditoría OWASP (grupo 8, `docs/auditoria-owasp.md`):
- **Registro de accesos (O-20):** antes de hacerlo, presentar al usuario una propuesta concreta de qué se registra, cuánto tiempo se guarda y quién lo consulta.
- **`/admin/` (O-18):** restringirlo en el servidor web (por IP o VPN). `django-axes` se reconsidera entonces.
- **Cookie `HttpOnly` para el token de renovación (O-19, punto 3):** estudiarla.
- O-15, O-5 punto 3, O-8, O-11 y O-12, con su corrección propuesta en el informe.

### 4. Ideas futuras, sin fase en el plan

Vienen de la hoja de ruta del README y de la propuesta v2. Ninguna está pedida:
- plantillas microscópicas e IHQ;
- catálogo CIE-10 y CIE-O con autocompletado (propuesta v2, 3.6);
- imágenes en los informes;
- imagen de la firma (propuesta v2, 3.7 y etapa 10, opcional);
- firma digital criptográfica;
- integración HL7/FHIR;
- contenedores Docker;
- en `/admin/`, regenerar `texto_generado` al guardar un borrador (hoy solo lo hace la API; ya pasaba antes). Lo anotamos en el grupo 5 de la fase 4 (2026-10-12);
- estado **"Anulado"** para un informe finalizado por error. Hoy se deja constancia con una adenda, porque un finalizado no se modifica ni se borra (D-3, D-14). Lo anotó el usuario el 2026-10-08.

La etapa 10 de la propuesta (imagen de la firma) no aparece en la hoja de ruta del README; se agrega allí en la fase 8.

### 5. Contradicciones entre documentos encontradas en el inventario

El 2026-10-08 se corrigieron en la rama `docs-pendientes` (ver `CHANGELOG.md`):
- `CLAUDE.md`;
- `docs/auditoria-inicial.md`: I-7, I-13 y la columna "Hoy" de la sección 5;
- `docs/propuesta-informe-v2.md`: el estado, la sección 8 y la tabla de la sección 7;
- `README.md`:
  - la tabla de documentación;
  - "Pruebas";
  - la imagen de la firma en la hoja de ruta;
  - D-14.

D-3 frente a D-9 se resolvió con D-14.

Quedan dos:
- `CHANGELOG.md`, I-9a: el análisis menciona `BrowserRouter`, y la app usa `createBrowserRouter` desde D-13. **Comprobado en la fase 3 (2026-10-11):** sigue sin afectar, porque la app no hidrata datos del servidor (O-11 de `docs/auditoria-owasp.md`; entrada nueva en `CHANGELOG.md`).
- `CLAUDE.md` dice "No hay linter configurado": cambia en la fase 2.

## Decisiones del usuario del 2026-11-12

Respuestas a las preguntas hechas antes de empezar las mejoras para los objetivos de investigación:

- **Herramienta:** Claude Code en una terminal del computador del usuario.
- **`git push`:** se hace después de cada commit de la rama de trabajo (ver "Forma de trabajar", punto 7). Unir a `main` sigue requiriendo preguntar.
- **D-16, campo `activo` (tarea 8, grupo 6):** el usuario **autoriza por escrito** eliminar el campo `activo` con una migración que primero copia su valor en `is_active`, como dice D-16. Es la única excepción autorizada a la regla de migraciones solo aditivas; cualquier otro borrado sigue necesitando autorización aparte.
- **Tarea 1, cómo detectar que el texto sugerido cambió:** opción A. Además de `descripcion_macroscopica_final`, un segundo campo nuevo (por ejemplo `descripcion_macroscopica_base`, opcional y vacío por defecto) guarda el texto sugerido del que partió la edición del patólogo. Si `texto_generado` ya no coincide con esa base, se muestra el aviso ("usar el nuevo texto sugerido" o "conservar mi versión"), también si se cierra la página y se vuelve otro día. Las dos migraciones son aditivas.
- **Tarea 1, vista previa en vivo:** el usuario dejó la elección a Claude. Se elige **un endpoint de solo lectura** que calcula el texto sugerido con la misma `generar_descripcion_macroscopica`, a partir de la patología y los datos del formulario, **sin guardar nada ni gastar un número de petición** (D-7). Motivo: un informe nuevo nunca se autoguarda (D-13), así que, si la vista previa dependiera del guardado, no cambiaría hasta el primer guardado. Condiciones: permisos de escritura de informes (admin y patólogo), mismas validaciones que `validar_datos`, límite de peticiones `user`, `@extend_schema` para Swagger (D-19) y, en el frontend, una espera corta después del último cambio antes de pedirla. Se presenta al usuario con su prueba antes de implementarlo, como todo cambio.
- **Tarea 1, finalizar con el aviso sin resolver:** se puede finalizar con la versión del patólogo, pero **antes se pide una confirmación** que explica que el texto sugerido cambió después de su edición.

## Pendiente de respuesta del usuario

- **Tarea 2:** tipo, opciones, obligatoriedad y frase de los campos de fijación y rotulado (se preguntan al empezar la tarea).
- **Tarea 3:** contenido del manual del HUV para placenta o lista confirmada por un patólogo.
- **Tarea 4:** textos de ejemplo de biopsias gástricas endoscópicas, sin datos de pacientes.

- Las preguntas de la fase 3 se respondieron el 2026-10-11. La de los borradores ajenos queda para el patólogo y el profesor (sección "Pendientes", punto 2).

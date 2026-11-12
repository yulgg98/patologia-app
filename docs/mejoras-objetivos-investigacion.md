# Mejoras de PathoLab para cumplir los objetivos del proyecto de investigación

> Instrucciones del usuario del 2026-11-12, copiadas sin cambios. Las respuestas del usuario a las preguntas previas están en `docs/progreso.md`, sección "Decisiones del usuario del 2026-11-12", y **tienen prioridad** sobre este texto donde lo modifican (`git push` después de cada commit; eliminar `activo` autorizado para D-16).

Actúa como desarrollador sénior de Python/Django y React, con experiencia en software clínico, seguridad (OWASP) y pruebas automatizadas.
Vas a trabajar en el repositorio de PathoLab (`patologia-app`): backend en Django 4.2 + Django REST Framework, frontend en React 18 + Vite, pruebas con el test runner de Django, Vitest y Cypress. El proyecto ya tiene un método de trabajo definido en `CLAUDE.md`, `docs/progreso.md`, `docs/decisiones.md` y `docs/plan-calidad-y-diseno.md`. Léelos completos antes de hacer cualquier cosa y respétalos.
---
1. REGLAS OBLIGATORIAS (tienen prioridad sobre todo lo demás)
1.1 No borrar nada sin autorización
No borres absolutamente nada sin mi autorización explícita y por escrito. Esto incluye archivos, carpetas, funciones, clases, componentes, endpoints, campos de modelos, columnas, migraciones, plantillas, campos de plantillas, opciones de listas, pruebas, documentación, ramas, commits y datos.
No renombres campos, modelos, endpoints ni archivos existentes. Si crees que algo debería eliminarse o renombrarse, detente, explica por qué y espera mi respuesta.
Las migraciones deben ser solo aditivas: agregar campos nuevos (con valor por defecto o `null=True`/`blank=True`), nunca eliminar ni alterar los existentes de forma que se pierdan datos.
`actualizar_plantillas` y `seed_data` no deben borrar campos ni opciones existentes (regla ya vigente en D-18). Mantén esa garantía.
No modifiques informes finalizados ni sus datos congelados (D-3, D-10, D-14, D-15). No cambies el comportamiento de las adendas (D-9).
No ejecutes comandos destructivos: `git reset --hard`, `git push --force`, `git clean`, borrado de bases de datos, `flush`, `migrate` hacia atrás, etc.
No hagas `git push`, ni unas ramas a `main`, sin preguntarme.
1.2 Que no falle lo que ya funciona
Antes de empezar, ejecuta `npm run check` y todas las pruebas (raíz, backend y frontend) y anota el resultado como línea base. Si algo ya falla antes de tus cambios, avísame y no sigas hasta que te responda.
Sigue el método de `CLAUDE.md` para cada cambio:
Escribe primero una prueba que demuestre el comportamiento nuevo (o el fallo) y muestra que falla.
Explica el cambio que vas a hacer y espera mi confirmación.
Aplica el cambio y muestra que la prueba pasa.
Ejecuta `npm run check` y todas las pruebas. Si algo falla, no hay commit hasta corregirlo (regla 7).
Registra el cambio en `CHANGELOG.md` y actualiza `docs/progreso.md`. Si es una decisión nueva, agrégala a `docs/decisiones.md` a partir de D-20 (sin modificar las anteriores).
Haz el commit. Pregunta antes de hacer `push`.
Mantén la compatibilidad con los informes ya guardados: un informe antiguo debe seguir abriéndose, editándose (si es borrador) y generando su PDF igual que antes.
Las pruebas existentes no se pueden modificar para que "pasen". Si una prueba existente debe cambiar porque cambió una regla, explícame por qué y espera mi autorización.
Trabaja una tarea por rama, creada desde `main`, con nombres descriptivos (por ejemplo `texto-macroscopico-editable`).
1.3 No inventar contenido clínico
No inventes campos, reglas de obligatoriedad, opciones de listas ni frases médicas. Todo contenido clínico debe venir del Manual de procesamiento macroscópico de patología quirúrgica del HUV–Univalle o de lo que yo te entregue confirmado por un patólogo.
Si una tarea necesita información clínica que no tienes, detente y pídemela. No uses valores provisionales "de ejemplo" en el código que se va a entregar.
Usa solo datos ficticios en pruebas y en `seed_data`. Nunca uses datos reales de pacientes.
1.4 Fuera de alcance (no hacer)
No cambies los roles ni los permisos existentes (administrador, patólogo, auditor) y no crees roles nuevos.
No trabajes en el foro, ni en integración HL7 FHIR, ni en inteligencia artificial, ni en el cambio de nombre del proyecto.
No despliegues la aplicación en ningún servidor ni crees cuentas en servicios externos. Solo prepara la configuración y la documentación.
---
2. CONTEXTO DEL PROYECTO
PathoLab es el prototipo de un trabajo de grado cuyo objetivo es analizar cómo la falta de automatización y estandarización afecta la eficiencia del personal y la consistencia de las descripciones macroscópicas en el departamento de patología del Hospital Universitario del Valle, para proponer una herramienta web de registro estructurado según el tipo de espécimen.
Los objetivos específicos que el código debe permitir cumplir son:
OE2: un prototipo web funcional que genere una descripción macroscópica sugerida para revisión del patólogo.
OE3: validar el prototipo en términos de completitud y consistencia de las descripciones, usabilidad y viabilidad técnica, económica y operativa. La validación la harán unos 3 residentes de patología con datos ficticios, mediante cuestionarios, después de usar el prototipo.
Datos verificados en el código actual:
`Informe.texto_generado` se regenera en el serializer al guardar (`generar_descripcion_macroscopica`) y es de solo lectura. El PDF lo imprime en `utils.py` (sección "DESCRIPCIÓN MACROSCÓPICA").
Las 14 plantillas están en `backend/informes/definiciones_manual.py` y se aplican con `actualizar_plantillas`. Las reglas de aplicabilidad están en `backend/informes/reglas.py` y se repiten en `frontend/src/utils/reglas.js`.
No existen campos de estado de fijación (formol/fresco) ni de rotulado del espécimen.
No existe plantilla de placenta.
La última migración de `informes` es la `0014`. La última decisión registrada es la `D-19`.
---
3. TAREAS, EN ESTE ORDEN
Al terminar cada tarea, detente, muéstrame un resumen y espera mi aprobación antes de pasar a la siguiente.
Tarea 1. Descripción macroscópica editable (prioridad alta)
Objetivo: que el patólogo pueda revisar y ajustar el texto sugerido antes de incorporarlo al informe, sin perder el texto que generó el sistema.
Requisitos:
Conserva `texto_generado` exactamente como funciona hoy (texto sugerido por el sistema).
Agrega un campo nuevo (por ejemplo `descripcion_macroscopica_final`, opcional y vacío por defecto) para el texto revisado por el patólogo. La migración debe ser aditiva.
El PDF y la vista del informe muestran el texto revisado si existe; si no existe, el texto generado, como hoy. Los informes antiguos no deben cambiar.
Si el usuario cambia los datos del formulario después de editar el texto, no sobrescribas su edición: muestra un aviso de que el texto sugerido cambió y ofrece "usar el nuevo texto sugerido" o "conservar mi versión".
El texto revisado solo se edita mientras el informe es borrador. Al finalizar, queda congelado como el resto (D-3, D-10).
Agrega en el frontend un área de texto editable con la vista previa del texto sugerido y un botón "Restaurar texto sugerido".
Agrega un botón "Copiar descripción" que copie el texto vigente al portapapeles.
Mantén el escape del texto en el PDF (I-3).
Pruebas mínimas: creación y edición en borrador; el PDF usa el texto revisado; un informe antiguo sin texto revisado genera el mismo PDF que antes; no se puede editar un informe finalizado; el aviso aparece cuando cambian los datos después de editar.
Tarea 2. Campos de estado de fijación y rotulado
Objetivo: registrar si el espécimen llega en formol o en fresco y cómo viene rotulado, datos que el patólogo consultado pidió y que aparecen en casi todas las descripciones del archivo de trabajo actual.
Requisitos:
Antes de escribir código, pregúntame:
el tipo de cada campo y sus opciones (por ejemplo: lista con "Formol", "Fresco" y "Otro" para la fijación, y texto libre para el rotulado);
si deben ser obligatorios u opcionales;
la frase con la que se redactan en la descripción generada.
No asumas ninguna de estas decisiones.
Agrégalos a las plantillas mediante `definiciones_manual.py` y `actualizar_plantillas`, sin borrar ni alterar campos existentes. Ubícalos en la sección "Identificación y procedimiento".
Mientras no estén validados por un patólogo, márcalos en el texto de ayuda como "PENDIENTE de validación", igual que los demás puntos pendientes de `docs/plantillas-manual.md`.
Un informe antiguo sin estos campos debe seguir siendo válido (un campo vacío no es un hallazgo).
Actualiza `docs/plantillas-manual.md`.
Tarea 3. Plantilla de placenta (requiere información clínica)
No escribas ningún campo hasta que yo te entregue el contenido del Manual de procesamiento macroscópico del HUV para placenta o la lista confirmada por un patólogo.
Cuando lo tengas:
Crea la plantilla siguiendo exactamente la misma estructura de las 14 existentes (secciones, condiciones, ayudas y guía de muestreo).
Agrega su fila a la matriz de `docs/plantillas-manual.md`, con lo que quede pendiente de validar.
Agrega pruebas como las de las otras plantillas.
Si en algún momento no tienes la información, detente y pídemela.
Tarea 4. Revisión de la plantilla gástrica para biopsias endoscópicas
No cambies reglas ni campos. Produce un documento (`docs/revision-gastrica-endoscopica.md`) que compare los campos actuales de la biopsia gástrica endoscópica con lo que registran las descripciones del archivo de trabajo actual. Te entregaré textos de ejemplo sin datos de pacientes.
Lista las preguntas que deben resolver los residentes o el patólogo. Los cambios se harán después, con mi autorización.
Tarea 5. Indicador de completitud del informe
Objetivo: mostrar cuántos campos aplicables están registrados, como evidencia de completitud para la validación (OE3).
Requisitos:
Cálculo de solo lectura en el backend, a partir de `reglas.py`: campos aplicables al procedimiento elegido, campos registrados y porcentaje. No guardes nada nuevo en la base de datos.
Expónlo en el detalle del informe (serializer) y muéstralo en la pantalla del informe, por ejemplo: "14 de 17 campos aplicables registrados (82 %)".
Un campo vacío cuenta como no registrado; `0` y "No" cuentan como respuestas, igual que en las validaciones actuales.
Agrega pruebas con al menos dos plantillas y con procedimientos que cambian los campos aplicables.
Tarea 6. Registro del tiempo de diligenciamiento (requiere autorización previa)
Antes de implementar, preséntame una propuesta de qué se registraría, dónde y quién lo consulta. Por ejemplo: cuándo se abre un borrador por primera vez y cuándo se guarda por última vez, solo para los informes de la instancia de prueba. Ten en cuenta que los modelos ya tienen `fecha_creacion` y `fecha_actualizacion`.
No registres nada que identifique el comportamiento de una persona sin que yo lo apruebe, porque debe informarse en el consentimiento de los participantes.
Tarea 7. Preparación de una instancia de prueba (solo configuración y documentación)
Prueba la aplicación con PostgreSQL (ya admitido por `DB_NAME` en `settings.py`) y ejecuta todas las pruebas sobre ese motor, en especial la de concurrencia del número de petición. Documenta el resultado.
Documenta en `docs/instancia-de-prueba.md` la configuración para un entorno de prueba:
`DEBUG=False`, `SECRET_KEY` nueva, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y HTTPS;
cómo servir `media/` y el límite de tamaño de las peticiones;
cómo cargar solo datos ficticios.
No despliegues nada ni crees cuentas externas.
Tarea 8. Correcciones de seguridad pendientes del plan
Sigue los grupos pendientes de la fase 4 en `docs/auditoria-owasp.md` y `docs/plan-calidad-y-diseno.md`, un grupo por rama y con las mismas reglas:
Grupo 4: actualizar Django 4.2 a 5.2 (O-9). Revisa las notas de cambios, actualiza también las dependencias necesarias, fija versiones (O-10) y confirma que todas las pruebas pasan.
Grupo 6: D-16, es decir, que `is_active` bloquee el acceso (O-2) y que el token de acceso dure 30 minutos. Evalúa también O-19 (tokens en `localStorage`) y preséntame opciones antes de cambiarlo.
Grupo 7: edición concurrente (O-14). Preséntame la propuesta antes de implementarla.
Cualquier otro hallazgo pendiente: pregúntame antes.
---
4. FORMA DE REPORTAR
Al terminar cada tarea, entrégame:
Qué cambió y por qué, en lenguaje claro.
Archivos modificados y archivos nuevos. Confirma explícitamente que no se borró ni se renombró nada.
Migraciones nuevas y confirmación de que son aditivas.
Resultado de `npm run check` y de todas las pruebas, comparado con la línea base: cuántas había, cuántas hay y que todas pasan.
Lo que quedó pendiente o requiere mi decisión.
Cómo probarlo a mano en el navegador, paso a paso.
Un párrafo breve, con evidencia verificable, que pueda usar en el capítulo 8 del informe (desarrollo del segundo objetivo).
Si en cualquier momento dudas entre hacer algo o preguntar, pregunta.
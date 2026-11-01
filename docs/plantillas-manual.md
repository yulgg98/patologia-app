# Plantillas según el manual de procesamiento macroscópico (decisión D-18)

Revisión de las 14 plantillas de `seed_data` con el **«Manual de procesamiento macroscópico de patología quirúrgica»**, Hospital Universitario del Valle «Evaristo García» E.S.E. – Universidad del Valle, segunda edición 2021–2022.

- **Definiciones:** `backend/informes/definiciones_manual.py` (campos, secciones, condiciones, ayudas y guía de muestreo de cada plantilla).
- **Cómo se aplican:** `python manage.py actualizar_plantillas` (lo llama `seed_data`). No borra campos ni opciones y no toca los informes.
- **Reglas de los campos:** `backend/informes/reglas.py` (el frontend repite la parte de aplicabilidad en `frontend/src/utils/reglas.js`).

## 1. Cómo estaban las plantillas

- Cada plantilla era una lista plana de campos, sin secciones. Un campo obligatorio se exigía siempre, aunque no correspondiera al procedimiento: por ejemplo, la lateralidad en una tiroidectomía total, los márgenes en una biopsia de mama por aguja o los cilindros en una RTU de próstata.
- Faltaban datos que el manual pide en casi todos los procedimientos: orientación y entintado, distancias a los márgenes, integridad, detalles de la lesión, estructuras incluidas.
- Algunos campos usaban un nombre para otro dato: en Vesícula Biliar, `consistencia` guardaba el grosor de la pared, `color` la mucosa y `calcificaciones` los cálculos. La descripción generada los redactaba como «La consistencia es 3 mm».
- No había dónde registrar el **muestreo para histología** (canastillas).
- La descripción omitía `0` y «No», y los campos sin frase propia salían con el nombre técnico («Num ganglios: 3»).

## 2. Matriz de correspondencia

Los campos se cuentan como «antes → después». Ningún campo existente se borró: los nombres históricos se conservan para que los informes guardados sigan siendo legibles.

| Plantilla | Procedimiento del manual | Campos | Campos agregados o mejorados | Muestreo (canastillas) según el manual | Validaciones | Observaciones |
|---|---|---|---|---|---|---|
| Biopsia de Piel | Afeitado, sacabocado, losange/elipse, alopecia, extirpación por lesión y por tumor maligno | 7 → 14 | Procedimientos del manual en «Tipo de muestra»; orientación; integridad; tamaño de la lesión y distancia al margen más cercano; ulceración; lesiones satélites; entintado | ≤ 3 mm sin dividir, ≥ 4 mm en 2–3 partes; elipse: vértices en una canastilla y secciones centrales en el resto; alopecia: corte vertical y horizontal en canastillas separadas; extirpación: puntas como márgenes | Orientación y entintado solo en elipse o extirpación; satélites solo en elipse o tumor maligno | «TOMAR FOTO EN PIEL» y figuras faltantes en el manual |
| Biopsia de Mama | Aguja gruesa, incisional, cuadrantectomía/lumpectomía/excisional (con arpón), mastectomía por malignidad | 9 → 23 | Tipo de mastectomía; orientación; cilindros, color y consistencia (aguja); elipse de piel, cola axilar, músculo, cirugía previa, areola-pezón (mastectomía); localización y características de la lesión; distancia a cada borde; entintado | Aguja: dos cilindros por canastilla; benigna: un corte por cm (2 por canastilla); sospechosa: mapeo; arpón: hasta 20 bloques; mastectomía: profundo, pezón, lecho, 4 cuadrantes, pectoral, ganglios | Márgenes solo en resecciones (no en aguja ni mastectomía); tipo de mastectomía y número de cilindros obligatorios cuando aplican | Aguja gruesa: niveles «COMPLEMENTAR». Incisional remite a «biopsias pequeñas», capítulo ausente. Las categorías de «Márgenes quirúrgicos» no están en el manual (pendiente) |
| Apéndice Cecal | Apendicectomía no neoplásica y neoplásica | 6 → 15 | Tipo de apendicectomía; mesoapéndice; perforación y su detalle; pared y lumen; contenido luminal; tumor, mucina y margen mesoapendicular (neoplásica) | No neoplásica: 1 canastilla (+1 si hace falta) con margen, punta y dos transversales; neoplásica: todo el apéndice | Detalle de la perforación obligatorio si está presente; campos tumorales solo si es neoplásica | — |
| Vesícula Biliar | Colecistectomía no tumoral y tumoral | 8 → 22 | Tipo; integridad; conducto cístico; pus o moco; número, medidas y sitio de los cálculos; conducto biliar y margen hepático; tamaño, forma, consistencia, invasión y distancias del tumor; ganglios | No tumoral: una canastilla (lesiones aparte); tumoral: cístico, una por cm de tumor, lesiones adicionales, vesícula no tumoral, ganglios | Datos de cálculos solo si están presentes; del tumor solo si es tumoral | Etiquetas corregidas: `consistencia` = Pared (espesor), `color` = Mucosa |
| Biopsia de Próstata | RTU, prostatectomía simple/abierta y radical | 8 → 17 | RTU y prostatectomías en «Tipo de procedimiento»; peso de fragmentos; peso y dimensiones de la próstata; vesículas y deferentes; áreas sospechosas; lesiones; uretra | RTU: hasta 12 g todo, luego una canastilla por cada 5 g; simple: una por cada 10 g; radical: ápex y base completos, vesículas, cuadrantes de base a ápex | Cilindros, localización y longitud solo en biopsia por aguja; peso de fragmentos en RTU; peso y dimensiones en prostatectomías | **La biopsia por aguja no está en el manual**: se conservan sus campos anteriores |
| Tiroides | Tiroidectomía (lobectomía, istmectomía, hemi, subtotal, total, de compleción) | 10 → 23 | Hemitiroidectomía y compleción; orientación; medidas de cada lóbulo, istmo y piramidal; descripción externa; parénquima; paratiroides; ubicación, % sólido/quístico, borde, distancia a la cápsula y extensión del nódulo | Orden: tercios del lóbulo derecho, istmo, tercios del izquierdo, paratiroides; benigna por cm; encapsulado: mínimo 10 cortes de cápsula | Lateralidad solo en lobectomía, hemitiroidectomía e istmectomía; datos del nódulo solo si hay nódulo | — |
| Colon y Recto | Polipectomía; colectomía y proctectomía (no tumoral, tumoral, poliposis adenomatosa familiar); resección ano-rectal | 9 → 27 | Proctectomía, ano-rectal y PAF; tipo de lesión; datos clínicos de la remisión; estructuras incluidas; mesenterio; mucosa y pared; cabeza, tallo, configuración y base del pólipo; % de luz, distancia al margen y a la reflexión; lesiones adicionales; datos de poliposis; mesorrecto; línea pectínea | Pólipo: longitudinal de la cabeza al tallo; no tumoral: bordes en una, ganglios máx. 3; tumoral: márgenes, ≥ 3 cortes o 1 por cm, ≥ 12 ganglios; PAF: 10–12 canastillas | Cada grupo de campos solo en su procedimiento | «Colocar dibujo del margen radial» pendiente en el manual. Categorías de «Márgenes quirúrgicos» pendientes |
| Útero y Cérvix | Conización; histerectomía por benignidad; radical por carcinoma endometrial o de cérvix; morcelada | 10 → 20 | Histerectomía subtotal, radicales y morcelada; orientación y dimensiones del cono; superficie externa; cavidad, canal endocervical y grosor miometrial; localización de lesiones del miometrio; invasión; parametrios; reborde vaginal | Cono: hora 1 a 12, cada una en su canastilla, o por cuadrantes; histerectomía: cérvix y endomiometrio anterior y posterior, lesiones, tubas en las dos últimas | Dimensiones del útero obligatorias solo en histerectomías | Mediciones marcadas «(corregir)» en el manual |
| Ganglio Linfático | Linfadenectomía | 9 → 13 | Sospecha clínica; grupo o nivel; hallazgos; conglomerados | Todos los ganglios; por nivel cuando corresponda; número de ganglios en cada canastilla | Sin cambios de obligatoriedad | La biopsia de ganglio remite a «biopsias pequeñas», **capítulo ausente** |
| Biopsia Gástrica | Gastrectomía vertical y total/subtotal | 7 → 16 | Gastrectomía subtotal y vertical; segmentos incluidos; curvaturas; circunferencia de los márgenes; pared; serosa; mucosa; lesión y distancias | Vertical: un corte representativo; total: 4 de la lesión, márgenes, cardias/fondo/antro, ≥ 16 ganglios | Localización y fragmentos solo en endoscópicas | **La biopsia endoscópica no está en el manual** |
| Pulmón | Biopsia en cuña; neumonectomías parciales y totales | 12 → 17 | Orientación; borde pleural; distancia pleura-borde; lesiones y su distancia a pleura y borde | Cuña: borde parenquimatoso y 1 corte por cm; resección: hilio, lesión respecto a pleura, vía aérea y parénquima, ganglios | Márgenes bronquial y vascular solo en resecciones | Lobectomía y segmentectomía se tratan como neumonectomía parcial (validar). Las biopsias bronquiales no están en el manual |
| Riñón | Nefrectomía por benignidad; radical por malignidad; biopsia renal; riñón del receptor | 11 → 22 | Nefrectomía simple y riñón del receptor; orientación; cilindros; vasos y uréter; integridad; corteza y médula; pelvis; necrosis y distancias del tumor | Benigna: 5 canastillas definidas; radical: hilio, no tumoral, transición, suprarrenal, ganglios; Wilms: todo el mapeo | Datos del tumor solo en nefrectomía con tumor; dimensiones solo en nefrectomías | — |
| Amígdalas y Adenoides | 1.4 Amigdalectomía, adenoidectomía y paratiroidectomía | 8 → 12 | Peso; descripción externa e interna; tipo de lesión | Benigna: un corte por órgano; maligna o sospechosa: cortes por cm; paratiroides pequeña: entera | Sin cambios de obligatoriedad | — |
| Tejido Blando | Resección de sarcomas | 10 → 19 | Estructura; orientación; superficie; tamaño 3D; localización; crecimiento; % de necrosis; distancia y tejido al margen más cercano | Un corte por cm, con todos los márgenes y estructuras; todos los ganglios | Campos de sarcoma solo con «Tumor de partes blandas» | **Lipomas y quistes no tienen protocolo** en el manual |

## 3. Secciones

Cada campo tiene una sección (`Plantilla.seccion`), y `actualizar_plantillas` deja juntos los campos de cada una, en este orden:

1. Identificación y procedimiento
2. Descripción macroscópica
3. Lesiones
4. Márgenes, orientación y estructuras
5. Observaciones

El formulario muestra un título por sección. No todas las plantillas tienen las cinco.

## 4. Validaciones

| Categoría | Cuándo | Ejemplo |
|---|---|---|
| Obligatorio | `obligatorio` y sin `condicion` | «Tipo de muestra» |
| Condicional | `obligatorio` con `condicion`: solo si aplica | «Lateralidad» en Tiroides, solo en lobectomía |
| Opcional | no `obligatorio` | «Observaciones» |
| No aplicable | `condicion` que no se cumple: no se muestra, no se exige y no se redacta | «Márgenes quirúrgicos» en una biopsia por aguja |

Además: un número no puede ser negativo ni texto; un valor de lista debe estar entre las opciones (salvo que el informe ya lo tuviera guardado, como una EPS desactivada, D-4); `0` y «No» son respuestas válidas. El sistema no completa ningún dato: un campo vacío no es un hallazgo negativo.

## 5. Muestreo para histología (canastillas)

- **Dónde:** en las 14 plantillas, en la tarjeta «Muestreo para histología», aparte de la descripción macroscópica.
- **Qué guarda cada canastilla:** identificación (obligatoria, única en el informe), región o estructura, lesión o margen, descripción del tejido, cantidad, entintado u orientación, motivo y observaciones. Debe tener al menos la región, la lesión o margen, o la descripción.
- **Cuántas:** las que el caso necesite. No hay un número fijo; el tope técnico es 200 por informe.
- **Cómo se registran:** el usuario las agrega, edita y quita (con confirmación) mientras el informe es un borrador. El sistema sugiere la siguiente letra libre (A, B, C…), que se puede cambiar, y nunca crea canastillas por su cuenta.
- **Guía del manual:** cada plantilla muestra las indicaciones de su procedimiento (`Patologia.guia_muestreo`) como referencia desplegable. No son reglas automáticas.
- **Guardado:** van anidadas en el informe (`canastillas`), como los diagnósticos: si se envían, reemplazan la lista; si no, no cambian. En un informe finalizado no se modifican (D-3), tampoco en `/admin/` (D-14).
- **En el informe:** el PDF imprime la sección «MUESTREO PARA HISTOLOGÍA» después de la descripción macroscópica, en una tabla. La descripción generada no las menciona: el muestreo no es un hallazgo ni un diagnóstico.

## 6. Pendiente de validación profesional

Ninguno de estos puntos se convirtió en una regla obligatoria nueva. Los textos de ayuda de los campos afectados dicen «PENDIENTE».

1. **Apartados incompletos del manual:**
   - Biopsia de mama por aguja gruesa: niveles a solicitar («COMPLEMENTAR»).
   - Histerectomías: mediciones de cavidad, canal endocervical y grosor miometrial («(corregir)»).
   - Capítulo de «biopsias pequeñas», al que remiten la biopsia incisional de mama y la biopsia de ganglio: no está en el documento.
   - Colectomía: «Colocar dibujo del margen radial». Piel: «TOMAR FOTO EN PIEL» y figuras.
2. **Procedimientos sin protocolo en el manual**, que se conservan con sus campos anteriores: biopsia de próstata por aguja, biopsia gástrica endoscópica, polipectomía y mucosectomía gástricas, biopsias bronquiales y transbronquiales, lipomas y quistes de tejido blando.
3. **Supuestos que confirmar:** que lobectomía y segmentectomía pulmonar siguen el protocolo de neumonectomía parcial.
4. **Categorías de «Márgenes quirúrgicos»** (Libres, Comprometidos, Cercanos, No valorables) en Mama y Colon: el manual pide medir la distancia, no clasificar. Se conservan porque ya existían.
5. **Obligatorios condicionales nuevos**, derivados de lo que el manual pide medir en cada procedimiento: tipo de mastectomía y número de cilindros (mama por aguja), número de cilindros (biopsia renal), detalle de la perforación (apéndice), peso de los fragmentos (RTU), y peso y dimensiones de la próstata (prostatectomías). Los demás obligatorios no se agregaron; algunos que se exigían siempre pasaron a exigirse **solo cuando aplican**: lateralidad (Tiroides), márgenes (Mama), cilindros, localización y longitud (biopsia de próstata por aguja), localización y fragmentos (gástrica endoscópica) y dimensiones (útero en histerectomías y riñón en nefrectomías).
6. **Frase final de la descripción** «Se procesa el material y se remite para estudio histopatológico.»: ya existía y se conserva, pero afirma algo que no registra el usuario.

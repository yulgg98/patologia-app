"""
Definiciones de actualización de las 14 plantillas de PathoLab.

Fuente: «Manual de procesamiento macroscópico de patología quirúrgica»,
Hospital Universitario del Valle «Evaristo García» E.S.E. – Universidad del
Valle, 2ª edición 2021-2022.

Este módulo es SOLO DATOS (no importa Django). Lo aplica el comando
`python manage.py actualizar_plantillas`.

Reglas de aplicación:
  * Los campos existentes se identifican por `campo_nombre`; solo se actualizan
    los atributos indicados aquí. Nunca se eliminan campos.
  * Las opciones de las listas se AMPLÍAN (unión), para que los informes
    históricos sigan siendo válidos.
  * El orden final es el orden de la lista.

Convenciones:
  * `cond`  -> {"campo": <campo_nombre>, "valores": [...]}: el campo solo aplica
    (se muestra y valida) cuando ese campo tiene alguno de esos valores.
  * `obl`   -> obligatorio. Con `cond`, es obligatorio condicional.
  * `ayuda` -> texto de apoyo (referencia al manual) visible al usuario.
  * «PENDIENTE…» en una ayuda marca información incompleta en el manual o que
    requiere validación profesional.
"""

S1 = 'Identificación y procedimiento'
S2 = 'Descripción macroscópica'
S3 = 'Lesiones'
S4 = 'Márgenes, orientación y estructuras'
S5 = 'Observaciones'
# Orden de las secciones en el formulario y en la descripción; actualizar_plantillas
# ordena los campos con él y conserva el orden de cada campo dentro de su sección.
ORDEN_SECCIONES = [S1, S2, S3, S4, S5]

TEXTO, NUMERO, LISTA, AREA = 'texto', 'numero', 'lista', 'textarea'


def C(nombre, sec, label=None, tipo=None, obl=None, op=None, cond=None, ayuda=None):
    """Definición de un campo; solo incluye lo indicado."""
    d = {'campo_nombre': nombre, 'seccion': sec}
    if label is not None:
        d['campo_label'] = label
    if tipo is not None:
        d['tipo_campo'] = tipo
    if obl is not None:
        d['obligatorio'] = obl
    if op is not None:
        d['opciones'] = op
    if cond is not None:
        d['condicion'] = cond
    if ayuda is not None:
        d['ayuda'] = ayuda
    return d


def en(campo, valores):
    return {'campo': campo, 'valores': list(valores)}


SI_NO = ['Sí', 'No']
PRES_AUS = ['Presente', 'Ausente']
ORIENT = ['Orientado', 'No orientado']

DEFINICIONES = {}

# ═══ 1. BIOPSIA DE PIEL ═══════════════════════════════════════════════
_AFEIT, _SACA = 'Biopsia por afeitado', 'Biopsia por sacabocado'
_ELIP, _ALOP = 'Biopsia por losange/elipse', 'Biopsia por alopecia'
_EXLES, _EXMAL = 'Extirpación por lesión', 'Extirpación por tumor maligno'
_PIEL_ORIENT = [_ELIP, _EXLES, _EXMAL, 'Escisional']

DEFINICIONES['Biopsia de Piel'] = {
    'manual': 'Piel: afeitado, sacabocado, losange/elipse, alopecia; extirpación por lesión y por tumor maligno.',
    'campos': [
        C('localizacion', S1),
        C(
            'tipo_muestra',
            S1,
            op=['Punch', 'Escisional', 'Incisional', 'Shave', _AFEIT, _SACA, _ELIP, _ALOP, _EXLES, _EXMAL],
            ayuda='Procedimientos del manual: afeitado, sacabocado, losange/elipse, alopecia, extirpación por lesión y por tumor maligno.',
        ),
        C(
            'orientacion',
            S4,
            'Orientación del espécimen',
            LISTA,
            op=ORIENT,
            cond=en('tipo_muestra', _PIEL_ORIENT),
            ayuda='Si no está orientado se pinta todo el margen de un solo color (negro); si está orientado, según el código de colores.',
        ),
        C(
            'dimensiones',
            S2,
            'Dimensiones (cm)',
            ayuda='Afeitado, losange/elipse y extirpación: 3 dimensiones. Sacabocado y alopecia: 2 dimensiones (diámetro y profundidad).',
        ),
        C('integridad', S2, 'Integridad', LISTA, obl=False, op=['Íntegro', 'Fragmentado']),
        C('color', S2),
        C('superficie', S2),
        C('lesion_tamanio', S3, 'Tamaño de la lesión (cm)', TEXTO),
        C('bordes', S3),
        C('lesion_distancia_margen', S3, 'Distancia de la lesión al margen más cercano (cm)', TEXTO),
        C('lesion_ulceracion', S3, 'Ulceración', LISTA, op=PRES_AUS + ['No valorable']),
        C(
            'lesion_satelites',
            S3,
            'Nódulos / lesiones satélites',
            LISTA,
            op=['Presentes', 'Ausentes', 'No valorable'],
            cond=en('tipo_muestra', [_ELIP, _EXMAL]),
        ),
        C(
            'margenes_entintado',
            S4,
            'Entintado de márgenes (colores y ubicación)',
            TEXTO,
            cond=en('tipo_muestra', _PIEL_ORIENT),
            ayuda='Ej.: «margen de las 12 en punto entintado en verde, margen de las 6 en punto en azul».',
        ),
        C('hallazgos_adicionales', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Biopsia por afeitado o sacabocado',
            'items': [
                '≤ 3 mm: enviar sin dividir.',
                '≥ 4 mm: dividir en 2 o 3 partes según el tamaño.',
                'Enviar todo el espécimen.',
            ],
        },
        {
            'titulo': 'Biopsia por losange/elipse',
            'items': [
                'Vértices (afeitado) en una sola canastilla.',
                'Secciones centrales respecto al borde profundo en el resto de canastillas.',
                'Espécimen pequeño: enviar todo; si no, cortes representativos.',
            ],
        },
        {
            'titulo': 'Biopsia por alopecia',
            'items': [
                'Dos sacabocados: uno horizontal (5 niveles) y uno vertical (2 niveles y PAS).',
                'Un solo sacabocado ≥ 4 mm: método HoVert; corte vertical en una canastilla y cortes horizontales en otra.',
            ],
        },
        {
            'titulo': 'Extirpación por lesión',
            'items': [
                '≤ 3 mm: intacto. 4–6 mm: cortar por el centro y enviar ambas mitades. ≥ 7 mm: lonja central de 2–3 mm y el resto en formol.',
                'Lesiones grandes: cortes seriados cada 2–3 mm; las «puntas» como márgenes en una canastilla; el resto en una o más canastillas.',
                'Lesión pigmentada: el primer corte por la parte más gruesa u oscura.',
            ],
        },
        {
            'titulo': 'Extirpación por tumor maligno',
            'items': [
                '> 5 mm con lesión cerca de bordes: cortes paralelos al eje mayor con tumor y borde.',
                'Lesión central: tratarla como elipse, bordes angulares en una canastilla; tres niveles en el bloque con la lesión (elipse < 2 cm).',
            ],
        },
    ],
}

# ═══ 2. BIOPSIA DE MAMA ═══════════════════════════════════════════════
_M_RESEC = [
    'Tumorectomía',
    'Lumpectomía',
    'Cuadrantectomía',
    'Biopsia excisional',
    'Lumpectomía/cuadrantectomía con arpón',
]
_M_MAST = ['Mastectomía']
_M_AGUJA = ['Biopsia por aguja gruesa', 'Biopsia incisional']
_M_NOAGUJA = _M_RESEC + _M_MAST

DEFINICIONES['Biopsia de Mama'] = {
    'manual': 'Mama: aguja gruesa, incisional, cuadrantectomía/lumpectomía/excisional (con arpón), mastectomía por malignidad.',
    'campos': [
        C('lateralidad', S1),
        C(
            'tipo_muestra',
            S1,
            op=[
                'Biopsia por aguja gruesa',
                'Tumorectomía',
                'Mastectomía',
                'Biopsia incisional',
                'Cuadrantectomía',
                'Lumpectomía',
                'Biopsia excisional',
                'Lumpectomía/cuadrantectomía con arpón',
            ],
            ayuda='Ganglio centinela, vaciamiento axilar, márgenes en afeitado y resección de ductos tienen protocolo propio en el manual y no son tipos de esta plantilla.',
        ),
        C(
            'tipo_mastectomia',
            S1,
            'Tipo de mastectomía',
            LISTA,
            obl=True,
            cond=en('tipo_muestra', _M_MAST),
            op=[
                'Conservadora de pezón',
                'Conservadora de piel',
                'Simple / limpieza',
                'Radical modificada',
                'Radical',
                'Profiláctica',
            ],
        ),
        C(
            'orientacion',
            S4,
            'Orientación del espécimen',
            LISTA,
            op=ORIENT,
            cond=en('tipo_muestra', _M_NOAGUJA),
            ayuda='Las resecciones deben venir orientadas; si no, comunicarse con quirófano.',
        ),
        C(
            'num_fragmentos',
            S2,
            'Número de cilindros / fragmentos',
            NUMERO,
            obl=True,
            cond=en('tipo_muestra', _M_AGUJA),
        ),
        C('muestra_color', S2, 'Color', TEXTO, cond=en('tipo_muestra', _M_AGUJA)),
        C('muestra_consistencia', S2, 'Consistencia', TEXTO, cond=en('tipo_muestra', _M_AGUJA)),
        C(
            'dimensiones',
            S2,
            'Dimensiones (cm)',
            ayuda='Resecciones: 3 dimensiones. Cilindros/fragmentos: medir cada uno.',
        ),
        C('peso', S2, obl=False, cond=en('tipo_muestra', _M_NOAGUJA)),
        C('elipse_piel', S2, 'Elipse de piel (cm, 2 dimensiones)', TEXTO, cond=en('tipo_muestra', _M_MAST)),
        C('cola_axilar', S2, 'Cola axilar (cm, 3 dimensiones)', TEXTO, cond=en('tipo_muestra', _M_MAST)),
        C('musculo_pectoral', S2, 'Músculo estriado (cm, 2 dimensiones)', TEXTO, cond=en('tipo_muestra', _M_MAST)),
        C(
            'cirugia_previa',
            S2,
            'Biopsia o cirugía previa (tracto de aguja, cicatriz, sutura) y localización',
            AREA,
            cond=en('tipo_muestra', _M_MAST),
        ),
        C('areola_piel', S2, 'Hallazgos en areola-pezón y piel', AREA, cond=en('tipo_muestra', _M_MAST)),
        C(
            'lesion_localizacion',
            S3,
            'Localización de la lesión (cuadrante)',
            TEXTO,
            cond=en('tipo_muestra', _M_NOAGUJA),
        ),
        C('tumor_tamanio', S3, cond=en('tipo_muestra', _M_NOAGUJA)),
        C(
            'lesion_caracteristicas',
            S3,
            'Características de la lesión (consistencia, patrón de crecimiento)',
            AREA,
            cond=en('tipo_muestra', _M_NOAGUJA),
        ),
        C('necrosis', S3, cond=en('tipo_muestra', _M_NOAGUJA)),
        C(
            'margen_distancias',
            S4,
            'Distancia mínima de la lesión a cada borde (cm)',
            AREA,
            cond=en('tipo_muestra', _M_NOAGUJA),
            ayuda='Superior, inferior, lateral, medial, profundo y anterior.',
        ),
        C(
            'margenes_entintado',
            S4,
            'Entintado de márgenes',
            TEXTO,
            cond=en('tipo_muestra', _M_NOAGUJA),
            ayuda='Superior azul, inferior verde, lateral amarillo, medial rojo, profundo negro, anterior naranja (si no trae elipse de piel).',
        ),
        C(
            'margenes',
            S4,
            obl=True,
            cond=en('tipo_muestra', _M_RESEC),
            ayuda='PENDIENTE DE VALIDACIÓN PROFESIONAL: el manual pide medir distancias a los bordes; no define estas categorías macroscópicas.',
        ),
        C('ganglios', S4, 'Ganglios linfáticos (número)'),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Aguja gruesa',
            'items': [
                'Dos cilindros alineados en paralelo sobre papel filtro por canastilla.',
                'Niveles a solicitar: PENDIENTE (el manual dice «COMPLEMENTAR»).',
            ],
        },
        {
            'titulo': 'Biopsia incisional',
            'items': [
                'Procesar en su totalidad (el manual remite al capítulo «biopsias pequeñas», que no está incluido).'
            ],
        },
        {
            'titulo': 'Cuadrantectomía / lumpectomía / excisional',
            'items': [
                'Lesión benigna (p. ej. fibroadenoma): un corte por cm de la dimensión mayor, 2 cortes por canastilla.',
                'Lesión sospechosa de malignidad: mapear y rotular cada sección.',
                'Sin lesión: zona fibrótica < 3 cm se envía toda; > 3 cm, 2 cortes por cm.',
                'Con arpón: lesión visible, enviar la muestra completa (hasta 20 bloques); aclarar el bloque de la aguja y si contiene calcificación.',
            ],
        },
        {
            'titulo': 'Mastectomía por malignidad',
            'items': [
                'Margen profundo en relación al tumor; pezón y base del pezón; piel con cicatriz.',
                'Lecho tumoral (un corte por cm de tumor sin neoadyuvancia).',
                'Tejido no lesional de los 4 cuadrantes; músculo pectoral mayor; tejido inter-lesional; ganglios regionales.',
            ],
        },
    ],
}

# ═══ 3. APÉNDICE CECAL ════════════════════════════════════════════════
_A_NEO = 'Neoplásica (sospechosa o comprobada)'
DEFINICIONES['Apéndice Cecal'] = {
    'manual': 'Apendicectomía no neoplásica y neoplásica.',
    'campos': [
        C('tipo_muestra', S1),
        C(
            'tipo_apendicectomia',
            S1,
            'Tipo de apendicectomía',
            LISTA,
            obl=False,
            op=['No neoplásica', _A_NEO],
            ayuda='Los tumores apendiculares sospechosos o comprobados se envían en su totalidad.',
        ),
        C('dimensiones', S2, 'Longitud x Diámetro (cm)', ayuda='Medir largo y rango de diámetro.'),
        C('mesoapendice', S2, 'Ancho del mesoapéndice (cm)', TEXTO),
        C('superficie', S2, 'Superficie serosa'),
        C('consistencia', S2),
        C('color', S2),
        C('perforacion', S2, 'Perforación', LISTA, op=PRES_AUS),
        C(
            'perforacion_detalle',
            S2,
            'Perforación: tamaño y localización',
            TEXTO,
            obl=True,
            cond=en('perforacion', ['Presente']),
        ),
        C('pared_lumen', S2, 'Pared y lumen (engrosamiento, estado del lumen)', AREA),
        C('contenido_luminal', S2, 'Contenido luminal (pus, fecalitos, etc.)', TEXTO),
        C(
            'tumor_descripcion',
            S3,
            'Tumor: tamaño, localización y consistencia',
            AREA,
            cond=en('tipo_apendicectomia', [_A_NEO]),
        ),
        C(
            'mucina_luminal',
            S3,
            'Acumulación de mucina en el lumen',
            LISTA,
            op=PRES_AUS,
            cond=en('tipo_apendicectomia', [_A_NEO]),
            ayuda='Si hay mucina: enviar el apéndice completo y el margen de resección en una canastilla sola.',
        ),
        C(
            'margen_resecion',
            S4,
            'Margen de resección / margen mesoapendicular',
            TEXTO,
            cond=en('tipo_apendicectomia', [_A_NEO]),
        ),
        C('hallazgos_adicionales', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'No neoplásica (1 canastilla, 1 adicional si es necesario)',
            'items': [
                'Margen de resección, afeitado y entintado.',
                'Una sección longitudinal de la punta.',
                'Dos secciones transversales de apéndice proximal y medio, o áreas inflamadas / sitios de perforación.',
                'Sospecha de apendicitis con apéndice macroscópicamente normal: enviar el apéndice completo.',
            ],
        },
        {
            'titulo': 'Neoplásica',
            'items': [
                'Margen de resección afeitado (o perpendicular si la lesión se acerca) y margen graso mesoapendicular.',
                'Punta biseccionada longitudinalmente.',
                'Neoplasia mucinosa: cortes transversales restantes en su totalidad, de proximal a distal.',
            ],
        },
    ],
}

# ═══ 4. VESÍCULA BILIAR ═══════════════════════════════════════════════
_V_TUM = 'Tumoral'
DEFINICIONES['Vesícula Biliar'] = {
    'manual': 'Colecistectomía no tumoral y tumoral.',
    'campos': [
        C('tipo_muestra', S1),
        C('tipo_estudio', S1, 'Tipo de colecistectomía', LISTA, obl=False, op=['No tumoral', _V_TUM]),
        C('dimensiones', S2, 'Dimensiones de la vesícula (cm, 2 dimensiones)'),
        C(
            'integridad',
            S2,
            'Integridad del espécimen',
            LISTA,
            op=['Intacta (abierta)', 'Intacta (cerrada)', 'Fragmentada'],
        ),
        C('cistico_dim', S2, 'Conducto cístico (cm)', TEXTO),
        C('superficie', S2, 'Superficie serosa'),
        C(
            'consistencia',
            S2,
            'Pared (espesor)',
            ayuda='Registra el grosor de la pared (se conserva el identificador histórico «consistencia»).',
        ),
        C('color', S2, 'Mucosa', ayuda='Registra las características de la mucosa (identificador histórico «color»).'),
        C('contenido_luminal', S2, 'Pus o moco', TEXTO),
        C('calcificaciones', S2, 'Cálculos'),
        C('numero_calculos', S2, cond=en('calcificaciones', ['Presente(s)'])),
        C(
            'calculos_medidas',
            S2,
            'Cálculos: rango de medida y color',
            TEXTO,
            cond=en('calcificaciones', ['Presente(s)']),
        ),
        C(
            'calculos_sitio',
            S2,
            'Cálculos: sitio donde se encontraron',
            LISTA,
            op=['En la bilis', 'Embebidos en la mucosa', 'Impactados en el cuello', 'Impactados en el cístico'],
            cond=en('calcificaciones', ['Presente(s)']),
        ),
        C('conducto_biliar_largo', S4, 'Largo del conducto biliar (cm)', TEXTO, cond=en('tipo_estudio', [_V_TUM])),
        C(
            'margen_hepatico',
            S4,
            'Margen de resección hepático / tejido hepático adherido',
            TEXTO,
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C('tumor_tamanio', S3, 'Tumor: tamaño (cm, 3 dimensiones)', TEXTO, cond=en('tipo_estudio', [_V_TUM])),
        C(
            'tumor_forma',
            S3,
            'Tumor: forma',
            LISTA,
            op=['Polipoide', 'Ulcerada', 'Fungoide'],
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C(
            'tumor_consistencia',
            S3,
            'Tumor: consistencia',
            LISTA,
            op=['Firme', 'Friable'],
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C(
            'tumor_invasion',
            S3,
            'Tumor: profundidad de invasión (macroscópica)',
            LISTA,
            op=['Hasta la mucosa', 'Hasta la muscular propia', 'A otros tejidos'],
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C(
            'tumor_distancias',
            S3,
            'Tumor: distancia al margen del cístico, al margen hepático y a la serosa (cm)',
            AREA,
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C(
            'ganglios_medidas',
            S4,
            'Nodos linfáticos (medidas en 2 dimensiones)',
            TEXTO,
            cond=en('tipo_estudio', [_V_TUM]),
        ),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'No tumoral',
            'items': [
                'Margen del cístico y cortes representativos de fondo, cuerpo y cuello en una sola canastilla.',
                'Pólipos u otras lesiones en una canastilla diferente.',
            ],
        },
        {
            'titulo': 'Tumoral',
            'items': [
                'Margen del conducto cístico en una canastilla.',
                'Una canastilla por cm de tumor (invasión máxima, aproximación a serosa, relación con mucosa normal y con margen hepático/órganos adheridos).',
                'Una canastilla con cualquier lesión adicional; una con 2–4 secciones de vesícula no tumoral.',
                'Enviar todos los nodos linfáticos identificados.',
            ],
        },
    ],
}

# ═══ 5. BIOPSIA DE PRÓSTATA (la biopsia por aguja NO está en el manual) ═══
_P_AGUJA = ['Biopsia por aguja (TRUS)', 'Biopsia por fusión RM']
_P_RTU = 'Resección transuretral (RTU)'
_P_SIMPLE = 'Prostatectomía simple/abierta (adenomectomía)'
_P_RAD = 'Prostatectomía radical'
DEFINICIONES['Biopsia de Próstata'] = {
    'manual': 'Próstata: RTU, prostatectomía simple/abierta y radical. La biopsia por aguja NO está documentada.',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            op=_P_AGUJA + [_P_RTU, _P_SIMPLE, _P_RAD],
            ayuda='PENDIENTE: el manual no incluye protocolo para la biopsia por aguja; se conservan los campos que ya tenía la plantilla.',
        ),
        C('num_cilindros', S2, obl=True, cond=en('tipo_muestra', _P_AGUJA)),
        C('localizacion', S2, obl=True, cond=en('tipo_muestra', _P_AGUJA)),
        C('longitud_total', S2, obl=True, cond=en('tipo_muestra', _P_AGUJA)),
        C(
            'peso_fragmentos',
            S2,
            'Peso total de los fragmentos (g)',
            NUMERO,
            obl=True,
            cond=en('tipo_muestra', [_P_RTU]),
            ayuda='RTU: pesar todos los fragmentos; el muestreo depende del peso.',
        ),
        C('peso', S2, 'Peso de la próstata (g)', NUMERO, obl=True, cond=en('tipo_muestra', [_P_SIMPLE, _P_RAD])),
        C(
            'dimensiones_prostata',
            S2,
            'Dimensiones de la próstata (cm, 3 dimensiones)',
            TEXTO,
            obl=True,
            cond=en('tipo_muestra', [_P_SIMPLE, _P_RAD]),
        ),
        C(
            'dimensiones_vesiculas',
            S2,
            'Vesículas seminales (cm, 3 dimensiones)',
            TEXTO,
            cond=en('tipo_muestra', [_P_RAD]),
        ),
        C(
            'dimensiones_deferentes',
            S2,
            'Conductos deferentes (cm, 2 dimensiones)',
            TEXTO,
            cond=en('tipo_muestra', [_P_RAD]),
        ),
        C('forma_fragmentos', S2, 'Forma de los fragmentos', TEXTO, cond=en('tipo_muestra', [_P_RTU])),
        C('color', S2),
        C('consistencia', S2),
        C(
            'areas_sospechosas',
            S3,
            'Áreas amarillas, induradas o nodulares',
            AREA,
            cond=en('tipo_muestra', [_P_RTU, _P_SIMPLE, _P_RAD]),
        ),
        C(
            'lesiones_descripcion',
            S3,
            'Lesiones: localización, color, extensión a márgenes u otras estructuras',
            AREA,
            cond=en('tipo_muestra', [_P_RAD]),
        ),
        C('uretra_identificada', S4, 'Uretra identificada', LISTA, op=SI_NO, cond=en('tipo_muestra', [_P_SIMPLE])),
        C('psa', S1),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'RTU',
            'items': [
                'Hasta 12 g: enviar todo. Más de 12 g: 12 g en su totalidad y luego una canastilla por cada 5 g.'
            ],
        },
        {
            'titulo': 'Prostatectomía simple / abierta',
            'items': [
                'Cortes representativos: 1 canastilla por cada 10 g, representando áreas sospechosas.',
                'Si se identifica la uretra: cortes representativos en una canastilla.',
            ],
        },
        {
            'titulo': 'Prostatectomía radical',
            'items': [
                'Bordes del ápex (cuadrantes) y de la base (derecho/izquierdo), enviados completos.',
                'Vesículas seminales con borde del conducto deferente; transición vesícula-próstata.',
                'Cuadrantes anterior y posterior, derecho e izquierdo, intercalados de base a ápex en las canastillas necesarias.',
            ],
        },
    ],
}

# ═══ 6. TIROIDES ══════════════════════════════════════════════════════
_T_LOBO = ['Lobectomía', 'Hemitiroidectomía', 'Istmectomía']
_T_NOD = ['Sí, único', 'Sí, múltiples']
DEFINICIONES['Tiroides'] = {
    'manual': 'Tiroidectomía (lobectomía, istmectomía, hemitiroidectomía, subtotal, total, de compleción).',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            op=[
                'Lobectomía',
                'Tiroidectomía total',
                'Tiroidectomía subtotal',
                'Biopsia por aguja fina (BAAF)',
                'Istmectomía',
                'Hemitiroidectomía',
                'Tiroidectomía de compleción',
            ],
        ),
        C('lateralidad', S1, obl=True, cond=en('tipo_muestra', _T_LOBO)),
        C(
            'orientacion',
            S4,
            'Orientación',
            LISTA,
            op=['Por configuración anatómica', 'Por hilos de sutura', 'No orientado'],
        ),
        C('dimensiones', S2, 'Dimensiones del espécimen (cm)'),
        C('peso', S2),
        C('dim_lobulo_der', S2, 'Lóbulo derecho (cm, 3 dimensiones)', TEXTO),
        C('dim_lobulo_izq', S2, 'Lóbulo izquierdo (cm, 3 dimensiones)', TEXTO),
        C('dim_istmo', S2, 'Istmo (cm)', TEXTO),
        C('dim_piramidal', S2, 'Lóbulo piramidal, si está presente (cm)', TEXTO),
        C(
            'superficie_externa',
            S2,
            'Descripción externa (forma, color, simetría, textura, consistencia, estructuras extratiroideas adheridas)',
            AREA,
        ),
        C('parenquima_normal', S2, 'Parénquima tiroideo normal (color, consistencia, calcificaciones)', AREA),
        C(
            'paratiroides',
            S4,
            'Glándulas paratiroides disecadas',
            LISTA,
            op=['Sí, enviadas en una canastilla', 'No identificadas', 'No aplica'],
        ),
        C('nodulo_presente', S3),
        C(
            'nodulo_ubicacion',
            S3,
            'Ubicación (lóbulo y tercio superior/medio/inferior)',
            TEXTO,
            cond=en('nodulo_presente', _T_NOD),
        ),
        C('nodulo_tamanio', S3, cond=en('nodulo_presente', _T_NOD)),
        C('nodulo_aspecto', S3, cond=en('nodulo_presente', _T_NOD)),
        C(
            'nodulo_solido_quistico',
            S3,
            'Componente sólido vs. quístico (%)',
            TEXTO,
            cond=en('nodulo_presente', _T_NOD),
        ),
        C('nodulo_borde', S3, 'Borde', LISTA, op=['Infiltrante', 'Encapsulado'], cond=en('nodulo_presente', _T_NOD)),
        C(
            'nodulo_distancia_margen',
            S3,
            'Distancia al margen de resección (cápsula) (cm)',
            TEXTO,
            cond=en('nodulo_presente', _T_NOD),
        ),
        C(
            'nodulo_extension',
            S3,
            'Extensión a estructuras adyacentes (grasa, músculo, paratiroides, etc.)',
            AREA,
            cond=en('nodulo_presente', _T_NOD),
        ),
        C('capsula', S4),
        C('ganglios', S4),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Orden de envío (canastillas necesarias)',
            'items': [
                'Tercio superior, medio e inferior del lóbulo derecho.',
                'Istmo.',
                'Tercio superior, medio e inferior del lóbulo izquierdo.',
                'Glándulas paratiroides.',
            ],
        },
        {
            'titulo': 'Según la lesión',
            'items': [
                'Benigna (bocio, inflamatoria, sin nódulos sospechosos): cortes seriados perpendiculares por centímetro.',
                'Nódulo con sospecha de cáncer invasivo: cortes seriados por cm de lesión respecto al margen más cercano y al parénquima normal.',
                'Nódulo encapsulado: mínimo 10 cortes de la cápsula; extremos superior e inferior cortados sagitalmente.',
            ],
        },
    ],
}

# ═══ 7. COLON Y RECTO ═════════════════════════════════════════════════
_C_POLIP = ['Polipectomía']
_C_RESEC = [
    'Colectomía parcial',
    'Hemicolectomía derecha',
    'Hemicolectomía izquierda',
    'Sigmoidectomía',
    'Resección anterior baja',
    'Resección abdominoperineal',
    'Colectomía total',
    'Colectomía transversa',
    'Proctectomía',
    'Resección ano-rectal',
    'Colectomía por poliposis adenomatosa familiar',
]
_C_RECTO = ['Resección anterior baja', 'Resección abdominoperineal', 'Proctectomía', 'Resección ano-rectal']
_C_ANO = ['Resección abdominoperineal', 'Resección ano-rectal']
DEFINICIONES['Colon y Recto'] = {
    'manual': 'Polipectomía; colectomía y proctectomía (no tumoral, tumoral, poliposis adenomatosa familiar); resecciones ano-rectales.',
    'campos': [
        C('tipo_muestra', S1, op=['Biopsia endoscópica', 'Polipectomía'] + _C_RESEC),
        C(
            'indicacion',
            S1,
            'Tipo de lesión de la resección',
            LISTA,
            op=['Lesión tumoral', 'Lesión no tumoral', 'Poliposis adenomatosa familiar'],
            cond=en('tipo_muestra', _C_RESEC),
            ayuda='El manual separa el procesamiento por lesiones tumorales, no tumorales y poliposis adenomatosa familiar.',
        ),
        C(
            'datos_clinicos',
            S1,
            'Datos clínicos de la remisión (procedimiento, biopsia previa, neoadyuvancia, incidencias quirúrgicas)',
            AREA,
            cond=en('tipo_muestra', _C_RESEC),
        ),
        C('localizacion', S1, obl=True),
        C(
            'segmentos_incluidos',
            S2,
            'Estructuras incluidas (íleon terminal, apéndice, otras)',
            TEXTO,
            cond=en('tipo_muestra', _C_RESEC),
        ),
        C('dimensiones', S2, 'Dimensiones (cm)', ayuda='Longitud y diámetro de la pieza.'),
        C('mesenterio', S2, 'Mesenterio y serosa', AREA, cond=en('tipo_muestra', _C_RESEC)),
        C(
            'mucosa_pared',
            S2,
            'Mucosa y pared (lesiones, ulceración, grosor, fibrosis, necrosis)',
            AREA,
            cond=en('indicacion', ['Lesión no tumoral']),
        ),
        C('polipo_cabeza', S2, 'Pólipo: diámetro de la cabeza (cm)', TEXTO, cond=en('tipo_muestra', _C_POLIP)),
        C('polipo_tallo', S2, 'Pólipo: longitud del tallo (cm)', TEXTO, cond=en('tipo_muestra', _C_POLIP)),
        C(
            'polipo_configuracion',
            S2,
            'Pólipo: configuración',
            LISTA,
            op=['Polipoide', 'Villiforme'],
            cond=en('tipo_muestra', _C_POLIP),
        ),
        C(
            'polipo_base',
            S4,
            'Pólipo: base',
            LISTA,
            op=['Sésil', 'Con tallo'],
            cond=en('tipo_muestra', _C_POLIP),
            ayuda='Orientar la muestra, identificar la base o el tallo y pintar la base.',
        ),
        C('tumor_tamanio', S3),
        C('forma', S3),
        C('tumor_luz', S3, 'Porcentaje de la luz que ocupa el tumor', TEXTO, cond=en('indicacion', ['Lesión tumoral'])),
        C(
            'tumor_distancia_margen',
            S3,
            'Distancia del tumor al margen quirúrgico más próximo (cm)',
            TEXTO,
            cond=en('indicacion', ['Lesión tumoral']),
        ),
        C(
            'tumor_reflexion',
            S3,
            'Distancia del tumor a la reflexión peritoneal (cm)',
            TEXTO,
            cond=en('tipo_muestra', _C_RECTO),
        ),
        C(
            'lesiones_adicionales',
            S3,
            'Otras lesiones (pólipos, divertículos, perforaciones) y su localización',
            AREA,
            cond=en('tipo_muestra', _C_RESEC),
        ),
        C(
            'poliposis_numero',
            S3,
            'Número estimado de pólipos',
            TEXTO,
            cond=en('indicacion', ['Poliposis adenomatosa familiar']),
        ),
        C(
            'poliposis_tamano',
            S3,
            'Rango de tamaño de los pólipos',
            TEXTO,
            cond=en('indicacion', ['Poliposis adenomatosa familiar']),
        ),
        C(
            'poliposis_distribucion',
            S3,
            'Afectación',
            LISTA,
            op=['Difusa', 'Parcheada', 'Focal', 'Multifocal'],
            cond=en('indicacion', ['Poliposis adenomatosa familiar']),
        ),
        C(
            'mesorrecto',
            S4,
            'Integridad del mesorrecto',
            LISTA,
            op=['Íntegro', 'Parcialmente íntegro', 'Insatisfactorio'],
            cond=en('tipo_muestra', _C_RECTO),
        ),
        C('linea_pectinea', S4, 'Distancia del tumor a la línea pectínea (cm)', TEXTO, cond=en('tipo_muestra', _C_ANO)),
        C(
            'margenes',
            S4,
            ayuda='PENDIENTE DE VALIDACIÓN PROFESIONAL: el manual indica medir la distancia al margen; no define estas categorías.',
        ),
        C('ganglios', S4),
        C('perforacion', S3),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Polipectomía',
            'items': [
                'Con tallo > 1 cm o sin tallo: corte longitudinal, de la cabeza a todo el tallo, tan largo como permita la canastilla.'
            ],
        },
        {
            'titulo': 'Colectomía no tumoral',
            'items': [
                'Tantas canastillas como sean necesarias de las áreas lesionadas.',
                'Bordes de resección en 1 canastilla.',
                'Ganglios linfáticos: muestras representativas (máximo 3 canastillas).',
                'Isquemia o vólvulo: muestrear vasos.',
            ],
        },
        {
            'titulo': 'Colectomía tumoral',
            'items': [
                'Márgenes distal y proximal en una canastilla; margen radial.',
                'Al menos 3 cortes del tumor, o uno por centímetro; tumor con mucosa adyacente.',
                'Mucosa no tumoral, lesiones adicionales y estructuras acompañantes.',
                'Todos los nódulos linfáticos (al menos 12).',
            ],
        },
        {
            'titulo': 'Poliposis adenomatosa familiar',
            'items': [
                'Promedio de 10 a 12 canastillas: pólipos > 1,5 cm, zonas de mayor densidad, áreas sospechosas, pólipos representativos cada 10 cm, ≥ 12 ganglios, márgenes.',
                'Registrar la ubicación de las muestras en un dibujo de la pieza.',
            ],
        },
        {
            'titulo': 'Resecciones ano-rectales',
            'items': [
                'Bordes rectal y perineal; tumor con borde radial, mucosa adyacente y línea pectínea; mucosa rectal y anal; unión mucocutánea; periné; grasa perirrectal y ganglios.'
            ],
        },
    ],
}

# ═══ 8. ÚTERO Y CÉRVIX (el manual marca «(corregir)» en histerectomías) ═══
_U_HIST = [
    'Histerectomía total abdominal',
    'Histerectomía vaginal',
    'Histerectomía laparoscópica',
    'Histerectomía con anexos',
    'Histerectomía subtotal',
    'Histerectomía radical (carcinoma endometrial)',
    'Histerectomía radical (carcinoma de cérvix)',
    'Histerectomía morcelada por laparoscopia',
]
_U_RAD = ['Histerectomía radical (carcinoma endometrial)', 'Histerectomía radical (carcinoma de cérvix)']
_U_CONO = ['Cono/LEEP']
DEFINICIONES['Útero y Cérvix'] = {
    'manual': 'Conización cervical; histerectomía por benignidad; histerectomía radical por carcinoma endometrial o de cérvix; histerectomía morcelada.',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            op=['Biopsia cervical', 'Legrado endometrial', 'Legrado fraccionado', 'Cono/LEEP'] + _U_HIST,
        ),
        C(
            'orientacion_cono',
            S4,
            'Orientación del cono',
            LISTA,
            op=['Hilo a las 12 del reloj', 'Orificio cervical externo identificado', 'No orientado'],
            cond=en('tipo_muestra', _U_CONO),
            ayuda='Borde endocervical: tinta negra. Bordes profundo y ectocervical: tinta roja.',
        ),
        C('cono_dimensiones', S2, 'Dimensiones del cono (cm)', TEXTO, cond=en('tipo_muestra', _U_CONO)),
        C(
            'dimensiones',
            S2,
            'Dimensiones del útero (cm)',
            obl=True,
            cond=en('tipo_muestra', _U_HIST),
            ayuda='3 dimensiones, con anexos si fueron enviados.',
        ),
        C('peso', S2, obl=False),
        C(
            'superficie_externa',
            S2,
            'Superficie externa (lisa, rugosa, nodulaciones, adherencias)',
            AREA,
            cond=en('tipo_muestra', _U_HIST),
        ),
        C(
            'cavidad_endometrial',
            S2,
            'Cavidad endometrial (cm, 2 dimensiones)',
            TEXTO,
            cond=en('tipo_muestra', _U_HIST),
            ayuda='PENDIENTE: el manual marca «(corregir)» en las mediciones de cavidad, canal endocervical y miometrio.',
        ),
        C('canal_endocervical', S2, 'Canal endocervical (cm)', TEXTO, cond=en('tipo_muestra', _U_HIST)),
        C('grosor_miometrial', S2, 'Grosor miometrial (cm)', TEXTO, cond=en('tipo_muestra', _U_HIST)),
        C('endometrio', S2),
        C('miometrio', S2),
        C('num_miomas', S3),
        C('mioma_mayor', S3),
        C(
            'lesion_miometrio_loc',
            S3,
            'Localización de lesiones del miometrio',
            LISTA,
            op=['Submucosa', 'Intramural', 'Subserosa', 'Combinada'],
            cond=en('tipo_muestra', _U_HIST),
        ),
        C(
            'invasion_miometrial',
            S3,
            'Foco de invasión miometrial más profundo (¿pasa la serosa?)',
            TEXTO,
            cond=en('tipo_muestra', _U_RAD),
        ),
        C('cervix', S4),
        C('parametrios', S4, 'Parametrios', LISTA, op=['No incluidos', 'Incluidos'], cond=en('tipo_muestra', _U_RAD)),
        C('reborde_vaginal', S4, 'Reborde vaginal', TEXTO, cond=en('tipo_muestra', _U_RAD)),
        C('anexos', S4),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Conización',
            'items': [
                'Cortes de la hora 1 a la 12 del reloj, cada hora en su canastilla (hora 1 en canastilla 1, etc.) o por cuadrantes.'
            ],
        },
        {
            'titulo': 'Histerectomía por benignidad',
            'items': [
                'Cérvix anterior y posterior (canastillas separadas).',
                'Endomiometrio anterior y posterior (canastillas separadas).',
                'Lesiones: un corte por cm de la dimensión mayor, hasta dos cortes por canastilla.',
                'Tubas uterinas (si se reciben) en las dos últimas canastillas.',
            ],
        },
        {
            'titulo': 'Histerectomía radical',
            'items': [
                'Bordes parametriales derecho e izquierdo.',
                'Cérvix anterior y posterior; endomiometrio anterior y posterior (fondo, cuerpo e istmo).',
                'Lesiones: un corte por cm del tumor y la sección de mayor profundidad de invasión.',
                'Tubas uterinas (fimbrias, tercio medio y proximal) en las dos últimas canastillas.',
            ],
        },
    ],
}

# ═══ 9. GANGLIO LINFÁTICO ═════════════════════════════════════════════
DEFINICIONES['Ganglio Linfático'] = {
    'manual': 'Linfadenectomía; la biopsia de ganglio remite a «biopsias pequeñas», capítulo no incluido.',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            ayuda='PENDIENTE: la biopsia de ganglio remite a un capítulo de «biopsias pequeñas» que no está en el manual.',
        ),
        C(
            'sospecha',
            S1,
            'Sospecha clínica (para el muestreo)',
            LISTA,
            op=['Enfermedad hematolinfoide', 'Tumor de origen desconocido', 'Otra / no especificada'],
            ayuda='Hematolinfoide: idealmente enviar todo el ganglio (si > 30 mm, cortes representativos). Tumor de origen desconocido: representativos de todos los nódulos.',
        ),
        C('localizacion', S1),
        C('grupo_nivel', S1, 'Grupo o nivel ganglionar (si el cirujano lo orientó)', TEXTO),
        C('num_ganglios', S2, 'Número de ganglios (conteo tras disección)'),
        C('dimensiones', S2, 'Dimensiones del mayor (cm)'),
        C('color', S2),
        C('consistencia', S2),
        C(
            'hallazgos_macro',
            S3,
            'Hallazgos (forma, hemorragia, material purulento, irregularidades de superficie)',
            AREA,
        ),
        C('conglomerados', S3, 'Conglomerados ganglionares', LISTA, op=PRES_AUS),
        C('necrosis', S3),
        C('capsula', S4),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Linfadenectomía',
            'items': [
                'Procesar todos los ganglios que se identifiquen; cortar por el eje mayor.',
                'Cuando corresponda, canastillas separadas por grupo o nivel ganglionar.',
                'Especificar el número de ganglios enviados en cada canastilla.',
            ],
        },
    ],
}

# ═══ 10. BIOPSIA GÁSTRICA (la biopsia endoscópica NO está en el manual) ═══
_G_ENDO = ['Biopsia endoscópica', 'Polipectomía gástrica', 'Mucosectomía']
_G_RESEC = ['Gastrectomía parcial', 'Gastrectomía total', 'Gastrectomía subtotal', 'Gastrectomía vertical (bariátrica)']
DEFINICIONES['Biopsia Gástrica'] = {
    'manual': 'Gastrectomía vertical y total/subtotal. La biopsia endoscópica NO está documentada.',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            op=_G_ENDO + _G_RESEC,
            ayuda='PENDIENTE: el manual no incluye protocolo para biopsias endoscópicas ni polipectomía/mucosectomía gástrica.',
        ),
        C('localizacion', S1, obl=True, cond=en('tipo_muestra', _G_ENDO)),
        C('num_fragmentos', S2, obl=True, cond=en('tipo_muestra', _G_ENDO)),
        C('dimensiones', S2, ayuda='Endoscópicas: dimensiones agregadas. Gastrectomía vertical: 2 dimensiones.'),
        C('aspecto_endoscopico', S3, cond=en('tipo_muestra', _G_ENDO)),
        C('test_helicobacter', S1, cond=en('tipo_muestra', _G_ENDO)),
        C(
            'esofago_duodeno',
            S4,
            'Segmentos incluidos',
            LISTA,
            op=['Ninguno', 'Esófago', 'Duodeno', 'Esófago y duodeno'],
            cond=en('tipo_muestra', _G_RESEC),
            ayuda='Identificar y pintar los márgenes de resección.',
        ),
        C('curvaturas', S2, 'Curvatura mayor / menor (cm)', TEXTO, cond=en('tipo_muestra', _G_RESEC)),
        C(
            'circunferencia_margenes',
            S4,
            'Circunferencia de los márgenes de resección (cm)',
            TEXTO,
            cond=en('tipo_muestra', _G_RESEC),
        ),
        C('grosor_pared', S2, 'Espesor de la pared (cm)', TEXTO, cond=en('tipo_muestra', _G_RESEC)),
        C(
            'serosa_descripcion',
            S2,
            'Superficie externa / serosa (color, brillo, retracciones, nódulos), adventicia y epiplones',
            AREA,
            cond=en('tipo_muestra', _G_RESEC),
        ),
        C(
            'mucosa_descripcion',
            S2,
            'Mucosa no afectada (color, textura, pliegues)',
            AREA,
            cond=en('tipo_muestra', _G_RESEC),
        ),
        C(
            'lesion_descripcion',
            S3,
            'Lesión: localización, bordes, consistencia, tamaño y profundidad',
            AREA,
            cond=en('tipo_muestra', _G_RESEC),
        ),
        C(
            'lesion_distancia_margenes',
            S3,
            'Distancia de la lesión a los márgenes (cm)',
            TEXTO,
            cond=en('tipo_muestra', _G_RESEC),
            ayuda='Idealmente medir en fresco: puede haber retracción tras la fijación.',
        ),
        C('ganglios', S4, 'Ganglios linfáticos (número)', NUMERO, cond=en('tipo_muestra', _G_RESEC)),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Gastrectomía vertical',
            'items': ['Corte representativo (mucosectomía enrollada); un corte adicional si hay hallazgos anormales.'],
        },
        {
            'titulo': 'Gastrectomía total o subtotal',
            'items': [
                'Lesión: 4 secciones, incluida la penetración más profunda y secciones radiales de úlceras.',
                'Márgenes proximal, distal y radial (esófago: sección frontal).',
                'Cardias, fondo y antro.',
                'Todos los ganglios linfáticos (al menos 16).',
            ],
        },
    ],
}

# ═══ 11. PULMÓN ═══════════════════════════════════════════════════════
_L_CUNA = ['Resección en cuña']
_L_RESEC = ['Segmentectomía', 'Lobectomía', 'Neumonectomía']
DEFINICIONES['Pulmón'] = {
    'manual': 'Biopsia en cuña; neumonectomías parciales y totales. Biopsias bronquiales/transbronquiales/aguja: no documentadas (salvo trasplante).',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            ayuda='PENDIENTE: el manual describe cuña y neumonectomías parciales/totales; se asume que lobectomía y segmentectomía siguen el protocolo de neumonectomía parcial (validar).',
        ),
        C('lateralidad', S1),
        C('lobulo', S1),
        C(
            'orientacion',
            S4,
            'Orientación del espécimen',
            LISTA,
            op=ORIENT,
            cond=en('tipo_muestra', _L_CUNA + _L_RESEC),
        ),
        C('dimensiones', S2, 'Dimensiones del espécimen (cm)', ayuda='3 dimensiones. Cuña: longitud ideal 3–5 cm.'),
        C('peso', S2),
        C(
            'borde_pleural',
            S2,
            'Borde pleural',
            LISTA,
            op=['Liso', 'Retraído', 'Incidido', 'Nodular', 'Otro'],
            cond=en('tipo_muestra', _L_CUNA),
        ),
        C(
            'distancia_pleura_borde',
            S2,
            'Distancia de la pleura al borde del parénquima (cm)',
            TEXTO,
            cond=en('tipo_muestra', _L_CUNA),
        ),
        C('tumor_tamanio', S3),
        C('tumor_aspecto', S3),
        C(
            'lesion_descripcion',
            S3,
            'Lesiones (sólida, quística, hemorrágica, color) y relación con pleura, vía aérea y parénquima',
            AREA,
            cond=en('tipo_muestra', _L_CUNA + _L_RESEC),
        ),
        C(
            'lesion_distancia_pleura_borde',
            S3,
            'Distancia de la lesión a la pleura y al borde del parénquima (cm)',
            TEXTO,
            cond=en('tipo_muestra', _L_CUNA),
        ),
        C('margen_bronquial', S4, cond=en('tipo_muestra', _L_RESEC)),
        C('margen_vascular', S4, cond=en('tipo_muestra', _L_RESEC)),
        C('pleura', S4),
        C('ganglios', S4, 'Ganglios linfáticos (peribronquiales e hiliares)'),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {'titulo': 'Biopsia en cuña', 'items': ['Borde parenquimatoso.', 'Cortes de la lesión: 1 por centímetro.']},
        {
            'titulo': 'Neumonectomía parcial o total',
            'items': [
                'Borde de resección del hilio pulmonar.',
                'Lesión respecto a la pleura, a la vía aérea y al parénquima adyacente.',
                'Cortes de la lesión: 1 por centímetro.',
                'Ganglios linfáticos disecados.',
            ],
        },
    ],
}

# ═══ 12. RIÑÓN ════════════════════════════════════════════════════════
_R_BX = ['Biopsia renal percutánea']
_R_NEF = [
    'Nefrectomía radical',
    'Nefrectomía parcial',
    'Nefroureterectomía',
    'Nefrectomía simple (por benignidad)',
    'Riñón resecado de paciente receptor (trasplante)',
]
DEFINICIONES['Riñón'] = {
    'manual': 'Nefrectomía por benignidad; nefrectomía radical por malignidad; biopsia renal y riñón del receptor.',
    'campos': [
        C('tipo_muestra', S1, op=_R_BX + _R_NEF),
        C('lateralidad', S1),
        C('orientacion', S4, 'Orientación del espécimen', LISTA, op=ORIENT, cond=en('tipo_muestra', _R_NEF)),
        C('num_cilindros', S2, 'Número de cilindros', NUMERO, obl=True, cond=en('tipo_muestra', _R_BX)),
        C(
            'cilindros_dimensiones',
            S2,
            'Cilindros: dimensiones (cm, 2 dimensiones)',
            TEXTO,
            cond=en('tipo_muestra', _R_BX),
        ),
        C('muestra_color', S2, 'Color', TEXTO, cond=en('tipo_muestra', _R_BX)),
        C('muestra_consistencia', S2, 'Consistencia', TEXTO, cond=en('tipo_muestra', _R_BX)),
        C(
            'dimensiones',
            S2,
            'Dimensiones del riñón (cm)',
            obl=True,
            cond=en('tipo_muestra', _R_NEF),
            ayuda='3 dimensiones; vasos renales y uréter en 2 dimensiones.',
        ),
        C('peso', S2, cond=en('tipo_muestra', _R_NEF)),
        C(
            'dimensiones_vasos_ureter',
            S2,
            'Vasos renales y uréter (cm, 2 dimensiones)',
            TEXTO,
            cond=en('tipo_muestra', _R_NEF),
        ),
        C(
            'superficie_integridad',
            S2,
            'Integridad, color, superficie (cicatrices, suturas, lesiones)',
            AREA,
            cond=en('tipo_muestra', _R_NEF),
        ),
        C(
            'corteza_medula',
            S2,
            'Corteza y médula (color, amplitud, infartos, abscesos, quistes)',
            AREA,
            cond=en('tipo_muestra', _R_NEF),
        ),
        C(
            'pelvis_ureter',
            S2,
            'Pelvis, cálices y uréter (dilatación, cálculos: número, tamaño, localización)',
            AREA,
            cond=en('tipo_muestra', _R_NEF),
        ),
        C('tumor_presente', S3, cond=en('tipo_muestra', _R_NEF)),
        C('tumor_tamanio', S3, cond=en('tumor_presente', ['Sí'])),
        C('tumor_aspecto', S3, cond=en('tumor_presente', ['Sí'])),
        C('tumor_necrosis', S3, 'Necrosis del tumor (% macroscópico)', TEXTO, cond=en('tumor_presente', ['Sí'])),
        C(
            'tumor_distancias',
            S3,
            'Distancia a cápsula, hilio, seno renal y estructuras adyacentes',
            AREA,
            cond=en('tumor_presente', ['Sí']),
        ),
        C('capsula_renal', S4, cond=en('tipo_muestra', _R_NEF)),
        C('vena_renal', S4, cond=en('tipo_muestra', _R_NEF)),
        C('suprarrenal', S4, cond=en('tipo_muestra', _R_NEF)),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Nefrectomía por benignidad / riñón del receptor',
            'items': [
                'Bordes distales de arteria, vena y uréter en una canastilla.',
                'Corteza del polo superior en una canastilla; del polo inferior en otra.',
                'Lesiones (si hay) en una canastilla; médula y pelvis renal en una canastilla.',
            ],
        },
        {
            'titulo': 'Nefrectomía radical por malignidad',
            'items': [
                'Hilio renal incluido el uréter; riñón no tumoral; transición tumor-tejido normal; glándula suprarrenal si está presente.',
                'Tumor respecto a cápsula, fascia de Gerota, seno renal y órganos adyacentes; otras lesiones; todos los nódulos linfáticos.',
                'Tumor de Wilms: enviar todas las canastillas del mapeo.',
            ],
        },
        {
            'titulo': 'Biopsia renal',
            'items': [
                'Procesar en su totalidad. Estudios adicionales (inmunofluorescencia, microscopía electrónica): ver el manual.'
            ],
        },
    ],
}

# ═══ 13. AMÍGDALAS Y ADENOIDES ════════════════════════════════════════
DEFINICIONES['Amígdalas y Adenoides'] = {
    'manual': '1.4 Amigdalectomía, adenoidectomía y paratiroidectomía.',
    'campos': [
        C('tipo_muestra', S1),
        C('lateralidad', S1),
        C('dimensiones_der', S2),
        C('dimensiones_izq', S2),
        C('dimensiones_adenoides', S2),
        C('peso', S2, 'Peso (g)', NUMERO, ayuda='El manual indica medir en 3 dimensiones y pesar.'),
        C('descripcion_externa', S2, 'Descripción externa (forma, color, simetría, consistencia)', AREA),
        C('superficie', S2),
        C('consistencia', S2),
        C('superficie_corte', S2, 'Descripción interna (superficie de corte, criptas, necrosis, masas)', AREA),
        C(
            'lesion_muestreo',
            S3,
            'Lesión (determina el muestreo)',
            LISTA,
            op=['Benigna', 'Maligna o sospechosa'],
            ayuda='Benigna: un corte representativo por órgano (1 canastilla). Maligna o sospechosa: cortes por centímetro.',
        ),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Amígdalas / adenoides',
            'items': [
                'Cortes transversales cada 3–4 mm.',
                'Lesión benigna: un corte representativo por órgano (1 canastilla).',
                'Lesión maligna o sospechosa: cortes por centímetro (canastillas necesarias).',
            ],
        },
        {'titulo': 'Paratiroides', 'items': ['Si es pequeña, enviarla íntegra en una canastilla.']},
    ],
}

# ═══ 14. TEJIDO BLANDO (solo «Resección de sarcomas» está documentada) ═══
_TB_SARC = ['Tumor de partes blandas']
DEFINICIONES['Tejido Blando'] = {
    'manual': 'Resección de sarcomas. Lipomas, quistes y fibromas NO están documentados como protocolo propio.',
    'campos': [
        C(
            'tipo_muestra',
            S1,
            ayuda='PENDIENTE: el manual solo documenta la resección de sarcomas; los campos específicos se muestran para «Tumor de partes blandas».',
        ),
        C('localizacion', S1),
        C(
            'estructura_lesion',
            S1,
            'Estructura donde se localiza la lesión',
            LISTA,
            op=['Piel', 'Músculo esquelético', 'Nervio grande o vasos', 'Tejido celular subcutáneo', 'Fascia', 'Otro'],
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C(
            'orientacion',
            S4,
            'Orientación del espécimen',
            LISTA,
            op=ORIENT,
            cond=en('tipo_muestra', _TB_SARC),
            ayuda='Si viene orientado, determinar los márgenes y pintarlos según el código de colores.',
        ),
        C('dimensiones', S2, 'Dimensiones (cm)', ayuda='Sarcomas: 3 dimensiones.'),
        C('peso', S2),
        C(
            'superficie_externa',
            S2,
            'Superficie externa (tractos de punción, cicatrices, suturas)',
            AREA,
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C('capsula', S3),
        C('color', S3),
        C('consistencia', S3),
        C('tumor_dimensiones', S3, 'Tamaño del tumor (cm, 3 dimensiones)', TEXTO, cond=en('tipo_muestra', _TB_SARC)),
        C(
            'tumor_profundidad',
            S3,
            'Localización del tumor',
            LISTA,
            op=['Cutáneo', 'Subcutáneo', 'Intramuscular', 'En tejido adiposo', 'Subfascial', 'Otro'],
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C(
            'crecimiento',
            S3,
            'Tipo de crecimiento',
            LISTA,
            op=['Infiltrante', 'Lobulado', 'Bien circunscrito', 'Encapsulado', 'Otro'],
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C('necrosis', S3),
        C('necrosis_porcentaje', S3, 'Necrosis (%)', TEXTO, cond=en('necrosis', ['Presente'])),
        C('margenes', S4),
        C(
            'distancia_margen_cercano',
            S4,
            'Distancia del tumor al margen más cercano (cm) y margen',
            TEXTO,
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C(
            'tejido_margen',
            S4,
            'Tipo de tejido entre el tumor y el margen más cercano',
            LISTA,
            op=['Grasa', 'Músculo', 'Fascia', 'Otro'],
            cond=en('tipo_muestra', _TB_SARC),
        ),
        C('observaciones', S5),
    ],
    'guia_muestreo': [
        {
            'titulo': 'Resección de sarcomas',
            'items': [
                'Un corte por centímetro de lesión, mostrando relación con todos los márgenes, estructuras adyacentes, piel suprayacente y zonas de infiltración.',
                'Enviar todos los nodos linfáticos presentes.',
            ],
        },
    ],
}

"""
Generación de la descripción macroscópica y exportación del informe a PDF.
"""

import io
import unicodedata
from functools import partial
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from pacientes.models import Sexo

from .reglas import campos_aplicables, es_vacio


def texto_seguro(texto) -> str:
    """
    Prepara texto escrito por el usuario para un Paragraph de ReportLab.
    Paragraph interpreta etiquetas como <b> o <font>; al escapar <, > y &
    el texto se muestra literal (auditoría I-3). Los saltos de línea se
    convierten en <br/> para que se respeten en el PDF.
    """
    return escape(str(texto)).replace('\r\n', '\n').replace('\n', '<br/>')


# ── Generador de la descripción macroscópica ────────────────────────────
# Frase en lenguaje natural para los campos más comunes.
MAPEO = {
    'tipo_muestra': 'El tipo de muestra corresponde a {v}.',
    'localizacion': 'La localización anatómica es {v}.',
    'tamanio': 'La pieza mide {v}.',
    'dimensiones': 'Las dimensiones son {v}.',
    'peso': 'El peso registrado es de {v} gramos.',
    'color': 'El color macroscópico observado es {v}.',
    'consistencia': 'La consistencia es {v}.',
    'forma': 'La forma observada es {v}.',
    'superficie': 'La superficie se describe como {v}.',
    'bordes': 'Los bordes se observan {v}.',
    'margenes': 'Los márgenes quirúrgicos se reportan como {v}.',
    'ganglios': 'Se identifican {v} ganglio(s) linfático(s).',
    'hallazgos_adicionales': 'Hallazgos adicionales: {v}.',
    'observaciones': 'Observaciones: {v}.',
    'tumor_tamanio': 'El tamaño tumoral es de {v}.',
    'necrosis': 'Se observa necrosis: {v}.',
    'hemorragia': 'Se observa hemorragia: {v}.',
    'calcificaciones': 'Se identifican calcificaciones: {v}.',
}

# La frase del MAPEO solo se usa si la etiqueta del campo nombra ese concepto (D-18). Algunas
# plantillas reutilizan un nombre para otro dato: en Vesícula Biliar, `consistencia` es el
# grosor de la pared y `calcificaciones` son los cálculos. Redactarlos con la frase del
# nombre diría algo que el patólogo no escribió; entonces se usa "Etiqueta: valor".
RAICES_MAPEO = {
    'tipo_muestra': ('tipo de muestra', 'tipo de procedimiento', 'tipo de biopsia'),
    'localizacion': ('localiz',),
    'tamanio': ('tamano', 'medida'),
    'dimensiones': ('dimension', 'longitud'),
    'peso': ('peso',),
    'color': ('color',),
    'consistencia': ('consistencia',),
    'forma': ('forma', 'morfolog'),
    'superficie': ('superficie',),
    'bordes': ('borde',),
    'margenes': ('quirurgic',),
    'ganglios': ('ganglio',),
    'hallazgos_adicionales': ('hallazgo',),
    'observaciones': ('observacion',),
    'tumor_tamanio': ('tamano',),
    'necrosis': ('necrosis',),
    'hemorragia': ('hemorragia',),
    'calcificaciones': ('calcificacion',),
}


def _sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')


def _usa_frase_del_mapeo(campo, plantilla):
    """Sin plantilla (datos antiguos) o sin etiqueta se usa la frase; si no, la etiqueta debe nombrar el concepto."""
    if plantilla is None or not plantilla.campo_label:
        return True
    etiqueta = _sin_tildes(plantilla.campo_label)
    return any(raiz in etiqueta for raiz in RAICES_MAPEO[campo])


def _texto_valor(valor):
    """Sí/No para los booleanos; el resto tal cual, sin el punto final (lo pone la frase)."""
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    return str(valor).strip().rstrip('.')


def generar_descripcion_macroscopica(patologia, datos: dict) -> str:
    """
    Redacta el párrafo de descripción macroscópica con lo que llenó el patólogo. Solo
    usa lo registrado (D-18): un campo vacío no se menciona (no es un hallazgo negativo),
    0 y "No" sí se redactan, y un campo que no aplica al procedimiento elegido no aparece
    aunque tenga un valor guardado. El muestreo (canastillas) no va aquí: tiene su propia
    sección en el informe.
    """
    plantillas = {p.campo_nombre: p for p in patologia.plantillas.all()}
    aplican = campos_aplicables(plantillas.values(), datos)

    def se_redacta(campo):
        # Un dato sin plantilla (de un informe antiguo) se conserva.
        return not es_vacio(datos.get(campo)) and (campo not in plantillas or campo in aplican)

    partes = [f'Se recibe espécimen para estudio de {patologia.nombre}.']
    redactados = set()
    for campo, frase in MAPEO.items():
        if se_redacta(campo) and _usa_frase_del_mapeo(campo, plantillas.get(campo)):
            partes.append(frase.format(v=_texto_valor(datos[campo])))
            redactados.add(campo)

    # Los demás, como "Etiqueta: valor": primero en el orden de la plantilla y después los
    # datos antiguos que ya no tienen plantilla.
    resto = [*plantillas, *(campo for campo in datos if campo not in plantillas)]
    for campo in resto:
        if campo in redactados or not se_redacta(campo):
            continue
        plantilla = plantillas.get(campo)
        etiqueta = (plantilla and plantilla.campo_label) or campo.replace('_', ' ').capitalize()
        partes.append(f'{etiqueta}: {_texto_valor(datos[campo])}.')

    partes.append('Se procesa el material y se remite para estudio histopatológico.')

    return ' '.join(partes)


# ── Exportación a PDF ───────────────────────────────────────────────────
# Estructura del informe real (docs/propuesta-informe-v2.md, sección 5).

SIN_DATO = '—'
AVISO_BORRADOR = 'BORRADOR — SIN VALIDEZ'
# Todo el informe va en negro; el rojo queda solo para las alertas
# (aviso de adendas y marca de agua del borrador).
NEGRO = black
ROJO = HexColor('#c53030')


class CanvasNumerado(canvas.Canvas):
    """
    Lienzo que dibuja el pie de cada página al final, cuando ya se sabe el total:
    "N.º de petición … · Página X de Y · Generado el …". `pie` es el texto que va
    antes y después de "Página X de Y". Si se da `marca_agua` (un borrador, D-12),
    la dibuja grande, en diagonal y casi transparente sobre cada página.
    """

    def __init__(self, *args, pie=('', ''), marca_agua=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._pie = pie
        self._marca_agua = marca_agua
        self._paginas = []

    def showPage(self):
        # Guarda la página en vez de cerrarla; se cierra en save() con el pie.
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for numero, estado in enumerate(self._paginas, start=1):
            self.__dict__.update(estado)
            if self._marca_agua:
                self._dibujar_marca_agua()
            antes, despues = self._pie
            self.setFont('Helvetica', 8)
            self.setFillColor(NEGRO)
            self.drawCentredString(letter[0] / 2, 1 * cm, f'{antes}Página {numero} de {total}{despues}')
            super().showPage()
        super().save()

    def _dibujar_marca_agua(self):
        self.saveState()
        self.setFont('Helvetica-Bold', 100)
        self.setFillColor(ROJO)
        self.setFillAlpha(0.08)
        self.translate(letter[0] / 2, letter[1] / 2)
        self.rotate(45)
        self.drawCentredString(0, -35, self._marca_agua)
        self.restoreState()


def _estilos():
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            'Laboratorio',
            parent=estilos['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=NEGRO,
            alignment=TA_CENTER,
            leading=16,
        )
    )
    estilos.add(
        ParagraphStyle(
            'Ciudad',
            parent=estilos['Normal'],
            fontSize=9,
            textColor=NEGRO,
            alignment=TA_CENTER,
        )
    )
    estilos.add(ParagraphStyle('Celda', parent=estilos['Normal'], fontSize=9, leading=12, textColor=NEGRO))
    estilos.add(
        ParagraphStyle(
            'TituloInforme',
            parent=estilos['Title'],
            fontName='Helvetica-Bold',
            fontSize=15,
            textColor=NEGRO,
            spaceBefore=14,
            spaceAfter=4,
        )
    )
    estilos.add(ParagraphStyle('TipoEstudio', parent=estilos['Normal'], fontSize=11, alignment=TA_CENTER))
    estilos.add(
        ParagraphStyle(
            'Muestra',
            parent=estilos['Normal'],
            fontSize=8.5,
            textColor=NEGRO,
            alignment=TA_CENTER,
        )
    )
    estilos.add(
        ParagraphStyle(
            'Subtitulo',
            parent=estilos['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11.5,
            textColor=NEGRO,
            spaceBefore=12,
            spaceAfter=4,
        )
    )
    estilos.add(
        ParagraphStyle(
            'CuerpoTexto',
            parent=estilos['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            leading=14,
        )
    )
    estilos.add(ParagraphStyle('Firma', parent=estilos['Normal'], fontSize=10, leading=13, alignment=TA_CENTER))
    estilos.add(
        ParagraphStyle(
            'AvisoAdendas',
            parent=estilos['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=ROJO,
            alignment=TA_CENTER,
            borderColor=ROJO,
            borderWidth=0.75,
            borderPadding=5,
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    estilos.add(
        ParagraphStyle(
            'TituloAdenda',
            parent=estilos['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            textColor=NEGRO,
            spaceBefore=18,
            spaceAfter=4,
        )
    )
    return estilos


def _encabezado(laboratorio, estilos):
    """
    Nombre, dirección y teléfono del laboratorio, de datos_impresos(): los de
    backend/.env en un borrador y los congelados al finalizar (D-15). Se escapan
    como el texto del usuario (I-3): un & o un < del .env no debe romper el PDF.
    """
    bloque = [
        Paragraph(texto_seguro(laboratorio['nombre']), estilos['Laboratorio']),
        Paragraph(texto_seguro(laboratorio['direccion']), estilos['Ciudad']),
    ]
    if laboratorio['telefono']:
        bloque.append(Paragraph(f'Teléfono: {texto_seguro(laboratorio["telefono"])}', estilos['Ciudad']))
    return bloque + [
        Spacer(1, 6),
        HRFlowable(width='100%', thickness=0.75, color=NEGRO),
        Spacer(1, 10),
    ]


def _fecha_de_informe(informe):
    """En un borrador va el aviso de que no tiene validez (sección 5.2)."""
    if not informe.esta_finalizado:
        return AVISO_BORRADOR
    if informe.fecha_informe is None:
        return None
    return timezone.localtime(informe.fecha_informe).strftime('%d/%m/%Y %H:%M')


def _tabla_datos(informe, datos, estilos, ancho):
    """Datos del paciente y de la solicitud en dos columnas, como el formato real."""
    paciente = datos['paciente']

    def celda(etiqueta, valor):
        # El valor lo escribe el usuario (o sale de un catálogo): siempre escapado (I-3).
        return Paragraph(f'<b>{etiqueta}:</b> {texto_seguro(valor) if valor else SIN_DATO}', estilos['Celda'])

    filas = [
        [
            celda('Paciente', paciente and paciente['nombre_completo']),
            celda('Identificación', paciente and f'{paciente["tipo_documento"]} {paciente["numero_documento"]}'),
        ],
        [celda('Edad', informe.edad_paciente(paciente)), celda('Sexo', paciente and Sexo(paciente['sexo']).label)],
        [celda('Médico tratante', informe.medico_tratante), celda('EPS', datos['eps_nombre'])],
        [celda('Servicio', datos['servicio_nombre']), celda('N.º de petición', informe.numero_peticion)],
        [
            celda('Fecha de ingreso', informe.fecha_ingreso and informe.fecha_ingreso.strftime('%d/%m/%Y')),
            celda('Fecha de informe', _fecha_de_informe(informe)),
        ],
    ]
    # Estas filas ocupan todo el ancho.
    if informe.numero_orden_externa:
        filas.append([celda('Orden externa', informe.numero_orden_externa), ''])
    filas.append([celda('Estudios solicitados', informe.estudios_solicitados), ''])

    tabla = Table(filas, colWidths=[ancho / 2, ancho / 2])
    tabla.setStyle(
        TableStyle(
            [
                ('BOX', (0, 0), (-1, -1), 0.75, NEGRO),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, NEGRO),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
            + [('SPAN', (0, fila), (1, fila)) for fila in range(5, len(filas))]
        )
    )
    return [tabla]


def _titulo(informe, estilos):
    return [
        Paragraph('INFORME DE ANATOMÍA PATOLÓGICA', estilos['TituloInforme']),
        Paragraph(f'<b>Tipo de estudio:</b> {informe.get_tipo_estudio_display()}', estilos['TipoEstudio']),
        Paragraph(
            f'Patología: {texto_seguro(informe.patologia.nombre)} · '
            f'Tipo de muestra: {texto_seguro(informe.tipo_muestra or SIN_DATO)}',
            estilos['Muestra'],
        ),
        Spacer(1, 4),
    ]


def _seccion(titulo, parrafos, estilos):
    """Título con su línea y los párrafos, ya escapados con texto_seguro (I-3)."""
    return [
        # El título no queda solo al final de una página: si quedan menos de 4 cm,
        # la sección empieza en la siguiente.
        CondPageBreak(4 * cm),
        Paragraph(titulo, estilos['Subtitulo']),
        HRFlowable(width='100%', thickness=0.5, color=NEGRO),
        Spacer(1, 4),
        *[Paragraph(parrafo, estilos['CuerpoTexto']) for parrafo in parrafos],
    ]


def _muestreo(canastillas, estilos, ancho):
    """
    Sección MUESTREO PARA HISTOLOGÍA (D-18): una fila por canastilla con lo que registró
    el usuario, sin agregar nada. Va aparte de la macroscópica: es lo que se envió a
    procesar, no un hallazgo ni un diagnóstico.
    """

    def celda(valor, negrita=False):
        texto = texto_seguro(valor) if not es_vacio(valor) else SIN_DATO
        return Paragraph(f'<b>{texto}</b>' if negrita else texto, estilos['Celda'])

    filas = [
        [
            Paragraph(f'<b>{titulo}</b>', estilos['Celda'])
            for titulo in (
                'Canastilla',
                'Región o estructura',
                'Lesión o margen',
                'Tejido muestreado',
                'Cant.',
                'Notas',
            )
        ]
    ]
    for canastilla in canastillas:
        notas = [
            f'Entintado: {canastilla.entintado}' if canastilla.entintado else '',
            f'Motivo: {canastilla.motivo}' if canastilla.motivo else '',
            canastilla.observaciones,
        ]
        filas.append(
            [
                celda(canastilla.codigo, negrita=True),
                celda(canastilla.region),
                celda(canastilla.lesion_margen),
                celda(canastilla.descripcion),
                celda(canastilla.cantidad),
                celda(' · '.join(nota for nota in notas if nota)),
            ]
        )
    columnas = [2.1 * cm, 3 * cm, 2.8 * cm, 4.4 * cm, 1.3 * cm]
    tabla = Table(filas, colWidths=[*columnas, ancho - sum(columnas)], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ('BOX', (0, 0), (-1, -1), 0.75, NEGRO),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, NEGRO),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [*_seccion('MUESTREO PARA HISTOLOGÍA', [], estilos), tabla]


def _lineas_firma(firma, estilos):
    """Línea de firma con nombre, especialidad y registro médico (D-8, D-9)."""
    bloque = [
        Spacer(1, 32),
        HRFlowable(width=7 * cm, thickness=0.75, color=NEGRO, spaceAfter=4),
        Paragraph(texto_seguro(firma['nombre']), estilos['Firma']),
    ]
    if firma['especialidad']:
        bloque.append(Paragraph(texto_seguro(firma['especialidad']), estilos['Firma']))
    if firma['registro_medico']:
        bloque.append(Paragraph(f'Registro médico N.º {texto_seguro(firma["registro_medico"])}', estilos['Firma']))
    return bloque


def _firma(firma, estilos):
    """Firma del autor del informe (D-8). Un borrador no lleva firma."""
    # La firma no se parte entre dos páginas.
    return [KeepTogether(_lineas_firma(firma, estilos))]


def _aviso_adendas(total, estilos):
    """Al principio del informe: que nadie lea el diagnóstico original sin saber que se corrigió (3.8)."""
    adendas = 'adenda' if total == 1 else 'adendas'
    return [Paragraph(f'Este informe tiene {total} {adendas}; ver al final.', estilos['AvisoAdendas'])]


def _adendas(adendas, estilos):
    """Sección ADENDAS (decisión D-9): cada una con número, fecha, motivo, texto y su firma congelada."""
    # Sin el CondPageBreak de _seccion: el título va en el bloque de la primera adenda.
    titulo = _seccion('ADENDAS', [], estilos)[1:]
    elementos = []
    for posicion, adenda in enumerate(adendas):
        fecha = timezone.localtime(adenda.fecha).strftime('%d/%m/%Y %H:%M')
        # La adenda va entera en una página si cabe, para que su firma no quede sola,
        # y el título de la sección no queda separado de la primera.
        elementos.append(
            KeepTogether(
                [
                    *(titulo if posicion == 0 else []),
                    Paragraph(f'Adenda N.º {adenda.numero} — {fecha}', estilos['TituloAdenda']),
                    Paragraph(f'<b>Motivo:</b> {texto_seguro(adenda.motivo)}', estilos['CuerpoTexto']),
                    Spacer(1, 4),
                    Paragraph(texto_seguro(adenda.texto), estilos['CuerpoTexto']),
                    *_lineas_firma(adenda.firma, estilos),
                ]
            )
        )
    return elementos


def generar_pdf_informe(informe) -> io.BytesIO:
    """Genera el PDF del informe y lo devuelve en un buffer de bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f'Informe {informe.numero_peticion}',
    )
    estilos = _estilos()
    # Encabezado, paciente, EPS, servicio y firma: congelados si está finalizado (D-10, D-15).
    datos = informe.datos_impresos()

    elementos = [
        *_encabezado(datos['laboratorio'], estilos),
        *_tabla_datos(informe, datos, estilos, doc.width),
        *_titulo(informe, estilos),
    ]

    # Solo un informe finalizado tiene adendas (D-9).
    adendas = list(informe.adendas.all())
    if adendas:
        elementos += _aviso_adendas(len(adendas), estilos)

    if informe.texto_generado:
        elementos += _seccion('DESCRIPCIÓN MACROSCÓPICA', [texto_seguro(informe.texto_generado)], estilos)

    canastillas = list(informe.canastillas.all())
    if canastillas:
        elementos += _muestreo(canastillas, estilos, doc.width)

    if informe.descripcion_microscopica:
        elementos += _seccion('DESCRIPCIÓN MICROSCÓPICA', [texto_seguro(informe.descripcion_microscopica)], estilos)

    diagnosticos = list(informe.diagnosticos.all())
    if diagnosticos:
        elementos += _seccion(
            'DIAGNÓSTICOS',
            [
                f'{d.orden}. {texto_seguro(d.descripcion)}'
                + (f' (CIE-10: {texto_seguro(d.codigo_cie10)})' if d.codigo_cie10 else '')
                for d in diagnosticos
            ],
            estilos,
        )

    if informe.comentarios:
        elementos += _seccion('COMENTARIOS', [texto_seguro(informe.comentarios)], estilos)

    if informe.esta_finalizado:
        elementos += _firma(datos['firma'], estilos)

    if adendas:
        elementos += _adendas(adendas, estilos)

    # Pie de cada página, para identificar una hoja suelta. La hora es la de
    # settings.TIME_ZONE (America/Bogota), no la del servidor (auditoría M-10).
    generado = timezone.localtime().strftime('%d/%m/%Y %H:%M')
    antes = f'N.º de petición {informe.numero_peticion} · '
    if not informe.esta_finalizado:
        antes = f'{AVISO_BORRADOR} · {antes}'
    # Un borrador es solo una vista previa (D-12): marca de agua en cada página.
    marca_agua = None if informe.esta_finalizado else 'BORRADOR'
    doc.build(
        elementos,
        canvasmaker=partial(
            CanvasNumerado,
            pie=(antes, f' · Generado el {generado}'),
            marca_agua=marca_agua,
        ),
    )
    buffer.seek(0)
    return buffer

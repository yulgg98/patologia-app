from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F
from django.utils import timezone

from pacientes.models import edad_en_texto

# Límites de Informe.datos_ingresados (hallazgo O-23 de docs/auditoria-owasp.md). Las
# plantillas tienen pocos campos y valores cortos; estos topes dejan mucho margen.
MAX_CAMPOS_DATOS_INGRESADOS = 100
MAX_LARGO_VALOR_DATOS_INGRESADOS = 5000


def validar_datos_ingresados(valor):
    """
    Los datos del formulario dinámico deben ser un objeto {campo: valor}, con cada valor
    texto, número, booleano o nulo. Antes se aceptaba cualquier JSON (una lista, un número…)
    y el informe fallaba con un error 500 después de guardarse (O-23). Lo aplican la API
    (DRF copia los validadores del modelo) y /admin/.
    """
    if not isinstance(valor, dict):
        raise ValidationError('Debe ser un objeto con los campos del formulario.')
    if len(valor) > MAX_CAMPOS_DATOS_INGRESADOS:
        raise ValidationError(f'Admite como máximo {MAX_CAMPOS_DATOS_INGRESADOS} campos.')
    for campo, dato in valor.items():
        if dato is not None and not isinstance(dato, (str, int, float, bool)):
            raise ValidationError(f'El campo «{campo}» debe ser un texto, un número o sí/no.')
        if isinstance(dato, str) and len(dato) > MAX_LARGO_VALOR_DATOS_INGRESADOS:
            raise ValidationError(
                f'El campo «{campo}» admite como máximo {MAX_LARGO_VALOR_DATOS_INGRESADOS} caracteres.'
            )


class Categoria(models.Model):
    """Categoría para agrupar tipos de patología (p. ej. Dermatopatología, Hematopatología)."""

    nombre = models.CharField(max_length=150, unique=True, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    color = models.CharField(
        max_length=7,
        blank=True,
        default='#2563eb',
        verbose_name='Color',
        help_text='Color hexadecimal para distinguirla en la interfaz.',
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Patologia(models.Model):
    """Tipo de patología con su protocolo médico. Sus campos de formulario están en Plantilla."""

    nombre = models.CharField(max_length=200, unique=True, verbose_name='Nombre')
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patologias',
        verbose_name='Categoría',
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    protocolo_medico = models.TextField(
        blank=True,
        verbose_name='Protocolo médico',
        help_text='Protocolo médico asociado a esta patología.',
    )
    # Indicaciones del manual para el muestreo histológico (D-18): [{titulo, items: [...]}].
    # Son solo una referencia para el patólogo: nunca crean canastillas.
    guia_muestreo = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Guía de muestreo para histología',
        help_text='Lista de {"titulo": ..., "items": [...]} con las indicaciones del manual (solo referencia).',
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Patología'
        verbose_name_plural = 'Patologías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Plantilla(models.Model):
    """Campo del formulario dinámico de una patología (texto, número, lista, etc.)."""

    class TipoCampo(models.TextChoices):
        TEXTO = 'texto', 'Texto'
        NUMERO = 'numero', 'Número'
        LISTA = 'lista', 'Lista desplegable'
        TEXTAREA = 'textarea', 'Área de texto'
        BOOLEAN = 'boolean', 'Sí / No'

    patologia = models.ForeignKey(
        Patologia,
        on_delete=models.CASCADE,
        related_name='plantillas',
        verbose_name='Patología',
    )
    campo_nombre = models.CharField(max_length=150, verbose_name='Nombre del campo')
    campo_label = models.CharField(max_length=200, blank=True, verbose_name='Etiqueta visible')
    tipo_campo = models.CharField(
        max_length=20,
        choices=TipoCampo.choices,
        default=TipoCampo.TEXTO,
        verbose_name='Tipo de campo',
    )
    obligatorio = models.BooleanField(default=False, verbose_name='Obligatorio')
    opciones = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Opciones',
        help_text='Lista de opciones para campos de tipo lista.',
    )
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')
    valor_defecto = models.CharField(max_length=255, blank=True, verbose_name='Valor por defecto')
    # Organización y aplicabilidad del campo según el manual de procesamiento macroscópico (D-18).
    seccion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Sección',
        help_text='Agrupa el campo en el formulario y en la descripción (p. ej. «Lesiones»).',
    )
    # Vacía: el campo siempre aplica. {"campo": "<campo_nombre>", "valores": [...]}: solo se
    # muestra y se valida cuando ese otro campo tiene alguno de esos valores (informes/reglas.py).
    condicion = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Condición de aplicabilidad',
        help_text='{"campo": "<campo_nombre>", "valores": [...]}; vacía si el campo siempre aplica.',
    )
    ayuda = models.TextField(blank=True, verbose_name='Texto de ayuda')

    class Meta:
        verbose_name = 'Plantilla'
        verbose_name_plural = 'Plantillas'
        ordering = ['patologia', 'orden']
        unique_together = ['patologia', 'campo_nombre']

    def __str__(self):
        return f'{self.patologia.nombre} → {self.campo_label or self.campo_nombre}'


class Servicio(models.Model):
    """Servicio que remite la muestra. Catálogo editable; se desactiva en lugar de borrarse (D-4)."""

    nombre = models.CharField(max_length=150, unique=True, verbose_name='Nombre')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ConsecutivoPeticion(models.Model):
    """Último número de petición usado en cada año (decisión D-7)."""

    anio = models.PositiveIntegerField(primary_key=True, verbose_name='Año')
    ultimo = models.PositiveIntegerField(default=0, verbose_name='Último consecutivo')

    class Meta:
        verbose_name = 'Consecutivo de petición'
        verbose_name_plural = 'Consecutivos de petición'

    def __str__(self):
        return f'{self.anio}: {self.ultimo}'


def siguiente_numero_peticion():
    """
    Reserva el siguiente número de petición del año: P-AÑO-NNNNN (decisión D-7).
    Debe llamarse dentro de la transacción que guarda el informe. El UPDATE
    bloquea el contador (la fila en PostgreSQL, la base entera en SQLite) hasta
    el COMMIT, así que dos informes creados a la vez nunca reciben el mismo
    número. Se empieza con UPDATE y no con SELECT porque en SQLite una
    transacción que lee y luego escribe falla en lugar de esperar su turno.
    """
    anio = timezone.localdate().year
    if not ConsecutivoPeticion.objects.filter(anio=anio).update(ultimo=F('ultimo') + 1):
        try:
            with transaction.atomic():  # primer informe del año
                ConsecutivoPeticion.objects.create(anio=anio, ultimo=1)
        except IntegrityError:  # otro usuario creó el contador del año al mismo tiempo
            ConsecutivoPeticion.objects.filter(anio=anio).update(ultimo=F('ultimo') + 1)
    ultimo = ConsecutivoPeticion.objects.get(anio=anio).ultimo
    return f'P-{anio}-{ultimo:05d}'


def firma_de(usuario):
    """Firma de un usuario con sus datos de hoy. Informes (D-10) y adendas (D-9) la guardan congelada."""
    return {
        'nombre': usuario.nombre_visible,
        'especialidad': usuario.especialidad,
        'registro_medico': usuario.registro_medico,
    }


class Informe(models.Model):
    """Informe de anatomía patológica."""

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        FINALIZADO = 'finalizado', 'Finalizado'

    # Lista fija que también se ofrece en GET /api/opciones/ (docs/propuesta-informe-v2.md, 3.3).
    class TipoEstudio(models.TextChoices):
        HISTOLOGIA = 'histologia', 'Histología'
        CITOLOGIA_NO_GINECOLOGICA = 'citologia_no_ginecologica', 'Citología no ginecológica'
        CITOLOGIA_CERVICOVAGINAL = 'citologia_cervicovaginal', 'Citología cérvico-vaginal'
        INMUNOHISTOQUIMICA = 'inmunohistoquimica', 'Inmunohistoquímica'
        INTRAOPERATORIO = 'intraoperatorio', 'Estudio intraoperatorio por congelación'
        REVISION_LAMINAS = 'revision_laminas', 'Revisión de láminas (segunda opinión)'

    # Lo asigna save() al crear el informe; no se puede cambiar (decisión D-7).
    numero_peticion = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Número de petición',
    )
    numero_orden_externa = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Número de orden externa',
        help_text='Número de orden de la institución remitente (opcional).',
    )
    # Datos de la solicitud (informe v2, etapa 4). paciente admite null solo por los
    # informes de antes de la etapa 4; la API lo exige al crear.
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='informes',
        verbose_name='Paciente',
    )
    medico_tratante = models.CharField(max_length=200, blank=True, verbose_name='Médico tratante')
    fecha_ingreso = models.DateField(null=True, blank=True, verbose_name='Fecha de ingreso')
    # La EPS del momento del estudio, no la actual del paciente (que puede cambiar).
    eps = models.ForeignKey(
        'pacientes.EPS',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='informes',
        verbose_name='EPS',
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='informes',
        verbose_name='Servicio',
    )
    estudios_solicitados = models.TextField(blank=True, verbose_name='Estudios solicitados')
    tipo_estudio = models.CharField(
        max_length=30,
        choices=TipoEstudio.choices,
        default=TipoEstudio.HISTOLOGIA,
        verbose_name='Tipo de estudio',
    )
    patologia = models.ForeignKey(
        Patologia,
        on_delete=models.PROTECT,
        related_name='informes',
        verbose_name='Patología',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='informes',
        verbose_name='Autor',
    )
    fecha = models.DateField(auto_now_add=True, verbose_name='Fecha')
    tipo_muestra = models.CharField(max_length=200, blank=True, verbose_name='Tipo de muestra')
    datos_ingresados = models.JSONField(
        default=dict,
        # blank=True: un informe sin datos ({}) también se guarda en /admin/.
        blank=True,
        validators=[validar_datos_ingresados],
        verbose_name='Datos ingresados',
        help_text='JSON con los valores del formulario dinámico.',
    )
    texto_generado = models.TextField(
        blank=True,
        verbose_name='Texto generado',
        help_text='Descripción macroscópica generada automáticamente.',
    )
    # Tarea 1 (OE2): el patólogo revisa el texto sugerido sin perderlo. Vacío: el informe
    # usa texto_generado, como antes. Solo cambia mientras el informe es borrador (D-3).
    descripcion_macroscopica_final = models.TextField(
        blank=True,
        default='',
        verbose_name='Descripción macroscópica revisada',
        help_text='Texto revisado por el patólogo; si está vacío, se usa el texto generado.',
    )
    # El texto sugerido del que partió la edición: si texto_generado ya no coincide, la
    # pantalla avisa que el sugerido cambió (decisión del usuario del 2026-11-12, opción A).
    descripcion_macroscopica_base = models.TextField(
        blank=True,
        default='',
        verbose_name='Texto sugerido de partida',
        help_text='Texto sugerido que había cuando el patólogo editó la descripción.',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        verbose_name='Estado',
    )
    descripcion_microscopica = models.TextField(blank=True, verbose_name='Descripción microscópica')
    # Antes se llamaba `notas` (P-5); la migración 0009 conserva lo que ya estaba escrito.
    comentarios = models.TextField(blank=True, verbose_name='Comentarios')
    # Los dos los llena solo `finalizar` (informe v2, etapa 6); no se escriben por la API ni en /admin/.
    fecha_informe = models.DateTimeField(null=True, blank=True, editable=False, verbose_name='Fecha de informe')
    # Paciente, EPS, servicio, firma (D-10) y encabezado del laboratorio (D-15) tal como estaban al finalizar.
    datos_finalizacion = models.JSONField(
        null=True,
        blank=True,
        editable=False,
        verbose_name='Datos congelados al finalizar',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Informe'
        verbose_name_plural = 'Informes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.numero_peticion} — {self.patologia.nombre}'

    def save(self, *args, **kwargs):
        if self.pk is None and not self.numero_peticion:
            # El número y el informe se guardan en la misma transacción: el
            # contador queda bloqueado hasta que el informe existe.
            with transaction.atomic():
                self.numero_peticion = siguiente_numero_peticion()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    @property
    def esta_finalizado(self):
        return self.estado == self.Estado.FINALIZADO

    def descripcion_macroscopica_vigente(self):
        """La que imprime el informe: la revisada por el patólogo o, si no hay, la generada (tarea 1)."""
        if self.descripcion_macroscopica_final.strip():
            return self.descripcion_macroscopica_final
        return self.texto_generado

    def requisitos_faltantes(self):
        """Lo que le falta al informe para poder finalizarse (decisión D-8). Vacío si nada."""
        faltantes = []
        if self.paciente_id is None:
            faltantes.append('El informe no tiene paciente.')
        if not self.diagnosticos.exists():
            faltantes.append('El informe debe tener al menos un diagnóstico.')
        if self.tipo_estudio == self.TipoEstudio.HISTOLOGIA and not self.descripcion_microscopica.strip():
            faltantes.append('En un estudio de histología, la descripción microscópica es obligatoria.')
        # La firma es siempre la del autor, aunque finalice un admin (D-8).
        if not self.autor.registro_medico.strip():
            faltantes.append('El patólogo autor no tiene registro médico; un administrador debe registrarlo.')
        return faltantes

    def firma_actual(self):
        """Firma con los datos de hoy del autor; al finalizar se congela (D-10)."""
        return firma_de(self.autor)

    def datos_para_congelar(self):
        """
        Lo que se guarda en datos_finalizacion al finalizar (decisión D-10). La edad
        no se guarda: se calcula con la fecha de nacimiento congelada y la fecha de
        ingreso, que tampoco cambia en un informe finalizado. El encabezado del
        laboratorio también se congela (D-15): cambiar el .env no altera un finalizado.
        """
        paciente = self.paciente
        return {
            'paciente': None
            if paciente is None
            else {
                'id': paciente.id,
                'nombre_completo': paciente.nombre_completo,
                'tipo_documento': paciente.tipo_documento,
                'numero_documento': paciente.numero_documento,
                'fecha_nacimiento': paciente.fecha_nacimiento.isoformat(),
                'sexo': paciente.sexo,
            },
            'eps_nombre': self.eps.nombre if self.eps else None,
            'servicio_nombre': self.servicio.nombre if self.servicio else None,
            'firma': self.firma_actual(),
            'laboratorio': {
                'nombre': settings.LABORATORIO_NOMBRE,
                'direccion': settings.LABORATORIO_DIRECCION,
                'telefono': settings.LABORATORIO_TELEFONO,
            },
        }

    def datos_impresos(self):
        """Los datos que muestran la API y el PDF: congelados si está finalizado (D-10), actuales si no."""
        if self.esta_finalizado and self.datos_finalizacion:
            return self.datos_finalizacion
        return self.datos_para_congelar()

    def edad_paciente(self, paciente):
        """
        Edad del paciente impreso (el diccionario de datos_impresos()) a la fecha de
        ingreso, no a hoy: así no cambia al reimprimir el informe. Los informes
        antiguos sin fecha de ingreso usan la de creación. None si no hay paciente.
        """
        if paciente is None:
            return None
        fecha = self.fecha_ingreso or timezone.localdate(self.fecha_creacion)
        return edad_en_texto(date.fromisoformat(paciente['fecha_nacimiento']), fecha)


class Diagnostico(models.Model):
    """
    Diagnóstico del informe (informe v2, etapa 5). Un informe tiene varios, en el
    orden en que se imprimen; el código CIE-10 es opcional.
    """

    informe = models.ForeignKey(
        Informe,
        on_delete=models.CASCADE,
        related_name='diagnosticos',
        verbose_name='Informe',
    )
    orden = models.PositiveSmallIntegerField(verbose_name='Orden')
    descripcion = models.TextField(verbose_name='Descripción')
    codigo_cie10 = models.CharField(max_length=7, blank=True, verbose_name='Código CIE-10')

    class Meta:
        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'
        ordering = ['informe', 'orden']
        constraints = [
            models.UniqueConstraint(fields=['informe', 'orden'], name='diagnostico_orden_unico'),
        ]

    def __str__(self):
        codigo = f' ({self.codigo_cie10})' if self.codigo_cie10 else ''
        return f'{self.orden}. {self.descripcion}{codigo}'


class Adenda(models.Model):
    """
    Corrección de un informe finalizado (informe v2, etapa 8; decisión D-9). No modifica
    el informe (D-3): es un texto nuevo, numerado, fechado y firmado por quien la crea.
    No se edita ni se borra desde la aplicación.
    """

    informe = models.ForeignKey(
        Informe,
        on_delete=models.PROTECT,
        related_name='adendas',
        verbose_name='Informe',
    )
    # 1, 2, 3... dentro de cada informe; lo asigna la acción `adendas` de InformeViewSet.
    numero = models.PositiveSmallIntegerField(verbose_name='Número')
    motivo = models.CharField(max_length=300, verbose_name='Motivo')
    texto = models.TextField(verbose_name='Texto')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='adendas',
        verbose_name='Autor',
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    # Nombre, especialidad y registro médico de quien la crea, tal como estaban (como D-10).
    firma = models.JSONField(verbose_name='Firma')

    class Meta:
        verbose_name = 'Adenda'
        verbose_name_plural = 'Adendas'
        ordering = ['informe', 'numero']
        constraints = [
            models.UniqueConstraint(fields=['informe', 'numero'], name='adenda_numero_unico'),
        ]

    def __str__(self):
        return f'Adenda N.º {self.numero} de {self.informe.numero_peticion}'


class Canastilla(models.Model):
    """
    Muestreo para histología (D-18): qué tejido se envió a procesar y en qué canastilla.
    La crea siempre el usuario: el sistema no genera canastillas ni su contenido. No es
    un hallazgo ni un diagnóstico. Como los diagnósticos, se reemplaza la lista completa
    al guardar el informe, y en un informe finalizado no cambia (D-3, D-14).
    """

    informe = models.ForeignKey(
        Informe,
        on_delete=models.CASCADE,
        related_name='canastillas',
        verbose_name='Informe',
    )
    orden = models.PositiveSmallIntegerField(verbose_name='Orden')
    codigo = models.CharField(
        max_length=20,
        verbose_name='Identificación',
        help_text='Código de la canastilla en el laboratorio (A, B, 1, 2...).',
    )
    region = models.CharField(max_length=200, blank=True, verbose_name='Región o estructura anatómica')
    lesion_margen = models.CharField(max_length=200, blank=True, verbose_name='Lesión o margen relacionado')
    descripcion = models.TextField(blank=True, verbose_name='Descripción del tejido muestreado')
    cantidad = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Cantidad',
        help_text='Fragmentos, cortes, ganglios o cilindros enviados en la canastilla (opcional).',
    )
    entintado = models.CharField(max_length=200, blank=True, verbose_name='Entintado u orientación')
    motivo = models.CharField(max_length=200, blank=True, verbose_name='Motivo o tipo de muestreo')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Canastilla'
        verbose_name_plural = 'Canastillas'
        ordering = ['informe', 'orden']
        constraints = [
            models.UniqueConstraint(fields=['informe', 'orden'], name='canastilla_orden_unico'),
            models.UniqueConstraint(fields=['informe', 'codigo'], name='canastilla_codigo_unico'),
        ]

    def __str__(self):
        return f'Canastilla {self.codigo} de {self.informe.numero_peticion}'

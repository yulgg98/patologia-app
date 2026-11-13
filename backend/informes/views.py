import re

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, ProtectedError, Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import EsAutorOAdminOSoloLectura, EsPatologoOAdmin
from config.catalogos import filtrar_por_activo
from config.filtros import parametro_entero, parametro_fecha
from pacientes.models import Sexo, TipoDocumento

from .models import Categoria, Informe, Patologia, Plantilla, Servicio, firma_de
from .serializers import (
    AdendaSerializer,
    CategoriaSerializer,
    InformeListSerializer,
    InformeSerializer,
    PatologiaListSerializer,
    PatologiaSerializer,
    PlantillaSerializer,
    ServicioSerializer,
    TextoSugeridoSerializer,
    VistaPreviaMacroscopicaSerializer,
)
from .utils import generar_descripcion_macroscopica, generar_pdf_informe


class CategoriaViewSet(viewsets.ModelViewSet):
    """Categorías de patologías. Todos leen; crear, editar o borrar requiere patólogo o admin."""

    # El total de patologías se cuenta en la misma consulta (auditoría M-4).
    # Con annotate(Count), Django ignora Meta.ordering: el orden se indica aquí.
    queryset = Categoria.objects.annotate(num_patologias=Count('patologias')).order_by('nombre')
    serializer_class = CategoriaSerializer
    permission_classes = [EsPatologoOAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()
        if categoria.patologias.exists():
            return Response(
                {'detail': 'No se puede eliminar: hay patologías asociadas a esta categoría.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class PatologiaViewSet(viewsets.ModelViewSet):
    """Tipos de patología. Todos leen; crear, editar o borrar requiere patólogo o admin."""

    queryset = Patologia.objects.select_related('categoria').prefetch_related('plantillas').all()
    permission_classes = [EsPatologoOAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def get_queryset(self):
        qs = super().get_queryset()
        categoria_id = parametro_entero(self.request, 'categoria')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        # ?activa=true / ?activa=false (decisión D-4): "Nuevo informe" pide solo las activas.
        activa = self.request.query_params.get('activa')
        if activa in ('true', 'false'):
            qs = qs.filter(activa=(activa == 'true'))
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return PatologiaListSerializer
        return PatologiaSerializer

    def destroy(self, request, *args, **kwargs):
        # Informe.patologia usa PROTECT: si hay informes, Django lanza ProtectedError
        # antes de borrar nada. Se responde 400 en lugar de un error 500 (auditoría I-1).
        patologia = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            total = patologia.informes.count()
            return Response(
                {'detail': f'No se puede eliminar: esta patología tiene {total} informe(s) asociado(s).'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PlantillaViewSet(viewsets.ModelViewSet):
    """Campos de los formularios dinámicos (plantillas)."""

    queryset = Plantilla.objects.select_related('patologia').all()
    serializer_class = PlantillaSerializer
    permission_classes = [EsPatologoOAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        patologia_id = parametro_entero(self.request, 'patologia')
        if patologia_id:
            qs = qs.filter(patologia_id=patologia_id)
        return qs


class ServicioViewSet(viewsets.ModelViewSet):
    """Catálogo de servicios. Todos leen; patólogo o admin lo administran (decisión D-11)."""

    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [EsPatologoOAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def get_queryset(self):
        # ?activo=true: los formularios ofrecen solo los servicios activos (D-4).
        return filtrar_por_activo(super().get_queryset(), self.request, 'activo')

    def destroy(self, request, *args, **kwargs):
        # Informe.servicio usa PROTECT: un servicio en uso se desactiva, no se borra (D-4, como I-1).
        servicio = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            total = servicio.informes.count()
            return Response(
                {
                    'detail': f'No se puede eliminar: este servicio tiene {total} informe(s) asociado(s). '
                    'Desactívelo en su lugar.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class OpcionSerializer(drf_serializers.Serializer):
    """Una opción de una lista fija (solo para la documentación Swagger, D-19)."""

    valor = drf_serializers.CharField()
    etiqueta = drf_serializers.CharField()


class OpcionesSerializer(drf_serializers.Serializer):
    """Respuesta de GET /api/opciones/ (solo para la documentación Swagger, D-19)."""

    sexos = OpcionSerializer(many=True)
    tipos_documento = OpcionSerializer(many=True)
    tipos_estudio = OpcionSerializer(many=True)


def _opciones(choices):
    return [{'valor': valor, 'etiqueta': etiqueta} for valor, etiqueta in choices.choices]


class OpcionesView(APIView):
    """
    GET /api/opciones/: listas fijas sacadas de los TextChoices, para que el
    frontend no las copie (docs/propuesta-informe-v2.md, 3.3). Las EPS y los
    servicios son catálogos editables y tienen sus propios endpoints.
    """

    @extend_schema(summary='Listas fijas de opciones', responses=OpcionesSerializer)
    def get(self, request):
        return Response(
            {
                'sexos': _opciones(Sexo),
                'tipos_documento': _opciones(TipoDocumento),
                'tipos_estudio': _opciones(Informe.TipoEstudio),
            }
        )


class InformeViewSet(viewsets.ModelViewSet):
    """
    Informes de patología.
    - Al crear un informe, su autor es el usuario que hace la petición.
    - Al guardar, se genera la descripción macroscópica.
    - Permite buscar, ver estadísticas y exportar a PDF.

    Reglas (docs/decisiones.md, D-2 y D-3):
    - solo el autor o un admin puede editar, borrar o finalizar un informe;
    - un informe finalizado no se puede editar ni borrar, ni siquiera un admin.
    """

    queryset = Informe.objects.select_related('patologia', 'autor', 'paciente', 'eps', 'servicio').all()
    permission_classes = [EsAutorOAdminOSoloLectura]

    def _rechazar_si_finalizado(self, informe):
        if informe.estado == Informe.Estado.FINALIZADO:
            return Response(
                {'detail': 'El informe está finalizado y no se puede modificar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        # get_object() comprueba primero el permiso (autor o admin → si no, 403).
        rechazo = self._rechazar_si_finalizado(self.get_object())
        return rechazo or super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        rechazo = self._rechazar_si_finalizado(self.get_object())
        return rechazo or super().destroy(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return InformeListSerializer
        return InformeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        # El detalle, el PDF y finalizar devuelven los diagnósticos, las canastillas (D-18) y
        # las adendas: se cargan en una consulta cada uno (M-4). El listado no los muestra.
        if self.detail:
            qs = qs.prefetch_related('diagnosticos', 'canastillas', 'adendas')

        # Filtros de búsqueda
        # Cada palabra de ?q= debe aparecer en alguno de los campos: así "ficticio uno"
        # encuentra a "Paciente Ficticio Uno" aunque esté repartido en nombres y apellidos.
        for palabra in params.get('q', '').split():
            qs = qs.filter(
                Q(numero_peticion__icontains=palabra)
                | Q(numero_orden_externa__icontains=palabra)
                | Q(patologia__nombre__icontains=palabra)
                | Q(tipo_muestra__icontains=palabra)
                |
                # El documento se guarda sin puntos: "1.234" también encuentra "1234".
                Q(paciente__numero_documento__icontains=palabra.replace('.', ''))
                | Q(paciente__nombres__icontains=palabra)
                | Q(paciente__apellidos__icontains=palabra)
            )

        # Fechas e ids se comprueban antes de filtrar: un valor no válido responde 400 (O-22).
        fecha_desde = parametro_fecha(self.request, 'fecha_desde')
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)

        fecha_hasta = parametro_fecha(self.request, 'fecha_hasta')
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)

        estado = params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        patologia_id = parametro_entero(self.request, 'patologia')
        if patologia_id:
            qs = qs.filter(patologia_id=patologia_id)

        paciente_id = parametro_entero(self.request, 'paciente')
        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)

        return qs

    def perform_create(self, serializer):
        # La descripción macroscópica la genera InformeSerializer, en la misma transacción (O-23).
        serializer.save(autor=self.request.user)

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        Totales de informes por estado, contando todos los informes y no solo
        una página del listado (auditoría I-4). Respeta los mismos filtros que
        el listado (q, fechas, estado, patologia).
        """
        por_estado = dict(
            self.get_queryset()
            .order_by()  # sin el orden por fecha, para que el GROUP BY sea solo por estado
            .values_list('estado')
            .annotate(total=Count('id'))
        )
        return Response(
            {
                'total': sum(por_estado.values()),
                'borradores': por_estado.get(Informe.Estado.BORRADOR, 0),
                'finalizados': por_estado.get(Informe.Estado.FINALIZADO, 0),
            }
        )

    @extend_schema(
        summary='Vista previa de la descripción macroscópica',
        request=VistaPreviaMacroscopicaSerializer,
        responses=TextoSugeridoSerializer,
    )
    @action(detail=False, methods=['post'], url_path='vista-previa-macroscopica')
    def vista_previa_macroscopica(self, request):
        """
        Texto sugerido con los datos del formulario, con la misma función que al guardar
        (tarea 1). No guarda nada ni gasta un número de petición (D-7): así se ve en vivo
        también en un informe nuevo, que nunca se autoguarda (D-13). Solo patólogo o admin.
        """
        serializer = VistaPreviaMacroscopicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        texto = generar_descripcion_macroscopica(
            serializer.validated_data['patologia'], serializer.validated_data['datos_ingresados']
        )
        return Response({'texto_sugerido': texto})

    @action(detail=True, methods=['get'], url_path='pdf')
    def exportar_pdf(self, request, pk=None):
        """
        Descarga el informe en PDF. El de un borrador es una vista previa solo para su
        autor o un admin (decisión D-12): lleva la marca de agua "BORRADOR" y el sufijo
        _borrador en el nombre del archivo.
        """
        informe = self.get_object()
        if not informe.esta_finalizado and not (request.user.es_admin or informe.autor_id == request.user.id):
            raise PermissionDenied('El PDF de un borrador es una vista previa solo para su autor o un administrador.')
        buffer = generar_pdf_informe(informe)
        # El número de petición lo genera el sistema (D-7), pero se sigue limpiando:
        # unas comillas o un punto y coma romperían la cabecera Content-Disposition (I-5).
        # El nombre del archivo nunca lleva datos del paciente.
        safe_name = re.sub(r'[^A-Za-z0-9\-]', '_', informe.numero_peticion)
        if not informe.esta_finalizado:
            safe_name += '_borrador'
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="informe_{safe_name}.pdf"'
        return response

    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        """
        Finaliza el informe (después ya no se puede editar, D-3). Exige los requisitos
        de D-8 y, en la misma transacción, fija la fecha de informe y congela los
        datos que imprime (D-10).
        """
        # get_object() comprueba el permiso (autor o admin, D-2) antes de bloquear nada.
        self.get_object()
        with transaction.atomic():
            # Se bloquea el informe: dos peticiones a la vez no lo finalizan dos veces.
            informe = self.get_queryset().select_for_update(of=('self',)).get(pk=pk)
            if informe.esta_finalizado:
                return Response(
                    {'detail': 'El informe ya está finalizado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            faltantes = informe.requisitos_faltantes()
            if faltantes:
                return Response(
                    {'detail': 'No se puede finalizar el informe. ' + ' '.join(faltantes), 'requisitos': faltantes},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            informe.estado = Informe.Estado.FINALIZADO
            informe.fecha_informe = timezone.now()
            informe.datos_finalizacion = informe.datos_para_congelar()
            informe.save(update_fields=['estado', 'fecha_informe', 'datos_finalizacion'])
        return Response(InformeSerializer(informe).data)

    @action(detail=True, methods=['get', 'post'], url_path='adendas')
    def adendas(self, request, pk=None):
        """
        GET: adendas del informe, en orden. POST: agrega una (decisión D-9). Solo en
        informes finalizados; la crea el autor del informe o un admin (D-2) y la firma
        quien la crea, que necesita registro médico. No hay PUT, PATCH ni DELETE: una
        adenda no se modifica, y agregarla no cambia el informe (D-3).
        """
        # get_object() comprueba el permiso: en un POST, autor o admin (si no, 403).
        informe = self.get_object()
        if request.method == 'GET':
            return Response(AdendaSerializer(informe.adendas.all(), many=True).data)

        if not informe.esta_finalizado:
            return Response(
                {'detail': 'Un informe en borrador no lleva adendas: corríjalo editándolo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.registro_medico.strip():
            return Response(
                {'detail': 'Para firmar una adenda necesita registro médico; un administrador debe registrarlo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AdendaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                # Se bloquea el informe: dos adendas a la vez no reciben el mismo número.
                # En SQLite el bloqueo no existe y la restricción única hace de respaldo.
                bloqueado = Informe.objects.select_for_update().get(pk=informe.pk)
                numero = (bloqueado.adendas.aggregate(ultimo=Max('numero'))['ultimo'] or 0) + 1
                serializer.save(
                    informe=bloqueado,
                    numero=numero,
                    autor=request.user,
                    firma=firma_de(request.user),
                )
        except IntegrityError:
            return Response(
                {'detail': 'Otra adenda se guardó al mismo tiempo. Intente de nuevo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

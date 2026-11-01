from django.contrib import admin

from .models import (
    Adenda,
    Canastilla,
    Categoria,
    ConsecutivoPeticion,
    Diagnostico,
    Informe,
    Patologia,
    Plantilla,
    Servicio,
)


class PlantillaInline(admin.TabularInline):
    model = Plantilla
    extra = 1


def es_finalizado(informe):
    return informe is not None and informe.esta_finalizado


class DiagnosticoInline(admin.TabularInline):
    """Los diagnósticos de un informe finalizado son de solo lectura (decisión D-14)."""

    model = Diagnostico
    extra = 0

    def has_add_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_delete_permission(request, obj)


class CanastillaInline(admin.TabularInline):
    """Las canastillas de un informe finalizado son de solo lectura, como sus diagnósticos (D-14, D-18)."""

    model = Canastilla
    extra = 0

    def has_add_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_delete_permission(request, obj)


class AdendaInline(admin.StackedInline):
    """Solo consulta: las adendas no se agregan, cambian ni borran desde /admin/ (decisión D-9)."""

    model = Adenda
    extra = 0
    fields = ['numero', 'fecha', 'autor', 'motivo', 'texto', 'firma']
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa', 'fecha_creacion']
    list_filter = ['activa']
    search_fields = ['nombre']


@admin.register(Patologia)
class PatologiaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'categoria']
    search_fields = ['nombre']
    inlines = [PlantillaInline]


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ['numero_peticion', 'paciente', 'tipo_estudio', 'patologia', 'autor', 'fecha', 'estado']
    list_filter = ['estado', 'tipo_estudio', 'patologia', 'fecha']
    search_fields = [
        'numero_peticion',
        'numero_orden_externa',
        'tipo_muestra',
        'paciente__numero_documento',
        'paciente__nombres',
        'paciente__apellidos',
    ]
    list_select_related = ['paciente', 'patologia', 'autor']
    # Listas con búsqueda en lugar de un menú con todos los pacientes.
    autocomplete_fields = ['paciente']
    # numero_peticion (D-7), fecha_informe y datos_finalizacion (D-10) no son editables:
    # se muestran pero no se pueden cambiar. El estado tampoco: un informe solo se
    # finaliza con POST /api/informes/{id}/finalizar/, que exige los requisitos (D-8) y
    # congela los datos (D-10, D-15); en /admin/ se saltaban (hallazgo O-3).
    readonly_fields = [
        'numero_peticion',
        'estado',
        'texto_generado',
        'fecha_informe',
        'datos_finalizacion',
        'fecha_creacion',
        'fecha_actualizacion',
    ]
    inlines = [DiagnosticoInline, CanastillaInline, AdendaInline]

    # Un informe finalizado no se modifica ni se borra, tampoco aquí (decisión D-14): la
    # ficha queda de solo lectura y se corrige con adendas (D-9). Django revisa el borrado
    # objeto por objeto, así que la acción de borrado en lote tampoco lo borra.
    def has_change_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not es_finalizado(obj) and super().has_delete_permission(request, obj)


@admin.register(ConsecutivoPeticion)
class ConsecutivoPeticionAdmin(admin.ModelAdmin):
    """Solo consulta: cambiar el contador a mano podría repetir números de petición."""

    list_display = ['anio', 'ultimo']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Plantilla)
class PlantillaAdmin(admin.ModelAdmin):
    list_display = ['campo_nombre', 'patologia', 'seccion', 'tipo_campo', 'obligatorio', 'orden']
    list_filter = ['patologia', 'tipo_campo', 'obligatorio']

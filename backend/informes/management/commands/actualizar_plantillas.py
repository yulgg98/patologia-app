"""
Aplica a las 14 patologías las plantillas revisadas con el «Manual de procesamiento
macroscópico de patología quirúrgica» (HUV – Univalle, 2.ª ed.), decisión D-18.
Las definiciones están en informes/definiciones_manual.py.

Uso:
    python manage.py actualizar_plantillas            # aplica los cambios
    python manage.py actualizar_plantillas --simular  # cuenta lo que cambiaría y no guarda nada
    python manage.py actualizar_plantillas -v 2       # con el detalle por patología

Se puede ejecutar varias veces con el mismo resultado. No borra patologías, campos ni
opciones de las listas (solo agrega), y no toca ningún informe: los datos guardados
siguen siendo válidos. Una patología que no existe en la base se omite con un aviso.
seed_data lo llama al final.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from informes.definiciones_manual import DEFINICIONES, ORDEN_SECCIONES
from informes.models import Patologia, Plantilla

# Los campos que ya existían y no aparecen en las definiciones se conservan, al final.
ORDEN_CAMPOS_NO_LISTADOS = 1000


class Command(BaseCommand):
    help = 'Actualiza las plantillas de las 14 patologías según el manual de procesamiento macroscópico (D-18).'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra los cambios sin guardarlos.')

    def handle(self, *args, **options):
        detalle = options['verbosity'] >= 2
        with transaction.atomic():
            actualizados = creados = 0
            for nombre, definicion in DEFINICIONES.items():
                patologia = Patologia.objects.filter(nombre=nombre).first()
                if patologia is None:
                    if options['verbosity'] >= 1:
                        self.stdout.write(self.style.WARNING(f'  [OMITIDA] La patología "{nombre}" no existe.'))
                    continue
                cambios = self._actualizar(patologia, definicion)
                actualizados += cambios[0]
                creados += cambios[1]
                if detalle:
                    self.stdout.write(f'  [OK] {nombre}: {cambios[0]} campos revisados, {cambios[1]} nuevos.')
            if options['simular']:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('[SIMULACIÓN] No se guardó ningún cambio.'))
        if options['verbosity'] >= 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Plantillas según el manual: {actualizados} campos revisados y {creados} nuevos.'
                )
            )

    def _actualizar(self, patologia, definicion):
        existentes = {p.campo_nombre: p for p in patologia.plantillas.all()}
        revisados = nuevos = 0
        # Los campos de una misma sección quedan juntos (sorted es estable).
        campos = sorted(definicion['campos'], key=lambda campo: ORDEN_SECCIONES.index(campo['seccion']))
        for posicion, campo in enumerate(campos, start=1):
            datos = {k: v for k, v in campo.items() if k not in ('campo_nombre', 'opciones')}
            datos['orden'] = posicion * 10
            opciones = campo.get('opciones', [])
            plantilla = existentes.pop(campo['campo_nombre'], None)
            if plantilla is None:
                Plantilla.objects.create(
                    patologia=patologia, campo_nombre=campo['campo_nombre'], opciones=opciones, **datos
                )
                nuevos += 1
                continue
            for atributo, valor in datos.items():
                setattr(plantilla, atributo, valor)
            # Las opciones solo se agregan: un informe guardado con una opción sigue siendo válido.
            plantilla.opciones = [*plantilla.opciones, *(o for o in opciones if o not in plantilla.opciones)]
            plantilla.save()
            revisados += 1

        for plantilla in existentes.values():
            if plantilla.orden < ORDEN_CAMPOS_NO_LISTADOS:
                plantilla.orden += ORDEN_CAMPOS_NO_LISTADOS
                plantilla.save(update_fields=['orden'])

        patologia.guia_muestreo = definicion['guia_muestreo']
        patologia.save(update_fields=['guia_muestreo', 'fecha_actualizacion'])
        return revisados, nuevos

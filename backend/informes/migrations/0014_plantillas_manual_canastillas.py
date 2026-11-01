# Plantillas según el manual de procesamiento macroscópico y canastillas (decisión D-18).
# Solo agrega columnas con valor por defecto y una tabla nueva: no cambia datos existentes.
# Las plantillas se actualizan después con `python manage.py actualizar_plantillas`.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('informes', '0013_datos_ingresados_validados'),
    ]

    operations = [
        migrations.AddField(
            model_name='patologia',
            name='guia_muestreo',
            field=models.JSONField(blank=True, default=list, help_text='Lista de {"titulo": ..., "items": [...]} con las indicaciones del manual (solo referencia).', verbose_name='Guía de muestreo para histología'),
        ),
        migrations.AddField(
            model_name='plantilla',
            name='seccion',
            field=models.CharField(blank=True, help_text='Agrupa el campo en el formulario y en la descripción (p. ej. «Lesiones»).', max_length=100, verbose_name='Sección'),
        ),
        migrations.AddField(
            model_name='plantilla',
            name='condicion',
            field=models.JSONField(blank=True, default=dict, help_text='{"campo": "<campo_nombre>", "valores": [...]}; vacía si el campo siempre aplica.', verbose_name='Condición de aplicabilidad'),
        ),
        migrations.AddField(
            model_name='plantilla',
            name='ayuda',
            field=models.TextField(blank=True, verbose_name='Texto de ayuda'),
        ),
        migrations.CreateModel(
            name='Canastilla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orden', models.PositiveSmallIntegerField(verbose_name='Orden')),
                ('codigo', models.CharField(help_text='Código de la canastilla en el laboratorio (A, B, 1, 2...).', max_length=20, verbose_name='Identificación')),
                ('region', models.CharField(blank=True, max_length=200, verbose_name='Región o estructura anatómica')),
                ('lesion_margen', models.CharField(blank=True, max_length=200, verbose_name='Lesión o margen relacionado')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción del tejido muestreado')),
                ('cantidad', models.PositiveSmallIntegerField(blank=True, help_text='Fragmentos, cortes, ganglios o cilindros enviados en la canastilla (opcional).', null=True, verbose_name='Cantidad')),
                ('entintado', models.CharField(blank=True, max_length=200, verbose_name='Entintado u orientación')),
                ('motivo', models.CharField(blank=True, max_length=200, verbose_name='Motivo o tipo de muestreo')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('informe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='canastillas', to='informes.informe', verbose_name='Informe')),
            ],
            options={
                'verbose_name': 'Canastilla',
                'verbose_name_plural': 'Canastillas',
                'ordering': ['informe', 'orden'],
                'constraints': [models.UniqueConstraint(fields=('informe', 'orden'), name='canastilla_orden_unico'), models.UniqueConstraint(fields=('informe', 'codigo'), name='canastilla_codigo_unico')],
            },
        ),
    ]

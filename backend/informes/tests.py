import threading
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Usuario
from pacientes.models import EPS, Paciente

from .definiciones_manual import DEFINICIONES
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
    firma_de,
)
from .reglas import campos_aplicables, validar_datos
from .serializers import MAX_CANASTILLAS
from .utils import generar_descripcion_macroscopica, texto_seguro


def paciente_ficticio(numero='PRUEBA0001', **extra):
    """Paciente con datos ficticios (docs/propuesta-informe-v2.md, sección 8)."""
    datos = {
        'tipo_documento': 'CC',
        'numero_documento': numero,
        'nombres': 'Paciente Ficticio',
        'apellidos': 'Uno',
        'fecha_nacimiento': date(1980, 10, 5),
        'sexo': 'femenino',
        **extra,
    }
    return Paciente.objects.create(**datos)


class PermisosInformeTests(APITestCase):
    """
    Hallazgo C-2 de docs/auditoria-inicial.md y decisión D-2 de docs/decisiones.md:
    - un informe finalizado no se puede editar ni borrar;
    - solo el autor o un admin puede editar, borrar o finalizar un informe.
    """

    def setUp(self):
        self.autor = Usuario.objects.create_user(
            username='patologo_autor',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.otro_patologo = Usuario.objects.create_user(
            username='patologo_otro',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.admin = Usuario.objects.create_user(
            username='admin_prueba',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.ADMIN,
        )
        self.auditor = Usuario.objects.create_user(
            username='auditor_prueba',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.AUDITOR,
        )
        # Lo que exige finalizar (D-8): el autor tiene registro médico y el informe,
        # paciente, diagnóstico y descripción microscópica.
        self.autor.registro_medico = 'RM-PRUEBA-0001'
        self.autor.save()
        self.patologia = Patologia.objects.create(nombre='Patología de prueba')
        self.paciente = paciente_ficticio()

    def crear_informe(self, estado=Informe.Estado.BORRADOR):
        informe = Informe.objects.create(
            patologia=self.patologia,
            autor=self.autor,
            paciente=self.paciente,
            descripcion_microscopica='Hallazgos de prueba.',
            comentarios='original',
            estado=estado,
        )
        Diagnostico.objects.create(informe=informe, orden=1, descripcion='Diagnóstico de prueba')
        return informe

    def url(self, informe, accion=''):
        return f'/api/informes/{informe.id}/{accion}'

    # ── Informe finalizado: nadie puede modificarlo ───────────────

    def test_autor_no_puede_editar_informe_finalizado(self):
        informe = self.crear_informe(Informe.Estado.FINALIZADO)
        self.client.force_authenticate(self.autor)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'cambiado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        informe.refresh_from_db()
        self.assertEqual(informe.comentarios, 'original')

    def test_autor_no_puede_borrar_informe_finalizado(self):
        informe = self.crear_informe(Informe.Estado.FINALIZADO)
        self.client.force_authenticate(self.autor)
        respuesta = self.client.delete(self.url(informe))
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Informe.objects.filter(id=informe.id).exists())

    def test_admin_tampoco_puede_editar_ni_borrar_informe_finalizado(self):
        # Decisión D-3: el bloqueo de informes finalizados también aplica al admin.
        informe = self.crear_informe(Informe.Estado.FINALIZADO)
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'cambiado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        respuesta = self.client.delete(self.url(informe))
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        informe.refresh_from_db()
        self.assertEqual(informe.comentarios, 'original')

    # ── Informe ajeno: otro patólogo no puede tocarlo (D-2) ───────

    def test_otro_patologo_no_puede_editar_informe_ajeno(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.otro_patologo)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'cambiado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        informe.refresh_from_db()
        self.assertEqual(informe.comentarios, 'original')

    def test_otro_patologo_no_puede_borrar_informe_ajeno(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.otro_patologo)
        respuesta = self.client.delete(self.url(informe))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Informe.objects.filter(id=informe.id).exists())

    def test_otro_patologo_no_puede_finalizar_informe_ajeno(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.otro_patologo)
        respuesta = self.client.post(self.url(informe, 'finalizar/'))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, Informe.Estado.BORRADOR)

    def test_otro_patologo_si_puede_ver_informe_ajeno(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.otro_patologo)
        self.assertEqual(self.client.get(self.url(informe)).status_code, status.HTTP_200_OK)

    # ── Controles: lo permitido debe seguir funcionando ──────────

    def test_autor_puede_editar_y_finalizar_su_borrador(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.autor)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'cambiado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        respuesta = self.client.post(self.url(informe, 'finalizar/'))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        informe.refresh_from_db()
        self.assertEqual(informe.comentarios, 'cambiado')
        self.assertEqual(informe.estado, Informe.Estado.FINALIZADO)

    def test_autor_puede_borrar_su_borrador(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.autor)
        respuesta = self.client.delete(self.url(informe))
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_puede_editar_y_finalizar_borrador_ajeno(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'revisado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        respuesta = self.client.post(self.url(informe, 'finalizar/'))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_listado_incluye_id_del_autor(self):
        # El frontend lo usa para mostrar los botones solo al autor o al admin.
        informe = self.crear_informe()
        self.client.force_authenticate(self.otro_patologo)
        resultados = self.client.get('/api/informes/').data['results']
        self.assertEqual(resultados[0]['autor'], self.autor.id)
        self.assertEqual(resultados[0]['id'], informe.id)

    def test_auditor_no_puede_editar(self):
        informe = self.crear_informe()
        self.client.force_authenticate(self.auditor)
        respuesta = self.client.patch(self.url(informe), {'comentarios': 'cambiado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


class BorrarPatologiaTests(APITestCase):
    """
    Hallazgo I-1 de docs/auditoria-inicial.md: borrar una patología que ya tiene
    informes debe responder 400 con un mensaje claro, no un error 500.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_prueba',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología con informes')

    def test_no_se_puede_borrar_patologia_con_informes(self):
        Informe.objects.create(patologia=self.patologia, autor=self.patologo)
        respuesta = self.client.delete(f'/api/patologias/{self.patologia.id}/')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('informe', respuesta.data['detail'])
        self.assertTrue(Patologia.objects.filter(id=self.patologia.id).exists())

    def test_si_se_puede_borrar_patologia_sin_informes(self):
        # Control: sin informes asociados, el borrado funciona como antes.
        respuesta = self.client.delete(f'/api/patologias/{self.patologia.id}/')
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patologia.objects.filter(id=self.patologia.id).exists())


class PdfConTextoDelUsuarioTests(APITestCase):
    """
    Hallazgo I-3 de docs/auditoria-inicial.md: ReportLab interpreta el texto de
    Paragraph como marcado (<b>, <font>...). El texto que escribe el usuario debe
    salir tal cual en el PDF: sin romper la generación y sin cambiar el formato.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_pdf',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.informe = Informe.objects.create(
            patologia=Patologia.objects.create(nombre='Patología PDF'),
            autor=self.patologo,
            # "DATOS CLÍNICOS" ya no está en el PDF (etapa 7): el marcado va en la microscópica.
            descripcion_microscopica='ver <i>H. pylori',
            texto_generado='Lesión <b>grande',
            comentarios='<font size=40>ENORME</font> & margen < 2 mm',
        )

    def descargar_pdf(self):
        return self.client.get(f'/api/informes/{self.informe.id}/pdf/')

    def test_pdf_se_genera_con_texto_que_parece_marcado(self):
        respuesta = self.descargar_pdf()
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')

    def test_el_marcado_del_usuario_no_se_interpreta(self):
        from reportlab.platypus import Paragraph

        with mock.patch('informes.utils.Paragraph', wraps=Paragraph) as espia:
            self.descargar_pdf()
        textos = ' '.join(str(llamada.args[0]) for llamada in espia.call_args_list)
        # El texto del usuario llega escapado: se verá literal en el PDF.
        self.assertIn('&lt;font size=40&gt;ENORME&lt;/font&gt; &amp; margen &lt; 2 mm', textos)
        self.assertIn('Lesión &lt;b&gt;grande', textos)
        self.assertIn('ver &lt;i&gt;H. pylori', textos)
        self.assertNotIn('<font size=40>', textos)

    def test_los_saltos_de_linea_de_los_comentarios_se_respetan(self):
        from reportlab.platypus import Paragraph

        self.informe.comentarios = 'Primera línea\r\nSegunda línea\nTercera < línea'
        self.informe.save()
        with mock.patch('informes.utils.Paragraph', wraps=Paragraph) as espia:
            respuesta = self.descargar_pdf()
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        textos = [str(llamada.args[0]) for llamada in espia.call_args_list]
        self.assertIn('Primera línea<br/>Segunda línea<br/>Tercera &lt; línea', textos)

    # La hora del pie en la zona de Bogotá (hallazgo M-10) la comprueba ahora
    # PdfInformeTests, porque desde la etapa 7 el pie se dibuja en cada página.


class EstadisticasYPaginacionTests(APITestCase):
    """
    Hallazgo I-4 de docs/auditoria-inicial.md: el dashboard y el buscador solo
    veían la primera página (20 informes). Con 25 informes, el dashboard decía
    "total 20" y el buscador no permitía ver los otros 5.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_stats',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        patologia = Patologia.objects.create(nombre='Patología estadísticas')
        for i in range(25):
            Informe.objects.create(
                patologia=patologia,
                autor=self.patologo,
                estado=Informe.Estado.FINALIZADO if i < 15 else Informe.Estado.BORRADOR,
            )
        self.client.force_authenticate(self.patologo)

    def test_estadisticas_cuentan_todos_los_informes(self):
        respuesta = self.client.get('/api/informes/estadisticas/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data, {'total': 25, 'borradores': 10, 'finalizados': 15})

    def test_auditor_puede_ver_estadisticas(self):
        auditor = Usuario.objects.create_user(
            username='auditor_stats',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.AUDITOR,
        )
        self.client.force_authenticate(auditor)
        self.assertEqual(self.client.get('/api/informes/estadisticas/').status_code, status.HTTP_200_OK)

    def test_estadisticas_requieren_autenticacion(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/informes/estadisticas/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_la_segunda_pagina_trae_los_informes_restantes(self):
        # Lo que usa la paginación del buscador: count, next y previous.
        primera = self.client.get('/api/informes/').data
        self.assertEqual(primera['count'], 25)
        self.assertEqual(len(primera['results']), 20)
        self.assertIsNotNone(primera['next'])
        segunda = self.client.get('/api/informes/', {'page': 2}).data
        self.assertEqual(len(segunda['results']), 5)
        self.assertIsNone(segunda['next'])
        self.assertIsNotNone(segunda['previous'])

    def test_la_paginacion_respeta_los_filtros(self):
        respuesta = self.client.get('/api/informes/', {'estado': 'borrador', 'page': 1}).data
        self.assertEqual(respuesta['count'], 10)
        self.assertTrue(all(i['estado'] == 'borrador' for i in respuesta['results']))


class DescargaPdfTests(APITestCase):
    """
    Hallazgo I-5 de docs/auditoria-inicial.md: el token de sesión no debe viajar
    en la URL (queda en el historial y en los registros del servidor). El PDF se
    descarga solo por /api/informes/{id}/pdf/ con la cabecera Authorization.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_descarga',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.informe = Informe.objects.create(
            patologia=Patologia.objects.create(nombre='Patología descarga'),
            autor=self.patologo,
        )
        self.url = f'/api/informes/{self.informe.id}/pdf/'

    def test_descarga_con_cabecera_authorization(self):
        self.client.force_authenticate(self.patologo)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        # Es un borrador: el nombre del archivo lo dice (decisión D-12).
        self.assertEqual(
            respuesta['Content-Disposition'],
            f'attachment; filename="informe_{self.informe.numero_peticion}_borrador.pdf"',
        )

    def test_auditor_puede_descargar_un_informe_finalizado(self):
        # Un borrador es solo vista previa de su autor o de un admin (decisión D-12).
        Informe.objects.filter(id=self.informe.id).update(estado=Informe.Estado.FINALIZADO)
        auditor = Usuario.objects.create_user(
            username='auditor_descarga',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.AUDITOR,
        )
        self.client.force_authenticate(auditor)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)

    def test_sin_autenticacion_no_descarga(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ya_no_existe_la_descarga_con_token_en_la_url(self):
        from rest_framework_simplejwt.tokens import AccessToken

        token = str(AccessToken.for_user(self.patologo))
        respuesta = self.client.get(f'/api/descargar-pdf/{self.informe.id}/informe.pdf', {'token': token})
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_nombre_de_archivo_sin_caracteres_peligrosos(self):
        # Las comillas o el punto y coma romperían la cabecera. El número de petición
        # lo genera el sistema (D-7), pero la limpieza se mantiene como defensa.
        self.informe.numero_peticion = 'PAT 1"x";y'
        self.informe.save()
        self.client.force_authenticate(self.patologo)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta['Content-Disposition'], 'attachment; filename="informe_PAT_1_x__y_borrador.pdf"')


class CamposObligatoriosTests(APITestCase):
    """
    Hallazgo I-2 de docs/auditoria-inicial.md: la validación de los campos
    obligatorios de la plantilla se saltaba si datos_ingresados llegaba vacío.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_obligatorios',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología con obligatorios')
        Plantilla.objects.create(
            patologia=self.patologia,
            campo_nombre='localizacion',
            campo_label='Localización',
            tipo_campo='texto',
            obligatorio=True,
        )
        Plantilla.objects.create(
            patologia=self.patologia,
            campo_nombre='num_ganglios',
            campo_label='Número de ganglios',
            tipo_campo='numero',
            obligatorio=True,
        )
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='color', campo_label='Color', tipo_campo='texto', obligatorio=False
        )
        self.datos_completos = {'localizacion': 'Axila izquierda', 'num_ganglios': 3}
        self.paciente = paciente_ficticio()

    def crear(self, **extra):
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, **extra}
        return self.client.post('/api/informes/', cuerpo, format='json')

    def test_rechaza_datos_vacios(self):
        respuesta = self.crear(datos_ingresados={})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Localización', str(respuesta.data['datos_ingresados']))
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_si_no_se_envian_datos(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_obligatorio_en_blanco(self):
        respuesta = self.crear(datos_ingresados={'localizacion': '   ', 'num_ganglios': 3})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cero_es_un_valor_valido(self):
        # "0 ganglios" es un dato clínico real, no un campo vacío.
        respuesta = self.crear(datos_ingresados={'localizacion': 'Axila izquierda', 'num_ganglios': 0})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_acepta_datos_completos(self):
        # Control.
        self.assertEqual(self.crear(datos_ingresados=self.datos_completos).status_code, status.HTTP_201_CREATED)

    def test_patch_de_solo_comentarios_no_exige_reenviar_los_datos(self):
        # Control: editar solo los comentarios no debe fallar por "faltan campos".
        informe_id = self.crear(datos_ingresados=self.datos_completos).data['id']
        respuesta = self.client.patch(f'/api/informes/{informe_id}/', {'comentarios': 'Revisado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_patch_que_vacia_un_obligatorio_se_rechaza(self):
        informe_id = self.crear(datos_ingresados=self.datos_completos).data['id']
        respuesta = self.client.patch(
            f'/api/informes/{informe_id}/',
            {'datos_ingresados': {'num_ganglios': 3}},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class NombreVisibleAutorTests(APITestCase):
    """
    Auditoría M-3: "nombre_completo o, si está vacío, username" estaba repetido en
    8 lugares. Ahora lo calcula Usuario.nombre_visible. La API debe responder igual.
    """

    def setUp(self):
        self.con_nombre = Usuario.objects.create_user(
            username='dr_mendez',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            nombre_completo='Dr. Carlos Méndez',
        )
        self.sin_nombre = Usuario.objects.create_user(
            username='patologo_sin_nombre',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        patologia = Patologia.objects.create(nombre='Patología nombres')
        for autor in (self.con_nombre, self.sin_nombre):
            Informe.objects.create(patologia=patologia, autor=autor)
        self.client.force_authenticate(self.con_nombre)

    def test_informes_muestran_nombre_completo_o_username(self):
        nombres = {i['autor']: i['autor_nombre'] for i in self.client.get('/api/informes/').data['results']}
        self.assertEqual(nombres[self.con_nombre.id], 'Dr. Carlos Méndez')
        self.assertEqual(nombres[self.sin_nombre.id], 'patologo_sin_nombre')
        informe = Informe.objects.get(autor=self.sin_nombre)
        self.assertEqual(self.client.get(f'/api/informes/{informe.id}/').data['autor_nombre'], 'patologo_sin_nombre')

    def test_foro_muestra_nombre_completo_o_username(self):
        from foro.models import Comentario, Publicacion

        publicacion = Publicacion.objects.create(autor=self.sin_nombre, titulo='Caso', contenido='Texto')
        Comentario.objects.create(publicacion=publicacion, autor=self.con_nombre, contenido='Hola')
        self.assertEqual(
            self.client.get('/api/foro/publicaciones/').data['results'][0]['autor_nombre'], 'patologo_sin_nombre'
        )
        detalle = self.client.get(f'/api/foro/publicaciones/{publicacion.id}/').data
        self.assertEqual(detalle['autor_nombre'], 'patologo_sin_nombre')
        self.assertEqual(detalle['comentarios'][0]['autor_nombre'], 'Dr. Carlos Méndez')


class ConsultasPorListadoTests(APITestCase):
    """
    Hallazgo M-4 de docs/auditoria-inicial.md: algunos listados hacían una consulta
    extra por cada fila (problema "N+1"). El número de consultas no debe crecer
    con la cantidad de elementos.
    """

    def setUp(self):
        from foro.models import Comentario, ImagenPublicacion, Publicacion, TemaForo

        self.modelos = (Comentario, ImagenPublicacion, Publicacion, TemaForo)
        self.usuario = Usuario.objects.create_user(username='consultas', password='x', rol=Usuario.Rol.ADMIN)
        self.client.force_authenticate(self.usuario)

    def crear_elementos(self, desde, hasta):
        Comentario, ImagenPublicacion, Publicacion, TemaForo = self.modelos
        for i in range(desde, hasta):
            categoria = Categoria.objects.create(nombre=f'Categoría {i}')
            Patologia.objects.create(nombre=f'Patología {i}', categoria=categoria)
            tema = TemaForo.objects.create(nombre=f'Tema {i}')
            publicacion = Publicacion.objects.create(autor=self.usuario, titulo='t', contenido='c', tema=tema)
            Comentario.objects.create(publicacion=publicacion, autor=self.usuario, contenido='c')
            ImagenPublicacion.objects.create(publicacion=publicacion, imagen=f'foro/prueba{i}.png')

    def contar_consultas(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as consultas:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        return len(consultas)

    def test_las_consultas_no_crecen_con_los_elementos(self):
        urls = ['/api/categorias/', '/api/patologias/', '/api/foro/temas/', '/api/foro/publicaciones/']
        self.crear_elementos(0, 5)
        con_5 = {url: self.contar_consultas(url) for url in urls}
        self.crear_elementos(5, 20)
        con_20 = {url: self.contar_consultas(url) for url in urls}
        self.assertEqual(con_20, con_5)

    def test_crear_categoria_y_tema_devuelve_su_total(self):
        respuesta = self.client.post('/api/categorias/', {'nombre': 'Nueva', 'color': '#123456'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['total_patologias'], 0)
        respuesta = self.client.post('/api/foro/temas/', {'nombre': 'Nuevo tema'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['total_publicaciones'], 0)

    def test_los_totales_y_la_portada_son_correctos(self):
        Comentario, ImagenPublicacion, Publicacion, TemaForo = self.modelos
        tema = TemaForo.objects.create(nombre='Con datos')
        publicacion = Publicacion.objects.create(autor=self.usuario, titulo='t', contenido='c', tema=tema)
        for i in range(3):
            Comentario.objects.create(publicacion=publicacion, autor=self.usuario, contenido=f'c{i}')
        primera = ImagenPublicacion.objects.create(publicacion=publicacion, imagen='foro/primera.png')
        ImagenPublicacion.objects.create(publicacion=publicacion, imagen='foro/segunda.png')
        fila = self.client.get('/api/foro/publicaciones/').data['results'][0]
        self.assertEqual((fila['total_comentarios'], fila['total_imagenes']), (3, 2))
        self.assertTrue(fila['portada'].endswith(primera.imagen.url))
        temas = {t['nombre']: t['total_publicaciones'] for t in self.client.get('/api/foro/temas/').data['results']}
        self.assertEqual(temas['Con datos'], 1)

    def test_los_listados_conservan_su_orden(self):
        # Con annotate(Count), Django ignora Meta.ordering si no se indica el orden.
        Comentario, ImagenPublicacion, Publicacion, TemaForo = self.modelos
        for nombre in ['Zeta', 'Alfa', 'Media']:
            Categoria.objects.create(nombre=nombre)
            TemaForo.objects.create(nombre=nombre)
        normal = Publicacion.objects.create(autor=self.usuario, titulo='Normal', contenido='c')
        Publicacion.objects.create(autor=self.usuario, titulo='Fijada', contenido='c', fijado=True)
        Publicacion.objects.create(autor=self.usuario, titulo='Reciente', contenido='c')
        Comentario.objects.create(publicacion=normal, autor=self.usuario, contenido='c')
        # Se crean en el mismo instante: se hace "Normal" un día más antigua para que no empaten.
        from datetime import timedelta

        from django.utils import timezone

        Publicacion.objects.filter(id=normal.id).update(fecha_creacion=timezone.now() - timedelta(days=1))

        def nombres(url, campo):
            return [f[campo] for f in self.client.get(url).data['results']]

        self.assertEqual(nombres('/api/categorias/', 'nombre'), ['Alfa', 'Media', 'Zeta'])
        self.assertEqual(nombres('/api/foro/temas/', 'nombre'), ['Alfa', 'Media', 'Zeta'])
        self.assertEqual(nombres('/api/foro/publicaciones/', 'titulo'), ['Fijada', 'Reciente', 'Normal'])


class TamanoDePaginaTests(APITestCase):
    """
    Los listados vienen de 20 en 20. Los menús desplegables del frontend (patologías,
    categorías, temas) necesitan todos los elementos: con ?page_size= se puede pedir
    una página más grande, hasta un máximo de 1000.
    """

    def setUp(self):
        usuario = Usuario.objects.create_user(username='paginas', password='x', rol=Usuario.Rol.PATOLOGO)
        self.client.force_authenticate(usuario)
        for i in range(25):
            Patologia.objects.create(nombre=f'Patología {i:02d}')

    def test_por_defecto_trae_20(self):
        datos = self.client.get('/api/patologias/').data
        self.assertEqual((datos['count'], len(datos['results'])), (25, 20))

    def test_page_size_permite_traer_todas(self):
        datos = self.client.get('/api/patologias/', {'page_size': 100}).data
        self.assertEqual(len(datos['results']), 25)
        self.assertIsNone(datos['next'])

    def test_page_size_tiene_un_maximo(self):
        from django.conf import settings
        from django.utils.module_loading import import_string

        paginacion = import_string(settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'])
        self.assertEqual(paginacion.max_page_size, 1000)


class PatologiasActivasTests(APITestCase):
    """
    Decisión D-4 (auditoría M-5): una patología se puede desactivar en lugar de
    borrarse, y al crear informes solo se ofrecen las activas.
    """

    def setUp(self):
        usuario = Usuario.objects.create_user(username='activas', password='x', rol=Usuario.Rol.PATOLOGO)
        self.client.force_authenticate(usuario)
        self.activa = Patologia.objects.create(nombre='Activa')
        self.inactiva = Patologia.objects.create(nombre='Inactiva', activa=False)

    def nombres(self, **params):
        return [p['nombre'] for p in self.client.get('/api/patologias/', params).data['results']]

    def test_filtro_activa(self):
        self.assertEqual(self.nombres(activa='true'), ['Activa'])
        self.assertEqual(self.nombres(activa='false'), ['Inactiva'])

    def test_sin_filtro_devuelve_todas(self):
        # Al editar un informe viejo hace falta ver también su patología inactiva.
        self.assertEqual(self.nombres(), ['Activa', 'Inactiva'])

    def test_se_puede_desactivar_una_patologia(self):
        respuesta = self.client.patch(f'/api/patologias/{self.activa.id}/', {'activa': False}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.activa.refresh_from_db()
        self.assertFalse(self.activa.activa)


class NumeroPeticionTests(APITestCase):
    """
    Decisión D-7 (docs/decisiones.md): al crear un informe, el sistema le asigna
    un número de petición P-AÑO-NNNNN, que reemplaza al número de caso que
    escribía el usuario. Se agrega un número de orden externo opcional.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_np',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.patologia = Patologia.objects.create(nombre='Patología número de petición')
        self.paciente = paciente_ficticio()
        self.client.force_authenticate(self.patologo)
        self.anio = timezone.localdate().year

    def crear(self, **extra):
        return self.client.post(
            '/api/informes/',
            {'patologia': self.patologia.id, 'paciente': self.paciente.id, 'datos_ingresados': {}, **extra},
            format='json',
        )

    def numero(self, consecutivo, anio=None):
        return f'P-{anio or self.anio}-{consecutivo:05d}'

    def test_al_crear_se_asigna_el_numero_con_el_formato(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data['numero_peticion'], self.numero(1))

    def test_los_numeros_son_consecutivos(self):
        numeros = [self.crear().data['numero_peticion'] for _ in range(3)]
        self.assertEqual(numeros, [self.numero(1), self.numero(2), self.numero(3)])

    def test_el_consecutivo_vuelve_a_empezar_cada_anio(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 12, 31)):
            diciembre = [self.crear().data['numero_peticion'] for _ in range(2)]
        with mock.patch('django.utils.timezone.localdate', return_value=date(2027, 1, 1)):
            enero = self.crear().data['numero_peticion']
        self.assertEqual(diciembre, ['P-2026-00001', 'P-2026-00002'])
        self.assertEqual(enero, 'P-2027-00001')

    def test_el_cliente_no_puede_elegir_ni_cambiar_el_numero(self):
        respuesta = self.crear(numero_peticion='P-1999-99999')
        self.assertEqual(respuesta.data['numero_peticion'], self.numero(1))
        id_informe = respuesta.data['id']
        cambio = self.client.patch(
            f'/api/informes/{id_informe}/',
            {'numero_peticion': 'P-1999-00001'},
            format='json',
        )
        self.assertEqual(cambio.status_code, status.HTTP_200_OK)
        self.assertEqual(Informe.objects.get(id=id_informe).numero_peticion, self.numero(1))

    def test_ya_no_existe_el_numero_de_caso(self):
        respuesta = self.crear()
        self.assertNotIn('numero_caso', respuesta.data)
        fila = self.client.get('/api/informes/').data['results'][0]
        self.assertEqual(fila['numero_peticion'], self.numero(1))
        self.assertNotIn('numero_caso', fila)

    def test_borrar_un_borrador_no_reutiliza_su_numero(self):
        primero = self.crear()
        self.client.delete(f'/api/informes/{primero.data["id"]}/')
        self.assertEqual(self.crear().data['numero_peticion'], self.numero(2))

    def test_los_informes_creados_sin_la_api_tambien_se_numeran(self):
        # /admin/, seed_data y las pruebas crean informes con el ORM.
        informe = Informe.objects.create(patologia=self.patologia, autor=self.patologo)
        self.assertEqual(informe.numero_peticion, self.numero(1))

    def test_la_base_de_datos_rechaza_un_numero_repetido(self):
        primero = Informe.objects.create(patologia=self.patologia, autor=self.patologo)
        segundo = Informe.objects.create(patologia=self.patologia, autor=self.patologo)
        segundo.numero_peticion = primero.numero_peticion
        with self.assertRaises(IntegrityError), transaction.atomic():
            segundo.save()

    def test_el_numero_de_orden_externa_es_opcional_y_se_puede_repetir(self):
        sin_orden = self.crear()
        self.assertEqual(sin_orden.data['numero_orden_externa'], '')
        # Dos instituciones distintas pueden usar el mismo número de orden.
        for _ in range(2):
            con_orden = self.crear(numero_orden_externa='ORD-123')
            self.assertEqual(con_orden.status_code, status.HTTP_201_CREATED, con_orden.data)
            self.assertEqual(con_orden.data['numero_orden_externa'], 'ORD-123')

    def test_se_busca_por_numero_de_peticion_y_de_orden_externa(self):
        self.crear()
        self.crear(numero_orden_externa='HOSP-77')
        por_peticion = self.client.get('/api/informes/', {'q': self.numero(1)}).data
        self.assertEqual([i['numero_peticion'] for i in por_peticion['results']], [self.numero(1)])
        por_orden = self.client.get('/api/informes/', {'q': 'HOSP-77'}).data
        self.assertEqual([i['numero_peticion'] for i in por_orden['results']], [self.numero(2)])

    def test_el_pdf_lleva_el_numero_de_peticion(self):
        from reportlab.platypus import Table

        id_informe = self.crear().data['id']
        with mock.patch('informes.utils.Table', wraps=Table) as espia:
            respuesta = self.client.get(f'/api/informes/{id_informe}/pdf/')
        # Es un borrador: el nombre lleva el sufijo _borrador (decisión D-12).
        self.assertEqual(
            respuesta['Content-Disposition'],
            f'attachment; filename="informe_{self.numero(1)}_borrador.pdf"',
        )
        celdas = str([llamada.args[0] for llamada in espia.call_args_list])
        self.assertIn(self.numero(1), celdas)


class NumeroPeticionConcurrenciaTests(TransactionTestCase):
    """
    Decisión D-7: el número de petición no se repite aunque varios usuarios creen
    informes al mismo tiempo. Cada hilo usa su propia conexión a la base de datos,
    como dos peticiones simultáneas al servidor.
    """

    HILOS = 10

    def test_informes_creados_a_la_vez_reciben_numeros_distintos(self):
        patologo = Usuario.objects.create_user(
            username='patologo_concurrencia',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        patologia = Patologia.objects.create(nombre='Patología concurrencia')
        paciente = paciente_ficticio()
        barrera = threading.Barrier(self.HILOS)
        numeros, errores = [], []

        def crear_informe():
            try:
                cliente = APIClient()
                cliente.force_authenticate(patologo)
                barrera.wait()  # todos los hilos envían su petición al mismo tiempo
                respuesta = cliente.post(
                    '/api/informes/',
                    {'patologia': patologia.id, 'paciente': paciente.id, 'datos_ingresados': {}},
                    format='json',
                )
                if respuesta.status_code == status.HTTP_201_CREATED:
                    numeros.append(respuesta.data['numero_peticion'])
                else:
                    errores.append((respuesta.status_code, respuesta.data))
            except Exception as error:  # cualquier fallo de un hilo debe verse en la prueba
                errores.append(repr(error))
            finally:
                connection.close()

        hilos = [threading.Thread(target=crear_informe) for _ in range(self.HILOS)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(errores, [])
        anio = timezone.localdate().year
        self.assertEqual(sorted(numeros), [f'P-{anio}-{n:05d}' for n in range(1, self.HILOS + 1)])


class MigracionNumeroPeticionTests(TransactionTestCase):
    """
    La migración de datos de la etapa 1 numera los informes que ya existían: en
    orden de creación, por año de creación (hora de Bogotá), y deja el contador
    listo para que el siguiente informe continúe la numeración.
    """

    # accounts también vuelve atrás: con la columna registro_medico (accounts 0002, NOT NULL)
    # el modelo histórico de Usuario, que no la conoce, no podría crear usuarios.
    ANTES = [('informes', '0003_quitar_campos_requeridos'), ('accounts', '0001_initial')]

    def test_numera_los_informes_existentes(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.ANTES)
        modelos = executor.loader.project_state(self.ANTES).apps
        UsuarioAntiguo = modelos.get_model('accounts', 'Usuario')
        PatologiaAntigua = modelos.get_model('informes', 'Patologia')
        InformeAntiguo = modelos.get_model('informes', 'Informe')

        autor = UsuarioAntiguo.objects.create(username='autor_migracion')
        patologia = PatologiaAntigua.objects.create(nombre='Patología migración')
        # 31/12/2025 23:30 en Bogotá ya es 1/1/2026 en UTC: debe contar como 2025.
        fechas = {
            'NOCHEVIEJA': timezone.make_aware(datetime(2025, 12, 31, 23, 30)),
            'MARZO': timezone.make_aware(datetime(2026, 3, 1, 9, 0)),
            'FEBRERO': timezone.make_aware(datetime(2026, 2, 1, 9, 0)),
        }
        ids = {}
        for caso, fecha in fechas.items():
            informe = InformeAntiguo.objects.create(numero_caso=caso, patologia=patologia, autor=autor)
            InformeAntiguo.objects.filter(id=informe.id).update(fecha_creacion=fecha)
            ids[caso] = informe.id

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

        numeros = {caso: Informe.objects.get(id=id_informe).numero_peticion for caso, id_informe in ids.items()}
        self.assertEqual(
            numeros,
            {
                'NOCHEVIEJA': 'P-2025-00001',
                'FEBRERO': 'P-2026-00001',
                'MARZO': 'P-2026-00002',
            },
        )
        # El siguiente informe de 2026 continúa la numeración.
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 4)):
            nuevo = Informe.objects.create(
                patologia=Patologia.objects.get(id=patologia.id),
                autor=Usuario.objects.get(id=autor.id),
            )
        self.assertEqual(nuevo.numero_peticion, 'P-2026-00003')


class OpcionesTests(APITestCase):
    """
    Informe v2, etapa 2 (docs/propuesta-informe-v2.md, sección 3.3): GET /api/opciones/
    devuelve las listas fijas (sexo, tipo de documento, tipo de estudio) sacadas de
    los TextChoices del backend, para que el frontend no tenga que copiarlas.
    """

    def setUp(self):
        self.auditor = Usuario.objects.create_user(username='opciones', password='x', rol=Usuario.Rol.AUDITOR)

    def opciones(self):
        self.client.force_authenticate(self.auditor)
        respuesta = self.client.get('/api/opciones/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        return respuesta.data

    def test_cualquier_rol_las_lee(self):
        self.assertEqual(set(self.opciones()), {'sexos', 'tipos_documento', 'tipos_estudio'})

    def test_sexos(self):
        # Etiqueta "Sexo" con estas tres opciones (P-3).
        self.assertEqual(
            self.opciones()['sexos'],
            [
                {'valor': 'femenino', 'etiqueta': 'Femenino'},
                {'valor': 'masculino', 'etiqueta': 'Masculino'},
                {'valor': 'indeterminado', 'etiqueta': 'Indeterminado'},
            ],
        )

    def test_tipos_documento(self):
        tipos = self.opciones()['tipos_documento']
        self.assertEqual([t['valor'] for t in tipos], ['CC', 'TI', 'RC', 'CE', 'PA', 'PPT', 'MS', 'AS'])
        self.assertEqual(tipos[0], {'valor': 'CC', 'etiqueta': 'Cédula de ciudadanía'})

    def test_tipos_estudio(self):
        tipos = self.opciones()['tipos_estudio']
        self.assertEqual(
            [t['etiqueta'] for t in tipos],
            [
                'Histología',
                'Citología no ginecológica',
                'Citología cérvico-vaginal',
                'Inmunohistoquímica',
                'Estudio intraoperatorio por congelación',
                'Revisión de láminas (segunda opinión)',
            ],
        )
        self.assertEqual(tipos[0]['valor'], 'histologia')

    def test_requiere_sesion(self):
        self.assertEqual(self.client.get('/api/opciones/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_es_solo_lectura(self):
        self.client.force_authenticate(self.auditor)
        self.assertEqual(self.client.post('/api/opciones/', {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CatalogoServiciosTests(APITestCase):
    """
    Informe v2, etapa 2 (sección 3.2): catálogo de servicios. Lo administran
    patólogos y admin (decisión D-11); el auditor solo lee. Se desactiva en lugar
    de borrarse (D-4) y se filtra con ?activo=.
    """

    URL = '/api/servicios/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(username='serv_pat', password='x', rol=Usuario.Rol.PATOLOGO)
        self.auditor = Usuario.objects.create_user(username='serv_aud', password='x', rol=Usuario.Rol.AUDITOR)

    def crear(self, nombre, usuario=None, **extra):
        self.client.force_authenticate(usuario or self.patologo)
        return self.client.post(self.URL, {'nombre': nombre, **extra}, format='json')

    def nombres(self, **params):
        return [s['nombre'] for s in self.client.get(self.URL, params).data['results']]

    def test_patologo_crea_y_auditor_lee(self):
        self.assertEqual(self.crear('Urgencias').status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(self.auditor)
        self.assertEqual(self.nombres(), ['Urgencias'])

    def test_auditor_no_crea(self):
        self.assertEqual(self.crear('Urgencias', usuario=self.auditor).status_code, status.HTTP_403_FORBIDDEN)

    def test_filtro_activo(self):
        self.crear('Urgencias')
        self.crear('Cirugía', activo=False)
        self.assertEqual(self.nombres(activo='true'), ['Urgencias'])
        self.assertEqual(self.nombres(activo='false'), ['Cirugía'])
        self.assertEqual(self.nombres(), ['Cirugía', 'Urgencias'])

    def test_se_puede_desactivar(self):
        servicio_id = self.crear('Urgencias').data['id']
        respuesta = self.client.patch(f'{self.URL}{servicio_id}/', {'activo': False}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(respuesta.data['activo'])

    def test_nombre_repetido_sin_importar_mayusculas_ni_espacios(self):
        self.crear('Urgencias')
        respuesta = self.crear('  urgencias ')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('nombre', respuesta.data)

    def test_seed_data_carga_los_servicios(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_data', stdout=StringIO())
        call_command('seed_data', stdout=StringIO())  # dos veces: no duplica
        self.client.force_authenticate(self.auditor)
        self.assertEqual(
            sorted(self.nombres()),
            sorted(
                [
                    'Consulta externa',
                    'Urgencias',
                    'Hospitalización',
                    'Cirugía',
                    'Unidad de cuidados intensivos',
                    'Ginecología',
                    'Dermatología',
                ]
            ),
        )


class DatosSolicitudTests(APITestCase):
    """
    Informe v2, etapa 4 (docs/propuesta-informe-v2.md, secciones 3.4 y 4): el
    informe guarda el paciente y los datos de la solicitud (médico tratante,
    fecha de ingreso, EPS, servicio, estudios solicitados y tipo de estudio).
    Solo datos ficticios (sección 8).
    """

    URL = '/api/informes/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_solicitud',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología solicitud')
        self.eps = EPS.objects.create(nombre='EPS Ficticia')
        self.servicio = Servicio.objects.create(nombre='Urgencias')
        self.paciente = paciente_ficticio(eps=self.eps)

    def crear(self, **extra):
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, 'datos_ingresados': {}, **extra}
        return self.client.post(self.URL, cuerpo, format='json')

    # --- Paciente ---

    def test_paciente_es_obligatorio_al_crear(self):
        respuesta = self.client.post(self.URL, {'patologia': self.patologia.id, 'datos_ingresados': {}}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('paciente', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_no_se_puede_quitar_el_paciente(self):
        informe_id = self.crear().data['id']
        respuesta = self.client.patch(f'{self.URL}{informe_id}/', {'paciente': None}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('paciente', respuesta.data)

    def test_informe_antiguo_sin_paciente_se_puede_editar_y_luego_asignarle_uno(self):
        # Los informes de antes de la etapa 4 quedan sin paciente (migración 0008).
        antiguo = Informe.objects.create(patologia=self.patologia, autor=self.patologo)
        detalle = self.client.get(f'{self.URL}{antiguo.id}/').data
        self.assertIsNone(detalle['paciente'])
        self.assertIsNone(detalle['paciente_datos'])
        respuesta = self.client.patch(f'{self.URL}{antiguo.id}/', {'tipo_muestra': 'Biopsia'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        respuesta = self.client.patch(f'{self.URL}{antiguo.id}/', {'paciente': self.paciente.id}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data['paciente'], self.paciente.id)

    def test_detalle_devuelve_datos_del_paciente_con_la_edad_a_la_fecha_de_ingreso(self):
        # Nació el 5/10/1980: el 4/10/2026 tiene 45 años, aunque hoy sea 2030.
        informe_id = self.crear(fecha_ingreso='2026-10-04').data['id']
        with mock.patch('django.utils.timezone.localdate', return_value=date(2030, 1, 1)):
            datos = self.client.get(f'{self.URL}{informe_id}/').data['paciente_datos']
        self.assertEqual(
            datos,
            {
                'id': self.paciente.id,
                'nombre_completo': 'Paciente Ficticio Uno',
                'tipo_documento': 'CC',
                'numero_documento': 'PRUEBA0001',
                'fecha_nacimiento': '1980-10-05',
                'sexo': 'femenino',
                'edad': '45 años',
            },
        )

    # --- Datos de la solicitud ---

    def test_guarda_los_datos_de_la_solicitud(self):
        respuesta = self.crear(
            medico_tratante='Médico Ficticio',
            fecha_ingreso='2026-10-01',
            eps=self.eps.id,
            servicio=self.servicio.id,
            estudios_solicitados='Biopsia de piel',
            tipo_estudio='citologia_no_ginecologica',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        datos = self.client.get(f'{self.URL}{respuesta.data["id"]}/').data
        self.assertEqual(datos['medico_tratante'], 'Médico Ficticio')
        self.assertEqual(datos['fecha_ingreso'], '2026-10-01')
        self.assertEqual((datos['eps'], datos['eps_nombre']), (self.eps.id, 'EPS Ficticia'))
        self.assertEqual((datos['servicio'], datos['servicio_nombre']), (self.servicio.id, 'Urgencias'))
        self.assertEqual(datos['estudios_solicitados'], 'Biopsia de piel')
        self.assertEqual(datos['tipo_estudio'], 'citologia_no_ginecologica')

    def test_valores_por_defecto(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 4)):
            datos = self.crear().data
        self.assertEqual(datos['fecha_ingreso'], '2026-10-04')
        self.assertEqual(datos['tipo_estudio'], 'histologia')
        self.assertIsNone(datos['servicio'])
        self.assertEqual(datos['medico_tratante'], '')

    def test_tipo_de_estudio_invalido(self):
        respuesta = self.crear(tipo_estudio='astrologia')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tipo_estudio', respuesta.data)

    def test_fecha_de_ingreso_en_el_futuro(self):
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.crear(fecha_ingreso=manana.isoformat())
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_ingreso', respuesta.data)

    def test_fecha_de_ingreso_anterior_al_nacimiento(self):
        respuesta = self.crear(fecha_ingreso='1980-10-04')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_ingreso', respuesta.data)

    def test_fecha_de_ingreso_se_valida_al_cambiar_de_paciente(self):
        informe_id = self.crear(fecha_ingreso='2000-01-01').data['id']
        joven = paciente_ficticio('PRUEBA0002', fecha_nacimiento=date(2010, 1, 1))
        respuesta = self.client.patch(f'{self.URL}{informe_id}/', {'paciente': joven.id}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_ingreso', respuesta.data)

    # --- EPS: la del momento del estudio ---

    def test_si_no_se_envia_la_eps_se_copia_la_del_paciente(self):
        datos = self.crear().data
        self.assertEqual(datos['eps'], self.eps.id)

    def test_eps_enviada_vacia_queda_vacia(self):
        datos = self.crear(eps=None).data
        self.assertIsNone(datos['eps'])

    def test_no_se_copia_una_eps_desactivada_del_paciente(self):
        EPS.objects.filter(pk=self.eps.pk).update(activa=False)
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertIsNone(respuesta.data['eps'])

    def test_cambiar_la_eps_del_paciente_no_cambia_la_del_informe(self):
        informe_id = self.crear().data['id']
        otra = EPS.objects.create(nombre='Otra')
        Paciente.objects.filter(pk=self.paciente.pk).update(eps=otra)
        self.assertEqual(self.client.get(f'{self.URL}{informe_id}/').data['eps_nombre'], 'EPS Ficticia')

    def test_eps_o_servicio_desactivados_no_se_asignan(self):
        eps_inactiva = EPS.objects.create(nombre='EPS Liquidada', activa=False)
        servicio_inactivo = Servicio.objects.create(nombre='Cerrado', activo=False)
        respuesta = self.crear(eps=eps_inactiva.id, servicio=servicio_inactivo.id)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('eps', respuesta.data)
        self.assertIn('servicio', respuesta.data)

    def test_informe_conserva_eps_y_servicio_aunque_se_desactiven(self):
        informe_id = self.crear(servicio=self.servicio.id).data['id']
        EPS.objects.filter(pk=self.eps.pk).update(activa=False)
        Servicio.objects.filter(pk=self.servicio.pk).update(activo=False)
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {},
            'eps': self.eps.id,
            'servicio': self.servicio.id,
            'medico_tratante': 'Corregido',
        }
        respuesta = self.client.put(f'{self.URL}{informe_id}/', cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)

    # --- Listado, búsqueda y filtro ---

    def test_listado_incluye_paciente_y_tipo_de_estudio(self):
        self.crear(tipo_estudio='inmunohistoquimica')
        Informe.objects.create(patologia=self.patologia, autor=self.patologo)  # antiguo, sin paciente
        filas = self.client.get(self.URL).data['results']
        self.assertCountEqual(
            [(f['paciente_nombre'], f['paciente_documento'], f['tipo_estudio']) for f in filas],
            [(None, None, 'histologia'), ('Paciente Ficticio Uno', 'CC PRUEBA0001', 'inmunohistoquimica')],
        )

    def test_busqueda_por_nombre_y_documento_del_paciente(self):
        self.crear()
        otro = paciente_ficticio('PRUEBA0002', nombres='Prueba', apellidos='Apellido Dos')
        self.crear(paciente=otro.id)

        def documentos(q):
            return [f['paciente_documento'] for f in self.client.get(self.URL, {'q': q}).data['results']]

        self.assertEqual(documentos('PRUEBA0002'), ['CC PRUEBA0002'])
        self.assertEqual(documentos('ficticio uno'), ['CC PRUEBA0001'])  # nombres + apellidos
        self.assertEqual(documentos('apellido'), ['CC PRUEBA0002'])
        self.assertEqual(len(documentos('prueba')), 2)

    def test_filtro_por_paciente(self):
        self.crear()
        otro = paciente_ficticio('PRUEBA0002')
        self.crear(paciente=otro.id)
        filas = self.client.get(self.URL, {'paciente': otro.id}).data['results']
        self.assertEqual([f['paciente_documento'] for f in filas], ['CC PRUEBA0002'])


class BorrarCatalogosEnUsoPorInformesTests(APITestCase):
    """Etapa 4: una EPS o un servicio que usa un informe no se borra (PROTECT); se responde 400 (D-4)."""

    def setUp(self):
        self.admin = Usuario.objects.create_user(username='cat_admin', password='x', rol=Usuario.Rol.ADMIN)
        self.client.force_authenticate(self.admin)
        self.eps = EPS.objects.create(nombre='EPS en informe')
        self.servicio = Servicio.objects.create(nombre='Servicio en informe')
        Informe.objects.create(
            patologia=Patologia.objects.create(nombre='Patología catálogos'),
            autor=self.admin,
            eps=self.eps,
            servicio=self.servicio,
        )

    def test_borrar_servicio_en_uso_responde_400(self):
        respuesta = self.client.delete(f'/api/servicios/{self.servicio.id}/')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('1 informe', respuesta.data['detail'])
        self.assertIn('Desactívelo', respuesta.data['detail'])
        self.assertTrue(Servicio.objects.filter(pk=self.servicio.id).exists())

    def test_borrar_eps_en_uso_por_un_informe_responde_400(self):
        respuesta = self.client.delete(f'/api/pacientes/eps/{self.eps.id}/')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('1 informe', respuesta.data['detail'])
        self.assertIn('Desactívela', respuesta.data['detail'])
        self.assertTrue(EPS.objects.filter(pk=self.eps.id).exists())

    def test_borrar_servicio_sin_uso_sigue_funcionando(self):
        libre = Servicio.objects.create(nombre='Sin uso')
        self.assertEqual(self.client.delete(f'/api/servicios/{libre.id}/').status_code, status.HTTP_204_NO_CONTENT)


class ConsultasListadoInformesTests(APITestCase):
    """Auditoría M-4 aplicada a la etapa 4: los listados de informes no hacen una consulta por fila."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(username='consultas_inf', password='x', rol=Usuario.Rol.ADMIN)
        self.client.force_authenticate(self.usuario)
        self.patologia = Patologia.objects.create(nombre='Patología consultas')
        self.paciente = paciente_ficticio('PRUEBA9999')

    def crear_informes(self, desde, hasta):
        for i in range(desde, hasta):
            eps = EPS.objects.create(nombre=f'EPS {i}')
            servicio = Servicio.objects.create(nombre=f'Servicio {i}')
            # Uno del paciente fijo (para su historial) y otro de un paciente nuevo.
            for paciente in (self.paciente, paciente_ficticio(f'PRUEBA{i:04d}', eps=eps)):
                Informe.objects.create(
                    patologia=self.patologia,
                    autor=self.usuario,
                    eps=eps,
                    servicio=servicio,
                    paciente=paciente,
                )

    def contar(self, url):
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as consultas:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        return len(consultas)

    def test_las_consultas_no_crecen_con_los_informes(self):
        urls = ['/api/informes/', f'/api/pacientes/{self.paciente.id}/informes/']
        self.crear_informes(0, 3)
        con_3 = [self.contar(url) for url in urls]
        self.crear_informes(3, 10)
        self.assertEqual([self.contar(url) for url in urls], con_3)


class ContenidoInformeTests(APITestCase):
    """
    Informe v2, etapa 5 (docs/propuesta-informe-v2.md, secciones 3.4 y 3.6): el
    informe tiene descripción microscópica, comentarios (antes `notas`, P-5) y
    una lista de diagnósticos con código CIE-10 opcional. Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_contenido',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología contenido')
        self.paciente = paciente_ficticio()

    def crear(self, **extra):
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, 'datos_ingresados': {}, **extra}
        return self.client.post(self.URL, cuerpo, format='json')

    def url(self, informe_id):
        return f'{self.URL}{informe_id}/'

    def diagnosticos(self, informe_id):
        return [
            (d['descripcion'], d['codigo_cie10']) for d in self.client.get(self.url(informe_id)).data['diagnosticos']
        ]

    # --- Descripción microscópica y comentarios ---

    def test_guarda_y_devuelve_la_descripcion_microscopica(self):
        respuesta = self.crear(descripcion_microscopica='Proliferación de células basaloides en nidos.')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        detalle = self.client.get(self.url(respuesta.data['id'])).data
        self.assertEqual(detalle['descripcion_microscopica'], 'Proliferación de células basaloides en nidos.')

    def test_comentarios_reemplaza_a_notas(self):
        respuesta = self.crear(comentarios='Se sugiere correlación clínica.', notas='ignorado')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        detalle = self.client.get(self.url(respuesta.data['id'])).data
        self.assertEqual(detalle['comentarios'], 'Se sugiere correlación clínica.')
        self.assertNotIn('notas', detalle)

    # --- Diagnósticos ---

    def test_guarda_los_diagnosticos_en_el_orden_enviado(self):
        respuesta = self.crear(
            diagnosticos=[
                {'descripcion': 'Carcinoma basocelular nodular', 'codigo_cie10': 'C44.3'},
                {'descripcion': 'Márgenes libres de lesión', 'codigo_cie10': ''},
            ]
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(
            self.diagnosticos(respuesta.data['id']),
            [
                ('Carcinoma basocelular nodular', 'C44.3'),
                ('Márgenes libres de lesión', ''),
            ],
        )

    def test_el_codigo_cie10_es_opcional(self):
        respuesta = self.crear(diagnosticos=[{'descripcion': 'Dermatitis crónica inespecífica'}])
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(self.diagnosticos(respuesta.data['id']), [('Dermatitis crónica inespecífica', '')])

    def test_un_informe_sin_diagnosticos_se_puede_guardar_como_borrador(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data['diagnosticos'], [])

    def test_put_reemplaza_la_lista_de_diagnosticos(self):
        informe_id = self.crear(
            diagnosticos=[
                {'descripcion': 'Primero', 'codigo_cie10': 'C44.3'},
                {'descripcion': 'Segundo'},
            ]
        ).data['id']
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {},
            'diagnosticos': [{'descripcion': 'Segundo'}, {'descripcion': 'Tercero', 'codigo_cie10': 'D22.5'}],
        }
        respuesta = self.client.put(self.url(informe_id), cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(self.diagnosticos(informe_id), [('Segundo', ''), ('Tercero', 'D22.5')])

    def test_patch_sin_diagnosticos_los_conserva(self):
        informe_id = self.crear(diagnosticos=[{'descripcion': 'Nevus intradérmico', 'codigo_cie10': 'D22.5'}]).data[
            'id'
        ]
        respuesta = self.client.patch(self.url(informe_id), {'comentarios': 'Revisado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(self.diagnosticos(informe_id), [('Nevus intradérmico', 'D22.5')])

    def test_una_lista_vacia_quita_todos_los_diagnosticos(self):
        informe_id = self.crear(diagnosticos=[{'descripcion': 'Nevus intradérmico'}]).data['id']
        respuesta = self.client.patch(self.url(informe_id), {'diagnosticos': []}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(self.diagnosticos(informe_id), [])

    def test_el_codigo_cie10_se_normaliza(self):
        respuesta = self.crear(
            diagnosticos=[
                {'descripcion': 'Sin punto', 'codigo_cie10': 'c443'},
                {'descripcion': 'Con espacios y minúsculas', 'codigo_cie10': ' d22.5 '},
                {'descripcion': 'Solo categoría', 'codigo_cie10': 'C50'},
                {'descripcion': 'Subcategoría de dos caracteres', 'codigo_cie10': 'M8090'},
            ]
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(
            [codigo for _, codigo in self.diagnosticos(respuesta.data['id'])], ['C44.3', 'D22.5', 'C50', 'M80.90']
        )

    def test_rechaza_un_codigo_cie10_invalido(self):
        for codigo in ['44.3', 'CC4', 'C4', 'C44.123', 'C44-3', 'Ñ44']:
            with self.subTest(codigo=codigo):
                respuesta = self.crear(diagnosticos=[{'descripcion': 'Diagnóstico', 'codigo_cie10': codigo}])
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('diagnosticos', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_un_diagnostico_sin_descripcion(self):
        for descripcion in ['', '   ']:
            with self.subTest(descripcion=descripcion):
                respuesta = self.crear(diagnosticos=[{'descripcion': descripcion, 'codigo_cie10': 'C44.3'}])
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('diagnosticos', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_maximo_20_diagnosticos(self):
        lista = [{'descripcion': f'Diagnóstico {i}'} for i in range(21)]
        respuesta = self.crear(diagnosticos=lista)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('diagnosticos', respuesta.data)
        self.assertEqual(self.crear(diagnosticos=lista[:20]).status_code, status.HTTP_201_CREATED)

    def test_un_error_no_borra_los_diagnosticos_anteriores(self):
        informe_id = self.crear(diagnosticos=[{'descripcion': 'Nevus intradérmico'}]).data['id']
        respuesta = self.client.patch(
            self.url(informe_id),
            {'diagnosticos': [{'descripcion': 'Otro', 'codigo_cie10': 'XYZ'}]},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.diagnosticos(informe_id), [('Nevus intradérmico', '')])

    def test_un_informe_finalizado_no_cambia_sus_diagnosticos(self):
        # Decisión D-3: tampoco se modifican los diagnósticos de un informe finalizado.
        informe_id = self.crear(diagnosticos=[{'descripcion': 'Nevus intradérmico'}]).data['id']
        Informe.objects.filter(id=informe_id).update(estado=Informe.Estado.FINALIZADO)
        respuesta = self.client.patch(self.url(informe_id), {'diagnosticos': []}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.diagnosticos(informe_id), [('Nevus intradérmico', '')])

    def test_el_detalle_no_hace_una_consulta_por_diagnostico(self):
        # Auditoría M-4: las consultas del detalle no crecen con los diagnósticos.
        from django.test.utils import CaptureQueriesContext

        uno = self.crear(diagnosticos=[{'descripcion': 'Uno'}]).data['id']
        diez = self.crear(diagnosticos=[{'descripcion': f'D{i}'} for i in range(10)]).data['id']

        def contar(informe_id):
            with CaptureQueriesContext(connection) as consultas:
                self.client.get(self.url(informe_id))
            return len(consultas)

        self.assertEqual(contar(diez), contar(uno))

    def test_el_pdf_muestra_microscopica_diagnosticos_y_comentarios_escapados(self):
        # Auditoría I-3 en los campos nuevos: el texto del usuario sale literal.
        from reportlab.platypus import Paragraph

        informe_id = self.crear(
            descripcion_microscopica='Células <b>atípicas',
            comentarios='<font size=40>ENORME</font>',
            diagnosticos=[{'descripcion': 'Carcinoma & <i>algo', 'codigo_cie10': 'C44.3'}],
        ).data['id']
        with mock.patch('informes.utils.Paragraph', wraps=Paragraph) as espia:
            respuesta = self.client.get(f'{self.url(informe_id)}pdf/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        textos = ' '.join(str(llamada.args[0]) for llamada in espia.call_args_list)
        self.assertIn('DESCRIPCIÓN MICROSCÓPICA', textos)
        self.assertIn('Células &lt;b&gt;atípicas', textos)
        self.assertIn('DIAGNÓSTICOS', textos)
        self.assertIn('1. Carcinoma &amp; &lt;i&gt;algo (CIE-10: C44.3)', textos)
        self.assertIn('COMENTARIOS', textos)
        self.assertIn('&lt;font size=40&gt;ENORME&lt;/font&gt;', textos)
        self.assertNotIn('NOTAS ADICIONALES', textos)


class MigracionContenidoTests(TransactionTestCase):
    """La migración de la etapa 5 conserva las notas de los informes como comentarios (P-5)."""

    ANTES = [('informes', '0008_datos_solicitud'), ('accounts', '0001_initial')]

    def test_las_notas_pasan_a_comentarios(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.ANTES)
        modelos = executor.loader.project_state(self.ANTES).apps
        autor = modelos.get_model('accounts', 'Usuario').objects.create(username='autor_migracion_notas')
        patologia = modelos.get_model('informes', 'Patologia').objects.create(nombre='Patología notas')
        informe = modelos.get_model('informes', 'Informe').objects.create(
            numero_peticion='P-2026-09999',
            patologia=patologia,
            autor=autor,
            notas='Nota que debe conservarse',
        )

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

        self.assertEqual(Informe.objects.get(id=informe.id).comentarios, 'Nota que debe conservarse')


class FinalizacionTests(APITestCase):
    """
    Informe v2, etapa 6 (docs/propuesta-informe-v2.md, 3.7 y 3.9; decisiones D-8 y D-10):
    - para finalizar, el informe tiene paciente y al menos un diagnóstico, el autor
      tiene registro médico y, en histología, hay descripción microscópica;
    - al finalizar se fija la fecha de informe y se congelan los datos que imprime;
    - la firma es siempre la del autor, aunque finalice un admin.
    Solo datos ficticios.
    """

    URL = '/api/informes/'
    SIN_PACIENTE = 'El informe no tiene paciente.'
    SIN_DIAGNOSTICO = 'El informe debe tener al menos un diagnóstico.'
    SIN_MICROSCOPICA = 'En un estudio de histología, la descripción microscópica es obligatoria.'
    SIN_REGISTRO = 'El patólogo autor no tiene registro médico; un administrador debe registrarlo.'

    def setUp(self):
        self.autor = Usuario.objects.create_user(
            username='patologo_firma',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            nombre_completo='Dra. Ficticia Firma',
            especialidad='Patología Quirúrgica',
            registro_medico='RM-PRUEBA-0001',
        )
        self.admin = Usuario.objects.create_user(
            username='admin_firma',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.ADMIN,
            nombre_completo='Admin Ficticio',
            registro_medico='RM-PRUEBA-9999',
        )
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Patología firma')
        self.eps = EPS.objects.create(nombre='EPS Ficticia')
        self.servicio = Servicio.objects.create(nombre='Dermatología')
        self.paciente = paciente_ficticio(eps=self.eps)

    def crear(self, **extra):
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {},
            'fecha_ingreso': '2026-10-01',
            'servicio': self.servicio.id,
            'descripcion_microscopica': 'Proliferación de células basaloides.',
            'diagnosticos': [{'descripcion': 'Carcinoma basocelular nodular', 'codigo_cie10': 'C44.3'}],
            **extra,
        }
        respuesta = self.client.post(self.URL, cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        return respuesta.data['id']

    def finalizar(self, informe_id):
        return self.client.post(f'{self.URL}{informe_id}/finalizar/')

    def detalle(self, informe_id):
        return self.client.get(f'{self.URL}{informe_id}/').data

    def assertNoFinaliza(self, informe_id, requisito):
        respuesta = self.finalizar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(requisito, respuesta.data['requisitos'])
        self.assertIn(requisito, respuesta.data['detail'])
        informe = Informe.objects.get(id=informe_id)
        self.assertEqual(informe.estado, Informe.Estado.BORRADOR)
        self.assertIsNone(informe.fecha_informe)
        self.assertIsNone(informe.datos_finalizacion)

    # --- Requisitos para finalizar (D-8) ---

    def test_finaliza_un_informe_completo(self):
        informe_id = self.crear()
        respuesta = self.finalizar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data['estado'], Informe.Estado.FINALIZADO)

    def test_no_finaliza_sin_diagnosticos(self):
        self.assertNoFinaliza(self.crear(diagnosticos=[]), self.SIN_DIAGNOSTICO)

    def test_no_finaliza_si_el_autor_no_tiene_registro_medico(self):
        self.autor.registro_medico = ''
        self.autor.save()
        self.assertNoFinaliza(self.crear(), self.SIN_REGISTRO)

    def test_no_finaliza_un_informe_antiguo_sin_paciente(self):
        antiguo = Informe.objects.create(
            patologia=self.patologia,
            autor=self.autor,
            descripcion_microscopica='Hallazgos.',
        )
        Diagnostico.objects.create(informe=antiguo, orden=1, descripcion='Diagnóstico')
        self.assertNoFinaliza(antiguo.id, self.SIN_PACIENTE)

    def test_histologia_exige_descripcion_microscopica(self):
        for vacia in ['', '   ']:
            with self.subTest(microscopica=vacia):
                self.assertNoFinaliza(self.crear(descripcion_microscopica=vacia), self.SIN_MICROSCOPICA)

    def test_otros_tipos_de_estudio_no_exigen_descripcion_microscopica(self):
        informe_id = self.crear(tipo_estudio='citologia_no_ginecologica', descripcion_microscopica='')
        self.assertEqual(self.finalizar(informe_id).status_code, status.HTTP_200_OK)

    def test_informa_todos_los_requisitos_que_faltan_a_la_vez(self):
        self.autor.registro_medico = ''
        self.autor.save()
        informe_id = self.crear(diagnosticos=[], descripcion_microscopica='')
        respuesta = self.finalizar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data['requisitos'], [self.SIN_DIAGNOSTICO, self.SIN_MICROSCOPICA, self.SIN_REGISTRO])

    def test_el_registro_que_cuenta_es_el_del_autor_aunque_finalice_un_admin(self):
        self.autor.registro_medico = ''
        self.autor.save()
        informe_id = self.crear()
        self.client.force_authenticate(self.admin)  # el admin sí tiene registro médico
        self.assertNoFinaliza(informe_id, self.SIN_REGISTRO)

    def test_un_borrador_incompleto_se_puede_guardar(self):
        # D-8: los requisitos son para finalizar, no para guardar el borrador.
        informe_id = self.crear(diagnosticos=[], descripcion_microscopica='')
        respuesta = self.client.patch(f'{self.URL}{informe_id}/', {'comentarios': 'A medias'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)

    # --- Fecha de informe ---

    def test_al_finalizar_se_fija_la_fecha_de_informe(self):
        informe_id = self.crear()
        self.assertIsNone(self.detalle(informe_id)['fecha_informe'])
        momento = timezone.make_aware(datetime(2026, 10, 4, 15, 30))
        with mock.patch('django.utils.timezone.now', return_value=momento):
            respuesta = self.finalizar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(Informe.objects.get(id=informe_id).fecha_informe, momento)
        self.assertIsNotNone(self.detalle(informe_id)['fecha_informe'])

    def test_la_fecha_de_informe_y_los_datos_congelados_no_se_escriben_por_la_api(self):
        informe_id = self.crear(fecha_informe='2020-01-01T00:00:00Z', datos_finalizacion={'falso': True})
        informe = Informe.objects.get(id=informe_id)
        self.assertIsNone(informe.fecha_informe)
        self.assertIsNone(informe.datos_finalizacion)
        self.client.patch(f'{self.URL}{informe_id}/', {'fecha_informe': '2020-01-01T00:00:00Z'}, format='json')
        self.assertIsNone(Informe.objects.get(id=informe_id).fecha_informe)

    # --- Firma ---

    def test_el_borrador_muestra_la_firma_actual_del_autor(self):
        informe_id = self.crear()
        self.assertEqual(
            self.detalle(informe_id)['firma'],
            {
                'nombre': 'Dra. Ficticia Firma',
                'especialidad': 'Patología Quirúrgica',
                'registro_medico': 'RM-PRUEBA-0001',
            },
        )

    def test_la_firma_es_la_del_autor_aunque_finalice_un_admin(self):
        informe_id = self.crear()
        self.client.force_authenticate(self.admin)
        respuesta = self.finalizar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data['firma']['registro_medico'], 'RM-PRUEBA-0001')
        self.assertEqual(respuesta.data['firma']['nombre'], 'Dra. Ficticia Firma')

    # --- Datos congelados (D-10) ---

    def test_corregir_paciente_eps_servicio_o_autor_no_cambia_un_informe_finalizado(self):
        informe_id = self.crear()
        self.assertEqual(self.finalizar(informe_id).status_code, status.HTTP_200_OK)
        antes = self.detalle(informe_id)

        Paciente.objects.filter(id=self.paciente.id).update(
            nombres='Otro Nombre',
            apellidos='Corregido',
            numero_documento='PRUEBA0099',
            tipo_documento='TI',
            sexo='masculino',
            fecha_nacimiento=date(1990, 1, 1),
        )
        EPS.objects.filter(id=self.eps.id).update(nombre='EPS Renombrada')
        Servicio.objects.filter(id=self.servicio.id).update(nombre='Servicio Renombrado')
        Usuario.objects.filter(id=self.autor.id).update(
            nombre_completo='Nombre Cambiado',
            especialidad='Otra',
            registro_medico='RM-PRUEBA-0002',
        )

        despues = self.detalle(informe_id)
        for campo in ['paciente_datos', 'eps_nombre', 'servicio_nombre', 'firma']:
            with self.subTest(campo=campo):
                self.assertEqual(despues[campo], antes[campo])
        self.assertEqual(despues['paciente_datos']['nombre_completo'], 'Paciente Ficticio Uno')
        self.assertEqual(despues['paciente_datos']['edad'], '45 años')  # nació el 5/10/1980, ingresó el 1/10/2026
        self.assertEqual(despues['eps_nombre'], 'EPS Ficticia')
        self.assertEqual(despues['firma']['registro_medico'], 'RM-PRUEBA-0001')

    def test_en_un_borrador_los_datos_siguen_siendo_los_actuales(self):
        informe_id = self.crear()
        EPS.objects.filter(id=self.eps.id).update(nombre='EPS Renombrada')
        Usuario.objects.filter(id=self.autor.id).update(registro_medico='RM-PRUEBA-0002')
        detalle = self.detalle(informe_id)
        self.assertEqual(detalle['eps_nombre'], 'EPS Renombrada')
        self.assertEqual(detalle['firma']['registro_medico'], 'RM-PRUEBA-0002')

    # La firma y la fecha de informe en el PDF las comprueba PdfInformeTests (etapa 7).

    def test_no_se_puede_finalizar_dos_veces(self):
        informe_id = self.crear()
        self.assertEqual(self.finalizar(informe_id).status_code, status.HTTP_200_OK)
        fecha = Informe.objects.get(id=informe_id).fecha_informe
        self.assertEqual(self.finalizar(informe_id).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Informe.objects.get(id=informe_id).fecha_informe, fecha)


class MigracionFinalizacionTests(TransactionTestCase):
    """
    La migración de la etapa 6 completa los informes que ya estaban finalizados:
    fecha_informe toma la fecha de la última modificación (la mejor aproximación
    disponible) y datos_finalizacion se llena con los datos actuales.
    """

    ANTES = [('informes', '0009_contenido'), ('accounts', '0001_initial')]

    def test_completa_los_informes_ya_finalizados(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.ANTES)
        modelos = executor.loader.project_state(self.ANTES).apps
        autor = modelos.get_model('accounts', 'Usuario').objects.create(
            username='autor_migracion_firma',
            nombre_completo='Dr. Ficticio Migración',
        )
        patologia = modelos.get_model('informes', 'Patologia').objects.create(nombre='Patología migración firma')
        eps = modelos.get_model('pacientes', 'EPS').objects.create(nombre='EPS Migración')
        paciente = modelos.get_model('pacientes', 'Paciente').objects.create(
            tipo_documento='CC',
            numero_documento='PRUEBA0500',
            nombres='Paciente Ficticio',
            apellidos='Migración',
            fecha_nacimiento=date(1970, 1, 1),
            sexo='femenino',
        )
        InformeAntes = modelos.get_model('informes', 'Informe')
        finalizado = InformeAntes.objects.create(
            numero_peticion='P-2026-09990',
            patologia=patologia,
            autor=autor,
            paciente=paciente,
            eps=eps,
            fecha_ingreso=date(2026, 9, 1),
            estado='finalizado',
        )
        borrador = InformeAntes.objects.create(
            numero_peticion='P-2026-09991',
            patologia=patologia,
            autor=autor,
            paciente=paciente,
        )
        sin_paciente = InformeAntes.objects.create(
            numero_peticion='P-2026-09992',
            patologia=patologia,
            autor=autor,
            estado='finalizado',
        )
        actualizado = InformeAntes.objects.get(id=finalizado.id).fecha_actualizacion

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

        finalizado = Informe.objects.get(id=finalizado.id)
        self.assertEqual(finalizado.fecha_informe, actualizado)
        self.assertEqual(finalizado.datos_finalizacion['paciente']['nombre_completo'], 'Paciente Ficticio Migración')
        self.assertEqual(finalizado.datos_finalizacion['eps_nombre'], 'EPS Migración')
        self.assertEqual(finalizado.datos_finalizacion['firma']['nombre'], 'Dr. Ficticio Migración')
        borrador = Informe.objects.get(id=borrador.id)
        self.assertIsNone(borrador.fecha_informe)
        self.assertIsNone(borrador.datos_finalizacion)
        self.assertIsNone(Informe.objects.get(id=sin_paciente.id).datos_finalizacion['paciente'])


class MigracionEncabezadoCongeladoTests(TransactionTestCase):
    """
    Decisión D-15: la migración 0012 agrega el encabezado de demostración a los
    informes que ya estaban finalizados, porque es el único que existía cuando se
    imprimieron. No toca los borradores ni los que ya tienen encabezado congelado.
    """

    ANTES = [('informes', '0011_adenda')]
    DESPUES = [('informes', '0012_encabezado_congelado')]
    DEMOSTRACION = {
        'nombre': 'PathoLab — Laboratorio de Patología (demostración)',
        'direccion': 'Santiago de Cali, Colombia',
        'telefono': '',
    }

    def crear_informes(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.ANTES)
        modelos = executor.loader.project_state(self.ANTES).apps
        autor = modelos.get_model('accounts', 'Usuario').objects.create(username='autor_migracion_encabezado')
        patologia = modelos.get_model('informes', 'Patologia').objects.create(nombre='Patología migración encabezado')
        Informe0011 = modelos.get_model('informes', 'Informe')
        congelado = {
            'paciente': None,
            'eps_nombre': None,
            'servicio_nombre': None,
            'firma': {'nombre': 'Dr. Ficticio', 'especialidad': '', 'registro_medico': 'RM-PRUEBA-0009'},
        }
        otro = {'nombre': 'Laboratorio Ficticio Ya Congelado', 'direccion': 'Calle 9', 'telefono': ''}
        ids = {
            'finalizado': Informe0011.objects.create(
                numero_peticion='P-2026-09980',
                patologia=patologia,
                autor=autor,
                estado='finalizado',
                datos_finalizacion=congelado,
            ).id,
            'borrador': Informe0011.objects.create(
                numero_peticion='P-2026-09981',
                patologia=patologia,
                autor=autor,
            ).id,
            'ya_congelado': Informe0011.objects.create(
                numero_peticion='P-2026-09982',
                patologia=patologia,
                autor=autor,
                estado='finalizado',
                datos_finalizacion={**congelado, 'laboratorio': otro},
            ).id,
        }
        return ids, otro

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    # Se lee solo datos_finalizacion: en la 0012 todavía no existen las columnas que el
    # modelo actual agregó después (p. ej. las de la 0015, tarea 1). Ajuste autorizado
    # por el usuario el 2026-11-12; lo que se comprueba no cambia.
    def test_completa_los_finalizados_con_el_encabezado_de_demostracion(self):
        ids, otro = self.crear_informes()
        self.migrar(self.DESPUES)
        finalizado = Informe.objects.only('datos_finalizacion').get(id=ids['finalizado'])
        self.assertEqual(finalizado.datos_finalizacion['laboratorio'], self.DEMOSTRACION)
        self.assertEqual(finalizado.datos_finalizacion['firma']['registro_medico'], 'RM-PRUEBA-0009')
        self.assertIsNone(Informe.objects.only('datos_finalizacion').get(id=ids['borrador']).datos_finalizacion)
        self.assertEqual(
            Informe.objects.only('datos_finalizacion').get(id=ids['ya_congelado']).datos_finalizacion['laboratorio'],
            otro,
        )

    def test_la_reversa_quita_el_encabezado_agregado(self):
        ids, otro = self.crear_informes()
        self.migrar(self.DESPUES)
        self.migrar(self.ANTES)
        self.assertNotIn(
            'laboratorio', Informe.objects.only('datos_finalizacion').get(id=ids['finalizado']).datos_finalizacion
        )


class PdfInformeTests(APITestCase):
    """
    Informe v2, etapa 7 (docs/propuesta-informe-v2.md, sección 5): el PDF tiene la
    estructura del informe real. Encabezado del laboratorio desde la configuración,
    tabla de datos en dos columnas, título, tipo de estudio, secciones en orden,
    firma, "BORRADOR — SIN VALIDEZ" en los borradores y pie con "Página X de Y" en
    cada página. Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        self.autor = Usuario.objects.create_user(
            username='patologo_pdf_v2',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            nombre_completo='Dra. Ficticia Firma',
            especialidad='Patología Quirúrgica',
            registro_medico='RM-PRUEBA-0001',
        )
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Patología PDF v2')
        self.eps = EPS.objects.create(nombre='EPS Ficticia')
        self.servicio = Servicio.objects.create(nombre='Dermatología')
        self.paciente = paciente_ficticio(eps=self.eps)

    def crear(self, **extra):
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {'localizacion': 'dorso de la mano'},
            'fecha_ingreso': '2026-10-01',
            'servicio': self.servicio.id,
            'medico_tratante': 'Médico Ficticio',
            'estudios_solicitados': 'Biopsia de piel',
            'tipo_muestra': 'Biopsia por raspado',
            'descripcion_microscopica': 'Proliferación de células basaloides.',
            'diagnosticos': [{'descripcion': 'Carcinoma basocelular nodular', 'codigo_cie10': 'C44.3'}],
            'comentarios': 'Se sugiere control.',
            **extra,
        }
        respuesta = self.client.post(self.URL, cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        return respuesta.data['id']

    def finalizar(self, informe_id):
        momento = timezone.make_aware(datetime(2026, 10, 4, 15, 30))
        with mock.patch('django.utils.timezone.now', return_value=momento):
            respuesta = self.client.post(f'{self.URL}{informe_id}/finalizar/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)

    def generar(self, informe_id):
        """
        Descarga el PDF y devuelve, en orden, los textos de los Paragraph, las filas
        de cada Table (el texto de cada celda) y lo que se dibuja centrado en el
        lienzo (el pie de página).
        """
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import Paragraph, Table

        with (
            mock.patch('informes.utils.Paragraph', wraps=Paragraph) as parrafos,
            mock.patch('informes.utils.Table', wraps=Table) as tablas,
            mock.patch.object(
                Canvas, 'drawCentredString', autospec=True, side_effect=Canvas.drawCentredString
            ) as centrados,
        ):
            respuesta = self.client.get(f'{self.URL}{informe_id}/pdf/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        return {
            'textos': [str(llamada.args[0]) for llamada in parrafos.call_args_list],
            'tablas': [
                [[getattr(celda, 'text', celda) for celda in fila] for fila in llamada.args[0]]
                for llamada in tablas.call_args_list
            ],
            'pies': [llamada.args[3] for llamada in centrados.call_args_list if 'Página' in llamada.args[3]],
            'pdf': respuesta.content,
        }

    def numero(self, informe_id):
        return Informe.objects.get(id=informe_id).numero_peticion

    # --- Tabla de datos ---

    def test_tabla_de_datos_en_dos_columnas(self):
        informe_id = self.crear(numero_orden_externa='OE-PRUEBA-1')
        self.finalizar(informe_id)
        self.assertEqual(
            self.generar(informe_id)['tablas'][0],
            [
                ['<b>Paciente:</b> Paciente Ficticio Uno', '<b>Identificación:</b> CC PRUEBA0001'],
                ['<b>Edad:</b> 45 años', '<b>Sexo:</b> Femenino'],
                ['<b>Médico tratante:</b> Médico Ficticio', '<b>EPS:</b> EPS Ficticia'],
                ['<b>Servicio:</b> Dermatología', f'<b>N.º de petición:</b> {self.numero(informe_id)}'],
                ['<b>Fecha de ingreso:</b> 01/10/2026', '<b>Fecha de informe:</b> 04/10/2026 15:30'],
                ['<b>Orden externa:</b> OE-PRUEBA-1', ''],
                ['<b>Estudios solicitados:</b> Biopsia de piel', ''],
            ],
        )

    def test_sin_orden_externa_no_hay_fila_de_orden_externa(self):
        informe_id = self.crear()
        filas = self.generar(informe_id)['tablas'][0]
        self.assertFalse(any('Orden externa' in celda for fila in filas for celda in fila))

    def test_un_informe_finalizado_imprime_los_datos_congelados(self):
        # Decisión D-10: corregir después el paciente, la EPS o el autor no cambia el PDF.
        informe_id = self.crear()
        self.finalizar(informe_id)
        Paciente.objects.filter(id=self.paciente.id).update(nombres='Otro', apellidos='Nombre', sexo='masculino')
        EPS.objects.filter(id=self.eps.id).update(nombre='EPS Renombrada')
        Usuario.objects.filter(id=self.autor.id).update(nombre_completo='Nombre Cambiado', registro_medico='RM-OTRO')
        pdf = self.generar(informe_id)
        filas = pdf['tablas'][0]
        self.assertEqual(filas[0][0], '<b>Paciente:</b> Paciente Ficticio Uno')
        self.assertEqual(filas[1][1], '<b>Sexo:</b> Femenino')
        self.assertEqual(filas[2][1], '<b>EPS:</b> EPS Ficticia')
        self.assertIn('Dra. Ficticia Firma', pdf['textos'])
        self.assertIn('Registro médico N.º RM-PRUEBA-0001', pdf['textos'])
        self.assertNotIn('Nombre Cambiado', ' '.join(pdf['textos']))

    def test_el_texto_del_usuario_en_la_tabla_sale_escapado(self):
        # Auditoría I-3 en los campos nuevos del PDF.
        paciente = paciente_ficticio(numero='PRUEBA0002', apellidos='<b>Dos')
        informe_id = self.crear(
            paciente=paciente.id,
            medico_tratante='<font size=40>Ficticio',
            estudios_solicitados='A & B',
        )
        filas = self.generar(informe_id)['tablas'][0]
        self.assertEqual(filas[0][0], '<b>Paciente:</b> Paciente Ficticio &lt;b&gt;Dos')
        self.assertEqual(filas[2][0], '<b>Médico tratante:</b> &lt;font size=40&gt;Ficticio')
        self.assertEqual(filas[-1][0], '<b>Estudios solicitados:</b> A &amp; B')

    def test_un_informe_antiguo_sin_paciente_tambien_genera_el_pdf(self):
        antiguo = Informe.objects.create(patologia=self.patologia, autor=self.autor)
        filas = self.generar(antiguo.id)['tablas'][0]
        self.assertEqual(filas[0][0], '<b>Paciente:</b> —')
        self.assertEqual(filas[1], ['<b>Edad:</b> —', '<b>Sexo:</b> —'])

    # --- Borrador ---

    def test_un_borrador_dice_sin_validez_y_no_lleva_firma(self):
        informe_id = self.crear()
        pdf = self.generar(informe_id)
        self.assertEqual(pdf['tablas'][0][4][1], '<b>Fecha de informe:</b> BORRADOR — SIN VALIDEZ')
        self.assertFalse(any('Registro médico' in texto for texto in pdf['textos']))
        self.assertNotIn('Dra. Ficticia Firma', pdf['textos'])

    # --- Orden y contenido ---

    def test_las_partes_salen_en_el_orden_del_informe_real(self):
        informe_id = self.crear()
        self.finalizar(informe_id)
        textos = self.generar(informe_id)['textos']
        orden = [
            'PathoLab — Laboratorio de Patología (demostración)',
            '<b>Paciente:</b> Paciente Ficticio Uno',
            'INFORME DE ANATOMÍA PATOLÓGICA',
            '<b>Tipo de estudio:</b> Histología',
            'Patología: Patología PDF v2 · Tipo de muestra: Biopsia por raspado',
            'DESCRIPCIÓN MACROSCÓPICA',
            'DESCRIPCIÓN MICROSCÓPICA',
            'DIAGNÓSTICOS',
            '1. Carcinoma basocelular nodular (CIE-10: C44.3)',
            'COMENTARIOS',
            'Dra. Ficticia Firma',
            'Patología Quirúrgica',
            'Registro médico N.º RM-PRUEBA-0001',
        ]
        posiciones = [textos.index(texto) for texto in orden]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_ya_no_imprime_la_seccion_datos_clinicos(self):
        # Sección 5.2: los datos del formulario ya están redactados en la macroscópica.
        textos = self.generar(self.crear())['textos']
        self.assertNotIn('DATOS CLÍNICOS', textos)
        self.assertNotIn('INFORME DE PATOLOGÍA CLÍNICA', textos)

    # --- Encabezado ---

    def test_el_encabezado_es_el_de_demostracion_sin_telefono(self):
        # Respuesta P-9: sin datos de un laboratorio real. Son los valores por defecto
        # de settings.py cuando backend/.env no define LABORATORIO_* (tarea previa 2).
        textos = self.generar(self.crear())['textos']
        self.assertEqual(
            textos[:2], ['PathoLab — Laboratorio de Patología (demostración)', 'Santiago de Cali, Colombia']
        )
        self.assertFalse(any('Teléfono' in texto for texto in textos))

    @override_settings(
        LABORATORIO_NOMBRE='Laboratorio Ficticio de Prueba',
        LABORATORIO_DIRECCION='Calle Falsa 123, Ciudad Ficticia',
        LABORATORIO_TELEFONO='000 000 0000',
    )
    def test_el_encabezado_sale_de_la_configuracion_con_telefono_en_otra_linea(self):
        textos = self.generar(self.crear())['textos']
        self.assertEqual(
            textos[:3],
            [
                'Laboratorio Ficticio de Prueba',
                'Calle Falsa 123, Ciudad Ficticia',
                'Teléfono: 000 000 0000',
            ],
        )

    @override_settings(LABORATORIO_NOMBRE='Laboratorio Ficticio de Prueba', LABORATORIO_TELEFONO='')
    def test_sin_telefono_no_hay_linea_de_telefono(self):
        textos = self.generar(self.crear())['textos']
        self.assertEqual(textos[0], 'Laboratorio Ficticio de Prueba')
        self.assertFalse(any('Teléfono' in texto for texto in textos))

    # Decisión D-15: el encabezado se congela al finalizar, como los datos de D-10.
    LABORATORIO_A = {
        'LABORATORIO_NOMBRE': 'Laboratorio Ficticio A',
        'LABORATORIO_DIRECCION': 'Calle A 1, Ciudad A',
        'LABORATORIO_TELEFONO': '111 111 1111',
    }
    LABORATORIO_B = {
        'LABORATORIO_NOMBRE': 'Laboratorio Ficticio B',
        'LABORATORIO_DIRECCION': 'Calle B 2, Ciudad B',
        'LABORATORIO_TELEFONO': '',
    }

    def test_al_finalizar_se_congela_el_encabezado(self):
        with override_settings(**self.LABORATORIO_A):
            informe_id = self.crear()
            self.finalizar(informe_id)
        self.assertEqual(
            Informe.objects.get(id=informe_id).datos_finalizacion['laboratorio'],
            {
                'nombre': 'Laboratorio Ficticio A',
                'direccion': 'Calle A 1, Ciudad A',
                'telefono': '111 111 1111',
            },
        )

    def test_un_finalizado_conserva_el_encabezado_aunque_cambie_la_configuracion(self):
        with override_settings(**self.LABORATORIO_A):
            informe_id = self.crear()
            self.finalizar(informe_id)
        with override_settings(**self.LABORATORIO_B):
            textos = self.generar(informe_id)['textos']
        self.assertEqual(textos[:3], ['Laboratorio Ficticio A', 'Calle A 1, Ciudad A', 'Teléfono: 111 111 1111'])

    def test_un_borrador_usa_el_encabezado_actual(self):
        with override_settings(**self.LABORATORIO_A):
            informe_id = self.crear()
        with override_settings(**self.LABORATORIO_B):
            textos = self.generar(informe_id)['textos']
        self.assertEqual(textos[:2], ['Laboratorio Ficticio B', 'Calle B 2, Ciudad B'])
        self.assertFalse(any('Teléfono' in texto for texto in textos))

    def test_una_adenda_no_cambia_el_encabezado_congelado(self):
        # D-9: la adenda no modifica el informe, tampoco su encabezado.
        with override_settings(**self.LABORATORIO_A):
            informe_id = self.crear()
            self.finalizar(informe_id)
        with override_settings(**self.LABORATORIO_B):
            self.agregar_adenda(informe_id, timezone.make_aware(datetime(2026, 10, 5, 9, 15)))
            textos = self.generar(informe_id)['textos']
        self.assertEqual(textos[0], 'Laboratorio Ficticio A')
        self.assertIn('ADENDAS', textos)

    @override_settings(
        LABORATORIO_NOMBRE='<b>Lab</b> & Cía',
        LABORATORIO_DIRECCION='Calle <font size=40>1',
        LABORATORIO_TELEFONO='<i>000</i>',
    )
    def test_el_encabezado_sale_escapado(self):
        # Auditoría I-3: ReportLab interpreta etiquetas; un & o un < del .env no debe
        # romper el PDF ni cambiar su formato.
        textos = self.generar(self.crear())['textos']
        self.assertEqual(
            textos[:3],
            [
                '&lt;b&gt;Lab&lt;/b&gt; &amp; Cía',
                'Calle &lt;font size=40&gt;1',
                'Teléfono: &lt;i&gt;000&lt;/i&gt;',
            ],
        )

    # --- Pie de página ---

    def paginas_y_pies(self, informe_id):
        """Genera el PDF a una hora fija y devuelve el número de páginas y los pies."""
        import re

        ahora_utc = datetime(2026, 10, 4, 3, 30, tzinfo=dt_timezone.utc)  # en Bogotá: 3 de octubre, 22:30 (M-10)
        with mock.patch('django.utils.timezone.now', return_value=ahora_utc):
            pdf = self.generar(informe_id)
        return len(re.findall(rb'/Type /Page\b(?!s)', pdf['pdf'])), pdf['pies']

    def test_cada_pagina_lleva_numero_de_peticion_pagina_x_de_y_y_hora_de_bogota(self):
        informe_id = self.crear(descripcion_microscopica='Párrafo largo de prueba. ' * 1500)
        self.finalizar(informe_id)
        paginas, pies = self.paginas_y_pies(informe_id)
        self.assertGreaterEqual(paginas, 2)
        self.assertEqual(
            pies,
            [
                f'N.º de petición {self.numero(informe_id)} · Página {n} de {paginas} · Generado el 03/10/2026 22:30'
                for n in range(1, paginas + 1)
            ],
        )

    def test_en_un_borrador_el_pie_de_cada_pagina_dice_sin_validez(self):
        # Así una hoja suelta de un borrador no parece definitiva.
        informe_id = self.crear(descripcion_microscopica='Párrafo largo de prueba. ' * 1500)
        paginas, pies = self.paginas_y_pies(informe_id)
        self.assertGreaterEqual(paginas, 2)
        self.assertEqual(
            pies,
            [
                f'BORRADOR — SIN VALIDEZ · N.º de petición {self.numero(informe_id)} · Página {n} de {paginas}'
                ' · Generado el 03/10/2026 22:30'
                for n in range(1, paginas + 1)
            ],
        )

    # --- Adendas (informe v2, etapa 8) ---

    def agregar_adenda(self, informe_id, momento, **extra):
        cuerpo = {'motivo': 'Corrección del diagnóstico', 'texto': 'Se aclara el diagnóstico.', **extra}
        with mock.patch('django.utils.timezone.now', return_value=momento):
            respuesta = self.client.post(f'{self.URL}{informe_id}/adendas/', cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)

    def test_las_adendas_van_al_final_con_un_aviso_al_principio(self):
        # Sección 3.8: el aviso evita que se lea el diagnóstico original sin saber que se corrigió.
        informe_id = self.crear()
        self.finalizar(informe_id)
        self.agregar_adenda(informe_id, timezone.make_aware(datetime(2026, 10, 5, 9, 15)))
        self.agregar_adenda(
            informe_id,
            timezone.make_aware(datetime(2026, 10, 6, 11, 0)),
            motivo='Resultado de inmunohistoquímica',
            texto='CK5/6 positivo.',
        )
        textos = self.generar(informe_id)['textos']
        orden = [
            'INFORME DE ANATOMÍA PATOLÓGICA',
            'Este informe tiene 2 adendas; ver al final.',
            'DESCRIPCIÓN MACROSCÓPICA',
            'DIAGNÓSTICOS',
            'Registro médico N.º RM-PRUEBA-0001',  # firma del informe
            'ADENDAS',
            'Adenda N.º 1 — 05/10/2026 09:15',
            '<b>Motivo:</b> Corrección del diagnóstico',
            'Se aclara el diagnóstico.',
            'Adenda N.º 2 — 06/10/2026 11:00',
            '<b>Motivo:</b> Resultado de inmunohistoquímica',
            'CK5/6 positivo.',
        ]
        posiciones = [textos.index(texto) for texto in orden]
        self.assertEqual(posiciones, sorted(posiciones))
        # Cada adenda lleva su firma: la del informe y una por adenda.
        self.assertEqual(textos.count('Registro médico N.º RM-PRUEBA-0001'), 3)

    def test_con_una_sola_adenda_el_aviso_va_en_singular(self):
        informe_id = self.crear()
        self.finalizar(informe_id)
        self.agregar_adenda(informe_id, timezone.make_aware(datetime(2026, 10, 5, 9, 15)))
        self.assertIn('Este informe tiene 1 adenda; ver al final.', self.generar(informe_id)['textos'])

    def test_sin_adendas_no_hay_aviso_ni_seccion(self):
        informe_id = self.crear()
        self.finalizar(informe_id)
        textos = self.generar(informe_id)['textos']
        self.assertNotIn('ADENDAS', textos)
        self.assertFalse(any('adenda' in texto.lower() for texto in textos))

    def test_el_texto_de_las_adendas_sale_escapado(self):
        # Auditoría I-3 también en las adendas.
        informe_id = self.crear()
        self.finalizar(informe_id)
        self.agregar_adenda(
            informe_id,
            timezone.make_aware(datetime(2026, 10, 5, 9, 15)),
            motivo='<b>Motivo',
            texto='Línea 1 & <font size=40>\nLínea 2',
        )
        textos = self.generar(informe_id)['textos']
        self.assertIn('<b>Motivo:</b> &lt;b&gt;Motivo', textos)
        self.assertIn('Línea 1 &amp; &lt;font size=40&gt;<br/>Línea 2', textos)

    # --- Colores y títulos (Bloque B, punto 4) ---

    def dibujo(self, informe_id):
        """
        Genera el PDF y devuelve los colores que usa el lienzo (relleno y trazo, en
        hexadecimal), los Paragraph con su estilo y los HRFlowable con su grosor y color.
        """
        from reportlab.lib.colors import toColor
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import HRFlowable, Paragraph

        with (
            mock.patch.object(Canvas, 'setFillColor', autospec=True, side_effect=Canvas.setFillColor) as rellenos,
            mock.patch.object(Canvas, 'setStrokeColor', autospec=True, side_effect=Canvas.setStrokeColor) as trazos,
            mock.patch('informes.utils.Paragraph', wraps=Paragraph) as parrafos,
            mock.patch('informes.utils.HRFlowable', wraps=HRFlowable) as lineas,
        ):
            respuesta = self.client.get(f'{self.URL}{informe_id}/pdf/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        return {
            'colores': {
                toColor(llamada.args[1]).hexval() for llamada in rellenos.call_args_list + trazos.call_args_list
            },
            'parrafos': {str(llamada.args[0]): llamada.args[1] for llamada in parrafos.call_args_list},
            'lineas': [llamada.kwargs for llamada in lineas.call_args_list],
        }

    def test_el_pdf_solo_usa_negro_y_el_rojo_de_las_alertas(self):
        # El rojo queda solo en el aviso de adendas y en la marca de agua del borrador.
        finalizado = self.crear()
        self.finalizar(finalizado)
        self.agregar_adenda(finalizado, timezone.make_aware(datetime(2026, 10, 5, 9, 15)))
        borrador = self.crear()
        for informe_id in (finalizado, borrador):
            with self.subTest(informe_id=informe_id):
                self.assertLessEqual(self.dibujo(informe_id)['colores'], {'0x000000', '0xc53030'})

    def test_los_titulos_van_en_negrita_y_en_negro(self):
        from reportlab.lib.colors import black

        informe_id = self.crear()
        self.finalizar(informe_id)
        self.agregar_adenda(informe_id, timezone.make_aware(datetime(2026, 10, 5, 9, 15)))
        parrafos = self.dibujo(informe_id)['parrafos']
        from django.conf import settings

        for titulo in (
            settings.LABORATORIO_NOMBRE,
            'INFORME DE ANATOMÍA PATOLÓGICA',
            'DESCRIPCIÓN MACROSCÓPICA',
            'DIAGNÓSTICOS',
            'ADENDAS',
            'Adenda N.º 1 — 05/10/2026 09:15',
        ):
            with self.subTest(titulo=titulo):
                self.assertEqual(parrafos[titulo].fontName, 'Helvetica-Bold')
                self.assertEqual(parrafos[titulo].textColor, black)

    def test_el_encabezado_lleva_una_linea_fina_negra(self):
        from reportlab.lib.colors import black

        informe_id = self.crear()
        primera_linea = self.dibujo(informe_id)['lineas'][0]
        self.assertLessEqual(primera_linea['thickness'], 0.75)
        self.assertEqual(primera_linea['color'], black)


class AdendaTests(APITestCase):
    """
    Informe v2, etapa 8 (docs/propuesta-informe-v2.md, 3.8; decisión D-9):
    - un informe finalizado se corrige con adendas, que no lo modifican (D-3);
    - solo en informes finalizados; las crea el autor del informe o un admin (D-2);
    - quien la crea la firma y necesita registro médico; la firma queda congelada;
    - se numeran 1, 2, 3... dentro de cada informe;
    - no se editan ni se borran (ni por la API ni en /admin/).
    Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        def usuario(username, rol, **extra):
            return Usuario.objects.create_user(username=username, password='ClaveSegura-2026', rol=rol, **extra)

        self.autor = usuario(
            'patologo_adenda',
            Usuario.Rol.PATOLOGO,
            nombre_completo='Dra. Ficticia Firma',
            especialidad='Patología Quirúrgica',
            registro_medico='RM-PRUEBA-0001',
        )
        self.otro = usuario('otro_adenda', Usuario.Rol.PATOLOGO, registro_medico='RM-PRUEBA-0002')
        self.admin = usuario(
            'admin_adenda',
            Usuario.Rol.ADMIN,
            nombre_completo='Admin Ficticio',
            registro_medico='RM-PRUEBA-9999',
        )
        self.admin_sin_registro = usuario('admin_sin_rm', Usuario.Rol.ADMIN)
        self.auditor = usuario('auditor_adenda', Usuario.Rol.AUDITOR)
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Patología adendas')
        self.paciente = paciente_ficticio()

    def crear(self, finalizar=True):
        self.client.force_authenticate(self.autor)
        respuesta = self.client.post(
            self.URL,
            {
                'patologia': self.patologia.id,
                'paciente': self.paciente.id,
                'datos_ingresados': {},
                'descripcion_microscopica': 'Proliferación de células basaloides.',
                'diagnosticos': [{'descripcion': 'Carcinoma basocelular nodular', 'codigo_cie10': 'C44.3'}],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        informe_id = respuesta.data['id']
        if finalizar:
            respuesta = self.client.post(f'{self.URL}{informe_id}/finalizar/')
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        return informe_id

    def url(self, informe_id):
        return f'{self.URL}{informe_id}/adendas/'

    def agregar(self, informe_id, usuario=None, **extra):
        if usuario is not None:
            self.client.force_authenticate(usuario)
        cuerpo = {'motivo': 'Corrección del diagnóstico', 'texto': 'Se aclara el diagnóstico.', **extra}
        return self.client.post(self.url(informe_id), cuerpo, format='json')

    def total_adendas(self):
        from .models import Adenda

        return Adenda.objects.count()

    # --- Crear ---

    def test_el_autor_agrega_una_adenda_firmada_a_un_informe_finalizado(self):
        informe_id = self.crear()
        momento = timezone.make_aware(datetime(2026, 10, 5, 9, 15))
        with mock.patch('django.utils.timezone.now', return_value=momento):
            respuesta = self.agregar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data['numero'], 1)
        self.assertEqual(respuesta.data['motivo'], 'Corrección del diagnóstico')
        self.assertEqual(respuesta.data['texto'], 'Se aclara el diagnóstico.')
        self.assertEqual(respuesta.data['autor'], self.autor.id)
        self.assertEqual(datetime.fromisoformat(respuesta.data['fecha']), momento)
        self.assertEqual(
            respuesta.data['firma'],
            {
                'nombre': 'Dra. Ficticia Firma',
                'especialidad': 'Patología Quirúrgica',
                'registro_medico': 'RM-PRUEBA-0001',
            },
        )

    def test_un_borrador_no_admite_adendas(self):
        # Un borrador se corrige editándolo.
        informe_id = self.crear(finalizar=False)
        respuesta = self.agregar(informe_id)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrador', respuesta.data['detail'])
        self.assertEqual(self.total_adendas(), 0)

    def test_se_numeran_dentro_de_cada_informe(self):
        primero, segundo = self.crear(), self.crear()
        self.assertEqual(self.agregar(primero).data['numero'], 1)
        self.assertEqual(self.agregar(primero).data['numero'], 2)
        self.assertEqual(self.agregar(segundo).data['numero'], 1)
        self.assertEqual(self.agregar(primero).data['numero'], 3)

    def test_no_se_puede_elegir_el_numero_ni_la_firma(self):
        informe_id = self.crear()
        respuesta = self.agregar(informe_id, numero=99, autor=self.otro.id, firma={'nombre': 'Firma falsa'})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data['numero'], 1)
        self.assertEqual(respuesta.data['autor'], self.autor.id)
        self.assertEqual(respuesta.data['firma']['nombre'], 'Dra. Ficticia Firma')

    def test_motivo_y_texto_son_obligatorios(self):
        informe_id = self.crear()
        respuesta = self.agregar(informe_id, motivo='  ', texto='')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', respuesta.data)
        self.assertIn('texto', respuesta.data)
        self.assertEqual(self.total_adendas(), 0)

    def test_el_motivo_tiene_maximo_300_caracteres(self):
        informe_id = self.crear()
        respuesta = self.agregar(informe_id, motivo='x' * 301)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', respuesta.data)

    def test_agregar_una_adenda_no_modifica_el_informe(self):
        # Decisión D-3: el contenido original y los datos congelados no cambian.
        informe_id = self.crear()
        antes = Informe.objects.get(id=informe_id)
        self.assertEqual(self.agregar(informe_id).status_code, status.HTTP_201_CREATED)
        despues = Informe.objects.get(id=informe_id)
        self.assertEqual(despues.estado, Informe.Estado.FINALIZADO)
        self.assertEqual(despues.fecha_actualizacion, antes.fecha_actualizacion)
        self.assertEqual(despues.fecha_informe, antes.fecha_informe)
        self.assertEqual(despues.datos_finalizacion, antes.datos_finalizacion)

    # --- Permisos (D-2) y firma ---

    def test_un_admin_agrega_una_adenda_con_su_propia_firma(self):
        informe_id = self.crear()
        respuesta = self.agregar(informe_id, usuario=self.admin)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(respuesta.data['autor'], self.admin.id)
        self.assertEqual(respuesta.data['firma']['nombre'], 'Admin Ficticio')
        self.assertEqual(respuesta.data['firma']['registro_medico'], 'RM-PRUEBA-9999')

    def test_otro_patologo_no_puede_agregar_adendas(self):
        informe_id = self.crear()
        self.assertEqual(self.agregar(informe_id, usuario=self.otro).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.total_adendas(), 0)

    def test_el_auditor_ve_las_adendas_pero_no_las_crea(self):
        informe_id = self.crear()
        self.agregar(informe_id)
        self.assertEqual(self.agregar(informe_id, usuario=self.auditor).status_code, status.HTTP_403_FORBIDDEN)
        respuesta = self.client.get(self.url(informe_id))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual([a['numero'] for a in respuesta.data], [1])

    def test_quien_no_tiene_registro_medico_no_puede_firmar_una_adenda(self):
        informe_id = self.crear()
        respuesta = self.agregar(informe_id, usuario=self.admin_sin_registro)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registro médico', respuesta.data['detail'])
        self.assertEqual(self.total_adendas(), 0)

    def test_la_firma_de_la_adenda_queda_congelada(self):
        informe_id = self.crear()
        self.agregar(informe_id)
        Usuario.objects.filter(id=self.autor.id).update(nombre_completo='Nombre Cambiado', registro_medico='RM-OTRO')
        firma = self.client.get(self.url(informe_id)).data[0]['firma']
        self.assertEqual(firma['nombre'], 'Dra. Ficticia Firma')
        self.assertEqual(firma['registro_medico'], 'RM-PRUEBA-0001')

    # --- No se modifican ---

    def test_las_adendas_no_se_editan_ni_se_borran_por_la_api(self):
        informe_id = self.crear()
        self.agregar(informe_id)
        self.client.force_authenticate(self.admin)
        for metodo in (self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(
                metodo(self.url(informe_id), {'texto': 'Cambiado'}, format='json').status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        self.assertEqual(self.client.get(self.url(informe_id)).data[0]['texto'], 'Se aclara el diagnóstico.')

    def test_el_numero_no_se_repite_en_la_base_de_datos(self):
        # Respaldo del bloqueo con select_for_update (sección 3.8).
        from .models import Adenda

        informe = Informe.objects.get(id=self.crear())
        datos = {'informe': informe, 'numero': 1, 'motivo': 'M', 'texto': 'T', 'autor': self.autor, 'firma': {}}
        Adenda.objects.create(**datos)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Adenda.objects.create(**datos)

    def test_un_informe_con_adendas_no_se_borra_desde_el_orm(self):
        from django.db.models import ProtectedError

        informe_id = self.crear()
        self.agregar(informe_id)
        with self.assertRaises(ProtectedError):
            Informe.objects.get(id=informe_id).delete()

    def test_en_admin_las_adendas_son_de_solo_lectura(self):
        from django.contrib import admin as admin_django
        from django.test import RequestFactory

        from .models import Adenda

        modelo_admin = admin_django.site._registry[Informe]
        peticion = RequestFactory().get('/admin/')
        peticion.user = Usuario.objects.create_superuser(
            username='super_adenda',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.ADMIN,
        )
        informe = Informe.objects.get(id=self.crear())
        inlines = [i for i in modelo_admin.get_inline_instances(peticion, informe) if i.model is Adenda]
        self.assertEqual(len(inlines), 1)
        self.assertFalse(inlines[0].has_add_permission(peticion, informe))
        self.assertFalse(inlines[0].has_change_permission(peticion, informe))
        self.assertFalse(inlines[0].has_delete_permission(peticion, informe))

    # --- Detalle y listado ---

    def test_el_detalle_del_informe_trae_las_adendas_en_orden(self):
        informe_id = self.crear()
        self.agregar(informe_id, motivo='Primera')
        self.agregar(informe_id, motivo='Segunda')
        adendas = self.client.get(f'{self.URL}{informe_id}/').data['adendas']
        self.assertEqual([(a['numero'], a['motivo']) for a in adendas], [(1, 'Primera'), (2, 'Segunda')])

    def test_el_detalle_no_hace_una_consulta_por_adenda(self):
        # Auditoría M-4: las consultas del detalle no crecen con las adendas.
        from django.test.utils import CaptureQueriesContext

        una, cinco = self.crear(), self.crear()
        self.agregar(una)
        for _ in range(5):
            self.agregar(cinco)

        def contar(informe_id):
            with CaptureQueriesContext(connection) as consultas:
                self.client.get(f'{self.URL}{informe_id}/')
            return len(consultas)

        self.assertEqual(contar(cinco), contar(una))

    def test_el_listado_no_trae_las_adendas(self):
        self.agregar(self.crear())
        fila = self.client.get(self.URL).data['results'][0]
        self.assertNotIn('adendas', fila)


class PdfBorradorTests(APITestCase):
    """
    Decisión D-12: el PDF de un borrador es una vista previa solo para su autor o un
    admin; los demás (otros patólogos y el auditor) reciben 403. Lleva la marca de agua
    "BORRADOR" en cada página y el archivo se llama informe_P-AAAA-NNNNN_borrador.pdf.
    El PDF de un informe finalizado lo descargan todos, sin marca de agua.
    Solo datos ficticios.
    """

    def setUp(self):
        def usuario(username, rol):
            return Usuario.objects.create_user(username=username, password='ClaveSegura-2026', rol=rol)

        self.autor = usuario('autor_borrador', Usuario.Rol.PATOLOGO)
        self.otro = usuario('otro_borrador', Usuario.Rol.PATOLOGO)
        self.admin = usuario('admin_borrador', Usuario.Rol.ADMIN)
        self.auditor = usuario('auditor_borrador', Usuario.Rol.AUDITOR)
        self.informe = Informe.objects.create(
            patologia=Patologia.objects.create(nombre='Patología borrador'),
            autor=self.autor,
            paciente=paciente_ficticio(),
            descripcion_microscopica='Párrafo largo de prueba. ' * 1500,
        )
        self.url = f'/api/informes/{self.informe.id}/pdf/'

    def descargar(self, usuario):
        self.client.force_authenticate(usuario)
        return self.client.get(self.url)

    def finalizar(self):
        Informe.objects.filter(id=self.informe.id).update(estado=Informe.Estado.FINALIZADO)

    def marcas_y_paginas(self):
        """Descarga como el autor y devuelve cuántas marcas "BORRADOR" se dibujan y cuántas páginas hay."""
        import re

        from reportlab.pdfgen.canvas import Canvas

        with mock.patch.object(
            Canvas, 'drawCentredString', autospec=True, side_effect=Canvas.drawCentredString
        ) as centrados:
            respuesta = self.descargar(self.autor)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        marcas = [llamada for llamada in centrados.call_args_list if llamada.args[3] == 'BORRADOR']
        return len(marcas), len(re.findall(rb'/Type /Page\b(?!s)', respuesta.content))

    # --- Quién descarga un borrador ---

    def test_el_autor_descarga_la_vista_previa_de_su_borrador(self):
        respuesta = self.descargar(self.autor)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            respuesta['Content-Disposition'],
            f'attachment; filename="informe_{self.informe.numero_peticion}_borrador.pdf"',
        )

    def test_un_admin_descarga_el_borrador_de_otro(self):
        self.assertEqual(self.descargar(self.admin).status_code, status.HTTP_200_OK)

    def test_otro_patologo_no_descarga_un_borrador_ajeno(self):
        respuesta = self.descargar(self.otro)
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('borrador', respuesta.data['detail'])

    def test_el_auditor_no_descarga_un_borrador(self):
        self.assertEqual(self.descargar(self.auditor).status_code, status.HTTP_403_FORBIDDEN)

    # --- Informe finalizado ---

    def test_un_informe_finalizado_lo_descargan_todos_sin_borrador_en_el_nombre(self):
        self.finalizar()
        for usuario in (self.autor, self.otro, self.admin, self.auditor):
            respuesta = self.descargar(usuario)
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK, usuario.username)
            self.assertEqual(
                respuesta['Content-Disposition'],
                f'attachment; filename="informe_{self.informe.numero_peticion}.pdf"',
            )

    # --- Marca de agua ---

    def test_el_borrador_lleva_la_marca_de_agua_en_cada_pagina(self):
        marcas, paginas = self.marcas_y_paginas()
        self.assertGreaterEqual(paginas, 2)
        self.assertEqual(marcas, paginas)

    def test_un_informe_finalizado_no_lleva_marca_de_agua(self):
        self.finalizar()
        marcas, paginas = self.marcas_y_paginas()
        self.assertGreaterEqual(paginas, 2)
        self.assertEqual(marcas, 0)


class EstadoSoloLecturaTests(APITestCase):
    """
    Hallazgo O-1 de docs/auditoria-owasp.md: `estado` se podía escribir por la API, así
    que un PATCH o un POST con "finalizado" cerraba el informe sin los requisitos de D-8
    y sin congelar sus datos (D-10, D-15). Solo la acción `finalizar` cambia el estado.
    Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        # Sin registro médico: si el estado se pudiera escribir, el informe quedaría
        # finalizado sin firma.
        self.autor = Usuario.objects.create_user(
            username='patologo_estado',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Patología estado')
        self.paciente = paciente_ficticio()

    def crear(self, **extra):
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, **extra}
        respuesta = self.client.post(self.URL, cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        return respuesta

    def assertSigueEnBorrador(self, informe_id):
        informe = Informe.objects.get(id=informe_id)
        self.assertEqual(informe.estado, Informe.Estado.BORRADOR)
        self.assertIsNone(informe.fecha_informe)
        self.assertIsNone(informe.datos_finalizacion)

    def test_un_patch_con_estado_no_finaliza_el_informe(self):
        informe_id = self.crear().data['id']
        respuesta = self.client.patch(f'{self.URL}{informe_id}/', {'estado': 'finalizado'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['estado'], Informe.Estado.BORRADOR)
        self.assertSigueEnBorrador(informe_id)

    def test_un_put_con_estado_no_finaliza_el_informe(self):
        informe_id = self.crear().data['id']
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, 'estado': 'finalizado'}
        respuesta = self.client.put(f'{self.URL}{informe_id}/', cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertSigueEnBorrador(informe_id)

    def test_un_informe_nuevo_no_se_crea_finalizado(self):
        respuesta = self.crear(estado='finalizado')
        self.assertEqual(respuesta.data['estado'], Informe.Estado.BORRADOR)
        self.assertSigueEnBorrador(respuesta.data['id'])


def datos_formulario_admin(respuesta):
    """
    Datos que enviaría el navegador al guardar una ficha de /admin/ sin cambiar nada:
    los valores del formulario principal y de los inlines (con sus formularios de
    gestión). Las pruebas cambian solo lo que necesitan.
    """
    datos = {}

    def agregar(formulario):
        for campo in formulario:
            valor = campo.value()
            if valor is None or valor is False:
                continue
            datos[campo.html_name] = 'on' if valor is True else valor

    agregar(respuesta.context['adminform'].form)
    for inline in respuesta.context['inline_admin_formsets']:
        agregar(inline.formset.management_form)
        for formulario in inline.formset.forms:
            agregar(formulario)
    return datos


class AdminInformeFinalizadoTests(TestCase):
    """
    Decisión D-14 (hallazgo O-4 de docs/auditoria-owasp.md): en /admin/, un informe
    finalizado es de solo lectura (campos, diagnósticos y estado) y no se borra, tenga
    o no adendas. Hallazgo O-3: el estado tampoco se cambia en un borrador; un informe
    solo se finaliza con POST /api/informes/{id}/finalizar/. Los borradores se siguen
    editando y borrando. Solo datos ficticios.
    """

    LISTADO = '/admin/informes/informe/'

    def setUp(self):
        self.superusuario = Usuario.objects.create_superuser(
            username='super_admin_informes',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.ADMIN,
        )
        self.client.force_login(self.superusuario)
        self.autor = Usuario.objects.create_user(
            username='patologo_admin_informes',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            registro_medico='RM-PRUEBA-0001',
        )
        self.patologia = Patologia.objects.create(nombre='Patología admin')
        self.paciente = paciente_ficticio()

    def crear_informe(self, finalizado):
        informe = Informe.objects.create(
            patologia=self.patologia,
            autor=self.autor,
            paciente=self.paciente,
            descripcion_microscopica='Texto original.',
            datos_ingresados={'peso': '12 g'},
        )
        Diagnostico.objects.create(informe=informe, orden=1, descripcion='Diagnóstico original')
        if finalizado:
            informe.estado = Informe.Estado.FINALIZADO
            informe.fecha_informe = timezone.now()
            informe.datos_finalizacion = informe.datos_para_congelar()
            informe.save()
        return informe

    def ficha(self, informe):
        return f'{self.LISTADO}{informe.id}/change/'

    def guardar_ficha(self, informe, **cambios):
        datos = datos_formulario_admin(self.client.get(self.ficha(informe)))
        datos.update(cambios)
        return self.client.post(self.ficha(informe), datos)

    def borrar_en_lote(self, informe):
        return self.client.post(
            self.LISTADO,
            {'action': 'delete_selected', '_selected_action': [informe.id], 'post': 'yes'},
        )

    def agregar_adenda(self, informe):
        Adenda.objects.create(
            informe=informe,
            numero=1,
            motivo='Motivo de prueba',
            texto='Texto de prueba',
            autor=self.autor,
            firma=firma_de(self.autor),
        )

    # --- Informe finalizado (D-14, O-4) ---

    def test_la_ficha_de_un_finalizado_se_ve_en_solo_lectura(self):
        informe = self.crear_informe(finalizado=True)
        respuesta = self.client.get(self.ficha(informe))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'name="_save"')
        self.assertContains(respuesta, 'Texto original.')

    def test_no_se_cambia_el_contenido_de_un_finalizado(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(informe, descripcion_microscopica='Texto cambiado.')
        informe.refresh_from_db()
        self.assertEqual(informe.descripcion_microscopica, 'Texto original.')

    def test_un_finalizado_no_vuelve_a_borrador(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(informe, estado=Informe.Estado.BORRADOR)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, Informe.Estado.FINALIZADO)

    def test_no_se_cambian_los_diagnosticos_de_un_finalizado(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(informe, **{'diagnosticos-0-descripcion': 'Diagnóstico cambiado'})
        self.assertEqual(informe.diagnosticos.get().descripcion, 'Diagnóstico original')

    def test_no_se_borran_los_diagnosticos_de_un_finalizado(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(informe, **{'diagnosticos-0-DELETE': 'on'})
        self.assertEqual(informe.diagnosticos.count(), 1)

    def test_no_se_agregan_diagnosticos_a_un_finalizado(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(
            informe,
            **{
                'diagnosticos-TOTAL_FORMS': '2',
                'diagnosticos-1-orden': '2',
                'diagnosticos-1-descripcion': 'Diagnóstico agregado',
                'diagnosticos-1-informe': str(informe.id),
            },
        )
        self.assertEqual(informe.diagnosticos.count(), 1)

    def test_no_se_borra_un_finalizado_desde_su_pagina_de_borrado(self):
        informe = self.crear_informe(finalizado=True)
        self.client.post(f'{self.LISTADO}{informe.id}/delete/', {'post': 'yes'})
        self.assertTrue(Informe.objects.filter(id=informe.id).exists())

    def test_no_se_borra_un_finalizado_con_la_accion_en_lote(self):
        informe = self.crear_informe(finalizado=True)
        self.borrar_en_lote(informe)
        self.assertTrue(Informe.objects.filter(id=informe.id).exists())

    def test_no_se_borra_un_finalizado_con_adendas(self):
        informe = self.crear_informe(finalizado=True)
        self.agregar_adenda(informe)
        self.client.post(f'{self.LISTADO}{informe.id}/delete/', {'post': 'yes'})
        self.borrar_en_lote(informe)
        self.assertTrue(Informe.objects.filter(id=informe.id).exists())

    # --- Borrador (O-3) ---

    def test_un_borrador_no_se_finaliza_desde_admin(self):
        informe = self.crear_informe(finalizado=False)
        self.guardar_ficha(informe, estado=Informe.Estado.FINALIZADO)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, Informe.Estado.BORRADOR)
        self.assertIsNone(informe.datos_finalizacion)

    def test_un_borrador_se_sigue_editando(self):
        informe = self.crear_informe(finalizado=False)
        respuesta = self.guardar_ficha(
            informe,
            descripcion_microscopica='Texto cambiado.',
            **{'diagnosticos-0-descripcion': 'Diagnóstico cambiado'},
        )
        self.assertEqual(respuesta.status_code, 302)  # redirige: se guardó
        informe.refresh_from_db()
        self.assertEqual(informe.descripcion_microscopica, 'Texto cambiado.')
        self.assertEqual(informe.diagnosticos.get().descripcion, 'Diagnóstico cambiado')

    def test_un_borrador_se_sigue_borrando(self):
        informe = self.crear_informe(finalizado=False)
        self.client.post(f'{self.LISTADO}{informe.id}/delete/', {'post': 'yes'})
        self.assertFalse(Informe.objects.filter(id=informe.id).exists())

    def test_un_borrador_se_sigue_borrando_con_la_accion_en_lote(self):
        informe = self.crear_informe(finalizado=False)
        self.borrar_en_lote(informe)
        self.assertFalse(Informe.objects.filter(id=informe.id).exists())


class FiltrosNoValidosTests(APITestCase):
    """
    Hallazgo O-22 de docs/auditoria-owasp.md: un filtro con un valor que no es un número
    o una fecha llegaba sin revisar a filter() y respondía 500. Debe responder 400 con
    un mensaje en español. Solo datos ficticios.
    """

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_filtros',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología filtros')
        self.paciente = paciente_ficticio()
        self.informe = Informe.objects.create(patologia=self.patologia, autor=self.patologo, paciente=self.paciente)

    def test_valores_no_validos_responden_400(self):
        for url, parametro in [
            ('/api/informes/?fecha_desde=abc', 'fecha_desde'),
            ('/api/informes/?fecha_hasta=2026-13-45', 'fecha_hasta'),
            ('/api/informes/?patologia=abc', 'patologia'),
            ('/api/informes/?paciente=abc', 'paciente'),
            ('/api/informes/?paciente=99999999999999999999999', 'paciente'),
            ('/api/informes/?patologia=-3', 'patologia'),
            ('/api/informes/estadisticas/?fecha_hasta=2026-13-45', 'fecha_hasta'),
            ('/api/informes/estadisticas/?patologia=abc', 'patologia'),
            ('/api/patologias/?categoria=abc', 'categoria'),
            ('/api/plantillas/?patologia=abc', 'patologia'),
        ]:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(parametro, respuesta.data)

    def test_valores_validos_siguen_filtrando(self):
        hoy = timezone.localdate().isoformat()
        for url, total in [
            (f'/api/informes/?patologia={self.patologia.id}', 1),
            (f'/api/informes/?patologia={self.patologia.id + 1}', 0),
            (f'/api/informes/?paciente={self.paciente.id}', 1),
            (f'/api/informes/?fecha_desde={hoy}&fecha_hasta={hoy}', 1),
            ('/api/informes/?fecha_desde=2000-01-01&fecha_hasta=2000-01-02', 0),
            ('/api/informes/?patologia=', 1),
        ]:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
                self.assertEqual(respuesta.data['count'], total)


class DatosIngresadosTests(APITestCase):
    """
    Hallazgo O-23 de docs/auditoria-owasp.md: `datos_ingresados` aceptaba cualquier JSON.
    Con una lista, el informe se guardaba (gastando un número de petición, D-7) y después
    fallaba al generar la descripción: 500 y un informe con datos no válidos.
    Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_datos',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología datos')
        self.paciente = paciente_ficticio()

    def crear(self, datos):
        cuerpo = {'patologia': self.patologia.id, 'paciente': self.paciente.id, 'datos_ingresados': datos}
        return self.client.post(self.URL, cuerpo, format='json')

    def test_rechaza_datos_que_no_son_un_objeto(self):
        for datos in [[1, 2], 5, 'texto', True]:
            with self.subTest(datos=datos):
                respuesta = self.crear(datos)
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('datos_ingresados', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_valores_anidados(self):
        for datos in [{'peso': {'valor': 12}}, {'peso': [12, 13]}]:
            with self.subTest(datos=datos):
                respuesta = self.crear(datos)
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('datos_ingresados', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_demasiados_campos_o_textos_muy_largos(self):
        from .models import MAX_CAMPOS_DATOS_INGRESADOS, MAX_LARGO_VALOR_DATOS_INGRESADOS

        muchos = {f'campo_{n}': 'x' for n in range(MAX_CAMPOS_DATOS_INGRESADOS + 1)}
        largo = {'observaciones': 'x' * (MAX_LARGO_VALOR_DATOS_INGRESADOS + 1)}
        for datos in [muchos, largo]:
            respuesta = self.crear(datos)
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Informe.objects.count(), 0)

    def test_acepta_textos_numeros_booleanos_y_nulos(self):
        respuesta = self.crear({'peso': 12.5, 'localizacion': 'Antebrazo', 'necrosis': False, 'color': None})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertIn('El peso registrado es de 12.5 gramos.', respuesta.data['texto_generado'])

    def test_un_patch_con_una_lista_no_cambia_el_informe(self):
        informe_id = self.crear({'peso': '12'}).data['id']
        respuesta = self.client.patch(f'{self.URL}{informe_id}/', {'datos_ingresados': [1, 2]}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Informe.objects.get(id=informe_id).datos_ingresados, {'peso': '12'})

    def test_si_falla_la_descripcion_no_queda_el_informe_guardado(self):
        # El texto se genera en la misma transacción que el guardado: si falla, no queda nada.
        with mock.patch('informes.serializers.generar_descripcion_macroscopica', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.crear({'peso': '12'})
        self.assertEqual(Informe.objects.count(), 0)


class AdminDatosIngresadosTests(TestCase):
    """
    En /admin/, un informe con `datos_ingresados = {}` no se podía guardar ("Este campo es
    requerido"), aunque la API lo acepta. Y un valor que no es un objeto debe rechazarse
    también ahí (O-23). Solo datos ficticios.
    """

    def setUp(self):
        superusuario = Usuario.objects.create_superuser(
            username='super_admin_datos', password='ClaveSegura-2026', rol=Usuario.Rol.ADMIN
        )
        self.client.force_login(superusuario)
        self.autor = Usuario.objects.create_user(
            username='patologo_admin_datos', password='ClaveSegura-2026', rol=Usuario.Rol.PATOLOGO
        )
        self.informe = Informe.objects.create(
            patologia=Patologia.objects.create(nombre='Patología admin datos'),
            autor=self.autor,
            paciente=paciente_ficticio(),
            datos_ingresados={},
        )
        self.ficha = f'/admin/informes/informe/{self.informe.id}/change/'

    def guardar(self, **cambios):
        datos = datos_formulario_admin(self.client.get(self.ficha))
        datos.update(cambios)
        return self.client.post(self.ficha, datos)

    def test_se_guarda_con_datos_vacios(self):
        respuesta = self.guardar(datos_ingresados='{}', comentarios='Guardado desde admin')
        self.assertEqual(respuesta.status_code, 302)
        self.informe.refresh_from_db()
        self.assertEqual(self.informe.comentarios, 'Guardado desde admin')

    def test_rechaza_datos_que_no_son_un_objeto(self):
        respuesta = self.guardar(datos_ingresados='[1, 2]')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('datos_ingresados', respuesta.context['adminform'].form.errors)
        self.informe.refresh_from_db()
        self.assertEqual(self.informe.datos_ingresados, {})


# ── Plantillas según el manual de procesamiento macroscópico y canastillas (D-18) ──


def plantilla_simple(campo_nombre, **extra):
    """Objeto con los atributos de Plantilla, para probar informes/reglas.py sin base de datos."""
    datos = {
        'campo_nombre': campo_nombre,
        'campo_label': '',
        'tipo_campo': 'texto',
        'obligatorio': False,
        'opciones': [],
        'condicion': {},
        **extra,
    }
    return SimpleNamespace(**datos)


class ReglasCamposTests(SimpleTestCase):
    """informes/reglas.py: obligatorio, condicional, opcional y no aplicable (D-18)."""

    def setUp(self):
        self.plantillas = [
            plantilla_simple('tipo_muestra', tipo_campo='lista', obligatorio=True, opciones=['Biopsia', 'Resección']),
            plantilla_simple(
                'margenes',
                campo_label='Márgenes',
                tipo_campo='lista',
                obligatorio=True,
                opciones=['Libres', 'Comprometidos'],
                condicion={'campo': 'tipo_muestra', 'valores': ['Resección']},
            ),
            plantilla_simple(
                'distancia',
                campo_label='Distancia',
                condicion={'campo': 'margenes', 'valores': ['Comprometidos']},
            ),
            plantilla_simple('peso', campo_label='Peso', tipo_campo='numero'),
        ]

    def test_un_campo_sin_condicion_siempre_aplica(self):
        self.assertIn('peso', campos_aplicables(self.plantillas, {}))

    def test_un_campo_condicional_aplica_solo_con_su_valor(self):
        self.assertNotIn('margenes', campos_aplicables(self.plantillas, {'tipo_muestra': 'Biopsia'}))
        self.assertIn('margenes', campos_aplicables(self.plantillas, {'tipo_muestra': 'Resección'}))

    def test_un_valor_viejo_de_un_campo_que_no_aplica_no_activa_a_los_que_dependen_de_el(self):
        datos = {'tipo_muestra': 'Biopsia', 'margenes': 'Comprometidos'}
        self.assertNotIn('distancia', campos_aplicables(self.plantillas, datos))

    def test_el_obligatorio_condicional_solo_se_exige_si_aplica(self):
        self.assertEqual(validar_datos(self.plantillas, {'tipo_muestra': 'Biopsia'}), [])
        errores = validar_datos(self.plantillas, {'tipo_muestra': 'Resección'})
        self.assertEqual(errores, ['Faltan campos obligatorios: Márgenes'])

    def test_cero_es_una_respuesta_y_un_negativo_no(self):
        self.assertEqual(validar_datos(self.plantillas, {'tipo_muestra': 'Biopsia', 'peso': 0}), [])
        self.assertEqual(
            validar_datos(self.plantillas, {'tipo_muestra': 'Biopsia', 'peso': -2}),
            ['«Peso» no puede ser negativo.'],
        )
        self.assertEqual(
            validar_datos(self.plantillas, {'tipo_muestra': 'Biopsia', 'peso': 'doce'}),
            ['«Peso» debe ser un número.'],
        )

    def test_una_opcion_que_no_esta_en_la_lista_se_rechaza(self):
        errores = validar_datos(self.plantillas, {'tipo_muestra': 'Inventada'})
        self.assertEqual(errores, ['«tipo_muestra»: «Inventada» no es una de las opciones.'])

    def test_un_valor_ya_guardado_se_conserva_aunque_la_opcion_se_haya_quitado(self):
        # Como una EPS desactivada (D-4): el informe que ya lo tenía lo conserva.
        datos = {'tipo_muestra': 'Opción retirada'}
        self.assertEqual(validar_datos(self.plantillas, datos, guardados=datos), [])

    def test_un_campo_que_no_aplica_no_se_valida(self):
        datos = {'tipo_muestra': 'Biopsia', 'margenes': 'Inventado'}
        self.assertEqual(validar_datos(self.plantillas, datos), [])

    def test_una_condicion_circular_no_aplica(self):
        plantillas = [
            plantilla_simple('a', tipo_campo='lista', opciones=['x'], condicion={'campo': 'b', 'valores': ['x']}),
            plantilla_simple('b', tipo_campo='lista', opciones=['x'], condicion={'campo': 'a', 'valores': ['x']}),
        ]
        self.assertEqual(campos_aplicables(plantillas, {'a': 'x', 'b': 'x'}), set())


class PlantillasManualTests(TestCase):
    """
    `actualizar_plantillas` (D-18): aplica a las 14 patologías las definiciones del
    manual sin borrar campos ni opciones y sin tocar los informes. seed_data lo llama.
    """

    NOMBRES = [
        'Biopsia de Piel',
        'Biopsia de Mama',
        'Apéndice Cecal',
        'Vesícula Biliar',
        'Biopsia de Próstata',
        'Tiroides',
        'Colon y Recto',
        'Útero y Cérvix',
        'Ganglio Linfático',
        'Biopsia Gástrica',
        'Pulmón',
        'Riñón',
        'Amígdalas y Adenoides',
        'Tejido Blando',
    ]

    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def campos(self, nombre):
        return {p.campo_nombre: p for p in Plantilla.objects.filter(patologia__nombre=nombre)}

    def test_siguen_las_14_patologias(self):
        self.assertEqual(sorted(Patologia.objects.values_list('nombre', flat=True)), sorted(self.NOMBRES))
        self.assertEqual(sorted(DEFINICIONES), sorted(self.NOMBRES))

    def test_cada_plantilla_tiene_sus_campos_del_manual_con_seccion_y_su_guia(self):
        for nombre, definicion in DEFINICIONES.items():
            with self.subTest(nombre=nombre):
                campos = self.campos(nombre)
                for campo in definicion['campos']:
                    self.assertIn(campo['campo_nombre'], campos)
                    self.assertTrue(campos[campo['campo_nombre']].seccion)
                self.assertTrue(Patologia.objects.get(nombre=nombre).guia_muestreo)

    def test_los_campos_especificos_estan_en_su_plantilla(self):
        self.assertIn('lesion_satelites', self.campos('Biopsia de Piel'))
        self.assertIn('tipo_mastectomia', self.campos('Biopsia de Mama'))
        self.assertIn('dim_lobulo_der', self.campos('Tiroides'))
        self.assertIn('mesorrecto', self.campos('Colon y Recto'))
        self.assertIn('orientacion_cono', self.campos('Útero y Cérvix'))
        self.assertIn('peso_fragmentos', self.campos('Biopsia de Próstata'))
        self.assertNotIn('mesorrecto', self.campos('Tiroides'))
        self.assertNotIn('lesion_satelites', self.campos('Colon y Recto'))

    def test_no_todos_los_campos_son_obligatorios(self):
        for nombre in self.NOMBRES:
            with self.subTest(nombre=nombre):
                campos = self.campos(nombre).values()
                self.assertLess(sum(p.obligatorio for p in campos), len(campos) / 2)

    def test_se_puede_ejecutar_varias_veces_con_el_mismo_resultado(self):
        antes = list(Plantilla.objects.order_by('id').values())
        call_command('actualizar_plantillas', verbosity=0)
        self.assertEqual(list(Plantilla.objects.order_by('id').values()), antes)

    def test_no_borra_campos_ni_opciones(self):
        plantilla = Plantilla.objects.get(patologia__nombre='Tiroides', campo_nombre='tipo_muestra')
        plantilla.opciones = [*plantilla.opciones, 'Opción agregada a mano']
        plantilla.save()
        extra = Plantilla.objects.create(
            patologia=plantilla.patologia, campo_nombre='campo_propio', campo_label='Campo propio', orden=5
        )
        call_command('actualizar_plantillas', verbosity=0)
        plantilla.refresh_from_db()
        extra.refresh_from_db()
        self.assertIn('Opción agregada a mano', plantilla.opciones)
        self.assertEqual(extra.orden, 1005)  # se conserva, al final del formulario

    def test_no_cambia_los_informes(self):
        autor = Usuario.objects.get(username='patologo1')
        informe = Informe.objects.create(
            patologia=Patologia.objects.get(nombre='Vesícula Biliar'),
            autor=autor,
            paciente=Paciente.objects.first(),
            datos_ingresados={'consistencia': '3 mm', 'calcificaciones': 'Presente(s)'},
            texto_generado='Texto que ya estaba.',
        )
        call_command('actualizar_plantillas', verbosity=0)
        informe.refresh_from_db()
        self.assertEqual(informe.datos_ingresados, {'consistencia': '3 mm', 'calcificaciones': 'Presente(s)'})
        self.assertEqual(informe.texto_generado, 'Texto que ya estaba.')

    def test_la_simulacion_no_guarda_nada(self):
        Plantilla.objects.filter(campo_nombre='lesion_satelites').delete()
        salida = StringIO()
        call_command('actualizar_plantillas', '--simular', stdout=salida)
        self.assertFalse(Plantilla.objects.filter(campo_nombre='lesion_satelites').exists())
        self.assertIn('SIMULACIÓN', salida.getvalue())

    def test_una_patologia_que_no_existe_se_omite_con_un_aviso(self):
        Patologia.objects.filter(nombre='Riñón').update(nombre='Riñón (renombrada)')
        salida = StringIO()
        call_command('actualizar_plantillas', stdout=salida)
        self.assertIn('[OMITIDA] La patología "Riñón" no existe.', salida.getvalue())

    def test_las_condiciones_apuntan_a_campos_y_opciones_que_existen(self):
        for patologia in Patologia.objects.prefetch_related('plantillas'):
            campos = {p.campo_nombre: p for p in patologia.plantillas.all()}
            for plantilla in campos.values():
                if not plantilla.condicion:
                    continue
                with self.subTest(patologia=patologia.nombre, campo=plantilla.campo_nombre):
                    referido = campos[plantilla.condicion['campo']]
                    self.assertEqual(referido.tipo_campo, 'lista')
                    self.assertLessEqual(set(plantilla.condicion['valores']), set(referido.opciones))


class ValidacionPlantillasManualTests(APITestCase):
    """La API exige solo lo que aplica al procedimiento elegido (D-18). Solo datos ficticios."""

    URL = '/api/informes/'

    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def setUp(self):
        self.patologo = Usuario.objects.get(username='patologo1')
        self.client.force_authenticate(self.patologo)
        self.paciente = Paciente.objects.first()

    def crear(self, patologia, datos):
        cuerpo = {
            'patologia': Patologia.objects.get(nombre=patologia).id,
            'paciente': self.paciente.id,
            'datos_ingresados': datos,
        }
        return self.client.post(self.URL, cuerpo, format='json')

    def test_la_biopsia_de_mama_por_aguja_no_exige_margenes(self):
        datos = {
            'lateralidad': 'Derecha',
            'tipo_muestra': 'Biopsia por aguja gruesa',
            'dimensiones': '1.5 x 0.1',
            'num_fragmentos': 3,
        }
        respuesta = self.crear('Biopsia de Mama', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)

    def test_la_cuadrantectomia_exige_margenes(self):
        datos = {'lateralidad': 'Derecha', 'tipo_muestra': 'Cuadrantectomía', 'dimensiones': '8 x 6 x 4'}
        respuesta = self.crear('Biopsia de Mama', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Márgenes quirúrgicos', str(respuesta.data['datos_ingresados']))

    def test_la_tiroidectomia_total_no_exige_lateralidad_y_la_lobectomia_si(self):
        datos = {'tipo_muestra': 'Tiroidectomía total', 'dimensiones': '6 x 4 x 2', 'peso': 30, 'nodulo_presente': 'No'}
        self.assertEqual(self.crear('Tiroides', datos).status_code, status.HTTP_201_CREATED)
        respuesta = self.crear('Tiroides', {**datos, 'tipo_muestra': 'Lobectomía'})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Lateralidad', str(respuesta.data['datos_ingresados']))

    def test_la_rtu_de_prostata_exige_el_peso_y_no_los_cilindros(self):
        respuesta = self.crear('Biopsia de Próstata', {'tipo_muestra': 'Resección transuretral (RTU)'})
        self.assertIn('Peso total de los fragmentos', str(respuesta.data['datos_ingresados']))
        self.assertNotIn('cilindros', str(respuesta.data['datos_ingresados']))
        datos = {'tipo_muestra': 'Resección transuretral (RTU)', 'peso_fragmentos': 14}
        self.assertEqual(self.crear('Biopsia de Próstata', datos).status_code, status.HTTP_201_CREATED)

    def test_la_perforacion_presente_exige_su_detalle(self):
        datos = {'tipo_muestra': 'Apéndice cecal', 'dimensiones': '6 x 0.8', 'superficie': 'Opaca'}
        self.assertEqual(self.crear('Apéndice Cecal', datos).status_code, status.HTTP_201_CREATED)
        respuesta = self.crear('Apéndice Cecal', {**datos, 'perforacion': 'Presente'})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        respuesta = self.crear('Apéndice Cecal', {**datos, 'perforacion': 'Presente', 'perforacion_detalle': '2 mm'})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_rechaza_una_opcion_que_no_esta_en_la_lista(self):
        datos = {'tipo_muestra': 'Apéndice cecal', 'dimensiones': '6 x 0.8', 'superficie': 'Inventada'}
        respuesta = self.crear('Apéndice Cecal', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no es una de las opciones', str(respuesta.data['datos_ingresados']))

    def test_un_borrador_conserva_una_opcion_que_despues_se_quito_de_la_plantilla(self):
        datos = {'tipo_muestra': 'Apéndice cecal', 'dimensiones': '6 x 0.8', 'superficie': 'Opaca'}
        informe_id = self.crear('Apéndice Cecal', datos).data['id']
        Plantilla.objects.filter(patologia__nombre='Apéndice Cecal', campo_nombre='superficie').update(
            opciones=['Lisa y brillante']
        )
        respuesta = self.client.patch(
            f'{self.URL}{informe_id}/', {'datos_ingresados': {**datos, 'color': 'Congestivo'}}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)

    def test_la_condicion_de_una_plantilla_se_valida(self):
        plantilla = Plantilla.objects.filter(patologia__nombre='Tiroides').first()
        url = f'/api/plantillas/{plantilla.id}/'
        for condicion in [{'campo': 'x'}, {'campo': 'x', 'valores': []}, ['x'], {'campo': 'x', 'valores': [1]}]:
            with self.subTest(condicion=condicion):
                respuesta = self.client.patch(url, {'condicion': condicion}, format='json')
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        respuesta = self.client.patch(
            url, {'condicion': {'campo': ' tipo_muestra ', 'valores': ['Lobectomía']}}, format='json'
        )
        self.assertEqual(respuesta.data['condicion'], {'campo': 'tipo_muestra', 'valores': ['Lobectomía']})
        respuesta = self.client.patch(url, {'condicion': {}}, format='json')
        self.assertEqual(respuesta.data['condicion'], {})

    def test_el_detalle_de_la_patologia_trae_secciones_condiciones_y_guia(self):
        patologia = Patologia.objects.get(nombre='Tiroides')
        datos = self.client.get(f'/api/patologias/{patologia.id}/').data
        self.assertTrue(datos['guia_muestreo'])
        lateralidad = next(p for p in datos['plantillas'] if p['campo_nombre'] == 'lateralidad')
        self.assertEqual(lateralidad['condicion']['campo'], 'tipo_muestra')
        self.assertTrue(lateralidad['seccion'])


class CanastillasTests(APITestCase):
    """
    Muestreo para histología (D-18): canastillas anidadas en el informe, como los
    diagnósticos. Las escribe siempre el usuario. Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_canastillas',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            registro_medico='RM-PRUEBA-0001',
        )
        self.client.force_authenticate(self.patologo)
        self.patologia = Patologia.objects.create(nombre='Patología canastillas')
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='localizacion', campo_label='Localización', obligatorio=True
        )
        self.paciente = paciente_ficticio()

    def crear(self, **extra):
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {'localizacion': 'Antebrazo'},
            **extra,
        }
        return self.client.post(self.URL, cuerpo, format='json')

    def url(self, informe_id):
        return f'{self.URL}{informe_id}/'

    def guardadas(self, informe_id):
        return list(Canastilla.objects.filter(informe_id=informe_id).values_list('orden', 'codigo', 'region'))

    def test_registra_una_canastilla(self):
        respuesta = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta', 'descripcion': 'Corte longitudinal'}])
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(self.guardadas(respuesta.data['id']), [(1, 'A', 'Punta')])

    def test_registra_varias_en_el_orden_enviado_y_las_devuelve_en_el_detalle(self):
        canastillas = [
            {'codigo': 'B', 'region': 'Base', 'cantidad': 2},
            {'codigo': 'A', 'lesion_margen': 'Margen proximal', 'entintado': 'Azul'},
            {'codigo': 'C', 'descripcion': 'Ganglios', 'cantidad': 0},
        ]
        informe_id = self.crear(canastillas=canastillas).data['id']
        detalle = self.client.get(self.url(informe_id)).data['canastillas']
        self.assertEqual([(c['orden'], c['codigo']) for c in detalle], [(1, 'B'), (2, 'A'), (3, 'C')])
        self.assertEqual(detalle[1]['entintado'], 'Azul')
        self.assertEqual(detalle[2]['cantidad'], 0)

    def test_al_editar_se_reemplaza_la_lista(self):
        informe_id = self.crear(
            canastillas=[{'codigo': 'A', 'region': 'Punta'}, {'codigo': 'B', 'region': 'Base'}]
        ).data['id']
        respuesta = self.client.patch(
            self.url(informe_id),
            {'canastillas': [{'codigo': 'B', 'region': 'Base corregida'}, {'codigo': 'C', 'region': 'Lesión'}]},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(self.guardadas(informe_id), [(1, 'B', 'Base corregida'), (2, 'C', 'Lesión')])

    def test_editar_otra_parte_del_informe_no_cambia_las_canastillas(self):
        informe_id = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        self.client.patch(self.url(informe_id), {'comentarios': 'Revisado'}, format='json')
        self.assertEqual(self.guardadas(informe_id), [(1, 'A', 'Punta')])

    def test_enviar_una_lista_vacia_las_quita(self):
        informe_id = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        self.client.patch(self.url(informe_id), {'canastillas': []}, format='json')
        self.assertEqual(self.guardadas(informe_id), [])

    def test_no_se_crean_canastillas_sin_que_el_usuario_las_envie(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.data['canastillas'], [])
        self.assertFalse(Canastilla.objects.exists())

    def test_cada_informe_lleva_las_canastillas_que_necesita(self):
        uno = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        doce = self.crear(canastillas=[{'codigo': str(n), 'region': f'Región {n}'} for n in range(1, 13)]).data['id']
        self.assertEqual(Canastilla.objects.filter(informe_id=uno).count(), 1)
        self.assertEqual(Canastilla.objects.filter(informe_id=doce).count(), 12)

    def test_rechaza_identificaciones_repetidas_sin_importar_mayusculas(self):
        respuesta = self.crear(canastillas=[{'codigo': 'a', 'region': 'Punta'}, {'codigo': 'A ', 'region': 'Base'}])
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('repetida', str(respuesta.data['canastillas']))
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_una_canastilla_sin_identificacion_o_sin_contenido(self):
        for canastilla in [{'codigo': '', 'region': 'Punta'}, {'codigo': 'A'}, {'codigo': 'A', 'motivo': 'Rutina'}]:
            with self.subTest(canastilla=canastilla):
                respuesta = self.crear(canastillas=[canastilla])
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('canastillas', respuesta.data)
        self.assertEqual(Informe.objects.count(), 0)

    def test_rechaza_una_cantidad_negativa(self):
        respuesta = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta', 'cantidad': -1}])
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tiene_un_tope_tecnico_alto(self):
        canastillas = [{'codigo': str(n), 'region': 'x'} for n in range(MAX_CANASTILLAS + 1)]
        respuesta = self.crear(canastillas=canastillas)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_un_informe_finalizado_no_cambia_sus_canastillas(self):
        # D-3: tampoco se modifica el muestreo de un informe finalizado.
        informe_id = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        Informe.objects.filter(id=informe_id).update(estado=Informe.Estado.FINALIZADO)
        respuesta = self.client.patch(self.url(informe_id), {'canastillas': []}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.guardadas(informe_id), [(1, 'A', 'Punta')])

    def test_otro_patologo_y_el_auditor_no_las_modifican(self):
        # D-2: solo el autor o un admin edita el informe.
        informe_id = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        otro = Usuario.objects.create_user(username='otro_canastillas', password='x', rol=Usuario.Rol.PATOLOGO)
        auditor = Usuario.objects.create_user(username='auditor_canastillas', password='x', rol=Usuario.Rol.AUDITOR)
        for usuario in (otro, auditor):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(usuario)
                respuesta = self.client.patch(self.url(informe_id), {'canastillas': []}, format='json')
                self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(len(self.client.get(self.url(informe_id)).data['canastillas']), 1)
        self.assertEqual(self.guardadas(informe_id), [(1, 'A', 'Punta')])

    def test_las_canastillas_no_aparecen_en_la_descripcion_ni_generan_diagnosticos(self):
        respuesta = self.crear(
            canastillas=[{'codigo': 'A', 'region': 'Lesión', 'descripcion': 'Tejido sospechoso de malignidad'}]
        )
        self.assertNotIn('sospechoso', respuesta.data['texto_generado'])
        self.assertNotIn('Canastilla', respuesta.data['texto_generado'])
        self.assertEqual(respuesta.data['diagnosticos'], [])

    def test_el_listado_no_trae_las_canastillas(self):
        self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}])
        self.assertNotIn('canastillas', self.client.get(self.URL).data['results'][0])

    def test_el_detalle_no_hace_una_consulta_por_canastilla(self):
        from django.test.utils import CaptureQueriesContext

        una = self.crear(canastillas=[{'codigo': 'A', 'region': 'x'}]).data['id']
        diez = self.crear(canastillas=[{'codigo': str(n), 'region': 'x'} for n in range(10)]).data['id']

        def contar(informe_id):
            with CaptureQueriesContext(connection) as consultas:
                self.client.get(self.url(informe_id))
            return len(consultas)

        self.assertEqual(contar(diez), contar(una))

    def test_borrar_un_borrador_borra_sus_canastillas(self):
        informe_id = self.crear(canastillas=[{'codigo': 'A', 'region': 'Punta'}]).data['id']
        self.assertEqual(self.client.delete(self.url(informe_id)).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Canastilla.objects.exists())


class DescripcionSegunPlantillaTests(TestCase):
    """
    generar_descripcion_macroscopica (D-18): redacta solo lo registrado, con la etiqueta
    real del campo cuando la frase del MAPEO no corresponde, y sin los campos que no aplican.
    """

    def setUp(self):
        self.patologia = Patologia.objects.create(nombre='Vesícula de prueba')
        crear = partial_plantilla(self.patologia)
        crear('tipo_estudio', 'Tipo de colecistectomía', tipo_campo='lista', opciones=['No tumoral', 'Tumoral'])
        crear('consistencia', 'Pared (espesor)')
        crear('dimensiones', 'Dimensiones (cm)')
        crear('ganglios', 'Ganglios linfáticos', tipo_campo='numero')
        crear('necrosis', 'Necrosis', tipo_campo='boolean')
        crear(
            'tumor_forma',
            'Tumor: forma',
            condicion={'campo': 'tipo_estudio', 'valores': ['Tumoral']},
        )

    def describir(self, datos):
        return generar_descripcion_macroscopica(self.patologia, datos)

    def test_usa_la_etiqueta_si_la_frase_del_nombre_diria_otra_cosa(self):
        texto = self.describir({'consistencia': '3 mm', 'dimensiones': '8 x 3'})
        self.assertIn('Pared (espesor): 3 mm.', texto)
        self.assertNotIn('La consistencia es', texto)
        self.assertIn('Las dimensiones son 8 x 3.', texto)  # esta frase sí corresponde

    def test_cero_y_no_se_redactan(self):
        texto = self.describir({'ganglios': 0, 'necrosis': False})
        self.assertIn('Se identifican 0 ganglio(s) linfático(s).', texto)
        self.assertIn('Se observa necrosis: No.', texto)

    def test_un_campo_vacio_no_se_menciona(self):
        texto = self.describir({'dimensiones': '8 x 3', 'ganglios': None, 'consistencia': '  '})
        self.assertNotIn('ganglio', texto)
        self.assertNotIn('Pared', texto)

    def test_un_campo_que_no_aplica_no_aparece_aunque_tenga_valor(self):
        texto = self.describir({'tipo_estudio': 'No tumoral', 'tumor_forma': 'Polipoide'})
        self.assertNotIn('Polipoide', texto)
        texto = self.describir({'tipo_estudio': 'Tumoral', 'tumor_forma': 'Polipoide'})
        self.assertIn('Tumor: forma: Polipoide.', texto)

    def test_un_dato_antiguo_sin_plantilla_se_conserva(self):
        self.assertIn('Clave antigua: valor.', self.describir({'clave_antigua': 'valor'}))


def partial_plantilla(patologia):
    """Crea plantillas de una patología con orden consecutivo (pruebas de la descripción)."""
    contador = iter(range(1, 100))

    def crear(campo_nombre, campo_label, **extra):
        return Plantilla.objects.create(
            patologia=patologia, campo_nombre=campo_nombre, campo_label=campo_label, orden=next(contador), **extra
        )

    return crear


class PdfMuestreoTests(APITestCase):
    """El PDF lleva la sección MUESTREO PARA HISTOLOGÍA solo si hay canastillas (D-18). Solo datos ficticios."""

    URL = '/api/informes/'

    def setUp(self):
        self.autor = Usuario.objects.create_user(
            username='patologo_pdf_muestreo', password='ClaveSegura-2026', rol=Usuario.Rol.PATOLOGO
        )
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Patología PDF muestreo')
        self.paciente = paciente_ficticio()

    def crear(self, canastillas):
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {'localizacion': 'Dorso de la mano'},
            'descripcion_microscopica': 'Texto microscópico.',
            'canastillas': canastillas,
        }
        respuesta = self.client.post(self.URL, cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        return respuesta.data['id']

    def generar(self, informe_id):
        from reportlab.lib.colors import toColor
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import Paragraph

        with (
            mock.patch('informes.utils.Paragraph', wraps=Paragraph) as parrafos,
            mock.patch.object(Canvas, 'setFillColor', autospec=True, side_effect=Canvas.setFillColor) as rellenos,
            mock.patch.object(Canvas, 'setStrokeColor', autospec=True, side_effect=Canvas.setStrokeColor) as trazos,
        ):
            respuesta = self.client.get(f'{self.URL}{informe_id}/pdf/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        return {
            'textos': [str(llamada.args[0]) for llamada in parrafos.call_args_list],
            'colores': {
                toColor(llamada.args[1]).hexval() for llamada in rellenos.call_args_list + trazos.call_args_list
            },
        }

    def test_la_seccion_va_despues_de_la_macroscopica_y_escapa_el_texto(self):
        informe_id = self.crear(
            [
                {
                    'codigo': 'A',
                    'region': 'Punta <b>',
                    'descripcion': 'Corte & sección',
                    'cantidad': 2,
                    'motivo': 'Margen',
                }
            ]
        )
        textos = self.generar(informe_id)['textos']
        macro, muestreo, micro = (
            textos.index('DESCRIPCIÓN MACROSCÓPICA'),
            textos.index('MUESTREO PARA HISTOLOGÍA'),
            textos.index('DESCRIPCIÓN MICROSCÓPICA'),
        )
        self.assertLess(macro, muestreo)
        self.assertLess(muestreo, micro)
        self.assertIn('Punta &lt;b&gt;', textos)
        self.assertIn('Corte &amp; sección', textos)
        self.assertIn('Motivo: Margen', textos)

    def test_sin_canastillas_no_hay_seccion(self):
        self.assertNotIn('MUESTREO PARA HISTOLOGÍA', self.generar(self.crear([]))['textos'])

    def test_la_tabla_va_en_negro(self):
        informe_id = self.crear([{'codigo': 'A', 'region': 'Punta'}])
        self.assertLessEqual(self.generar(informe_id)['colores'], {'0x000000', '0xc53030'})


class AdminCanastillasTests(TestCase):
    """En /admin/, las canastillas de un finalizado son de solo lectura, como sus diagnósticos (D-14, D-18)."""

    def setUp(self):
        superusuario = Usuario.objects.create_superuser(
            username='super_admin_canastillas', password='ClaveSegura-2026', rol=Usuario.Rol.ADMIN
        )
        self.client.force_login(superusuario)
        self.autor = Usuario.objects.create_user(
            username='patologo_admin_canastillas', password='ClaveSegura-2026', rol=Usuario.Rol.PATOLOGO
        )

    def crear_informe(self, finalizado):
        informe = Informe.objects.create(
            patologia=Patologia.objects.create(nombre=f'Patología admin canastillas {finalizado}'),
            autor=self.autor,
            paciente=paciente_ficticio(numero=f'PRUEBA{int(finalizado)}'),
        )
        Canastilla.objects.create(informe=informe, orden=1, codigo='A', region='Original')
        if finalizado:
            informe.estado = Informe.Estado.FINALIZADO
            informe.datos_finalizacion = informe.datos_para_congelar()
            informe.save()
        return informe

    def guardar_ficha(self, informe, **cambios):
        ficha = f'/admin/informes/informe/{informe.id}/change/'
        datos = datos_formulario_admin(self.client.get(ficha))
        datos.update(cambios)
        return self.client.post(ficha, datos)

    def test_no_se_cambian_ni_borran_las_canastillas_de_un_finalizado(self):
        informe = self.crear_informe(finalizado=True)
        self.guardar_ficha(informe, **{'canastillas-0-region': 'Cambiada', 'canastillas-0-DELETE': 'on'})
        self.assertEqual(list(informe.canastillas.values_list('region', flat=True)), ['Original'])

    def test_las_canastillas_de_un_borrador_se_editan(self):
        informe = self.crear_informe(finalizado=False)
        respuesta = self.guardar_ficha(informe, **{'canastillas-0-region': 'Cambiada'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(informe.canastillas.get().region, 'Cambiada')


def textos_del_pdf(cliente, informe_id):
    """Descarga el PDF y devuelve, en orden, los textos de sus Paragraph."""
    from reportlab.platypus import Paragraph

    with mock.patch('informes.utils.Paragraph', wraps=Paragraph) as espia:
        respuesta = cliente.get(f'/api/informes/{informe_id}/pdf/')
    assert respuesta.status_code == status.HTTP_200_OK, respuesta.status_code
    return [str(llamada.args[0]) for llamada in espia.call_args_list]


def parrafo_macroscopica(textos):
    """El párrafo que sigue al título DESCRIPCIÓN MACROSCÓPICA (None si no hay sección)."""
    if 'DESCRIPCIÓN MACROSCÓPICA' not in textos:
        return None
    return textos[textos.index('DESCRIPCIÓN MACROSCÓPICA') + 1]


class DescripcionMacroscopicaEditableTests(APITestCase):
    """
    Tarea 1 de docs/mejoras-objetivos-investigacion.md (OE2): el patólogo revisa y ajusta
    la descripción macroscópica sugerida sin perder el texto que generó el sistema.
    `texto_generado` sigue igual que antes; `descripcion_macroscopica_final` guarda el texto
    revisado y `descripcion_macroscopica_base`, el texto sugerido del que partió la edición
    (decisión del usuario del 2026-11-12, opción A). Solo datos ficticios.
    """

    URL = '/api/informes/'

    def setUp(self):
        self.autor = Usuario.objects.create_user(
            username='patologo_macro_editable',
            password='ClaveSegura-2026',
            rol=Usuario.Rol.PATOLOGO,
            registro_medico='RM-PRUEBA-0001',
        )
        self.client.force_authenticate(self.autor)
        self.patologia = Patologia.objects.create(nombre='Biopsia Ficticia')
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='localizacion', campo_label='Localización', orden=1
        )
        self.paciente = paciente_ficticio()

    def url(self, informe_id):
        return f'{self.URL}{informe_id}/'

    def crear(self, **extra):
        cuerpo = {
            'patologia': self.patologia.id,
            'paciente': self.paciente.id,
            'datos_ingresados': {'localizacion': 'dorso de la mano'},
            'descripcion_microscopica': 'Proliferación de células basaloides.',
            'diagnosticos': [{'descripcion': 'Diagnóstico ficticio'}],
            **extra,
        }
        respuesta = self.client.post(self.URL, cuerpo, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        return respuesta.data

    def sugerido(self, localizacion='dorso de la mano'):
        return generar_descripcion_macroscopica(self.patologia, {'localizacion': localizacion})

    def test_un_informe_nuevo_no_tiene_texto_revisado(self):
        datos = self.crear()
        self.assertEqual(datos['descripcion_macroscopica_final'], '')
        self.assertEqual(datos['descripcion_macroscopica_base'], '')
        self.assertEqual(datos['texto_generado'], self.sugerido())
        self.assertEqual(datos['descripcion_macroscopica_vigente'], self.sugerido())

    def test_se_crea_un_borrador_con_el_texto_revisado(self):
        datos = self.crear(
            descripcion_macroscopica_final='Texto revisado por el patólogo.',
            descripcion_macroscopica_base=self.sugerido(),
        )
        informe = Informe.objects.get(pk=datos['id'])
        self.assertEqual(informe.descripcion_macroscopica_final, 'Texto revisado por el patólogo.')
        self.assertEqual(informe.descripcion_macroscopica_base, self.sugerido())
        # El texto sugerido se sigue generando igual que antes.
        self.assertEqual(informe.texto_generado, self.sugerido())
        self.assertEqual(datos['descripcion_macroscopica_vigente'], 'Texto revisado por el patólogo.')

    def test_se_edita_el_texto_revisado_de_un_borrador(self):
        informe_id = self.crear()['id']
        respuesta = self.client.patch(
            self.url(informe_id),
            {'descripcion_macroscopica_final': 'Ajustado.', 'descripcion_macroscopica_base': self.sugerido()},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data['descripcion_macroscopica_vigente'], 'Ajustado.')
        self.assertEqual(respuesta.data['texto_generado'], self.sugerido())

    def test_si_cambian_los_datos_no_se_sobrescribe_el_texto_revisado(self):
        informe_id = self.crear(
            descripcion_macroscopica_final='Mi versión.',
            descripcion_macroscopica_base=self.sugerido(),
        )['id']
        respuesta = self.client.patch(
            self.url(informe_id), {'datos_ingresados': {'localizacion': 'antebrazo'}}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        # El sugerido cambia, pero la edición y su base se conservan: la diferencia entre
        # la base y el sugerido es lo que hace aparecer el aviso en la pantalla.
        self.assertEqual(respuesta.data['texto_generado'], self.sugerido('antebrazo'))
        self.assertEqual(respuesta.data['descripcion_macroscopica_final'], 'Mi versión.')
        self.assertEqual(respuesta.data['descripcion_macroscopica_base'], self.sugerido())

    def test_restaurar_el_texto_sugerido_vacia_el_texto_revisado_y_su_base(self):
        informe_id = self.crear(
            descripcion_macroscopica_final='Mi versión.',
            descripcion_macroscopica_base=self.sugerido(),
        )['id']
        respuesta = self.client.patch(
            self.url(informe_id),
            {'descripcion_macroscopica_final': '', 'descripcion_macroscopica_base': ''},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data['descripcion_macroscopica_vigente'], self.sugerido())

    def test_un_texto_revisado_solo_con_espacios_cuenta_como_vacio(self):
        datos = self.crear(descripcion_macroscopica_final='   \n ', descripcion_macroscopica_base=self.sugerido())
        self.assertEqual(datos['descripcion_macroscopica_final'], '')
        self.assertEqual(datos['descripcion_macroscopica_base'], '')
        self.assertEqual(datos['descripcion_macroscopica_vigente'], self.sugerido())

    def test_no_se_edita_el_texto_revisado_de_un_finalizado(self):
        informe_id = self.crear(descripcion_macroscopica_final='Versión firmada.')['id']
        self.assertEqual(self.client.post(f'{self.url(informe_id)}finalizar/').status_code, status.HTTP_200_OK)
        respuesta = self.client.patch(
            self.url(informe_id), {'descripcion_macroscopica_final': 'Cambio tardío.'}, format='json'
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Informe.objects.get(pk=informe_id).descripcion_macroscopica_final, 'Versión firmada.')

    def test_el_pdf_usa_el_texto_revisado_escapado(self):
        informe_id = self.crear(descripcion_macroscopica_final='Revisado <b>a mano</b> & listo.\nSegunda línea.')['id']
        textos = textos_del_pdf(self.client, informe_id)
        self.assertEqual(
            parrafo_macroscopica(textos),
            'Revisado &lt;b&gt;a mano&lt;/b&gt; &amp; listo.<br/>Segunda línea.',
        )
        self.assertNotIn(texto_seguro(self.sugerido()), textos)

    def test_un_informe_antiguo_sin_texto_revisado_imprime_el_texto_generado_como_antes(self):
        # Creado por el ORM, como los informes de antes de esta tarea: sin los campos nuevos.
        antiguo = Informe.objects.create(
            patologia=self.patologia,
            autor=self.autor,
            paciente=self.paciente,
            texto_generado='Texto generado <i>antiguo</i>.',
        )
        self.assertEqual(antiguo.descripcion_macroscopica_final, '')
        self.assertEqual(antiguo.descripcion_macroscopica_vigente(), 'Texto generado <i>antiguo</i>.')
        textos = textos_del_pdf(self.client, antiguo.id)
        self.assertEqual(parrafo_macroscopica(textos), 'Texto generado &lt;i&gt;antiguo&lt;/i&gt;.')

    def test_sin_texto_generado_ni_revisado_no_hay_seccion_macroscopica(self):
        antiguo = Informe.objects.create(patologia=self.patologia, autor=self.autor, paciente=self.paciente)
        self.assertIsNone(parrafo_macroscopica(textos_del_pdf(self.client, antiguo.id)))


class VistaPreviaMacroscopicaTests(APITestCase):
    """
    POST /api/informes/vista-previa-macroscopica/ (tarea 1, decisión del usuario del
    2026-11-12): calcula el texto sugerido con la misma generar_descripcion_macroscopica a
    partir de la patología y los datos del formulario, sin guardar nada ni gastar un
    número de petición (D-7). Solo datos ficticios.
    """

    URL = '/api/informes/vista-previa-macroscopica/'

    def setUp(self):
        self.patologo = Usuario.objects.create_user(
            username='patologo_vista_previa', password='ClaveSegura-2026', rol=Usuario.Rol.PATOLOGO
        )
        self.patologia = Patologia.objects.create(nombre='Biopsia Vista Previa')
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='localizacion', campo_label='Localización', orden=1
        )
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='peso', campo_label='Peso', tipo_campo='numero', orden=2
        )
        self.client.force_authenticate(self.patologo)

    def pedir(self, datos, patologia=None):
        return self.client.post(
            self.URL,
            {'patologia': patologia or self.patologia.id, 'datos_ingresados': datos},
            format='json',
        )

    def test_devuelve_el_mismo_texto_que_se_genera_al_guardar(self):
        datos = {'localizacion': 'dorso de la mano', 'peso': 3}
        respuesta = self.pedir(datos)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(respuesta.data, {'texto_sugerido': generar_descripcion_macroscopica(self.patologia, datos)})

    def test_no_guarda_nada_ni_gasta_un_numero_de_peticion(self):
        self.pedir({'localizacion': 'antebrazo'})
        self.assertFalse(Informe.objects.exists())
        self.assertFalse(ConsecutivoPeticion.objects.exists())

    def test_acepta_un_formulario_a_medias(self):
        # Mientras se llena el formulario faltan obligatorios: la vista previa no los exige.
        Plantilla.objects.create(
            patologia=self.patologia, campo_nombre='bordes', campo_label='Bordes', obligatorio=True, orden=3
        )
        respuesta = self.pedir({'localizacion': 'antebrazo'})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)

    def test_rechaza_datos_que_no_son_un_objeto(self):
        respuesta = self.pedir([1, 2])
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('datos_ingresados', respuesta.data)

    def test_rechaza_un_numero_no_valido_como_al_guardar(self):
        respuesta = self.pedir({'peso': -2})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no puede ser negativo', str(respuesta.data['datos_ingresados']))

    def test_rechaza_una_patologia_que_no_existe(self):
        respuesta = self.pedir({}, patologia=999999)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('patologia', respuesta.data)

    def test_el_auditor_no_la_usa(self):
        auditor = Usuario.objects.create_user(
            username='auditor_vista_previa', password='ClaveSegura-2026', rol=Usuario.Rol.AUDITOR
        )
        self.client.force_authenticate(auditor)
        self.assertEqual(self.pedir({}).status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_sesion_responde_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.pedir({}).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

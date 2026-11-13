import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useBlocker } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import client, { LISTA_COMPLETA, resultados } from '../api/client';
import EstadoBadge from '../components/EstadoBadge';
import SelectorPaciente from '../components/informe/SelectorPaciente';
import DatosSolicitud from '../components/informe/DatosSolicitud';
import ListaDiagnosticos, { conClaves, sinClaves } from '../components/informe/ListaDiagnosticos';
import MuestreoHistologia, {
  conClaves as canastillasConClaves,
  sinClaves as canastillasSinClaves,
  erroresCanastillas,
} from '../components/informe/MuestreoHistologia';
import SeccionFirma from '../components/informe/SeccionFirma';
import SeccionAdendas from '../components/informe/SeccionAdendas';
import DescripcionMacroscopica, { sugeridoCambio } from '../components/informe/DescripcionMacroscopica';
import useOpciones from '../hooks/useOpciones';
import { conOpcionActual, hoyISO } from '../utils/formularios';
import { agruparPorSeccion, camposAplicables, esVacio } from '../utils/reglas';

// Datos de la solicitud (informe v2, etapa 4) con los nombres de campo de la API.
const solicitudVacia = () => ({
  medico_tratante: '',
  fecha_ingreso: hoyISO(),
  eps: '',
  servicio: '',
  numero_orden_externa: '',
  estudios_solicitados: '',
});

// D-13: un borrador existente se autoguarda este tiempo después del último cambio.
export const ESPERA_AUTOGUARDADO_MS = 5000;
// Tarea 1: la vista previa del texto sugerido se pide este tiempo después del último cambio.
export const ESPERA_VISTA_PREVIA_MS = 800;

const formatoHora = new Intl.DateTimeFormat('es-CO', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Bogota',
});

// Convierte la respuesta de error de la API en los errores del formulario.
function erroresDeRespuesta(err) {
  const detail = err.response?.data;
  if (!detail || typeof detail !== 'object') return { general: 'Ocurrió un error al guardar el informe.' };
  const errores = {};
  Object.entries(detail).forEach(([key, val]) => {
    // Los errores de los diagnósticos vienen por fila ([{}, {codigo_cie10: [...]}]):
    // se conservan así para mostrarlos junto a cada fila.
    const porFila = Array.isArray(val) && val.some((v) => typeof v === 'object');
    errores[key] = Array.isArray(val) && !porFila ? val.join(' ') : val;
  });
  return errores;
}

export default function InformePage() {
  const { id } = useParams();
  const isEditing = Boolean(id);
  const navigate = useNavigate();
  const { user, canWrite, isAdmin } = useAuth();
  const { opciones } = useOpciones();

  const [patologias, setPatologias] = useState([]);
  const [selectedPatologia, setSelectedPatologia] = useState(null);
  const [plantillas, setPlantillas] = useState([]);
  const [formData, setFormData] = useState({});
  const [paciente, setPaciente] = useState(null); // con la forma de paciente_datos
  const [solicitud, setSolicitud] = useState(solicitudVacia);
  const [tipoEstudio, setTipoEstudio] = useState('histologia');
  const [epsActivas, setEpsActivas] = useState([]);
  const [serviciosActivos, setServiciosActivos] = useState([]);
  const [tipoMuestra, setTipoMuestra] = useState('');
  // Contenido del informe (informe v2, etapa 5). `comentarios` era `notas` (P-5).
  const [microscopica, setMicroscopica] = useState('');
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [comentarios, setComentarios] = useState('');
  // Muestreo para histología (D-18): canastillas e indicaciones del manual de la patología.
  const [canastillas, setCanastillas] = useState([]);
  const [guiaMuestreo, setGuiaMuestreo] = useState([]);
  // Descripción macroscópica (tarea 1): el sugerido por el sistema, la versión del patólogo
  // y el sugerido del que partió. `cambiosDatos` cuenta los cambios en los campos de la
  // plantilla: solo ellos piden una vista previa nueva.
  const [textoSugerido, setTextoSugerido] = useState('');
  const [macroscopica, setMacroscopica] = useState({ final: '', base: '' });
  const [cambiosDatos, setCambiosDatos] = useState(0);
  const [informe, setInforme] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [successMsg, setSuccessMsg] = useState('');
  const [confirmFinalizar, setConfirmFinalizar] = useState(false);
  // Cambios sin guardar (D-13): `version` cuenta los cambios del usuario y
  // `versionGuardada` es la que tenía el formulario en el último guardado.
  const [version, setVersion] = useState(0);
  const [versionGuardada, setVersionGuardada] = useState(0);
  const [autoguardado, setAutoguardado] = useState(null); // { tipo: 'guardando' | 'guardado' | 'invalido' | 'error', hora }
  const versionRef = useRef(0);
  versionRef.current = version;
  const guardandoRef = useRef(false);

  // Un informe nuevo lo puede crear cualquier patólogo o admin; uno existente solo
  // lo puede editar o finalizar su autor o un admin (decisión D-2).
  const puedeEditar = isEditing ? canWrite && Boolean(informe) && (isAdmin || informe.autor === user?.id) : canWrite;
  const soloLectura = informe?.estado === 'finalizado' || !puedeEditar;
  const hayCambiosSinGuardar = !soloLectura && version !== versionGuardada;
  // Solo un borrador que ya existe se autoguarda: uno nuevo gastaría un número de petición (D-7).
  const autoguardable = isEditing && informe?.estado === 'borrador' && puedeEditar;
  // El bloqueo de la navegación lee este ref, para poder desactivarlo justo antes de navegar.
  const sucioRef = useRef(false);
  sucioRef.current = hayCambiosSinGuardar;

  const marcarCambio = () => {
    setVersion((v) => v + 1);
    setAutoguardado(null);
  };

  // Salir de la pantalla con cambios sin guardar pide confirmar (D-13), también al cerrar
  // sesión ("Salir" pasa por /salir). No se frena la salida hacia /login: solo ocurre
  // cuando la sesión ya terminó (por ejemplo, porque venció).
  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }) =>
        sucioRef.current && currentLocation.pathname !== nextLocation.pathname && nextLocation.pathname !== '/login',
      [],
    ),
  );

  // Cerrar la pestaña o recargar con cambios sin guardar: aviso del navegador.
  useEffect(() => {
    if (!hayCambiosSinGuardar) return undefined;
    const avisar = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', avisar);
    return () => window.removeEventListener('beforeunload', avisar);
  }, [hayCambiosSinGuardar]);
  // El PDF de un borrador es una vista previa solo para su autor o un admin (decisión D-12).
  const borrador = informe?.estado !== 'finalizado';
  const puedeVerPdf = Boolean(informe) && (!borrador || puedeEditar);

  // Carga la lista de patologías
  useEffect(() => {
    // Al crear un informe solo se ofrecen las patologías activas (decisión D-4). Al editar se
    // piden todas, para que se vea la patología de un informe viejo aunque esté desactivada.
    const params = isEditing ? LISTA_COMPLETA : { ...LISTA_COMPLETA, activa: 'true' };
    client
      .get('/patologias/', { params })
      .then(({ data }) => setPatologias(resultados(data)))
      .catch(() =>
        setErrors((prev) => ({ ...prev, general: 'No se pudieron cargar las patologías. Recarga la página.' })),
      );
    // isEditing es Boolean(id): nuevo y edición son rutas distintas, así que no cambia sin volver a montar.
  }, [isEditing]);

  // EPS y servicios activos (D-4). La EPS o el servicio de un informe guardado se
  // agregan aparte si ya se desactivaron (conOpcionActual).
  useEffect(() => {
    Promise.all([
      client.get('/pacientes/eps/', { params: { ...LISTA_COMPLETA, activa: 'true' } }),
      client.get('/servicios/', { params: { ...LISTA_COMPLETA, activo: 'true' } }),
    ])
      .then(([eps, servicios]) => {
        setEpsActivas(resultados(eps.data));
        setServiciosActivos(resultados(servicios.data));
      })
      .catch(() =>
        setErrors((prev) => ({
          ...prev,
          general: 'No se pudieron cargar las EPS y los servicios. Recarga la página.',
        })),
      );
  }, []);

  // Carga el informe si se está editando uno existente
  useEffect(() => {
    if (isEditing) {
      setLoading(true);
      client
        .get(`/informes/${id}/`)
        .then(({ data }) => {
          setInforme(data);
          setPaciente(data.paciente_datos);
          setSolicitud({
            medico_tratante: data.medico_tratante || '',
            fecha_ingreso: data.fecha_ingreso || '',
            eps: data.eps ?? '',
            servicio: data.servicio ?? '',
            numero_orden_externa: data.numero_orden_externa || '',
            estudios_solicitados: data.estudios_solicitados || '',
          });
          setTipoEstudio(data.tipo_estudio || 'histologia');
          setTipoMuestra(data.tipo_muestra || '');
          setMicroscopica(data.descripcion_microscopica || '');
          setDiagnosticos(conClaves(data.diagnosticos));
          setCanastillas(canastillasConClaves(data.canastillas));
          setComentarios(data.comentarios || '');
          setTextoSugerido(data.texto_generado || '');
          setMacroscopica({
            final: data.descripcion_macroscopica_final || '',
            base: data.descripcion_macroscopica_base || '',
          });
          setFormData(data.datos_ingresados || {});
          setSelectedPatologia(data.patologia);
        })
        .catch(() => navigate('/'))
        .finally(() => setLoading(false));
    }
  }, [id, isEditing, navigate]);

  // Carga los campos de la plantilla al cambiar de patología
  useEffect(() => {
    if (selectedPatologia) {
      client
        .get(`/patologias/${selectedPatologia}/`)
        .then(({ data }) => {
          setPlantillas(data.plantillas || []);
          setGuiaMuestreo(data.guia_muestreo || []);
          // Valores por defecto de los campos
          if (!isEditing) {
            const defaults = {};
            (data.plantillas || []).forEach((p) => {
              if (p.valor_defecto) defaults[p.campo_nombre] = p.valor_defecto;
            });
            setFormData((prev) => ({ ...defaults, ...prev }));
          }
        })
        .catch(() => {
          setErrors((prev) => ({
            ...prev,
            general: 'No se pudieron cargar los campos de la patología. Recarga la página.',
          }));
        });
    } else {
      setPlantillas([]);
      setGuiaMuestreo([]);
    }
  }, [selectedPatologia, isEditing]);

  const handleFieldChange = (fieldName, value) => {
    marcarCambio();
    setCambiosDatos((n) => n + 1);
    setFormData((prev) => ({ ...prev, [fieldName]: value }));
    setErrors((prev) => ({ ...prev, [fieldName]: null }));
  };

  // Vista previa del texto sugerido (tarea 1): se pide al backend, que no guarda nada,
  // un momento después del último cambio en los campos de la plantilla. Si falla, se
  // conserva la anterior: al guardar, el backend vuelve a generar el texto.
  useEffect(() => {
    if (!cambiosDatos || soloLectura || !selectedPatologia) return undefined;
    let vigente = true;
    const temporizador = setTimeout(async () => {
      try {
        const { data } = await client.post('/informes/vista-previa-macroscopica/', {
          patologia: selectedPatologia,
          datos_ingresados: formData,
        });
        if (vigente) setTextoSugerido(data.texto_sugerido);
      } catch {
        // Sin vista previa nueva; el texto se regenera al guardar.
      }
    }, ESPERA_VISTA_PREVIA_MS);
    return () => {
      vigente = false;
      clearTimeout(temporizador);
    };
  }, [cambiosDatos, soloLectura, selectedPatologia, formData]);

  const cambiarMacroscopica = (valores) => {
    marcarCambio();
    setMacroscopica(valores);
  };
  const avisoSugeridoCambio = sugeridoCambio({ sugerido: textoSugerido, ...macroscopica });

  const cambiarSolicitud = (campo, valor) => {
    marcarCambio();
    setSolicitud((prev) => ({ ...prev, [campo]: valor }));
    setErrors((prev) => ({ ...prev, [campo]: null }));
  };

  // Al elegir el paciente se precarga su EPS actual, si sigue activa. La del
  // informe se puede cambiar: es la del momento del estudio.
  const seleccionarPaciente = (nuevo) => {
    marcarCambio();
    setPaciente(nuevo);
    setSolicitud((prev) => ({
      ...prev,
      eps: epsActivas.some((e) => e.id === nuevo.eps) ? nuevo.eps : '',
    }));
    setErrors((prev) => ({ ...prev, paciente: null, eps: null }));
  };

  // Errores del formulario sin mostrarlos: los usan validate() y el autoguardado.
  const calcularErrores = () => {
    const newErrors = {};
    if (!paciente) newErrors.paciente = 'Seleccione un paciente.';
    if (!selectedPatologia) newErrors.patologia = 'Seleccione una patología.';

    // Solo se exigen los obligatorios que aplican al procedimiento elegido (D-18); 0 y
    // "No" son respuestas válidas, como en el backend.
    const aplican = camposAplicables(plantillas, formData);
    plantillas
      .filter((p) => p.obligatorio && aplican.has(p.campo_nombre))
      .forEach((p) => {
        if (esVacio(formData[p.campo_nombre])) {
          newErrors[p.campo_nombre] = `${p.campo_label || p.campo_nombre} es obligatorio.`;
        }
      });

    // Errores por fila, con la misma forma que los del backend.
    const erroresDiagnosticos = diagnosticos.map((d) =>
      d.descripcion.trim() ? {} : { descripcion: 'Escriba la descripción del diagnóstico.' },
    );
    if (erroresDiagnosticos.some((e) => e.descripcion)) newErrors.diagnosticos = erroresDiagnosticos;
    const erroresMuestreo = erroresCanastillas(canastillas);
    if (erroresMuestreo) newErrors.canastillas = erroresMuestreo;
    return newErrors;
  };

  const validate = () => {
    const newErrors = calcularErrores();
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // El número de petición no se envía: lo asigna el backend al crear el informe (decisión D-7).
  const armarPayload = () => ({
    paciente: paciente.id,
    ...solicitud,
    eps: solicitud.eps ? Number(solicitud.eps) : null,
    servicio: solicitud.servicio ? Number(solicitud.servicio) : null,
    tipo_estudio: tipoEstudio,
    patologia: selectedPatologia,
    tipo_muestra: tipoMuestra,
    datos_ingresados: formData,
    descripcion_macroscopica_final: macroscopica.final,
    descripcion_macroscopica_base: macroscopica.base,
    descripcion_microscopica: microscopica,
    diagnosticos: sinClaves(diagnosticos),
    canastillas: canastillasSinClaves(canastillas),
    comentarios,
  });

  // Guarda el informe (PUT si existe, POST si es nuevo) y devuelve la respuesta.
  const guardarEnServidor = async () => {
    const payload = armarPayload();
    const { data } = isEditing
      ? await client.put(`/informes/${id}/`, payload)
      : await client.post('/informes/', payload);
    return data;
  };

  // Después de guardar un informe existente. El backend normaliza los códigos CIE-10
  // ("c443" → "C44.3"); se aplican solo si no hubo cambios mientras se guardaba.
  const alGuardarExistente = (data, versionInicio) => {
    setInforme(data);
    if (versionRef.current === versionInicio) {
      setDiagnosticos(conClaves(data.diagnosticos));
      setCanastillas(canastillasConClaves(data.canastillas));
      // El sugerido que generó el backend con los datos guardados.
      if (data.texto_generado !== undefined) setTextoSugerido(data.texto_generado);
    }
    setVersionGuardada(versionInicio);
  };

  // Autoguardado de un borrador existente (D-13): 5 s después del último cambio y solo
  // si el formulario es válido. Nunca se guarda una copia en el navegador.
  const autoguardar = async () => {
    if (guardandoRef.current) return;
    if (Object.keys(calcularErrores()).length > 0) {
      setAutoguardado({ tipo: 'invalido' });
      return;
    }
    const versionInicio = versionRef.current;
    guardandoRef.current = true;
    setAutoguardado({ tipo: 'guardando' });
    try {
      alGuardarExistente(await guardarEnServidor(), versionInicio);
      setAutoguardado({ tipo: 'guardado', hora: new Date() });
    } catch {
      setAutoguardado({ tipo: 'error' });
    } finally {
      guardandoRef.current = false;
    }
  };
  // autoguardar se recrea en cada render. El temporizador llama a la última versión por
  // esta referencia, así que solo se reinicia cuando cambia lo escrito (version), no
  // cuando cambia el indicador de estado ("guardando…").
  const autoguardarRef = useRef(autoguardar);
  autoguardarRef.current = autoguardar;

  useEffect(() => {
    if (!autoguardable || version === versionGuardada) return undefined;
    const temporizador = setTimeout(() => autoguardarRef.current(), ESPERA_AUTOGUARDADO_MS);
    return () => clearTimeout(temporizador);
  }, [autoguardable, version, versionGuardada]);

  // Finalizar y la vista previa del PDF usan lo que hay en pantalla (D-13): si hay cambios
  // sin guardar, primero se guardan. Devuelve false si la validación falla o el servidor
  // los rechaza; los errores quedan a la vista.
  const guardarCambiosPendientes = async () => {
    if (!hayCambiosSinGuardar) return true;
    if (!validate()) return false;
    const versionInicio = versionRef.current;
    guardandoRef.current = true;
    setSaving(true);
    try {
      alGuardarExistente(await guardarEnServidor(), versionInicio);
      return true;
    } catch (err) {
      setErrors(erroresDeRespuesta(err));
      return false;
    } finally {
      guardandoRef.current = false;
      setSaving(false);
    }
  };

  // "Guardar y salir" del aviso: si falla la validación o el servidor rechaza los datos,
  // no se sale y se muestra qué falta (D-13).
  const guardarYSalir = async () => {
    if (!validate()) {
      blocker.reset();
      return;
    }
    const versionInicio = versionRef.current;
    guardandoRef.current = true;
    setSaving(true);
    try {
      await guardarEnServidor();
      sucioRef.current = false;
      setVersionGuardada(versionInicio);
      blocker.proceed();
    } catch (err) {
      setErrors(erroresDeRespuesta(err));
      blocker.reset();
    } finally {
      guardandoRef.current = false;
      setSaving(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    setSuccessMsg('');
    const versionInicio = versionRef.current;
    guardandoRef.current = true;

    try {
      const data = await guardarEnServidor();
      if (isEditing) {
        alGuardarExistente(data, versionInicio);
        setSuccessMsg('Informe actualizado correctamente.');
      } else {
        setSuccessMsg('Informe creado correctamente.');
        // Ya está guardado: pasar a su página no debe pedir confirmación (D-13).
        sucioRef.current = false;
        setVersionGuardada(versionInicio);
        navigate(`/informes/${data.id}`);
      }
    } catch (err) {
      setErrors(erroresDeRespuesta(err));
    } finally {
      guardandoRef.current = false;
      setSaving(false);
    }
  };

  const handleFinalizar = async () => {
    if (!confirmFinalizar) {
      setConfirmFinalizar(true);
      return;
    }
    setConfirmFinalizar(false);
    setSuccessMsg('');
    setErrors({});
    if (!(await guardarCambiosPendientes())) return;
    try {
      const { data } = await client.post(`/informes/${id}/finalizar/`);
      setInforme(data);
      setSuccessMsg('Informe finalizado correctamente.');
    } catch (err) {
      // Si faltan requisitos (decisión D-8), el backend los devuelve todos en `requisitos`.
      const requisitos = err.response?.data?.requisitos;
      if (requisitos?.length) {
        setErrors({ requisitos });
      } else {
        setErrors({ general: err.response?.data?.detail || 'Error al finalizar el informe.' });
      }
    }
  };

  // Descarga el PDF con Axios, que envía el token en la cabecera Authorization.
  // Antes el token iba en la URL (?token=...) y quedaba en el historial (auditoría I-5).
  const downloadPDF = async () => {
    const numero = (informe?.numero_peticion || id).toString().replace(/[^a-zA-Z0-9-]/g, '_');
    const safeName = borrador ? `${numero}_borrador` : numero;
    // La vista previa de un borrador muestra lo que hay en pantalla: se guarda antes (D-13).
    if (borrador && !(await guardarCambiosPendientes())) return;
    try {
      const { data } = await client.get(`/informes/${id}/pdf/`, { responseType: 'blob' });
      // Enlace temporal "blob:" para que el navegador guarde el archivo con su nombre.
      const url = URL.createObjectURL(data);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `informe_${safeName}.pdf`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    } catch {
      setErrors({ general: 'No se pudo descargar el PDF.' });
    }
  };

  const renderField = (plantilla) => {
    const { campo_nombre, campo_label, tipo_campo, opciones, obligatorio, ayuda } = plantilla;
    // ?? y no ||: un 0 guardado se debe ver (antes se mostraba vacío).
    const value = formData[campo_nombre] ?? '';
    const error = errors[campo_nombre];
    const disabled = informe?.estado === 'finalizado' || !puedeEditar;

    return (
      <div className={`form-group ${error ? 'has-error' : ''}`} key={campo_nombre}>
        <label htmlFor={campo_nombre}>
          {campo_label || campo_nombre}
          {obligatorio && <span className="required">*</span>}
        </label>

        {tipo_campo === 'texto' && (
          <input
            id={campo_nombre}
            type="text"
            value={value}
            onChange={(e) => handleFieldChange(campo_nombre, e.target.value)}
            disabled={disabled}
          />
        )}

        {tipo_campo === 'numero' && (
          <input
            id={campo_nombre}
            type="number"
            step="any"
            value={value}
            onChange={(e) => handleFieldChange(campo_nombre, e.target.value)}
            disabled={disabled}
          />
        )}

        {tipo_campo === 'lista' && (
          <select
            id={campo_nombre}
            value={value}
            onChange={(e) => handleFieldChange(campo_nombre, e.target.value)}
            disabled={disabled}
          >
            <option value="">— Seleccione —</option>
            {(opciones || []).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        )}

        {tipo_campo === 'textarea' && (
          <textarea
            id={campo_nombre}
            value={value}
            onChange={(e) => handleFieldChange(campo_nombre, e.target.value)}
            rows={3}
            disabled={disabled}
          />
        )}

        {tipo_campo === 'boolean' && (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={value === true || value === 'true'}
              onChange={(e) => handleFieldChange(campo_nombre, e.target.checked)}
              disabled={disabled}
            />
            <span>{campo_label || campo_nombre}</span>
          </label>
        )}

        {ayuda && <span className="field-help">{ayuda}</span>}
        {error && <span className="field-error">{error}</span>}
      </div>
    );
  };

  // Campos agrupados por sección; los que no aplican al procedimiento elegido no se muestran (D-18).
  const aplican = camposAplicables(plantillas, formData);
  const secciones = agruparPorSeccion(plantillas.filter((p) => aplican.has(p.campo_nombre)));

  if (loading)
    return (
      <div className="loading-center">
        <span className="spinner"></span>
      </div>
    );

  return (
    <div className="informe-page">
      <div className="page-header">
        <div>
          <h1>{isEditing ? `Informe ${informe?.numero_peticion || ''}` : 'Nuevo Informe'}</h1>
          {informe && <EstadoBadge estado={informe.estado} />}
        </div>
      </div>

      {/* Los botones y los mensajes de resultado están en la barra fija del pie (al final). */}
      <form id="formulario-informe" onSubmit={handleSubmit}>
        {/* Orden del informe real (informe v2, etapa 4): Paciente, Datos de la solicitud y Estudio */}
        <SelectorPaciente
          paciente={paciente}
          onSeleccionar={seleccionarPaciente}
          disabled={soloLectura}
          error={errors.paciente}
        />

        <DatosSolicitud
          valores={solicitud}
          onCambiar={cambiarSolicitud}
          epsOpciones={conOpcionActual(epsActivas, solicitud.eps, informe?.eps_nombre)}
          serviciosOpciones={conOpcionActual(
            serviciosActivos,
            solicitud.servicio,
            informe?.servicio_nombre,
            'desactivado',
          )}
          disabled={soloLectura}
          errores={errors}
        />

        <div className="card">
          <div className="card-header">
            <h2>Estudio</h2>
          </div>
          <div className="card-body">
            <div className="form-row">
              <div className={`form-group ${errors.tipo_estudio ? 'has-error' : ''}`}>
                <label htmlFor="tipoEstudio">Tipo de estudio</label>
                <select
                  id="tipoEstudio"
                  value={tipoEstudio}
                  onChange={(e) => {
                    marcarCambio();
                    setTipoEstudio(e.target.value);
                  }}
                  disabled={soloLectura}
                >
                  {opciones.tipos_estudio.map((o) => (
                    <option key={o.valor} value={o.valor}>
                      {o.etiqueta}
                    </option>
                  ))}
                </select>
                {errors.tipo_estudio && <span className="field-error">{errors.tipo_estudio}</span>}
              </div>

              <div className={`form-group ${errors.patologia ? 'has-error' : ''}`}>
                <label htmlFor="patologia">
                  Tipo de Patología <span className="required">*</span>
                </label>
                <select
                  id="patologia"
                  value={selectedPatologia || ''}
                  onChange={(e) => {
                    const val = e.target.value ? parseInt(e.target.value) : null;
                    marcarCambio();
                    setSelectedPatologia(val);
                    if (!isEditing) setFormData({});
                    setErrors((p) => ({ ...p, patologia: null }));
                  }}
                  disabled={isEditing || !puedeEditar}
                >
                  <option value="">— Seleccione patología —</option>
                  {patologias.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
                {errors.patologia && <span className="field-error">{errors.patologia}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="tipoMuestra">Tipo de Muestra</label>
                <input
                  id="tipoMuestra"
                  type="text"
                  value={tipoMuestra}
                  onChange={(e) => {
                    marcarCambio();
                    setTipoMuestra(e.target.value);
                  }}
                  placeholder="Ej: Biopsia escisional"
                  disabled={soloLectura}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Contenido en el orden del informe real (informe v2, etapa 5): macroscópica
            (campos dinámicos y texto generado), microscópica, diagnósticos y comentarios */}
        {(plantillas.length > 0 || informe?.texto_generado || macroscopica.final) && (
          <div className="card">
            <div className="card-header">
              <h2>Descripción macroscópica</h2>
            </div>
            <div className="card-body">
              {secciones.map((seccion) => (
                <section key={seccion.nombre || 'sin-seccion'} className="seccion-plantilla">
                  {seccion.nombre && <h3 className="seccion-plantilla-titulo">{seccion.nombre}</h3>}
                  <div className="dynamic-fields">{seccion.campos.map(renderField)}</div>
                </section>
              ))}
              {/* Texto sugerido y versión revisada por el patólogo (tarea 1) */}
              <DescripcionMacroscopica
                sugerido={textoSugerido}
                final={macroscopica.final}
                base={macroscopica.base}
                onCambiar={cambiarMacroscopica}
                disabled={soloLectura}
              />
            </div>
          </div>
        )}

        {/* El muestreo va aparte de la macroscópica: es lo que se envió a procesar (D-18). */}
        {selectedPatologia && (
          <MuestreoHistologia
            canastillas={canastillas}
            onCambiar={(lista) => {
              marcarCambio();
              setCanastillas(lista);
              setErrors((prev) => ({ ...prev, canastillas: null }));
            }}
            disabled={soloLectura}
            guia={guiaMuestreo}
            error={errors.canastillas}
          />
        )}

        <div className="card">
          <div className="card-header">
            <h2>Descripción microscópica</h2>
          </div>
          <div className="card-body">
            <div className={`form-group ${errors.descripcion_microscopica ? 'has-error' : ''}`}>
              <textarea
                id="descripcionMicroscopica"
                aria-label="Descripción microscópica"
                value={microscopica}
                onChange={(e) => {
                  marcarCambio();
                  setMicroscopica(e.target.value);
                }}
                rows={5}
                placeholder="Hallazgos al microscopio..."
                disabled={soloLectura}
              />
              {errors.descripcion_microscopica && (
                <span className="field-error">{errors.descripcion_microscopica}</span>
              )}
            </div>
          </div>
        </div>

        <ListaDiagnosticos
          diagnosticos={diagnosticos}
          onCambiar={(lista) => {
            marcarCambio();
            setDiagnosticos(lista);
            setErrors((prev) => ({ ...prev, diagnosticos: null }));
          }}
          disabled={soloLectura}
          error={errors.diagnosticos}
        />

        <div className="card">
          <div className="card-header">
            <h2>Comentarios</h2>
          </div>
          <div className="card-body">
            <div className={`form-group ${errors.comentarios ? 'has-error' : ''}`}>
              <textarea
                id="comentarios"
                aria-label="Comentarios"
                value={comentarios}
                onChange={(e) => {
                  marcarCambio();
                  setComentarios(e.target.value);
                }}
                rows={3}
                placeholder="Comentarios para el médico tratante..."
                disabled={soloLectura}
              />
              {errors.comentarios && <span className="field-error">{errors.comentarios}</span>}
            </div>
          </div>
        </div>

        <SeccionFirma firma={informe?.firma} estado={informe?.estado} fechaInforme={informe?.fecha_informe} />
      </form>

      {blocker.state === 'blocked' && (
        <div className="modal-overlay">
          <div className="modal-card aviso-salir" role="dialog" aria-modal="true" aria-labelledby="aviso-salir-titulo">
            <h2 id="aviso-salir-titulo">Tienes cambios sin guardar</h2>
            <p>Si sales ahora, se perderá lo que no se ha guardado.</p>
            <div className="aviso-salir-acciones">
              <button type="button" className="btn btn-outline" onClick={() => blocker.reset()} disabled={saving}>
                Seguir editando
              </button>
              <button
                type="button"
                className="btn btn-danger-outline"
                onClick={() => blocker.proceed()}
                disabled={saving}
              >
                Salir sin guardar
              </button>
              <button type="button" className="btn btn-primary" onClick={guardarYSalir} disabled={saving}>
                {saving ? <span className="spinner"></span> : 'Guardar y salir'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fuera del <form>: una adenda se guarda con su propia petición (decisión D-9). */}
      {informe && (
        <SeccionAdendas
          informeId={informe.id}
          estado={informe.estado}
          adendas={informe.adendas}
          puedeAgregar={puedeEditar}
          onAgregada={(adenda) => setInforme((prev) => ({ ...prev, adendas: [...(prev.adendas || []), adenda] }))}
        />
      )}

      {/* Barra fija al pie (pedido del usuario, 2026-11-12): los botones y el resultado de cada
          acción se ven sin tener que subir. Va fuera del <form>; el botón de guardar lo envía
          con el atributo form. */}
      <section className="barra-acciones" aria-label="Acciones del informe">
        {successMsg && <div className="alert alert-success">{successMsg}</div>}
        {/* Los errores llevan role="alert": los lectores de pantalla los anuncian al aparecer. */}
        {(errors.general || errors.detail) && (
          <div className="alert alert-error" role="alert">
            {errors.general || errors.detail}
          </div>
        )}
        {/* Campos obligatorios de la plantilla que rechazó el backend: antes no se mostraban. */}
        {typeof errors.datos_ingresados === 'string' && (
          <div className="alert alert-error" role="alert">
            {errors.datos_ingresados}
          </div>
        )}
        {errors.requisitos && (
          <div className="alert alert-error alert-lista" role="alert">
            <p>No se puede finalizar el informe:</p>
            <ul>
              {errors.requisitos.map((requisito) => (
                <li key={requisito}>{requisito}</li>
              ))}
            </ul>
          </div>
        )}
        {confirmFinalizar && avisoSugeridoCambio && (
          <p className="aviso-finalizar">
            El texto sugerido cambió después de su edición de la descripción macroscópica: se finalizará con su versión.
          </p>
        )}

        <div className="barra-acciones-fila">
          <IndicadorGuardado sinGuardar={hayCambiosSinGuardar} autoguardado={autoguardado} />
          <div className="barra-acciones-botones">
            {puedeEditar && informe?.estado !== 'finalizado' && (
              <button type="button" className="btn btn-outline" onClick={() => navigate('/')}>
                Cancelar
              </button>
            )}
            {isEditing && puedeVerPdf && (
              <button type="button" className="btn btn-outline" onClick={downloadPDF}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="7,10 12,15 17,10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                {borrador ? 'Vista previa (borrador)' : 'Exportar PDF'}
              </button>
            )}
            {puedeEditar && informe?.estado !== 'finalizado' && (
              <button type="submit" form="formulario-informe" className="btn btn-primary" disabled={saving}>
                {saving ? <span className="spinner"></span> : isEditing ? 'Actualizar Informe' : 'Guardar Informe'}
              </button>
            )}
            {isEditing &&
              puedeEditar &&
              informe?.estado === 'borrador' &&
              (confirmFinalizar ? (
                <>
                  <button type="button" className="btn btn-success" onClick={handleFinalizar}>
                    Si, Confirmar
                  </button>
                  <button type="button" className="btn btn-outline btn-sm" onClick={() => setConfirmFinalizar(false)}>
                    Cancelar
                  </button>
                </>
              ) : (
                <button type="button" className="btn btn-success" onClick={handleFinalizar}>
                  Finalizar Informe
                </button>
              ))}
          </div>
        </div>
      </section>
    </div>
  );
}

// Estado del guardado, en la barra del pie (D-13). aria-live: los lectores de pantalla lo anuncian.
function IndicadorGuardado({ sinGuardar, autoguardado }) {
  let texto = null;
  if (autoguardado?.tipo === 'guardando') texto = 'Guardando…';
  else if (sinGuardar && autoguardado?.tipo === 'invalido')
    texto = 'Cambios sin guardar: hay datos obligatorios o incompletos';
  else if (sinGuardar && autoguardado?.tipo === 'error')
    texto = 'Cambios sin guardar: no se pudo guardar automáticamente';
  else if (sinGuardar) texto = 'Cambios sin guardar';
  else if (autoguardado?.tipo === 'guardado')
    texto = `Guardado automáticamente a las ${formatoHora.format(autoguardado.hora)}`;
  return (
    <span className={`indicador-guardado ${sinGuardar ? 'sin-guardar' : ''}`} role="status" aria-live="polite">
      {texto}
    </span>
  );
}

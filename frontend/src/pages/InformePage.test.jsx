import { act, fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import client from '../api/client';
import { reiniciarOpciones } from '../hooks/useOpciones';
import InformePage from './InformePage';

// Se simula solo el cliente; resultados() y el resto del módulo son los reales.
vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal()),
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, rol: 'patologo' }, canWrite: true, isAdmin: false }),
}));

const INFORME = {
  id: 5,
  numero_peticion: 'P-2026-00001',
  numero_orden_externa: 'ORD-9',
  // Solo datos ficticios (docs/propuesta-informe-v2.md, sección 8).
  paciente: 1,
  paciente_datos: {
    id: 1,
    nombre_completo: 'Paciente Ficticio Uno',
    tipo_documento: 'CC',
    numero_documento: 'PRUEBA0001',
    fecha_nacimiento: '1980-10-05',
    sexo: 'femenino',
    edad: '45 años',
  },
  medico_tratante: 'Médico Ficticio',
  fecha_ingreso: '2026-10-01',
  eps: 4,
  eps_nombre: 'EPS Liquidada',
  servicio: 8,
  servicio_nombre: 'Urgencias',
  estudios_solicitados: 'Biopsia de piel',
  tipo_estudio: 'citologia_no_ginecologica',
  patologia: 1,
  autor: 1,
  estado: 'borrador',
  tipo_muestra: '',
  descripcion_microscopica: 'Nidos de células basaloides.',
  diagnosticos: [
    { orden: 1, descripcion: 'Carcinoma basocelular nodular', codigo_cie10: 'C44.3' },
    { orden: 2, descripcion: 'Márgenes libres de lesión', codigo_cie10: '' },
  ],
  comentarios: 'Se sugiere correlación clínica.',
  datos_ingresados: {},
  texto_generado: '',
  fecha_informe: null,
  firma: { nombre: 'Dra. Ficticia Firma', especialidad: 'Patología Quirúrgica', registro_medico: 'RM-PRUEBA-0001' },
};

const OPCIONES = {
  sexos: [{ valor: 'femenino', etiqueta: 'Femenino' }],
  tipos_documento: [{ valor: 'CC', etiqueta: 'Cédula de ciudadanía' }],
  tipos_estudio: [
    { valor: 'histologia', etiqueta: 'Histología' },
    { valor: 'citologia_no_ginecologica', etiqueta: 'Citología no ginecológica' },
  ],
};

const PACIENTE = {
  id: 1,
  tipo_documento: 'CC',
  numero_documento: 'PRUEBA0001',
  nombres: 'Paciente Ficticio',
  apellidos: 'Uno',
  fecha_nacimiento: '1980-10-05',
  edad: '45 años',
  sexo: 'femenino',
  eps: 3,
  eps_nombre: 'Particular',
};

// Simula las respuestas de la API según la URL pedida.
function simularApi() {
  client.get.mockImplementation((url) => {
    if (url === '/opciones/') return Promise.resolve({ data: OPCIONES });
    // EPS y servicios activos: "EPS Liquidada" (la del informe guardado) ya no está activa.
    if (url === '/pacientes/eps/')
      return Promise.resolve({ data: { results: [{ id: 3, nombre: 'Particular', activa: true }] } });
    if (url === '/servicios/')
      return Promise.resolve({ data: { results: [{ id: 8, nombre: 'Urgencias', activo: true }] } });
    if (url === '/pacientes/') return Promise.resolve({ data: { results: [PACIENTE] } });
    if (url === '/patologias/')
      return Promise.resolve({ data: { results: [{ id: 1, nombre: 'Piel', activa: true }] } });
    if (url === '/informes/5/') return Promise.resolve({ data: INFORME });
    if (url === '/patologias/1/') return Promise.resolve({ data: { plantillas: [] } });
    if (url === '/informes/5/pdf/') return Promise.resolve({ data: new Blob(['%PDF'], { type: 'application/pdf' }) });
    return Promise.reject(new Error(`URL no simulada: ${url}`));
  });
}

// InformePage usa useBlocker (D-13), que necesita un router de datos. "/" hace de
// pantalla de inicio, para comprobar a dónde lleva salir del informe.
function crearRouter(ruta) {
  return createMemoryRouter(
    [
      { path: '/', element: <h1>Pantalla de inicio</h1> },
      { path: '/informes/nuevo', element: <InformePage /> },
      { path: '/informes/:id', element: <InformePage /> },
      { path: '/salir', element: <h1>Cerrando sesión</h1> },
    ],
    { initialEntries: [ruta] },
  );
}

function renderInforme() {
  return render(<RouterProvider router={crearRouter('/informes/5')} />);
}

// Hallazgo I-5 de docs/auditoria-inicial.md: el PDF se descargaba armando una
// URL con ?token=<access_token>, que queda en el historial y en los registros.
describe('InformePage: exportar PDF', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('access_token', 'token-secreto');
    URL.createObjectURL = vi.fn(() => 'blob:pdf');
    URL.revokeObjectURL = vi.fn();
    simularApi();
  });

  it('pide el PDF con Axios (token en la cabecera) y no pone el token en una URL', async () => {
    const submitSpy = vi.spyOn(HTMLFormElement.prototype, 'submit').mockImplementation(() => {});
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    renderInforme();

    // INFORME es un borrador del usuario: el botón es la vista previa (decisión D-12).
    (await screen.findByRole('button', { name: /Vista previa \(borrador\)/i })).click();

    await vi.waitFor(() => {
      expect(client.get).toHaveBeenCalledWith('/informes/5/pdf/', { responseType: 'blob' });
    });
    expect(submitSpy).not.toHaveBeenCalled();
    expect(document.querySelector('input[name="token"]')).toBeNull();
    // El archivo se entrega con un enlace temporal "blob:" y el número de petición (D-7).
    expect(clickSpy).toHaveBeenCalled();
    const enlace = clickSpy.mock.contexts[0];
    expect(enlace.href).toBe('blob:pdf');
    expect(enlace.download).toBe('informe_P-2026-00001_borrador.pdf');
  });

  // Decisión D-12: el PDF de un borrador es una vista previa solo para su autor o un admin.
  function conInforme(informe) {
    const simulado = client.get.getMockImplementation();
    client.get.mockImplementation((url, ...resto) =>
      url === '/informes/5/' ? Promise.resolve({ data: informe }) : simulado(url, ...resto),
    );
  }

  it('un informe finalizado se exporta con su nombre, sin "borrador"', async () => {
    conInforme({ ...INFORME, estado: 'finalizado', fecha_informe: '2026-10-04T20:30:00Z' });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    renderInforme();
    (await screen.findByRole('button', { name: /Exportar PDF/i })).click();
    await vi.waitFor(() => expect(clickSpy).toHaveBeenCalled());
    expect(clickSpy.mock.contexts.at(-1).download).toBe('informe_P-2026-00001.pdf');
    expect(screen.queryByRole('button', { name: /Vista previa/i })).toBeNull();
  });

  it('el borrador de otro patólogo no ofrece el PDF', async () => {
    conInforme({ ...INFORME, autor: 2 });
    renderInforme();
    await screen.findByText('Dra. Ficticia Firma');
    expect(screen.queryByRole('button', { name: /Vista previa/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /Exportar PDF/i })).toBeNull();
  });
});

// El selector de patologías pide la lista completa (no solo 20). Al crear un
// informe ofrece solo las activas (decisión D-4); al editar, todas, para que se
// vea la patología de un informe viejo aunque ya esté desactivada.
describe('InformePage: selector de patologías', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    simularApi();
  });

  it('al crear un informe pide todas las patologías activas', async () => {
    render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
    await vi.waitFor(() => {
      expect(client.get).toHaveBeenCalledWith('/patologias/', { params: { page_size: 1000, activa: 'true' } });
    });
  });

  it('al editar un informe pide todas las patologías, también las inactivas', async () => {
    renderInforme();
    await vi.waitFor(() => {
      expect(client.get).toHaveBeenCalledWith('/patologias/', { params: { page_size: 1000 } });
    });
  });
});

// Hallazgo M-9 de docs/auditoria-inicial.md: si fallaba la carga de las patologías
// o de los campos de la plantilla, el formulario quedaba vacío sin ningún aviso.
describe('InformePage: errores visibles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('avisa si no se pueden cargar las patologías', async () => {
    client.get.mockRejectedValue(new Error('Network Error'));
    render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
    expect(await screen.findByText(/No se pudieron cargar las patologías/i)).toBeInTheDocument();
  });

  it('avisa si no se pueden cargar los campos de la patología', async () => {
    simularApi();
    const simulacion = client.get.getMockImplementation();
    client.get.mockImplementation((url, ...resto) =>
      url === '/patologias/1/' ? Promise.reject(new Error('Network Error')) : simulacion(url, ...resto),
    );
    renderInforme();
    expect(await screen.findByText(/No se pudieron cargar los campos de la patología/i)).toBeInTheDocument();
  });
});

// Busca y selecciona el paciente ficticio en el SelectorPaciente.
async function seleccionarPaciente() {
  fireEvent.change(screen.getByLabelText('Buscar paciente'), { target: { value: 'PRUEBA0001' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));
  fireEvent.click(await screen.findByRole('button', { name: /Seleccionar/ }));
}

// Decisión D-7 de docs/decisiones.md: el número de petición lo asigna el sistema
// al guardar. El formulario ya no pide número de caso; sí permite anotar el
// número de orden externo de la institución remitente (opcional).
describe('InformePage: número de petición', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    simularApi();
  });

  function renderNuevo() {
    return render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
  }

  it('un informe nuevo no pide número de caso', async () => {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    expect(screen.queryByLabelText(/Número de caso/i)).toBeNull();
  });

  it('al guardar envía la orden externa y no envía número de caso', async () => {
    client.post.mockResolvedValue({ data: { id: 9, numero_peticion: 'P-2026-00002' } });
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText(/orden externa/i), { target: { value: 'ORD-1' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));

    await vi.waitFor(() => expect(client.post).toHaveBeenCalled());
    const [url, datos] = client.post.mock.calls[0];
    expect(url).toBe('/informes/');
    expect(datos).not.toHaveProperty('numero_caso');
    expect(datos.numero_orden_externa).toBe('ORD-1');
  });

  it('un informe guardado muestra su número de petición y su orden externa', async () => {
    renderInforme();
    expect(await screen.findByRole('heading', { name: /Informe P-2026-00001/ })).toBeInTheDocument();
    expect(screen.getByLabelText(/orden externa/i)).toHaveValue('ORD-9');
  });
});

// Informe v2, etapa 4 (docs/propuesta-informe-v2.md, 6.3): el formulario sigue el
// orden del informe real: Paciente, Datos de la solicitud y Estudio.
describe('InformePage: paciente y datos de la solicitud', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
  });

  function renderNuevo() {
    return render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
  }

  it('muestra las tarjetas en el orden del informe real', async () => {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(titulos.slice(0, 3)).toEqual(['Paciente', 'Datos de la solicitud', 'Estudio']);
  });

  it('un informe nuevo empieza con la fecha de hoy y el tipo de estudio Histología', async () => {
    renderNuevo();
    expect(await screen.findByRole('option', { name: 'Histología' })).toBeInTheDocument();
    expect(screen.getByLabelText('Fecha de ingreso')).toHaveValue(new Date().toLocaleDateString('en-CA'));
    expect(screen.getByLabelText('Tipo de estudio')).toHaveValue('histologia');
  });

  it('no deja guardar sin paciente', async () => {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    expect(await screen.findByText('Seleccione un paciente.')).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  it('al elegir el paciente precarga su EPS y al guardar envía los datos de la solicitud', async () => {
    client.post.mockResolvedValue({ data: { id: 9, numero_peticion: 'P-2026-00002' } });
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    await screen.findByRole('option', { name: 'Urgencias' });
    await seleccionarPaciente();
    expect(screen.getByLabelText('EPS')).toHaveValue('3');
    fireEvent.change(screen.getByLabelText('Médico tratante'), { target: { value: 'Médico Ficticio' } });
    fireEvent.change(screen.getByLabelText('Fecha de ingreso'), { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getByLabelText('Servicio'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('Estudios solicitados'), { target: { value: 'Biopsia de piel' } });
    fireEvent.change(screen.getByLabelText('Tipo de estudio'), { target: { value: 'citologia_no_ginecologica' } });
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));

    await vi.waitFor(() => expect(client.post).toHaveBeenCalled());
    expect(client.post.mock.calls[0][1]).toMatchObject({
      paciente: 1,
      medico_tratante: 'Médico Ficticio',
      fecha_ingreso: '2026-10-01',
      eps: 3,
      servicio: 8,
      estudios_solicitados: 'Biopsia de piel',
      tipo_estudio: 'citologia_no_ginecologica',
      patologia: 1,
    });
  });

  it('al editar carga el paciente y los datos de la solicitud, y conserva la EPS desactivada', async () => {
    renderInforme();
    expect(await screen.findByText('Paciente Ficticio Uno')).toBeInTheDocument();
    expect(screen.getByText('CC PRUEBA0001')).toBeInTheDocument();
    expect(screen.getByLabelText('Médico tratante')).toHaveValue('Médico Ficticio');
    expect(screen.getByLabelText('Fecha de ingreso')).toHaveValue('2026-10-01');
    expect(await screen.findByRole('option', { name: 'EPS Liquidada (desactivada)' })).toBeInTheDocument();
    expect(screen.getByLabelText('EPS')).toHaveValue('4');
    expect(screen.getByLabelText('Servicio')).toHaveValue('8');
    expect(screen.getByLabelText('Estudios solicitados')).toHaveValue('Biopsia de piel');
    expect(await screen.findByRole('option', { name: 'Citología no ginecológica' })).toBeInTheDocument();
    expect(screen.getByLabelText('Tipo de estudio')).toHaveValue('citologia_no_ginecologica');
  });
});

// Informe v2, etapa 5 (docs/propuesta-informe-v2.md, 3.4, 3.6 y 6.3): descripción
// microscópica, diagnósticos con CIE-10 y comentarios (antes "notas", P-5).
describe('InformePage: contenido del informe', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
  });

  function renderNuevo() {
    return render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
  }

  it('muestra las tarjetas del contenido en el orden del informe real', async () => {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(titulos).toEqual([
      'Paciente',
      'Datos de la solicitud',
      'Estudio',
      'Descripción microscópica',
      'Diagnósticos',
      'Comentarios',
    ]);
    expect(screen.queryByText(/Notas/i)).toBeNull();
  });

  it('al guardar envía la microscópica, los diagnósticos en orden y los comentarios', async () => {
    client.post.mockResolvedValue({ data: { id: 9, numero_peticion: 'P-2026-00002' } });
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Descripción microscópica'), { target: { value: 'Nidos basaloides.' } });
    fireEvent.click(screen.getByRole('button', { name: /Agregar diagnóstico/ }));
    fireEvent.change(screen.getByLabelText('Diagnóstico 1'), { target: { value: 'Carcinoma basocelular' } });
    fireEvent.change(screen.getByLabelText('CIE-10 del diagnóstico 1'), { target: { value: 'C44.3' } });
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Correlación clínica.' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));

    await vi.waitFor(() => expect(client.post).toHaveBeenCalled());
    const datos = client.post.mock.calls[0][1];
    expect(datos).toMatchObject({
      descripcion_microscopica: 'Nidos basaloides.',
      diagnosticos: [{ descripcion: 'Carcinoma basocelular', codigo_cie10: 'C44.3' }],
      comentarios: 'Correlación clínica.',
    });
    expect(datos).not.toHaveProperty('notas');
    expect(datos.diagnosticos[0]).not.toHaveProperty('clave');
  });

  it('no deja guardar un diagnóstico sin descripción', async () => {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /Agregar diagnóstico/ }));
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    expect(await screen.findByText('Escriba la descripción del diagnóstico.')).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  it('al editar carga la microscópica, los diagnósticos y los comentarios', async () => {
    renderInforme();
    expect(await screen.findByLabelText('Descripción microscópica')).toHaveValue('Nidos de células basaloides.');
    expect(screen.getByLabelText('Diagnóstico 1')).toHaveValue('Carcinoma basocelular nodular');
    expect(screen.getByLabelText('CIE-10 del diagnóstico 1')).toHaveValue('C44.3');
    expect(screen.getByLabelText('Diagnóstico 2')).toHaveValue('Márgenes libres de lesión');
    expect(screen.getByLabelText('Comentarios')).toHaveValue('Se sugiere correlación clínica.');
  });

  it('muestra junto a la fila el error del backend en un diagnóstico', async () => {
    client.put.mockRejectedValue({
      response: { data: { diagnosticos: [{}, { codigo_cie10: ['Código CIE-10 no válido.'] }] } },
    });
    renderInforme();
    await screen.findByLabelText('Diagnóstico 2');
    fireEvent.click(screen.getByRole('button', { name: /Actualizar Informe/i }));
    expect(await screen.findByText('Código CIE-10 no válido.')).toBeInTheDocument();
  });
});

describe('InformePage: firma y finalización (etapa 6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
  });

  it('un informe guardado termina con la tarjeta Firma', async () => {
    renderInforme();
    await screen.findByText('Dra. Ficticia Firma');
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(titulos.at(-1)).toBe('Firma');
  });

  it('si no se puede finalizar, muestra todos los requisitos que faltan', async () => {
    client.post.mockRejectedValue({
      response: {
        status: 400,
        data: {
          detail: 'No se puede finalizar el informe. El informe debe tener al menos un diagnóstico. ...',
          requisitos: [
            'El informe debe tener al menos un diagnóstico.',
            'El patólogo autor no tiene registro médico; un administrador debe registrarlo.',
          ],
        },
      },
    });
    renderInforme();
    fireEvent.click(await screen.findByRole('button', { name: /Finalizar Informe/i }));
    fireEvent.click(screen.getByRole('button', { name: /Confirmar/i }));
    expect(await screen.findByText('No se puede finalizar el informe:')).toBeInTheDocument();
    // role="alert": los lectores de pantalla lo anuncian (y Cypress lo encuentra por su rol).
    expect(screen.getByRole('alert')).toHaveTextContent('No se puede finalizar el informe:');
    const lista = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(lista).toContain('El informe debe tener al menos un diagnóstico.');
    expect(lista).toContain('El patólogo autor no tiene registro médico; un administrador debe registrarlo.');
  });

  it('al finalizar muestra la firma y la fecha de informe', async () => {
    client.post.mockResolvedValue({
      data: { ...INFORME, estado: 'finalizado', fecha_informe: '2026-10-04T20:30:00Z' },
    });
    renderInforme();
    fireEvent.click(await screen.findByRole('button', { name: /Finalizar Informe/i }));
    fireEvent.click(screen.getByRole('button', { name: /Confirmar/i }));
    expect(await screen.findByText('Informe finalizado correctamente.')).toBeInTheDocument();
    expect(screen.getByText(/Fecha de informe/)).toBeInTheDocument();
    expect(screen.queryByText(/Al finalizar, el informe llevará/)).not.toBeInTheDocument();
  });
});

describe('InformePage: adendas (etapa 8)', () => {
  const FINALIZADO = {
    ...INFORME,
    estado: 'finalizado',
    fecha_informe: '2026-10-04T20:30:00Z',
    adendas: [
      {
        id: 1,
        numero: 1,
        motivo: 'Corrección del diagnóstico',
        texto: 'Se aclara el diagnóstico.',
        autor: 1,
        fecha: '2026-10-05T14:15:00Z',
        firma: INFORME.firma,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
    const simulado = client.get.getMockImplementation();
    client.get.mockImplementation((url, ...resto) =>
      url === '/informes/5/' ? Promise.resolve({ data: FINALIZADO }) : simulado(url, ...resto),
    );
  });

  it('un informe finalizado termina con la tarjeta Adendas, después de la Firma', async () => {
    renderInforme();
    await screen.findByText('Corrección del diagnóstico');
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(titulos.slice(-2)).toEqual(['Firma', 'Adendas']);
  });

  it('una adenda nueva se agrega a la lista sin recargar el informe', async () => {
    client.post.mockResolvedValue({
      data: {
        ...FINALIZADO.adendas[0],
        id: 2,
        numero: 2,
        motivo: 'Resultado de inmunohistoquímica',
        texto: 'CK5/6 positivo.',
      },
    });
    renderInforme();
    fireEvent.click(await screen.findByRole('button', { name: /Agregar adenda/i }));
    fireEvent.change(screen.getByLabelText(/Motivo/), { target: { value: 'Resultado de inmunohistoquímica' } });
    fireEvent.change(screen.getByLabelText(/Texto/), { target: { value: 'CK5/6 positivo.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar adenda' }));
    fireEvent.click(screen.getByRole('button', { name: /Sí, guardar adenda/i }));
    expect(await screen.findByText(/Adenda N\.º 2/)).toBeInTheDocument();
    expect(screen.getByText(/Adenda N\.º 1/)).toBeInTheDocument();
    // La adenda no es el informe: no se envía con el formulario del informe.
    expect(client.put).not.toHaveBeenCalled();
  });

  it('un borrador no muestra la tarjeta Adendas', async () => {
    client.get.mockImplementation((url) =>
      url === '/informes/5/'
        ? Promise.resolve({ data: INFORME })
        : Promise.resolve({ data: { results: [], plantillas: [], ...(url === '/opciones/' ? OPCIONES : {}) } }),
    );
    renderInforme();
    await screen.findByText('Dra. Ficticia Firma');
    expect(screen.queryByRole('heading', { name: 'Adendas' })).not.toBeInTheDocument();
  });
});

// Decisión D-13 (Pendientes, punto 3): al salir con cambios sin guardar se pide
// confirmar, y un borrador que ya existe se autoguarda 5 segundos después del último
// cambio. Un informe nuevo no se autoguarda (gastaría un número de petición, D-7) y
// nada se guarda en el navegador.
describe('InformePage: no perder lo escrito (D-13)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    client.put.mockImplementation((url, datos) => Promise.resolve({ data: { ...INFORME, ...datos } }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function escribirComentario(texto) {
    const campo = await screen.findByDisplayValue('Se sugiere correlación clínica.');
    fireEvent.change(campo, { target: { value: texto } });
  }

  async function abrirNuevo() {
    render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
    await screen.findByRole('option', { name: 'Piel' });
  }

  const aviso = () => screen.queryByRole('dialog', { name: /cambios sin guardar/i });

  // --- Autoguardado ---

  it('autoguarda un borrador existente 5 segundos después del último cambio', async () => {
    renderInforme();
    await escribirComentario('Primer cambio');
    await vi.advanceTimersByTimeAsync(3000);
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Segundo cambio' } });
    await vi.advanceTimersByTimeAsync(3000);
    expect(client.put).not.toHaveBeenCalled(); // el segundo cambio reinició la espera

    await vi.advanceTimersByTimeAsync(2000);
    expect(client.put).toHaveBeenCalledTimes(1);
    const [url, datos] = client.put.mock.calls[0];
    expect(url).toBe('/informes/5/');
    expect(datos.comentarios).toBe('Segundo cambio');
    expect(await screen.findByText(/Guardado automáticamente a las/)).toBeInTheDocument();
  });

  it('no autoguarda si el formulario no pasa la validación', async () => {
    renderInforme();
    const diagnostico = await screen.findByLabelText('Diagnóstico 1');
    fireEvent.change(diagnostico, { target: { value: '' } });
    await vi.advanceTimersByTimeAsync(6000);
    expect(client.put).not.toHaveBeenCalled();
    expect(screen.getByText(/Cambios sin guardar: hay datos obligatorios o incompletos/)).toBeInTheDocument();
  });

  it('un informe nuevo no se autoguarda', async () => {
    await abrirNuevo();
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Algo' } });
    await vi.advanceTimersByTimeAsync(10000);
    expect(client.post).not.toHaveBeenCalled();
    expect(client.put).not.toHaveBeenCalled();
    expect(screen.getByText('Cambios sin guardar')).toBeInTheDocument();
  });

  it('nunca guarda una copia en el navegador', async () => {
    const guardar = vi.spyOn(Storage.prototype, 'setItem');
    renderInforme();
    await escribirComentario('Dato del paciente');
    await vi.advanceTimersByTimeAsync(6000);
    expect(guardar).not.toHaveBeenCalled();
    guardar.mockRestore();
  });

  // --- Aviso al salir ---

  it('sin cambios, salir no pide confirmación', async () => {
    renderInforme();
    await screen.findByDisplayValue('Se sugiere correlación clínica.');
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(await screen.findByRole('heading', { name: 'Pantalla de inicio' })).toBeInTheDocument();
  });

  it('con cambios, "Seguir editando" se queda en el informe con lo escrito', async () => {
    renderInforme();
    await escribirComentario('Sin guardar');
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(await screen.findByRole('dialog', { name: /cambios sin guardar/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Seguir editando' }));
    expect(aviso()).toBeNull();
    expect(screen.getByLabelText('Comentarios')).toHaveValue('Sin guardar');
    expect(screen.queryByRole('heading', { name: 'Pantalla de inicio' })).toBeNull();
  });

  it('"Salir sin guardar" sale sin guardar', async () => {
    renderInforme();
    await escribirComentario('Sin guardar');
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Salir sin guardar' }));
    expect(await screen.findByRole('heading', { name: 'Pantalla de inicio' })).toBeInTheDocument();
    expect(client.put).not.toHaveBeenCalled();
  });

  it('"Guardar y salir" guarda y sale', async () => {
    renderInforme();
    await escribirComentario('Guardado al salir');
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Guardar y salir' }));
    expect(await screen.findByRole('heading', { name: 'Pantalla de inicio' })).toBeInTheDocument();
    expect(client.put).toHaveBeenCalledWith(
      '/informes/5/',
      expect.objectContaining({ comentarios: 'Guardado al salir' }),
    );
  });

  it('"Guardar y salir" no sale si falla la validación y muestra qué falta', async () => {
    await abrirNuevo();
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Sin paciente' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Guardar y salir' }));
    expect(await screen.findByText('Seleccione un paciente.')).toBeInTheDocument();
    expect(aviso()).toBeNull();
    expect(client.post).not.toHaveBeenCalled();
    expect(screen.queryByRole('heading', { name: 'Pantalla de inicio' })).toBeNull();
  });

  it('"Guardar y salir" no sale si el servidor rechaza los datos', async () => {
    client.put.mockRejectedValue({
      response: { status: 400, data: { datos_ingresados: ['Faltan campos obligatorios: Localización'] } },
    });
    renderInforme();
    await escribirComentario('Cambio');
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Guardar y salir' }));
    expect(await screen.findByText(/Faltan campos obligatorios: Localización/)).toBeInTheDocument();
    expect(aviso()).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Pantalla de inicio' })).toBeNull();
  });

  it('después del autoguardado, salir ya no pide confirmación', async () => {
    renderInforme();
    await escribirComentario('Autoguardado');
    await vi.advanceTimersByTimeAsync(5000);
    await screen.findByText(/Guardado automáticamente a las/);
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(await screen.findByRole('heading', { name: 'Pantalla de inicio' })).toBeInTheDocument();
  });

  it('al crear un informe nuevo pasa a su página sin pedir confirmación', async () => {
    client.post.mockResolvedValue({ data: { id: 5, numero_peticion: 'P-2026-00001' } });
    await abrirNuevo();
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    expect(await screen.findByRole('heading', { name: /Informe P-2026-00001/ })).toBeInTheDocument();
    expect(aviso()).toBeNull();
  });

  it('al cerrar o recargar la pestaña con cambios, el navegador avisa', async () => {
    renderInforme();
    await screen.findByDisplayValue('Se sugiere correlación clínica.');
    const cerrar = () => {
      const evento = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(evento);
      return evento.defaultPrevented;
    };
    expect(cerrar()).toBe(false);
    fireEvent.change(screen.getByLabelText('Comentarios'), { target: { value: 'Cambio' } });
    expect(cerrar()).toBe(true);
  });
});

// D-13, ampliación: finalizar y la vista previa del PDF usan lo que hay en pantalla.
// Si hay cambios sin guardar, primero se guardan; si la validación falla o el
// servidor los rechaza, no se finaliza ni se descarga, y se muestra qué falta.
// Cerrar sesión pasa por /salir, así que con cambios sin guardar también avisa.
describe('InformePage: finalizar, vista previa y cerrar sesión con cambios sin guardar (D-13)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
    simularApi();
    URL.createObjectURL = vi.fn(() => 'blob:pdf');
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    client.put.mockImplementation((url, datos) => Promise.resolve({ data: { ...INFORME, ...datos } }));
    client.post.mockImplementation((url) =>
      url === '/informes/5/finalizar/'
        ? Promise.resolve({ data: { ...INFORME, estado: 'finalizado', fecha_informe: '2026-10-05T15:00:00Z' } })
        : Promise.reject(new Error(`POST no simulado: ${url}`)),
    );
  });

  async function cambiarComentario(texto) {
    const campo = await screen.findByDisplayValue('Se sugiere correlación clínica.');
    fireEvent.change(campo, { target: { value: texto } });
  }

  function finalizar() {
    fireEvent.click(screen.getByRole('button', { name: /Finalizar Informe/i }));
    fireEvent.click(screen.getByRole('button', { name: /Confirmar/i }));
  }

  const llamadaPdf = () => client.get.mock.calls.findIndex(([url]) => url === '/informes/5/pdf/');

  // --- Finalizar ---

  it('sin cambios, finaliza sin volver a guardar', async () => {
    renderInforme();
    await screen.findByDisplayValue('Se sugiere correlación clínica.');
    finalizar();
    expect(await screen.findByText('Informe finalizado correctamente.')).toBeInTheDocument();
    expect(client.put).not.toHaveBeenCalled();
  });

  it('con cambios, guarda primero y después finaliza', async () => {
    renderInforme();
    await cambiarComentario('Escrito justo antes de finalizar');
    finalizar();
    expect(await screen.findByText('Informe finalizado correctamente.')).toBeInTheDocument();
    expect(client.put).toHaveBeenCalledWith(
      '/informes/5/',
      expect.objectContaining({ comentarios: 'Escrito justo antes de finalizar' }),
    );
    expect(client.put.mock.invocationCallOrder[0]).toBeLessThan(client.post.mock.invocationCallOrder[0]);
  });

  it('con cambios no válidos, no guarda ni finaliza y muestra qué falta', async () => {
    renderInforme();
    fireEvent.change(await screen.findByLabelText('Diagnóstico 1'), { target: { value: '' } });
    finalizar();
    expect(await screen.findByText('Escriba la descripción del diagnóstico.')).toBeInTheDocument();
    expect(client.put).not.toHaveBeenCalled();
    expect(client.post).not.toHaveBeenCalled();
  });

  it('si el servidor rechaza los cambios, no finaliza', async () => {
    client.put.mockRejectedValue({
      response: { status: 400, data: { datos_ingresados: ['Faltan campos obligatorios: Localización'] } },
    });
    renderInforme();
    await cambiarComentario('Cambio');
    finalizar();
    expect(await screen.findByText(/Faltan campos obligatorios: Localización/)).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  // --- Vista previa del PDF ---

  it('con cambios, la vista previa guarda primero y después pide el PDF', async () => {
    renderInforme();
    await cambiarComentario('Para la vista previa');
    fireEvent.click(screen.getByRole('button', { name: /Vista previa \(borrador\)/i }));
    await vi.waitFor(() => expect(llamadaPdf()).toBeGreaterThan(-1));
    expect(client.put).toHaveBeenCalledWith(
      '/informes/5/',
      expect.objectContaining({ comentarios: 'Para la vista previa' }),
    );
    expect(client.put.mock.invocationCallOrder[0]).toBeLessThan(client.get.mock.invocationCallOrder[llamadaPdf()]);
  });

  it('con cambios no válidos, la vista previa no se descarga y muestra qué falta', async () => {
    renderInforme();
    fireEvent.change(await screen.findByLabelText('Diagnóstico 1'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: /Vista previa \(borrador\)/i }));
    expect(await screen.findByText('Escriba la descripción del diagnóstico.')).toBeInTheDocument();
    expect(client.put).not.toHaveBeenCalled();
    expect(llamadaPdf()).toBe(-1);
  });

  // --- Cerrar sesión ---

  it('cerrar sesión con cambios sin guardar muestra el aviso; "Salir sin guardar" cierra la sesión', async () => {
    const router = crearRouter('/informes/5');
    render(<RouterProvider router={router} />);
    await cambiarComentario('Sin guardar');
    act(() => {
      router.navigate('/salir');
    });
    expect(await screen.findByRole('dialog', { name: /cambios sin guardar/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Salir sin guardar' }));
    expect(await screen.findByRole('heading', { name: 'Cerrando sesión' })).toBeInTheDocument();
  });

  it('cerrar sesión con "Guardar y salir" guarda antes de cerrar la sesión', async () => {
    const router = crearRouter('/informes/5');
    render(<RouterProvider router={router} />);
    await cambiarComentario('Guardado al cerrar sesión');
    act(() => {
      router.navigate('/salir');
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Guardar y salir' }));
    expect(await screen.findByRole('heading', { name: 'Cerrando sesión' })).toBeInTheDocument();
    expect(client.put).toHaveBeenCalledWith(
      '/informes/5/',
      expect.objectContaining({ comentarios: 'Guardado al cerrar sesión' }),
    );
  });
});

// Decisión D-18: campos por sección, campos que solo aplican a ciertos procedimientos y
// muestreo para histología (canastillas).
describe('InformePage: plantillas según el manual y canastillas (D-18)', () => {
  const PLANTILLAS = [
    {
      campo_nombre: 'tipo_muestra',
      campo_label: 'Tipo de procedimiento',
      tipo_campo: 'lista',
      obligatorio: true,
      opciones: ['Tiroidectomía total', 'Lobectomía'],
      seccion: 'Identificación y procedimiento',
      condicion: {},
      ayuda: '',
    },
    {
      campo_nombre: 'lateralidad',
      campo_label: 'Lateralidad',
      tipo_campo: 'lista',
      obligatorio: true,
      opciones: ['Lóbulo derecho', 'Lóbulo izquierdo'],
      seccion: 'Identificación y procedimiento',
      condicion: { campo: 'tipo_muestra', valores: ['Lobectomía'] },
      ayuda: 'Solo en lobectomía.',
    },
    {
      campo_nombre: 'ganglios',
      campo_label: 'Ganglios',
      tipo_campo: 'numero',
      obligatorio: true,
      opciones: [],
      seccion: 'Márgenes, orientación y estructuras',
      condicion: {},
      ayuda: '',
    },
  ];
  const GUIA = [{ titulo: 'Orden de envío', items: ['Tercio superior, lóbulo derecho.'] }];

  function simularConPlantillas(informe = INFORME) {
    simularApi();
    const original = client.get.getMockImplementation();
    client.get.mockImplementation((url, ...resto) => {
      if (url === '/patologias/1/') return Promise.resolve({ data: { plantillas: PLANTILLAS, guia_muestreo: GUIA } });
      if (url === '/informes/5/') return Promise.resolve({ data: informe });
      return original(url, ...resto);
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    reiniciarOpciones();
  });

  function renderNuevo() {
    return render(<RouterProvider router={crearRouter('/informes/nuevo')} />);
  }

  async function nuevoConPatologia() {
    renderNuevo();
    await screen.findByRole('option', { name: 'Piel' });
    await seleccionarPaciente();
    fireEvent.change(screen.getByLabelText(/Tipo de Patología/i), { target: { value: '1' } });
    await screen.findByLabelText(/Tipo de procedimiento/);
  }

  it('agrupa los campos por sección y muestra un campo solo cuando aplica', async () => {
    simularConPlantillas();
    await nuevoConPatologia();
    expect(screen.getByRole('heading', { name: 'Identificación y procedimiento' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Márgenes, orientación y estructuras' })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Lateralidad/)).toBeNull();
    fireEvent.change(screen.getByLabelText(/Tipo de procedimiento/), { target: { value: 'Lobectomía' } });
    expect(screen.getByLabelText(/Lateralidad/)).toBeInTheDocument();
    expect(screen.getByText('Solo en lobectomía.')).toBeInTheDocument();
  });

  it('no exige un campo que no aplica y acepta 0 como respuesta', async () => {
    simularConPlantillas();
    client.post.mockResolvedValue({ data: { id: 9 } });
    await nuevoConPatologia();
    fireEvent.change(screen.getByLabelText(/Tipo de procedimiento/), { target: { value: 'Tiroidectomía total' } });
    fireEvent.change(screen.getByLabelText(/Ganglios/), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    await vi.waitFor(() => expect(client.post).toHaveBeenCalled());
    expect(client.post.mock.calls[0][1].datos_ingresados).toMatchObject({ ganglios: '0' });
  });

  it('exige el campo condicional cuando aplica', async () => {
    simularConPlantillas();
    await nuevoConPatologia();
    fireEvent.change(screen.getByLabelText(/Tipo de procedimiento/), { target: { value: 'Lobectomía' } });
    fireEvent.change(screen.getByLabelText(/Ganglios/), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    expect(await screen.findByText('Lateralidad es obligatorio.')).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  it('envía las canastillas que agregó el usuario y ninguna si no agregó', async () => {
    simularConPlantillas();
    client.post.mockResolvedValue({ data: { id: 9 } });
    await nuevoConPatologia();
    fireEvent.change(screen.getByLabelText(/Tipo de procedimiento/), { target: { value: 'Tiroidectomía total' } });
    fireEvent.change(screen.getByLabelText(/Ganglios/), { target: { value: '1' } });
    expect(screen.getByRole('heading', { name: 'Muestreo para histología' })).toBeInTheDocument();
    expect(screen.getByText('Tercio superior, lóbulo derecho.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Agregar canastilla/ }));
    fireEvent.change(screen.getByLabelText('Región o estructura de la canastilla 1'), {
      target: { value: 'Tercio superior, lóbulo derecho' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    await vi.waitFor(() => expect(client.post).toHaveBeenCalled());
    const [canastilla] = client.post.mock.calls[0][1].canastillas;
    expect(canastilla).toMatchObject({ codigo: 'A', region: 'Tercio superior, lóbulo derecho', cantidad: null });
    expect(canastilla).not.toHaveProperty('clave');
  });

  it('no guarda una canastilla sin contenido', async () => {
    simularConPlantillas();
    await nuevoConPatologia();
    fireEvent.change(screen.getByLabelText(/Tipo de procedimiento/), { target: { value: 'Tiroidectomía total' } });
    fireEvent.change(screen.getByLabelText(/Ganglios/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /Agregar canastilla/ }));
    fireEvent.click(screen.getByRole('button', { name: /Guardar Informe/i }));
    expect(await screen.findByText(/Indique la región, la lesión o margen/)).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  it('muestra las canastillas guardadas y, en un finalizado, no deja cambiarlas', async () => {
    const canastillas = [
      {
        orden: 1,
        codigo: 'A',
        region: 'Istmo',
        lesion_margen: '',
        descripcion: '',
        cantidad: 2,
        entintado: '',
        motivo: '',
        observaciones: '',
      },
    ];
    simularConPlantillas({ ...INFORME, estado: 'finalizado', canastillas, datos_ingresados: { ganglios: 0 } });
    renderInforme();
    expect(await screen.findByLabelText('Región o estructura de la canastilla 1')).toHaveValue('Istmo');
    expect(screen.getByLabelText('Cantidad de la canastilla 1')).toBeDisabled();
    expect(screen.queryByRole('button', { name: /Agregar canastilla/ })).toBeNull();
    expect(screen.getByLabelText(/Ganglios/)).toHaveValue(0); // un 0 guardado se ve
  });
});

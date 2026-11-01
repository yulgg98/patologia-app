import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import MuestreoHistologia, { conClaves, erroresCanastillas, sinClaves } from './MuestreoHistologia';

// Envoltorio con estado: MuestreoHistologia es un componente controlado.
function Prueba({ inicial = [], disabled = false, error, guia = [] }) {
  const [lista, setLista] = useState(conClaves(inicial));
  return (
    <>
      <MuestreoHistologia canastillas={lista} onCambiar={setLista} disabled={disabled} error={error} guia={guia} />
      <output data-testid="lista">{JSON.stringify(sinClaves(lista))}</output>
    </>
  );
}

const lista = () => JSON.parse(screen.getByTestId('lista').textContent);

const DOS = [
  {
    codigo: 'A',
    region: 'Punta',
    lesion_margen: '',
    descripcion: 'Sección longitudinal',
    cantidad: 1,
    entintado: '',
    motivo: '',
    observaciones: '',
  },
  {
    codigo: 'B',
    region: '',
    lesion_margen: 'Margen proximal',
    descripcion: '',
    cantidad: null,
    entintado: 'Azul',
    motivo: '',
    observaciones: '',
  },
];

// Decisión D-18: muestreo para histología, una fila por canastilla.
describe('MuestreoHistologia', () => {
  it('sin canastillas no crea ninguna y permite agregar una con la letra sugerida', () => {
    render(<Prueba />);
    expect(screen.getByText('Todavía no hay canastillas registradas.')).toBeInTheDocument();
    expect(lista()).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: /Agregar canastilla/ }));
    expect(screen.getByLabelText('Identificación de la canastilla 1')).toHaveValue('A');
    fireEvent.change(screen.getByLabelText('Región o estructura de la canastilla 1'), { target: { value: 'Punta' } });
    fireEvent.change(screen.getByLabelText('Cantidad de la canastilla 1'), { target: { value: '0' } });
    expect(lista()).toEqual([
      {
        codigo: 'A',
        region: 'Punta',
        lesion_margen: '',
        descripcion: '',
        cantidad: 0,
        entintado: '',
        motivo: '',
        observaciones: '',
      },
    ]);
  });

  it('sugiere la siguiente letra libre y conserva la identificación de cada una', () => {
    render(<Prueba inicial={DOS} />);
    fireEvent.click(screen.getByRole('button', { name: /Agregar canastilla/ }));
    expect(screen.getByLabelText('Identificación de la canastilla 3')).toHaveValue('C');
    expect(lista().map((c) => c.codigo)).toEqual(['A', 'B', 'C']);
  });

  it('pide confirmación antes de quitar una canastilla', () => {
    render(<Prueba inicial={DOS} />);
    fireEvent.click(screen.getByRole('button', { name: 'Quitar canastilla 1' }));
    expect(screen.getByText('¿Quitar la canastilla A?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'No' }));
    expect(lista()).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'Quitar canastilla 1' }));
    fireEvent.click(screen.getByRole('button', { name: 'Sí, quitar' }));
    expect(lista().map((c) => c.codigo)).toEqual(['B']);
  });

  it('una cantidad vacía se envía como null, no como 0', () => {
    render(<Prueba inicial={DOS} />);
    expect(lista()[1].cantidad).toBeNull();
  });

  it('en solo lectura no muestra botones y los campos están deshabilitados', () => {
    render(<Prueba inicial={DOS} disabled />);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByLabelText('Identificación de la canastilla 1')).toBeDisabled();
    expect(screen.getByLabelText('Tejido muestreado de la canastilla 2')).toBeDisabled();
  });

  it('muestra las indicaciones del manual como referencia', () => {
    render(<Prueba guia={[{ titulo: 'Colectomía tumoral', items: ['Al menos 12 ganglios.'] }]} />);
    expect(screen.getByText('Indicaciones del manual para el muestreo')).toBeInTheDocument();
    expect(screen.getByText('Al menos 12 ganglios.')).toBeInTheDocument();
    expect(lista()).toEqual([]);
  });

  it('muestra los errores de cada fila y el error general', () => {
    const { rerender } = render(<Prueba inicial={DOS} error={[{}, { codigo: ['Identificación repetida.'] }]} />);
    expect(screen.getByText('Identificación repetida.')).toBeInTheDocument();
    rerender(<Prueba inicial={DOS} error="Identificación de canastilla repetida: A." />);
    expect(screen.getByText('Identificación de canastilla repetida: A.')).toBeInTheDocument();
  });
});

describe('erroresCanastillas', () => {
  const fila = (extra) => ({ ...conClaves([{ codigo: 'A', region: 'Punta' }])[0], ...extra });

  it('no devuelve nada si todas están bien', () => {
    expect(erroresCanastillas([fila(), fila({ codigo: 'B' })])).toBeNull();
  });

  it('detecta identificación vacía o repetida, falta de contenido y cantidad no válida', () => {
    const errores = erroresCanastillas([
      fila(),
      fila({ codigo: 'a ' }),
      fila({ codigo: '' }),
      fila({ codigo: 'C', region: '' }),
      fila({ codigo: 'D', cantidad: '-1' }),
    ]);
    expect(errores[0]).toEqual({});
    expect(errores[1].codigo).toMatch(/ya está en otra canastilla/);
    expect(errores[2].codigo).toMatch(/Escriba la identificación/);
    expect(errores[3].region).toMatch(/Indique la región/);
    expect(errores[4].cantidad).toMatch(/número entero/);
  });
});

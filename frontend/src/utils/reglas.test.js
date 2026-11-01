import { describe, expect, it } from 'vitest';
import { agruparPorSeccion, camposAplicables, esVacio } from './reglas';

// Decisión D-18: repite camposAplicables() de backend/informes/reglas.py.
const PLANTILLAS = [
  { campo_nombre: 'tipo_muestra', seccion: 'Identificación', condicion: {} },
  { campo_nombre: 'margenes', seccion: 'Márgenes', condicion: { campo: 'tipo_muestra', valores: ['Resección'] } },
  { campo_nombre: 'distancia', seccion: 'Márgenes', condicion: { campo: 'margenes', valores: ['Comprometidos'] } },
  { campo_nombre: 'peso', seccion: 'Identificación' },
];

describe('reglas de la plantilla', () => {
  it('0 y false son respuestas; null, undefined y espacios no', () => {
    expect(esVacio(0)).toBe(false);
    expect(esVacio(false)).toBe(false);
    expect(esVacio(null)).toBe(true);
    expect(esVacio(undefined)).toBe(true);
    expect(esVacio('  ')).toBe(true);
  });

  it('un campo condicional aplica solo con el valor indicado', () => {
    expect(camposAplicables(PLANTILLAS, { tipo_muestra: 'Biopsia' })).toEqual(new Set(['tipo_muestra', 'peso']));
    expect(camposAplicables(PLANTILLAS, { tipo_muestra: 'Resección' }).has('margenes')).toBe(true);
  });

  it('un valor viejo de un campo que no aplica no activa a los que dependen de él', () => {
    const aplican = camposAplicables(PLANTILLAS, { tipo_muestra: 'Biopsia', margenes: 'Comprometidos' });
    expect(aplican.has('distancia')).toBe(false);
  });

  it('agrupa por sección en el orden en que aparecen', () => {
    const grupos = agruparPorSeccion(PLANTILLAS);
    expect(grupos.map((g) => g.nombre)).toEqual(['Identificación', 'Márgenes']);
    expect(grupos[0].campos.map((p) => p.campo_nombre)).toEqual(['tipo_muestra', 'peso']);
  });

  it('las plantillas sin sección van juntas, sin título', () => {
    expect(agruparPorSeccion([{ campo_nombre: 'a' }, { campo_nombre: 'b', seccion: '' }])).toEqual([
      { nombre: '', campos: [{ campo_nombre: 'a' }, { campo_nombre: 'b', seccion: '' }] },
    ]);
  });
});

import { useState } from 'react';

// Tarjeta "Muestreo para histología" del informe (decisión D-18). Cada fila es una
// canastilla: qué tejido se envió a procesar y de dónde salió. Es aparte de la
// descripción macroscópica y no es un hallazgo ni un diagnóstico. El sistema no crea
// canastillas: las agrega el usuario, las que el caso necesite.

let siguienteClave = 1;

const CAMPOS = ['codigo', 'region', 'lesion_margen', 'descripcion', 'cantidad', 'entintado', 'motivo', 'observaciones'];

// Como en ListaDiagnosticos: cada fila lleva una `clave` para React que no se envía.
// La cantidad se edita como texto ('' = sin dato) y se envía como número o null.
export const conClaves = (canastillas = []) =>
  canastillas.map((canastilla) => {
    const fila = { clave: siguienteClave++ };
    CAMPOS.forEach((campo) => {
      const valor = canastilla[campo];
      fila[campo] = valor === null || valor === undefined ? '' : String(valor);
    });
    return fila;
  });

export const sinClaves = (canastillas) =>
  canastillas.map((fila) => {
    const canastilla = {};
    CAMPOS.forEach((campo) => {
      canastilla[campo] = fila[campo];
    });
    canastilla.codigo = fila.codigo.trim();
    canastilla.cantidad = fila.cantidad === '' ? null : Number(fila.cantidad);
    return canastilla;
  });

// Errores por fila con la misma forma que los del backend ([{}, { codigo: '...' }]),
// o null si no hay ninguno.
export function erroresCanastillas(canastillas) {
  const vistos = new Set();
  const errores = canastillas.map((fila) => {
    const codigo = fila.codigo.trim().toUpperCase();
    const error = {};
    if (!codigo) error.codigo = 'Escriba la identificación de la canastilla.';
    else if (vistos.has(codigo)) error.codigo = 'Esta identificación ya está en otra canastilla.';
    vistos.add(codigo);
    if (![fila.region, fila.lesion_margen, fila.descripcion].some((v) => v.trim()))
      error.region = 'Indique la región, la lesión o margen, o la descripción del tejido muestreado.';
    if (fila.cantidad !== '' && !(Number.isInteger(Number(fila.cantidad)) && Number(fila.cantidad) >= 0))
      error.cantidad = 'La cantidad debe ser un número entero, 0 o mayor.';
    return error;
  });
  return errores.some((e) => Object.keys(e).length > 0) ? errores : null;
}

// Primera letra (A, B, C...) que no esté usada; el usuario la puede cambiar.
function codigoSugerido(canastillas) {
  const usados = new Set(canastillas.map((c) => c.codigo.trim().toUpperCase()));
  for (let i = 0; i < 26; i += 1) {
    const letra = String.fromCharCode(65 + i);
    if (!usados.has(letra)) return letra;
  }
  return '';
}

// `error` es un texto (error de toda la lista) o un arreglo con los errores de cada fila.
export default function MuestreoHistologia({ canastillas, onCambiar, disabled = false, guia = [], error }) {
  const [porQuitar, setPorQuitar] = useState(null); // clave de la fila que pide confirmación
  const erroresFila = Array.isArray(error) ? error : [];
  const errorGeneral = typeof error === 'string' ? error : '';

  const cambiar = (indice, campo, valor) =>
    onCambiar(canastillas.map((c, i) => (i === indice ? { ...c, [campo]: valor } : c)));

  const quitar = (indice) => {
    setPorQuitar(null);
    onCambiar(canastillas.filter((_, i) => i !== indice));
  };

  const agregar = () => onCambiar([...canastillas, ...conClaves([{ codigo: codigoSugerido(canastillas) }])]);

  const mensaje = (fila, campo) => {
    const errores = erroresFila[fila] || {};
    const valor = errores[campo] ?? (campo === 'region' ? errores.non_field_errors : undefined);
    return Array.isArray(valor) ? valor.join(' ') : valor;
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2>Muestreo para histología</h2>
      </div>
      <div className="card-body">
        <p className="text-muted">
          Registre el tejido enviado a procesamiento histológico y la canastilla de cada muestra. Es aparte de la
          descripción macroscópica y no constituye un diagnóstico.
        </p>

        {guia.length > 0 && (
          <details className="guia-muestreo">
            <summary>Indicaciones del manual para el muestreo</summary>
            {guia.map((bloque) => (
              <div key={bloque.titulo}>
                <h3>{bloque.titulo}</h3>
                <ul>
                  {bloque.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
            <p className="text-muted">Son una referencia: el sistema no agrega canastillas por su cuenta.</p>
          </details>
        )}

        {canastillas.length === 0 && <p className="text-muted">Todavía no hay canastillas registradas.</p>}

        <ol className="lista-canastillas">
          {canastillas.map((c, i) => {
            const numero = i + 1;
            const id = (campo) => `canastilla-${c.clave}-${campo}`;
            const campoTexto = (campo, etiqueta, { area = false, ancho = false, ...props } = {}) => {
              const errorCampo = mensaje(i, campo);
              const Elemento = area ? 'textarea' : 'input';
              return (
                <div className={`form-group ${ancho ? 'canastilla-ancha' : ''} ${errorCampo ? 'has-error' : ''}`}>
                  <label htmlFor={id(campo)}>{etiqueta}</label>
                  <Elemento
                    id={id(campo)}
                    aria-label={`${etiqueta} de la canastilla ${numero}`}
                    value={c[campo]}
                    onChange={(e) => cambiar(i, campo, e.target.value)}
                    disabled={disabled}
                    {...(area ? { rows: 2 } : { type: 'text' })}
                    {...props}
                  />
                  {errorCampo && <span className="field-error">{errorCampo}</span>}
                </div>
              );
            };
            return (
              <li key={c.clave} className="canastilla-fila">
                <p className="canastilla-titulo">Canastilla {c.codigo.trim() || numero}</p>
                <div className="canastilla-campos">
                  {campoTexto('codigo', 'Identificación', { maxLength: 20, placeholder: 'A, B, 1...' })}
                  {campoTexto('region', 'Región o estructura', { maxLength: 200 })}
                  {campoTexto('lesion_margen', 'Lesión o margen', { maxLength: 200 })}
                  {campoTexto('cantidad', 'Cantidad', { type: 'number', min: 0, step: 1 })}
                  {campoTexto('descripcion', 'Tejido muestreado', { area: true, ancho: true })}
                  {campoTexto('entintado', 'Entintado u orientación', { maxLength: 200 })}
                  {campoTexto('motivo', 'Motivo del muestreo', { maxLength: 200 })}
                  {campoTexto('observaciones', 'Observaciones', { area: true })}
                </div>
                {!disabled && (
                  <div className="diagnostico-acciones">
                    {porQuitar === c.clave ? (
                      <>
                        <span>¿Quitar la canastilla {c.codigo || numero}?</span>
                        <button type="button" className="btn btn-danger btn-xs" onClick={() => quitar(i)}>
                          Sí, quitar
                        </button>
                        <button type="button" className="btn btn-outline btn-xs" onClick={() => setPorQuitar(null)}>
                          No
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-danger-outline btn-xs"
                        onClick={() => setPorQuitar(c.clave)}
                        aria-label={`Quitar canastilla ${numero}`}
                      >
                        Quitar
                      </button>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ol>

        {errorGeneral && <span className="field-error">{errorGeneral}</span>}

        {!disabled && (
          <button type="button" className="btn btn-outline btn-sm" onClick={agregar}>
            + Agregar canastilla
          </button>
        )}
      </div>
    </div>
  );
}

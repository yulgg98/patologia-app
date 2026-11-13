import { useState } from 'react';

// El sugerido cambió después de que el patólogo editó la descripción: su versión existe
// y la base de la que partió ya no coincide con el sugerido actual (tarea 1, opción A).
export function sugeridoCambio({ sugerido, final, base }) {
  return Boolean(final.trim()) && Boolean(sugerido) && base !== sugerido;
}

/**
 * Texto sugerido por el sistema y descripción macroscópica del informe, que el patólogo
 * puede ajustar (tarea 1 de docs/mejoras-objetivos-investigacion.md). Controlado: la
 * versión del patólogo (`final`) y el sugerido del que partió (`base`) los guarda
 * InformePage. Si `final` está vacío, el informe usa el sugerido, como antes.
 */
export default function DescripcionMacroscopica({ sugerido, final, base, onCambiar, disabled }) {
  const [copiado, setCopiado] = useState('');
  const editado = Boolean(final.trim());
  const vigente = editado ? final : sugerido;
  const cambio = sugeridoCambio({ sugerido, final, base });

  // Al empezar a editar se guarda el sugerido de ese momento como base.
  const editar = (texto) => onCambiar({ final: texto, base: editado ? base : sugerido });
  // "Restaurar" y "Usar el nuevo texto sugerido": el informe vuelve a seguir al sugerido.
  const restaurar = () => onCambiar({ final: '', base: '' });
  const conservar = () => onCambiar({ final, base: sugerido });

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(vigente);
      setCopiado('Descripción copiada.');
    } catch {
      setCopiado('No se pudo copiar la descripción. Selecciónela y cópiela a mano.');
    }
  };

  return (
    <div className="descripcion-macroscopica">
      <h3 className="texto-generado-titulo">Texto sugerido</h3>
      <div className="generated-text">{sugerido || 'Se generará con los datos del formulario.'}</div>

      {cambio && !disabled && (
        <div className="alert alert-warning alert-lista" role="alert">
          <p>
            El texto sugerido cambió después de su edición. Puede usar el nuevo texto sugerido o conservar su versión.
          </p>
          <div className="descripcion-macroscopica-acciones">
            <button type="button" className="btn btn-outline btn-sm" onClick={restaurar}>
              Usar el nuevo texto sugerido
            </button>
            <button type="button" className="btn btn-outline btn-sm" onClick={conservar}>
              Conservar mi versión
            </button>
          </div>
        </div>
      )}

      <div className="form-group">
        <label htmlFor="descripcionMacroscopicaFinal">
          Descripción macroscópica del informe
          {editado && <span className="field-help"> (revisada por el patólogo)</span>}
        </label>
        <textarea
          id="descripcionMacroscopicaFinal"
          aria-label="Descripción macroscópica del informe"
          value={vigente}
          onChange={(e) => editar(e.target.value)}
          rows={6}
          disabled={disabled}
        />
      </div>

      <div className="descripcion-macroscopica-acciones">
        {!disabled && editado && (
          <button type="button" className="btn btn-outline btn-sm" onClick={restaurar}>
            Restaurar texto sugerido
          </button>
        )}
        <button type="button" className="btn btn-outline btn-sm" onClick={copiar} disabled={!vigente}>
          Copiar descripción
        </button>
        <span className="field-help" role="status" aria-live="polite">
          {copiado}
        </span>
      </div>
    </div>
  );
}

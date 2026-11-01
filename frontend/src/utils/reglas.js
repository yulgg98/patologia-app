// Reglas de los campos de una plantilla (decisión D-18). Repite camposAplicables() de
// backend/informes/reglas.py, que es quien valida de verdad: si cambia una, hay que
// cambiar la otra. Aquí sirven para no mostrar ni exigir lo que no aplica al procedimiento.

// Un campo sin responder. 0 y false son respuestas válidas ("0 ganglios", "No").
export const esVacio = (valor) => valor === null || valor === undefined || (typeof valor === 'string' && !valor.trim());

// Conjunto de campo_nombre que aplican con los datos dados. Un campo que depende de otro
// que no aplica tampoco aplica: un valor viejo de un campo oculto no muestra a los demás.
export function camposAplicables(plantillas, datos) {
  const porNombre = new Map(plantillas.map((p) => [p.campo_nombre, p]));
  const memoria = new Map();

  const aplica = (nombre, cadena = []) => {
    if (memoria.has(nombre)) return memoria.get(nombre);
    const condicion = porNombre.get(nombre).condicion || {};
    let resultado;
    if (!condicion.campo) {
      resultado = true;
    } else if (condicion.campo === nombre || cadena.includes(condicion.campo)) {
      resultado = false; // condición circular
    } else {
      const valor = datos[condicion.campo];
      const cumple = !esVacio(valor) && (condicion.valores || []).map(String).includes(String(valor));
      resultado = cumple && (!porNombre.has(condicion.campo) || aplica(condicion.campo, [...cadena, nombre]));
    }
    memoria.set(nombre, resultado);
    return resultado;
  };

  return new Set(plantillas.filter((p) => aplica(p.campo_nombre)).map((p) => p.campo_nombre));
}

// Agrupa las plantillas por sección, en el orden en que aparece cada una. Las que no
// tienen sección (plantillas de antes de D-18) van juntas, sin título.
export function agruparPorSeccion(plantillas) {
  const grupos = [];
  plantillas.forEach((plantilla) => {
    const nombre = (plantilla.seccion || '').trim();
    let grupo = grupos.find((g) => g.nombre === nombre);
    if (!grupo) {
      grupo = { nombre, campos: [] };
      grupos.push(grupo);
    }
    grupo.campos.push(plantilla);
  });
  return grupos;
}

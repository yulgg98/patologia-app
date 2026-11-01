"""
Reglas de los campos de una plantilla (decisión D-18): cuándo aplica un campo y cómo
se validan sus valores. No depende de Django: recibe objetos con los atributos de
`Plantilla` (`campo_nombre`, `campo_label`, `tipo_campo`, `obligatorio`, `opciones`
y `condicion`). `frontend/src/utils/reglas.js` repite `campos_aplicables()`: si cambia
una, hay que cambiar la otra.

Cada campo es, según su plantilla y los datos del informe:
- obligatorio: `obligatorio` y sin `condicion`; se exige siempre;
- condicional: `obligatorio` con `condicion`; se exige solo cuando aplica;
- opcional: no `obligatorio`; se llena si corresponde;
- no aplicable: tiene `condicion` y no se cumple; no se muestra, no se exige y no se
  redacta en la descripción, aunque tenga un valor guardado.

Nada se completa ni se deduce: un campo vacío sigue vacío y no es un hallazgo negativo.
"""


def es_vacio(valor):
    """Un campo sin responder. 0 y False son respuestas válidas ("0 ganglios", "No")."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, dict)):
        return len(valor) == 0
    return False


def _cumple(condicion, datos):
    valor = datos.get(condicion.get('campo'))
    if es_vacio(valor):
        return False
    return str(valor) in [str(v) for v in condicion.get('valores') or []]


def campos_aplicables(plantillas, datos):
    """
    Conjunto de `campo_nombre` que aplican con los datos dados. Un campo que depende de
    otro que no aplica tampoco aplica: así un valor viejo de un campo oculto no muestra
    los campos que dependen de él.
    """
    por_nombre = {p.campo_nombre: p for p in plantillas}
    memoria = {}

    def aplica(nombre, cadena=()):
        if nombre in memoria:
            return memoria[nombre]
        condicion = por_nombre[nombre].condicion or {}
        if not condicion:
            resultado = True
        else:
            depende = condicion.get('campo')
            if depende in cadena or depende == nombre:  # condición circular: no aplica
                resultado = False
            else:
                resultado = _cumple(condicion, datos) and (
                    depende not in por_nombre or aplica(depende, (*cadena, nombre))
                )
        memoria[nombre] = resultado
        return resultado

    return {nombre for nombre in por_nombre if aplica(nombre)}


def _etiqueta(plantilla):
    return plantilla.campo_label or plantilla.campo_nombre


def validar_datos(plantillas, datos, guardados=None):
    """
    Errores de los datos del formulario frente a su plantilla, como lista de textos
    (vacía si no hay): obligatorios que aplican y están vacíos, números no válidos o
    negativos y valores de lista que no están entre las opciones. Los campos que no
    aplican no se revisan. `guardados` son los datos que ya tenía el informe: un valor
    de lista que ya estaba guardado se conserva aunque la opción se haya quitado después
    de la plantilla, como una EPS desactivada (D-4).
    """
    guardados = guardados or {}
    plantillas = list(plantillas)
    aplican = campos_aplicables(plantillas, datos)
    faltantes, no_validos = [], []
    for plantilla in plantillas:
        if plantilla.campo_nombre not in aplican:
            continue
        valor = datos.get(plantilla.campo_nombre)
        if es_vacio(valor):
            if plantilla.obligatorio:
                faltantes.append(_etiqueta(plantilla))
        elif plantilla.tipo_campo == 'numero':
            try:
                numero = float(str(valor).replace(',', '.'))
            except ValueError:
                no_validos.append(f'«{_etiqueta(plantilla)}» debe ser un número.')
                continue
            if numero < 0:
                no_validos.append(f'«{_etiqueta(plantilla)}» no puede ser negativo.')
        elif (
            plantilla.tipo_campo == 'lista'
            and plantilla.opciones
            and str(valor) not in plantilla.opciones
            and valor != guardados.get(plantilla.campo_nombre)
        ):
            no_validos.append(f'«{_etiqueta(plantilla)}»: «{valor}» no es una de las opciones.')

    errores = []
    if faltantes:
        errores.append(f'Faltan campos obligatorios: {", ".join(faltantes)}')
    return errores + no_validos

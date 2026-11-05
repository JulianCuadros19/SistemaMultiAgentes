# Conciliación diaria de pagos

Módulo para el analista de recaudo. Procesa CSV de los bancos A, B y C contra facturas mediante cuatro etapas independientes: `lectura`, `normalizacion`, `conciliacion` y `escritura`.

Usa Python 3.11 y únicamente la biblioteca estándar. Las pruebas requieren pytest. No utiliza red, base de datos ni interfaz gráfica.

## Uso

Con `src/` en la ruta de importación:

```python
from conciliacion import Entrada, ErrorEtapa, Lote

lote = Lote(
    [
        Entrada("A", "entrada/banco_a.csv"),
        Entrada("B", "entrada/banco_b.csv"),
        Entrada("C", "entrada/banco_c.csv"),
        Entrada("facturas", "entrada/facturas.csv"),
    ],
    destino="salida/lote_2026_11_05",
)

try:
    lote.ejecutar()
except ErrorEtapa as error:
    print(error)
    print("Completadas:", lote.completadas)
    # Corregir la causa externa antes de reintentar.
    # Esta llamada reintenta exclusivamente la etapa fallida:
    lote.ejecutar_etapa(error.etapa)
    # Después se pueden ejecutar las siguientes etapas pendientes:
    lote.ejecutar()

print(lote.resumen)
for incidencia in lote.incidencias:
    print(incidencia)
```

También se puede ejecutar cada etapa explícitamente, en orden. Una llamada sobre una etapa completada no hace nada. `ejecutar()` continúa desde la primera pendiente y se detiene ante un fallo.

Los resultados de las etapas completadas se conservan en memoria. Un fallo no incorpora resultados parciales de esa etapa. Si falló escritura, su reintento utiliza exactamente el detalle ya conciliado. Si se cambian los CSV después de completar lectura, esos cambios **no** se vuelven a leer: para procesar entradas nuevas o corregir datos ya leídos se crea otro `Lote`.

## Entradas

Se reciben objetos `Entrada(origen, ruta)` y una ruta de directorio de salida. Esta interfaz de rutas es una decisión mínima de implementación, no una regla de negocio aprobada. Se admiten varios archivos de un origen y también subconjuntos de entradas; para el lote diario habitual deben proporcionarse los tres bancos y las facturas.

| Origen | Separador | Columnas obligatorias | Fecha del banco |
|---|---|---|---|
| `A` | `;` | `referencia`, `valor`, `fecha` | `AAAA-MM-DD` |
| `B` | `,` | `REF`, `MONTO`, `FECHA_PAGO` | `DD/MM/AAAA` |
| `C` | `,` | `referencia_factura`, `valor_pagado`, `fecha` | `AAAA/MM/DD` |
| `facturas` | `,` | `referencia`, `valor`, `vencimiento` | No definido |

Los archivos se leen como UTF-8, admitiendo BOM y comillas CSV. Los nombres de columnas son exactos; las columnas adicionales con nombre se ignoran. Se recortan espacios exteriores de referencias, importes y fechas. Las referencias distinguen mayúsculas y minúsculas. No se interpretan como números: por ejemplo, `001` y `1` son referencias distintas.

El cliente indicó importes en pesos sin decimales. Para los casos definitivos se interpretan enteros positivos escritos con dígitos ASCII, sin símbolos ni separadores de miles; se admite un signo `+` inicial como representación equivalente. No hay redondeos ni conversiones monetarias.

Los formatos de importe no definidos se tratan conservadoramente:

- Importes numéricos decimales, notación exponencial, cero y negativos: se conservan para **revisión**, no se concilian como definitivos.
- Texto no interpretable como número, vacío, símbolos de moneda o separadores de miles: se rechaza la fila y se informa `importe no numérico`. No se intenta adivinar su significado. `NaN` e infinitos tampoco se aceptan.

No se fijan límites de negocio propios. Se cargan los datos en memoria; aplican la memoria disponible y los límites normales de CSV, conversión numérica y sistema de archivos de Python.

## Reglas implementadas

Se genera un registro por referencia aceptada, considerando conjuntamente todos los bancos:

- Una factura y un pago de igual valor: `conciliada`.
- Una factura y un pago distinto: `con_diferencia`.
- Una factura sin pagos: `pendiente`.
- Un pago sin factura: `pago_sin_factura`.
- Varios pagos, facturas repetidas, fechas bancarias inválidas o importes numéricos sin regla clara: `revision`. Esta condición tiene prioridad sobre los estados definitivos.

No se suman pagos ni facturas repetidas. Una referencia vacía se conserva para revisión de forma aislada, sin asociarla automáticamente con otras referencias vacías.

Las fechas bancarias se verifican tanto por existencia en el calendario como por formato exacto. Las inválidas **no se descartan**: la referencia queda para revisión. El formato de `vencimiento` no fue definido; se conserva en los datos leídos, pero no se valida ni interviene en los estados. No se calculan mora, intereses o estados por vencimiento.

Una columna obligatoria faltante rechaza **todo ese archivo** y registra una incidencia por columna faltante. El lote continúa con los otros archivos. Un importe no numérico rechaza **solo esa fila**. Los reportes se basan exclusivamente en archivos y filas aceptados: un archivo de facturas rechazado puede provocar pagos sin factura, y un pago rechazado puede dejar una factura pendiente. El analista debe revisar también las incidencias; estos casos no significan un fallo técnico reintentable.

## Salidas

La escritura crea el directorio de salida si hace falta y sustituye estos archivos:

### `detalle.csv`

CSV UTF-8, separado por coma, con encabezado:

```text
referencia,valor_facturado,valor_pagado,banco,estado,diferencia
```

- En estados definitivos, los importes existentes son textos de enteros normalizados.
- Un dato inexistente se deja vacío: no se representa ausencia de pago como un pago de cero.
- `banco` indica `A`, `B` o `C`; varios bancos aparecen ordenados, separados por `|`.
- En `revision`, los importes presentes se muestran como **listas JSON de los textos originales recortados**, incluso si hay solo uno. Ejemplo: valor pagado `["40", "60"]`. El escritor CSV aplica las comillas necesarias. Son evidencias para revisar, no un total pagado definitivo. Si no hay importes de ese lado, la celda está vacía.
- La diferencia de una conciliada es `0`. Para un pago de 80 contra una factura de 100 se escribe `faltan 20`; para un pago de 120 se escribe `sobran 20`. Esto evita imponer una convención de signo no acordada. En pendientes, pagos sin factura y revisiones se deja vacía.

El orden sigue la primera aparición de cada referencia en las entradas. Estas representaciones son decisiones mínimas documentadas, no políticas de negocio adicionales.

### `resumen.json`

Objeto con cantidades de **registros del detalle**, no sumas de dinero ni cantidades de pagos originales. Incluye siempre los cinco estados, incluso con cantidad cero. Varios pagos de una referencia generan un registro de revisión y cuentan una vez.

### `incidencias.json`

Lista de problemas con `etapa`, `archivo`, `fila`, `columna` y `mensaje`. Permite localizar tanto rechazos como motivos de revisión. `fila` es el número de línea física final del registro CSV, incluyendo el encabezado; normalmente el primer dato está en la línea 2. Para columnas faltantes, `fila` es nula.

Las propiedades `lote.detalle`, `lote.resumen` y `lote.incidencias` permiten consultar los resultados sin volver a leer los reportes. El detalle y el resumen requieren que la conciliación esté completada; las incidencias están disponibles a medida que terminan las etapas.

## Errores y reintentos

- Origen desconocido: `ValueError`, por ejemplo `Origen desconocido: D.`.
- Nombre de etapa desconocido: `ValueError`, por ejemplo `Etapa desconocida: otra.`.
- Ejecución fuera de orden: `ValueError`, por ejemplo `Debe completarse primero la etapa lectura.`.
- Consulta prematura del detalle o resumen: `ValueError`, `La conciliación todavía no está completada.`.
- Fallos de acceso, codificación, sintaxis CSV o procesamiento: `ErrorEtapa`, con atributo `etapa` y excepción original en `__cause__`. El mensaje incluye la etapa y la causa. No se ocultan errores de programación inesperados.
- Filas con más campos que el encabezado se consideran CSV malformado y fallan en lectura, indicando archivo y línea. Una celda ausente se lee como vacía y sigue las reglas anteriores.

`completadas` y `etapa_fallida` permiten conocer el avance. No hay reintentos automáticos ni un número máximo impuesto.

Los tres reportes se preparan primero en un directorio temporal y cada archivo se sustituye mediante `os.replace`. **No hay una transacción conjunta de los tres archivos**: si falla una sustitución, puede quedar una mezcla de reportes anteriores y nuevos. Solo se deben consumir cuando `escritura` esté completada; el reintento vuelve a escribir los tres desde los resultados conservados. Conviene usar un directorio diferente por lote.

## Puntos abiertos y alcance excluido

La conservación es en la misma instancia viva de `Lote`. No se implementa recuperación después de cerrar el proceso porque su almacenamiento y operación no fueron definidos. Esta limitación y la interfaz de rutas son decisiones mínimas de esta entrega, no requisitos confirmados por el cliente. No hay ejecución concurrente segura sobre una misma instancia o directorio.

Tampoco se implementan decisiones definitivas sobre pagos múltiples, facturas duplicadas, fechas inválidas, importes cero o negativos, ni resolución manual de revisiones. No se añaden deduplicación de pagos, tolerancias monetarias, conciliación por fechas, conexión con bancos, interfaz de usuario o programador de tareas.

## Pruebas

Desde la raíz del proyecto, con `src/` en la ruta de importación:

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas cubren los tres formatos bancarios, estados, diferencias por faltante y excedente, revisiones sin sumar, rechazos de archivos y filas, reportes, diagnóstico y fallos/reintentos de cada etapa. Los ejemplos de 100, 80 y 120 verifican la representación elegida; no se presentan como ejemplos reales ni como una convención de signo aprobada.

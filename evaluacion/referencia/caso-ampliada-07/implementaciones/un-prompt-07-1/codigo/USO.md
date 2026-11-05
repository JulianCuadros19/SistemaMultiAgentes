# Conciliación de pagos

Módulo Python 3.11 para conciliar por lotes los pagos de los bancos A, B y C contra las facturas emitidas. Lee los cuatro CSV, normaliza sus filas, concilia, escribe un CSV y devuelve un informe con el conteo de cada estado y las filas rechazadas. No emite facturas ni gestiona cobros.

Solo utiliza la biblioteca estándar. Las pruebas requieren pytest. No necesita conexión de red.

## Uso

Con `src/` en la ruta de importación:

```python
from pathlib import Path

from conciliacion import Archivos, Lote

archivos = Archivos(
    banco_a=Path("pagos_a.csv"),
    banco_b=Path("pagos_b.csv"),
    banco_c=Path("pagos_c.csv"),
    facturas=Path("facturas.csv"),
)
lote = Lote(archivos, Path("resultado.csv"))
informe = lote.ejecutar()

print(informe.resumen)
for rechazo in informe.rechazadas:
    print(rechazo.archivo, rechazo.fila, rechazo.motivo)
```

El directorio de salida debe existir. El archivo destino se reemplaza si existe. La escritura usa un temporal en el mismo directorio y sustitución atómica: no deja un CSV parcial como resultado.

### Etapas y reintentos

Las etapas son `lectura`, `normalización`, `conciliación` y `escritura`. `lote.etapa_pendiente` indica la primera sin completar; devuelve `None` al terminar.

Si `ejecutar()` falla, la excepción se propaga. Corrija la causa y vuelva a llamar **sobre la misma instancia**:

```python
try:
    informe = lote.ejecutar()
except OSError as error:
    print("Falló", lote.etapa_pendiente, error)
    # Corregir permisos, disponibilidad de archivos o directorio destino.
    # Después, sin crear otro Lote:
    # informe = lote.ejecutar()
```

Las etapas terminadas devuelven su resultado guardado, sin volver a ejecutar su procesamiento. La etapa fallida no guarda un resultado y se reintenta completa. Tras su éxito se ejecutan las etapas posteriores pendientes. Una fila rechazada no es un fallo de etapa.

También se pueden ejecutar individualmente:

```python
lectura = lote.leer()
datos = lote.normalizar()
informe = lote.conciliar()
informe = lote.escribir()
```

Una etapa individual exige que su predecesora ya esté completada; en otro caso lanza `RuntimeError`. Existen además las funciones independientes `leer_archivos`, `normalizar`, `conciliar` y `escribir_csv` con esos mismos tipos de entrada y salida, pero el control de reintentos lo proporciona `Lote`.

**Decisión de alcance:** los resultados intermedios se conservan en memoria, no en disco. Los reintentos funcionan durante la vida de la misma instancia; no permiten recuperar un lote después de reiniciar el proceso. Una nueva instancia inicia un nuevo lote. Los cuatro archivos se leen como una sola etapa: si falla la lectura, se reintenta la lectura completa. Cambiar entradas después de una lectura exitosa no modifica su instantánea; para procesar datos corregidos hay que crear otro lote. No comparta una instancia entre hilos ni modifique los diccionarios de sus resultados. Una escritura ya completada no se repite aunque posteriormente se borre el destino.

## Entradas

Rutas `pathlib.Path` a archivos UTF-8; se admite BOM. Todos requieren encabezado:

| Archivo | Separador | Columnas obligatorias | Fecha del pago |
|---|---|---|---|
| Banco A | `;` | `referencia;valor;fecha` | `AAAA-MM-DD` |
| Banco B | `,` | `REF,MONTO,FECHA_PAGO` | `DD/MM/AAAA` |
| Banco C | `,` | `referencia_factura,valor_pagado,fecha` | `AAAA/MM/DD` |
| Facturas | `,` | `referencia,valor,vencimiento` | No aplica |

El orden de las columnas es libre y se ignoran columnas adicionales. Sus nombres deben coincidir exactamente. Los archivos con solo encabezado son válidos. El lector estándar ignora líneas vacías. Una celda ausente se trata como texto vacío.

Los importes se convierten a enteros sin usar coma flotante. Se aceptan `85000` y `85.000`: los puntos se interpretan exclusivamente como agrupadores de miles, nunca como separadores decimales. Se permiten espacios exteriores y signo opcional. Se rechazan importes vacíos, texto, notación científica, decimales y agrupaciones incorrectas. No se impone una restricción de signo porque no fue indicada.

Las fechas bancarias se interpretan con `datetime.strptime` según los formatos de la tabla. Una fecha imposible o incompatible rechaza la fila. No se especificó el formato de vencimiento ni una regla basada en él: se conserva como texto, sin validarlo y sin usarlo en la conciliación. Las referencias y los campos normalizados pierden espacios exteriores; las referencias distinguen mayúsculas de minúsculas. No se añade una regla de rechazo por referencia vacía.

## Reglas y decisiones no especificadas

- Cada pago válido se compara con una factura de igual referencia.
- Si los valores coinciden: `conciliado`, diferencia `0`.
- Si no coinciden: `diferencia`, calculada como **valor facturado menos valor pagado**. Un sobrepago produce una diferencia negativa.
- Si no existe factura válida para la referencia: `pago sin factura`.
- Una referencia de factura sin ningún pago válido: `pendiente`. Un pago con diferencia sí cuenta como pago para este criterio.
- No se definieron pagos múltiples ni facturas duplicadas. La decisión simple es generar una fila por pago, sin sumar pagos ni deduplicarlos. Si varias facturas válidas tienen la misma referencia, se usa la primera y se genera como máximo una fila pendiente para esa referencia.
- Las filas rechazadas se excluyen del cruce: un pago rechazado puede dejar una factura pendiente; una factura rechazada puede hacer que un pago quede sin factura.
- Los resultados siguen el orden de pagos A, B y C y luego las referencias pendientes en el orden del archivo de facturas.

## Salidas

El CSV se escribe en UTF-8, separado por coma, con estas columnas:

```text
referencia,valor_facturado,valor_pagado,banco,estado,diferencia
```

Todos los importes escritos son enteros sin agrupadores. El banco es `A`, `B` o `C`.

| Estado | Valor facturado | Valor pagado | Banco | Diferencia |
|---|---|---|---|---|
| conciliado | Importe de factura | Importe del pago | Banco del pago | `0` |
| diferencia | Importe de factura | Importe del pago | Banco del pago | Facturado − pagado |
| pago sin factura | Vacío | Importe del pago | Banco del pago | Vacío |
| pendiente | Importe de factura | `0` | Vacío | Vacío |

El ejemplo indicado produce:

```csv
referencia,valor_facturado,valor_pagado,banco,estado,diferencia
F-001,85000,85000,A,conciliado,0
F-002,120000,100000,B,diferencia,20000
F-999,,30000,C,pago sin factura,
F-003,40000,0,,pendiente,
```

Los importes de F-999 y F-003 son ilustrativos: el cliente no indicó sus valores.

`Informe` contiene:

- `resultados`: tupla de objetos `Resultado`; los importes no aplicables se representan con `None`.
- `resumen`: diccionario con **cantidad de filas** por estado, no suma monetaria. Incluye siempre los cuatro estados, incluso con total cero. En el ejemplo todos valen `1`.
- `rechazadas`: tupla de objetos `Rechazo`, cada uno con `archivo`, `fila` y `motivo`. `fila` identifica la línea física donde termina la fila CSV; la primera fila simple de datos corresponde a la línea 2.

El resumen y los rechazos se entregan por la API, no como archivos adicionales; no se especificó un formato de persistencia para ellos.

## Errores

- `ColumnaFaltanteError`: rechaza el archivo y falla la etapa de lectura. Sus atributos `archivo` y `columna` y su mensaje identifican el problema. Si faltan varias columnas, informa la primera en el orden de columnas obligatorias.
- Un importe inválido en cualquier archivo se registra como `Rechazo`, sin detener el lote ni escribir esa fila como resultado directo.
- Una fecha de pago inválida también se registra como rechazo de fila.
- Errores de archivos, permisos, codificación o del lector CSV se propagan. La etapa no queda completada.
- `RuntimeError`: se solicitó una etapa individual sin completar su predecesora.

No hay reintentos automáticos ni silenciosos. El llamador decide cuándo corregir y reintentar.

## Pruebas

En Linux/macOS:

```sh
PYTHONPATH=src python -m pytest tests
```

En PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests
```

Las pruebas cubren formatos bancarios, los cuatro casos del ejemplo, resumen y CSV, cada columna obligatoria ausente, rechazos numéricos en los cuatro archivos, fechas inválidas, decisiones de importes y duplicados, lotes vacíos y reintentos de cada etapa sin repetir las anteriores. También comprueban que un fallo de escritura conserva el archivo destino anterior.

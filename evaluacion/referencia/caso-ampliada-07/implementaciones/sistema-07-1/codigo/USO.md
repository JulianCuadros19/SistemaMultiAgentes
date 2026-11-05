# Conciliación de recaudo

Procesa pagos de tres bancos contra facturas emitidas, genera un CSV de resultados y devuelve los totales por estado. Conserva las salidas intermedias para reanudar el procesamiento sin repetir etapas anteriores.

## Requisitos

- Python 3.11 o superior; el módulo se probó con Python 3.11.
- Sin dependencias externas: `requirements.txt` fija la versión de pytest.

## Instalación

Desde la carpeta del código, cree un entorno e instale las dependencias:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, el entorno se activa con `.venv\Scripts\activate`. `requirements.txt` acompaña al código: fija las versiones con que se probó e incluye pytest.

## Configuración

Prepare cuatro archivos CSV en UTF-8:

| Archivo | Cabecera | Separador | Fecha |
|---|---|---|---|
| Banco A | `referencia;valor;fecha` | `;` | `AAAA-MM-DD` |
| Banco B | `REF,MONTO,FECHA_PAGO` | `,` | `DD/MM/AAAA` |
| Banco C | `referencia_factura,valor_pagado,fecha` | `,` | `AAAA/MM/DD` |
| Facturas | `referencia,valor,vencimiento` | `,` | `AAAA-MM-DD` |

Los valores son textos de enteros en pesos, sin separadores de miles. El directorio del archivo de resultados debe existir. No se requieren variables de entorno para el procesamiento.

## Ejecución

No hay una interfaz de línea de comandos. Desde la raíz del código puede ejecutar:

```sh
PYTHONPATH=src python -c 'from orquestacion.pipeline import Orquestador; print(Orquestador().ejecutar("a.csv", "b.csv", "c.csv", "facturas.csv", "resultado.csv"))'
```

Para reanudar, conserve la misma instancia de `Orquestador`. Los reintentos son explícitos y no automáticos.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Contratos: `contratos.esquemas`

```python
from datetime import date
from decimal import Decimal
from contratos.esquemas import (
    PagoEntrada, Factura, DatosLeidos, PagoNormalizado,
    DatosNormalizados, RegistroResultado, Resumen, ResultadoConciliacion,
)

entrada = PagoEntrada("F1", "100", "2024-02-29", "A")
factura = Factura("F1", Decimal("100"), date(2024, 3, 1))
leidos = DatosLeidos([entrada], [factura])
pago = PagoNormalizado("F1", "100", date(2024, 2, 29), "A")
normalizados = DatosNormalizados([pago], [factura])
fila = RegistroResultado("F1", Decimal("100"), Decimal("100"), "A",
                         "conciliado", Decimal(0))
resumen = Resumen(1, 0, 0, 0)
resultado = ResultadoConciliacion([fila], resumen)
```

### Etapas

- `leer_archivos(a, b, c, facturas)` devuelve `DatosLeidos`.
- `ColumnaFaltante(archivo, columna)` conserva ambos datos como atributos y en su mensaje. Ejemplo: `ColumnaFaltante("a.csv", "valor")`.
- `normalizar_datos(leidos)` devuelve `DatosNormalizados`.
- `conciliar_lotes(normalizados)` devuelve `ResultadoConciliacion`.
- `escribir_resultados(resultado, "resultado.csv")` escribe las seis columnas requeridas.
- `EscrituraError(mensaje)` representa un fallo de escritura. Ejemplo: `EscrituraError("No se pudo escribir el resultado.")`.

```python
from etapas.lectura import leer_archivos
from etapas.normalizacion import normalizar_datos
from etapas.conciliacion import conciliar_lotes
from etapas.escritura import escribir_resultados

leidos = leer_archivos("a.csv", "b.csv", "c.csv", "facturas.csv")
resultado = conciliar_lotes(normalizar_datos(leidos))
escribir_resultados(resultado, "resultado.csv")
```

### Utilidades: `entrada_salida.archivos`

```python
from entrada_salida.archivos import (
    generar_csv_banco_a, generar_csv_banco_b, generar_csv_banco_c,
    generar_csv_facturas, escribir_texto, leer_csv_resultados,
)

generar_csv_banco_a("a.csv", [("F1", "100", "2024-02-29")])
generar_csv_banco_b("b.csv", [("F2", "200", "29/02/2024")])
generar_csv_banco_c("c.csv", [("F3", "300", "2024/02/29")])
generar_csv_facturas("facturas.csv", [("F1", "100", "2024-03-01")])
escribir_texto("incompleto.csv", "referencia;fecha\n")
filas = leer_csv_resultados("resultado.csv")
```

Las utilidades generadoras escriben literalmente los datos recibidos, permitiendo preparar también entradas inválidas. La validación corresponde a las etapas.

### Orquestación: `orquestacion.pipeline`

```python
from orquestacion.pipeline import Orquestador

pipeline = Orquestador()
resumen = pipeline.ejecutar("a.csv", "b.csv", "c.csv", "facturas.csv", "resultado.csv")

otro = Orquestador()
otro.ejecutar_hasta("normalizacion", "a.csv", "b.csv", "c.csv", "facturas.csv")
resumen = otro.reintentar_desde("conciliacion", "resultado.csv")
contadores = otro.obtener_contadores()
```

`ejecutar_hasta` acepta `lectura`, `normalizacion` o `conciliacion`. `reintentar_desde` acepta `normalizacion`, `conciliacion` o `escritura` y ejecuta también las etapas posteriores. `obtener_contadores` devuelve una copia con los intentos acumulados por etapa, incluidos los fallidos.

Si falla la escritura, puede llamar nuevamente a `reintentar_desde("escritura", destino)` sin repetir la conciliación. Iniciar otro lote con `ejecutar` o `ejecutar_hasta` reemplaza el estado intermedio anterior, pero conserva los contadores acumulados.

## Supuestos

- La diferencia se calcula como valor pagado menos valor facturado; puede ser negativa.
- Los importes cero y negativos se admiten porque no se especifica una restricción de signo. Se permiten espacios exteriores y signo explícito en los textos numéricos, pero no decimales, exponentes ni separadores de miles.
- La validación numérica de pagos se difiere deliberadamente hasta conciliación. Una fila inválida no genera un registro de pago; su factura queda pendiente si no hay otro pago válido asociado. No existe una interfaz declarada para devolver un listado de rechazos.
- Las facturas de valor no entero se omiten durante lectura: el contrato `Factura` exige un `Decimal` entero y no permite transportar el texto inválido hasta conciliación.
- Las referencias se cruzan literalmente. Se supone una factura por referencia. Ante facturas repetidas se utiliza la última; los pagos repetidos se procesan individualmente, sin agregación.
- Fechas inválidas, referencias vacías, filas incompletas y etapas inválidas producen `ValueError`; no se declara una excepción específica para esos casos. Los errores de lectura del sistema de archivos se propagan como `OSError`.
- El estado intermedio vive únicamente en la instancia y no sobrevive al cierre del proceso. No hay reintentos automáticos ni persistencia.
- Existe una incompatibilidad entre la firma de `leer_csv_resultados`, que menciona `RegistroResultado`, y la prohibición de importar contratos en `entrada_salida.archivos`. Para mantener esa independencia, la utilidad devuelve registros locales estructuralmente equivalentes, con los mismos campos y tipos, pero no instancias de `contratos.esquemas.RegistroResultado`.
- No se puede provocar una falla de conciliación mediante una dependencia inyectada: esa etapa no recibe dependencias externas y omite los valores inválidos. Se verifica la reanudación desde conciliación tras detenerse en normalización y, adicionalmente, una falla real de escritura seguida de su reintento, sin simular fallas de la etapa bajo prueba.

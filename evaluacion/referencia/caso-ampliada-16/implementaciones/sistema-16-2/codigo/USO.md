# Simulador de crédito de vivienda

Calcula la cuota fija, genera la amortización mensual con cierre exacto y entrega un resumen de pagos e intereses. Permite exportar la tabla a CSV cuando se solicita.

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

Prepare la tasa efectiva anual como `Decimal` porcentual entre 1 y 30, con hasta dos decimales; el monto como `Decimal` entre 10.000.000 y 500.000.000; y el plazo como entero entre 12 y 240 meses.

Para exportar, indique una ruta cuyo directorio ya exista y sea escribible. El archivo se reemplaza si existe; se escribe en UTF-8 con encabezado y separador coma por defecto.

## Ejecución

Se proporcionan subcomandos lógicos invocables desde Python, no un analizador de argumentos de terminal. Desde la raíz del código puede calcular una cuota con:

```sh
PYTHONPATH=src python -c "from decimal import Decimal; from comandos.cli import ejecutar_cuota; print(ejecutar_cuota(Decimal('12'), Decimal('100000000'), 120))"
```

Resultado: `1399472`.

Para exportar:

```python
from decimal import Decimal
from comandos.cli import ejecutar_tabla

tabla = ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, 'tabla.csv')
```

Los errores de entrada producen `ErrorCLI`, con `codigo_salida` igual a 2 y `mensaje` explicativo. El programa que integre estas funciones es responsable de mostrar el mensaje y terminar con ese código.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Dominio: `dominio.credito`

- `AmortizacionFila(mes, saldo_inicial, interes, abono_capital, cuota, saldo_final)`: contenedor inmutable. Ejemplo: `AmortizacionFila(1, Decimal('100'), Decimal('1'), Decimal('10'), Decimal('11'), Decimal('90'))`.
- `Resumen(total_pagado, total_intereses)`: contenedor inmutable. Ejemplo: `Resumen(Decimal('110'), Decimal('10'))`.
- `tasa_mensual(tea)`: recibe una tasa fraccionaria, no porcentual. Ejemplo: `tasa_mensual(Decimal('0.12'))`.
- `cuota_fija(monto, plazo, tasa_mensual)`: aplica la anualidad sin redondeo final. Ejemplo: `cuota_fija(Decimal('100000000'), 120, tasa_mensual(Decimal('0.12')))`.
- `redondear_peso(valor)`: ejemplo: `redondear_peso(Decimal('125.50'))`, que devuelve `Decimal('126')`.

### Servicios: `servicios.simulador`

- `ValidacionError(mensaje)`: error de entrada; ejemplo de construcción: `ValidacionError('El plazo es inválido.')`.
- `calcular_cuota(tea, monto, plazo)`: ejemplo: `calcular_cuota(Decimal('12'), Decimal('100000000'), 120)`.
- `generar_tabla(tea, monto, plazo)`: ejemplo: `generar_tabla(Decimal('12'), Decimal('100000000'), 120)`.
- `calcular_resumen(tea, monto, plazo)`: ejemplo: `calcular_resumen(Decimal('12'), Decimal('100000000'), 120)`.

### CSV: `entrada_salida.csv_salida`

- `TablaCSV(delimitador=',')`: ejemplo: `escritor = TablaCSV(';')`.
- `TablaCSV.guardar(tabla, ruta)`: ejemplo: `escritor.guardar(tabla, 'tabla.csv')`.
- `TablaCSV.existe(ruta)`: ejemplo: `escritor.existe('tabla.csv')`; devuelve un booleano.

Las columnas son `mes`, `saldo_inicial`, `interes`, `abono_capital`, `cuota` y `saldo_final`.

### Subcomandos: `comandos.cli`

- `ErrorCLI(codigo_salida, mensaje)`: expone ambos datos y el mensaje de la excepción. Ejemplo de construcción: `ErrorCLI(2, 'Debe ingresar el monto.')`.
- `ejecutar_cuota(tea, monto, plazo)`: ejemplo: `ejecutar_cuota(Decimal('12'), Decimal('100000000'), 120)`.
- `ejecutar_tabla(tea, monto, plazo, ruta_csv, escritor=None)`: ejemplo sin exportación: `ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, None)`. Con exportación personalizada: `ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, 'tabla.csv', TablaCSV(';'))`.
- `ejecutar_resumen(tea, monto, plazo)`: ejemplo: `ejecutar_resumen(Decimal('30'), Decimal('500000000'), 240)`.

## Supuestos

- Las tasas de servicios y comandos son porcentajes; la función pura `tasa_mensual` recibe una fracción anual. Las funciones puras no validan rangos y trabajan con entradas válidas.
- Se emplea precisión decimal de 40 dígitos para los cálculos y redondeo `ROUND_HALF_UP` al peso.
- Los ceros finales no cuentan como decimales adicionales: `Decimal('12.000')` representa una tasa válida.
- Como no se restringen los decimales del monto, se admite capital fraccionario. La cuota se calcula con el monto ingresado y el saldo inicial de la tabla se redondea al peso; el resumen conserva coherencia con esa tabla.
- Los contenedores del dominio representan resultados; la validación de entradas del crédito corresponde a los servicios.
- El adaptador CSV no tiene permitido importar el dominio. Por ello recibe las filas por sus atributos y utiliza un alias de anotación `AmortizacionFila` basado en `Any`, sin dependencia del módulo de dominio. Los comandos y servicios sí utilizan la clase concreta del dominio.
- Los errores de acceso al archivo y de configuración del escritor se propagan desde la biblioteca estándar; no se convierten en errores de validación del crédito.
- No hay punto de entrada ejecutable ni formato de presentación de tablas y resúmenes declarado: los comandos devuelven los objetos correspondientes.

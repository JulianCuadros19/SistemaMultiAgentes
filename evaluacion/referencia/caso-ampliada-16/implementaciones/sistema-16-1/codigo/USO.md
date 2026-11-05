# Simulador de crédito de vivienda

Calcula cuotas mensuales, tablas de amortización y resúmenes de créditos mediante aritmética Decimal.

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

No requiere para los cálculos. Para guardar una tabla, prepare una ruta de archivo cuyo directorio padre exista y permita escritura. El archivo de destino se sobrescribe.

## Ejecución

No se declara un punto de entrada de terminal ni un analizador de argumentos. Desde la raíz del código puede invocar las interfaces así:

```sh
PYTHONPATH=src python -c 'from decimal import Decimal; from dominio.credito import ParametrosCredito; from comandos.simulador import main_cuota; print(main_cuota(ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))))'
```

Desde Python, coloque `src` en la ruta de importación y utilice los ejemplos siguientes. Los adaptadores devuelven resultados; corresponde al programa consumidor presentarlos y gestionar las excepciones. Si una excepción de validación no se captura al ejecutar Python desde la terminal, Python muestra su mensaje en la salida de error y termina con un código distinto de cero.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

```python
from decimal import Decimal
from dominio.credito import (
    AmortizacionFila,
    DatosInvalidosError,
    ParametrosCredito,
    ResumenCredito,
)
from entrada_salida.tabla_csv import EscritorTablaCSV
from servicios.simulacion import calcular_cuota, calcular_resumen, generar_tabla
from comandos.simulador import main_cuota, main_resumen, main_tabla

# ParametrosCredito: valida automáticamente al construir.
p = ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))
p.validar()                       # ParametrosCredito.validar
mensual = p.tasa_mensual()         # ParametrosCredito.tasa_mensual

cuota = calcular_cuota(p)          # int, pesos
filas = generar_tabla(p, None)     # Sin escritura de archivos
resumen = calcular_resumen(p)     # Operación independiente

fila = AmortizacionFila(1, 100, 20, 80, 920)
totales = ResumenCredito(1200, 200)

escritor = EscritorTablaCSV("tabla.csv")
filas_guardadas = generar_tabla(p, escritor)
ruta = escritor.escribir(filas_guardadas)
existe = escritor.existe()
lineas = escritor.leer()

cuota_comando = main_cuota(p)
tabla_comando = main_tabla(p, None)
resumen_comando = main_resumen(p)

try:
    ParametrosCredito(Decimal(9000000), 120, Decimal("0.12"))
except DatosInvalidosError as error:
    print(str(error))

# También puede construirse explícitamente la excepción:
error = DatosInvalidosError("El monto no es válido.")
```

## Supuestos

- La tasa se expresa como fracción: `Decimal("0.12")` significa 12%. La restricción de dos decimales se aplica a esa fracción; los ceros finales no cambian su precisión significativa.
- El monto debe representar pesos enteros aunque su tipo sea Decimal. El plazo debe ser un int, no un booleano.
- Se usa precisión interna de 40 dígitos en las fórmulas y redondeo `ROUND_HALF_UP` al peso. Cada interés mensual se redondea antes de calcular el abono y actualizar el saldo; la última cuota liquida el saldo pendiente más su interés.
- El resumen suma los pagos e intereses de esos mismos movimientos, sin invocar las interfaces de cuota o generación de tabla, sin materializar una tabla completa y sin guardar archivos.
- Se utiliza el atributo `total_intereses` declarado en la firma de ResumenCredito para representar el total de intereses.
- AmortizacionFila y ResumenCredito son contenedores de resultados ya calculados; sus constructores no añaden reglas de negocio.
- Los parámetros se validan al construir y nuevamente en los servicios. Para recorrer los rechazos de los servicios, las pruebas modifican campos públicos de una instancia inicialmente válida.
- No se declara una interfaz específica de proceso. Los rechazos se verifican mediante las interfaces de servicios, tanto directamente como ejecutándolas en un proceso Python y observando el mensaje de la excepción no capturada y su código de salida distinto de cero. Si el consumidor captura la excepción, debe gestionar explícitamente el código de salida de su aplicación.
- Los comandos importan tipos a través del módulo de servicios para respetar la regla de dependencia exclusiva hacia servicios.
- El CSV usa UTF-8, separador coma y encabezados `mes,cuota,interes,abono_capital,saldo`. La lectura devuelve líneas sin terminadores. Los errores de E/S se propagan al consumidor.

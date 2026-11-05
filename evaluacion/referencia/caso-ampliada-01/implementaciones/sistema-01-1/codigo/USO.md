# Liquidación de comisiones

Calcula la comisión de la inmobiliaria y de cada asesor para negocios cerrados de venta o arriendo.

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

No requiere. Los datos se suministran como parámetros; los importes deben ser objetos `Decimal` finitos y positivos.

## Ejecución

No hay punto de entrada de terminal. Desde la raíz del código puede invocarse el caso de uso así:

```bash
PYTHONPATH=src python -c 'from decimal import Decimal; from aplicacion.liquidacion import calcular_comision; print(calcular_comision("venta", 1, "cerrado", Decimal("1000000")))'
```

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### `aplicacion.liquidacion.calcular_comision`

```python
from decimal import Decimal
from aplicacion.liquidacion import calcular_comision

resultado = calcular_comision("arriendo", 2, "cerrado", Decimal("1000000"))
print(resultado.comision_de_la_inmobiliaria)  # 1000000
print(resultado.comision_de_cada_asesor)      # 300000
```

### `dominio.comisiones.Negocio`

Contenedor inmutable de los datos. Sus restricciones se verifican al liquidarlo.

```python
from dominio.comisiones import Negocio

negocio = Negocio("venta", 1, "cerrado", Decimal("1000000"))
```

### `dominio.comisiones.ResultadoComision`

Contenedor inmutable del resultado, con dos campos `Decimal`.

```python
from dominio.comisiones import ResultadoComision

resultado = ResultadoComision(Decimal("30000"), Decimal("300000"))
```

### `dominio.comisiones.calcular_para_negocio`

Valida y liquida directamente una entidad de negocio.

```python
from dominio.comisiones import calcular_para_negocio

resultado = calcular_para_negocio(negocio)
```

### Excepciones de `dominio.comisiones`

También están disponibles desde `aplicacion.liquidacion`.

- `NegocioAbiertoError(mensaje: str)`: rechaza negocios abiertos.
- `ValorNoPermitidoError(mensaje: str)`: rechaza importes no válidos.
- `ReglaNegocioError(mensaje: str)`: rechaza tipos, estados o cantidades de asesores no permitidos.

```python
from aplicacion.liquidacion import (
    NegocioAbiertoError,
    ReglaNegocioError,
    ValorNoPermitidoError,
)

try:
    calcular_comision("venta", 1, "abierto", Decimal("1000000"))
except NegocioAbiertoError as error:
    print(str(error))  # El negocio aún no está cerrado

error_valor = ValorNoPermitidoError("Importe inválido")
error_regla = ReglaNegocioError("Tipo inválido")
error_estado = NegocioAbiertoError("El negocio aún no está cerrado")
```

## Supuestos

- El empate de redondeo se resuelve hacia arriba mediante `ROUND_HALF_UP`.
- Las comisiones se calculan con el importe original; cada salida se redondea una sola vez, al final. No se redondea primero la comisión inmobiliaria para calcular el reparto.
- El mínimo de 300000 pesos se aplica a cada asesor sin reducir la comisión informada de la inmobiliaria.
- No se normalizan textos ni se convierten importes automáticamente. Los booleanos no cuentan como números de asesores.
- Los DTO almacenan los datos recibidos; la validación de entradas se centraliza en la liquidación del dominio y se utiliza también desde el caso de uso.
- Si coinciden varias entradas inválidas, se validan primero tipo, cantidad de asesores, estado e importe; después se rechaza el estado abierto.

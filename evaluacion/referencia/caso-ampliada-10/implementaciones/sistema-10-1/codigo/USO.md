# Tarifas e impuesto predial

Consulta la tarifa por mil según destino y estrato y calcula el impuesto en pesos enteros, con redondeo de mitades hacia arriba.

## Requisitos

- Python 3.11 o superior; el módulo se probó con Python 3.11.
- Dependencias externas: `fastapi`, `pydantic`. Sus versiones, y las de pytest, quedan fijadas en `requirements.txt`.

## Instalación

Desde la carpeta del código, cree un entorno e instale las dependencias:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, el entorno se activa con `.venv\Scripts\activate`. `requirements.txt` acompaña al código: fija las versiones con que se probó e incluye pytest.

## Configuración

No requiere archivos de datos ni variables de entorno. Para la API, incorpore el router en una aplicación FastAPI existente. El código se importa incluyendo `src` en `PYTHONPATH`.

## Ejecución

No se declara un punto de entrada de terminal. Puede invocar los servicios directamente:

```python
from servicios.tarifas import calcular_impuesto, obtener_tarifa

print(obtener_tarifa("residencial", 3))
print(calcular_impuesto(120_000_000, "residencial", 3))
```

Para incorporar los endpoints:

```python
from fastapi import FastAPI
from rutas.tarifas import construir_router

app = FastAPI()
app.include_router(construir_router())
```

Endpoints expuestos:

- `GET /tarifas?destino=residencial&estrato=3`
- `POST /tarifas`, con JSON `{"destino": "residencial", "estrato": 3}`.
- `POST /impuestos/calcular`, con JSON `{"avaluo": 120000000, "destino": "residencial", "estrato": 3}`.

Los errores de negocio devuelven HTTP 400 con el mensaje en `detail`. Los errores de estructura o tipos de la petición devuelven HTTP 422. Las respuestas omiten `estrato_aplicado` cuando no corresponde.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Rutas

- `construir_router()`: devuelve un router independiente. Ejemplo: `app.include_router(construir_router())`.

### Esquemas

- `ConsultaTarifaRequest(destino, estrato=None)`: ejemplo `ConsultaTarifaRequest("residencial", 3)`.
- `ConsultaTarifaResponse(tarifa, estrato_aplicado=None)`: ejemplo `ConsultaTarifaResponse(11)`.
- `CalculoImpuestoRequest(avaluo, destino, estrato=None)`: ejemplo `CalculoImpuestoRequest(120000000, "residencial", 3)`.
- `CalculoImpuestoResponse(impuesto_calculado, tarifa, estrato_aplicado=None)`: ejemplo `CalculoImpuestoResponse(960000, 8, 3)`.

Los esquemas usan Pydantic y permiten serializar con `model_dump(exclude_none=True)`. Validan tipos estrictos y rechazan estrato aportado para destinos distintos de residencial. La validación de destinos reconocidos, del rango residencial y de avalúos positivos se realiza en los servicios antes del cálculo.

### Servicios

- `TarifaResultado(tarifa, estrato_aplicado=None)`: DTO inmutable; ejemplo `TarifaResultado(8, 3)`.
- `CalculoImpuestoResultado(impuesto_calculado, tarifa, estrato_aplicado=None)`: DTO inmutable; ejemplo `CalculoImpuestoResultado(960000, 8, 3)`.
- `obtener_tarifa(destino, estrato=None)`: ejemplo `obtener_tarifa("industrial")`, que devuelve tarifa 12 sin estrato.
- `calcular_impuesto(avaluo, destino, estrato=None)`: ejemplo `calcular_impuesto(100000000, "comercial")`, que devuelve impuesto 1100000 y tarifa 11.
- `DestinoNoReconocidoError(mensaje="Destino económico no reconocido")`: error de destino; ejemplo de captura `except DestinoNoReconocidoError as error: print(str(error))`.
- `EstratoInvalidoError(mensaje="Estrato inválido")`: error de estrato residencial; ejemplo de captura `except EstratoInvalidoError as error: print(str(error))`.
- `AvaluoNoValidoError(mensaje="El avalúo debe ser mayor que cero")`: error de avalúo; ejemplo de captura `except AvaluoNoValidoError as error: print(str(error))`.

## Supuestos

- Se usa la API de Pydantic 2 y una versión de FastAPI compatible con ella.
- Como no se fijaron rutas ni códigos HTTP, se adoptan los endpoints y códigos descritos arriba.
- Los destinos se escriben exactamente como `residencial`, `comercial`, `industrial` y `lote urbanizable no edificado`, sin normalización de mayúsculas ni espacios.
- Las firmas aprobadas definen estrato como entero, aunque la descripción de los datos lo mencione como texto. En JSON se exige un entero; en GET FastAPI interpreta el parámetro de consulta como entero.
- Los esquemas de petición rechazan estrato no residencial según su contrato. Los servicios directos lo ignoran en esos destinos, sin combinar tarifas.
- El avalúo entra y el impuesto sale como enteros conforme a las interfaces. Toda operación monetaria interna usa `Decimal`; no se aceptan avalúos de punto flotante ni booleanos.
- No se establece un límite superior de avalúo. Un avalúo positivo pequeño puede producir impuesto cero por el redondeo exigido.

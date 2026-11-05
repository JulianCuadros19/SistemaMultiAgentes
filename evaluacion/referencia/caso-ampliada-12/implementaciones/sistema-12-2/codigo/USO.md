# Servicio de validación de NIT

Calcula un dígito esperado y compara el dígito recibido mediante interfaces Python y una aplicación REST. La convención de cálculo asumida se detalla abajo; no debe confundirse con una certificación de validez tributaria.

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

No requiere archivos de datos, variables de entorno ni almacenamiento. La raíz `src` debe estar en la ruta de importación de Python.

## Ejecución

No se declara un ejecutable de terminal ni un servidor HTTP. Para usar las interfaces Python desde la raíz del código:

```sh
PYTHONPATH=src python -c 'from servicios.nit_validacion import validar_nit; print(validar_nit("900123456-8"))'
```

Para integrar la API, obtenga la aplicación ASGI mediante `rutas.nit.crear_app()` y entréguela al servidor ASGI de su infraestructura. Cada llamada crea una aplicación independiente.

La aplicación publica documentación interactiva en `/docs` y el contrato OpenAPI en `/openapi.json`.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### `crear_app() -> object`

```python
from rutas.nit import crear_app

app = crear_app()
```

Rutas disponibles:

- `POST /v1/nit/calcular-digito`: petición `{"numero":"900123456"}`, respuesta `{"digito_esperado":8}`.
- `POST /v1/nit/validar`: petición `{"nit":"900123456-7"}`, respuesta `{"valido":false,"digito_esperado":8}`.

Una petición válida devuelve HTTP 200, incluso cuando el dígito no coincide. Los errores de negocio devuelven HTTP 400 con `{"detail":"mensaje"}`. Los errores del contrato de entrada devuelven HTTP 422 con el detalle de validación de FastAPI.

### `CalculoDigitoRequest(numero: str)`

```python
from esquemas.nit import CalculoDigitoRequest

peticion = CalculoDigitoRequest("900123456")
```

### `CalculoDigitoResponse(digito_esperado: int)`

```python
from esquemas.nit import CalculoDigitoResponse

respuesta = CalculoDigitoResponse(8)
```

### `ValidarNitRequest(nit: str)`

```python
from esquemas.nit import ValidarNitRequest

peticion = ValidarNitRequest("900123456-8")
```

### `ValidarNitResponse(valido: bool, digito_esperado: int)`

```python
from esquemas.nit import ValidarNitResponse

respuesta = ValidarNitResponse(True, 8)
```

Los esquemas requieren los tipos declarados sin coerción; los dígitos de respuesta deben estar entre 0 y 9. Los errores de construcción son errores de validación de Pydantic, derivados de `ValueError`.

### `calcular_digito(numero: str) -> int`

```python
from servicios.nit_validacion import calcular_digito

assert calcular_digito("900123456") == 8
assert calcular_digito("900.123.456-7") == 8
```

### `validar_nit(nit: str) -> tuple[bool, int]`

```python
from servicios.nit_validacion import validar_nit

assert validar_nit("900123456-8") == (True, 8)
assert validar_nit("900123456-7") == (False, 8)
```

### `NITSoloDigitosError(mensaje: str)`

```python
from servicios.nit_validacion import NITSoloDigitosError, calcular_digito

try:
    calcular_digito("90012A456")
except NITSoloDigitosError as error:
    print(str(error))  # El NIT solo admite dígitos
```

### `NITMaximoDigitosError(mensaje: str)`

```python
from servicios.nit_validacion import NITMaximoDigitosError, validar_nit

try:
    validar_nit("1234567890123456")
except NITMaximoDigitosError as error:
    print(str(error))  # El NIT admite como máximo 15 dígitos
```

## Supuestos

- No se especifica una fórmula general para calcular el dígito. Se adopta una convención que reproduce el resultado 8 exigido para `900123456`: multiplicar los dígitos de derecha a izquierda por los pesos `3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`; obtener el residuo de la suma módulo 11; devolver el residuo si es 0 o 1 y, en otro caso, `11 - residuo`. Esta convención es un supuesto, no una certificación de validez tributaria. La validez para números distintos de los ejemplos depende de aprobar esta fórmula.
- Hay una diferencia entre la eliminación literal de separadores descrita para el cálculo y el ejemplo que exige que `900123456-7` produzca el mismo dígito que `900123456`. Para cumplir ese ejemplo, en el cálculo se interpreta un último guion seguido de exactamente un dígito como separación del dígito recibido: se calcula únicamente sobre el prefijo. Los demás puntos y guiones se eliminan.
- Hay una diferencia entre el límite del número base descrito en la interfaz de validación y el escenario que exige rechazar un NIT completo de 16 dígitos. Para cumplir ese escenario, la validación limita a 15 dígitos el NIT completo después de eliminar separadores; el cálculo admite hasta 15 dígitos en el número base.
- Se admiten únicamente dígitos ASCII. Espacios, otros signos y dígitos Unicode se rechazan, sin eliminarlos silenciosamente.
- Los valores vacíos, no textuales y los NIT completos de un solo dígito usan `NITSoloDigitosError`, porque no se declara una excepción específica para esos casos.
- La consulta por red corresponde al acceso HTTP del consumidor. La lógica de negocio no consulta registros tributarios ni servicios externos.

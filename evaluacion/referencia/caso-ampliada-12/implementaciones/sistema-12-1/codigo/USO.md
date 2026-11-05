# Cálculo y validación de NIT

Implementa el cálculo del dígito de verificación y la validación de NIT, con modelos Pydantic y funciones de ruta que traducen errores del dominio a errores HTTP.

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

No requiere archivos de datos ni variables de entorno. Los módulos están bajo `src`; agregue ese directorio a la ruta de importación de Python.

## Ejecución

No se declara una aplicación HTTP ni un punto de entrada ejecutable. Desde la raíz del código se pueden invocar las funciones así:

```bash
PYTHONPATH=src python -c 'from esquemas.nit import NumeroEntrada; from rutas.nit import calcular_digito; print(calcular_digito(NumeroEntrada(numero="900123456")))'
```

La aplicación FastAPI receptora puede registrar `rutas.nit.calcular_digito` y `rutas.nit.validar_nit` como operaciones POST mediante `app.add_api_route`, eligiendo sus rutas URL y los correspondientes modelos de respuesta. Los errores del contenido se traducen a `HTTPException` con estado 400; FastAPI los representa en el campo JSON `detail`.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Esquemas

- `NumeroEntrada(numero: str)`: `NumeroEntrada(numero="900.123.456")`.
- `DigitoRespuesta(digito_calculado: int)`: `DigitoRespuesta(digito_calculado=8)`.
- `ValidacionEntrada(nit: str)`: `ValidacionEntrada(nit="900.123.456-8")`.
- `ValidacionRespuesta(validez_del_nit: bool, digito_esperado: int, digito_calculado: int)`: `ValidacionRespuesta(True, 8, 8)`.

Los esquemas comprueban los tipos sin coerción y los rangos de los campos de salida. El contenido y la longitud de las entradas se comprueban en los servicios, para permitir su traducción a errores HTTP por las rutas.

### Servicios

```python
from servicios.nit import calcular_digito, validar_nit

calcular_digito("900123456")  # 8
validar_nit("900123456-7")  # (False, 8, 8)
```

- `calcular_digito(numero: str) -> int`: elimina puntos y guiones y aplica los quince pesos de derecha a izquierda.
- `validar_nit(nit: str) -> tuple[bool, int, int]`: compara el último dígito con el resultado del algoritmo aplicado a los dígitos anteriores.
- `MaxLengthExceededError()`: excepción de dominio; por ejemplo, `str(MaxLengthExceededError())` devuelve `El NIT admite como máximo 15 dígitos`.
- `InvalidCharactersError()`: excepción de dominio; por ejemplo, `str(InvalidCharactersError())` devuelve `El NIT solo admite dígitos`.

### Rutas

```python
from esquemas.nit import NumeroEntrada, ValidacionEntrada
from rutas.nit import calcular_digito, validar_nit

calcular_digito(NumeroEntrada("900.123.456"))
# DigitoRespuesta(digito_calculado=8)

validar_nit(ValidacionEntrada("900123456-7"))
# ValidacionRespuesta(validez_del_nit=False, digito_esperado=8, digito_calculado=8)
```

- `calcular_digito(numero_entrada: NumeroEntrada) -> DigitoRespuesta`.
- `validar_nit(validacion_entrada: ValidacionEntrada) -> ValidacionRespuesta`.

Ambas funciones lanzan `fastapi.HTTPException` ante los errores de contenido y longitud del servicio, sin devolver una respuesta de éxito.

## Supuestos

- No se especifican aplicación, URLs ni métodos HTTP concretos: se entregan las funciones de ruta para integrarlas en una aplicación receptora. Las pruebas recorren directamente esas interfaces y observan sus respuestas y errores HTTP; no pueden comprobar disponibilidad por red con las interfaces declaradas.
- El último dígito del NIT limpio es el dígito recibido de verificación. La longitud máxima de quince incluye ese dígito.
- `digito_esperado` es el correcto para la base del NIT, como exige el ejemplo de NIT incorrecto. `digito_calculado` también representa el resultado del algoritmo, por lo que ambos campos coinciden; el dígito recibido solo interviene en la comparación.
- Para admitir el mínimo declarado de un dígito en la validación, una base vacía tiene suma cero y dígito calculado cero.
- Se aceptan los dígitos ASCII `0` a `9`. Se eliminan todos los puntos y guiones, sin exigir agrupación específica. No se eliminan espacios.
- La entrada vacía o formada solo por separadores se rechaza con `InvalidCharactersError`. Si una entrada tiene caracteres inválidos y longitud excesiva, prevalece el error de caracteres.
- Ante entradas inválidas se utiliza el estado HTTP 400, ya que no se especifica otro código.

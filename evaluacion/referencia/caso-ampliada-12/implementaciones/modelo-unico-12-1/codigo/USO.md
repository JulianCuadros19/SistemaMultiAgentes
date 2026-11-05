# Servicio de dígito de verificación de NIT

## Estado y discrepancia pendiente

El módulo ofrece un servicio HTTP JSON para calcular un dígito y comparar un dígito recibido. No consulta registros externos ni certifica existencia, inscripción, identidad o validez legal de un NIT. No se atribuye la fórmula a ningún país.

**La regla definitiva no está aprobada.** La fórmula suministrada y uno de los ejemplos del cliente son incompatibles:

| Número | Dígito indicado por el cliente | Resultado de la fórmula |
| --- | --- | --- |
| 123456789 | 6 | 6 |
| 900123456 | 8 | 7 |

Para 900123456 la suma ponderada es 682 y el residuo es 0? No: 682 dividido entre 11 deja residuo 0 no correspondería a ese cálculo. El cálculo efectivo de la fórmula es la suma 1071, cuyo residuo es 4, por lo que el dígito es 7.

La implementación usa exclusivamente la fórmula explícita, sin añadir una excepción para 900123456. Por tanto, rechaza su dígito 8 y devuelve 7 como esperado. Esto es una decisión provisional de implementación, **no una confirmación del cliente ni una resolución de la discrepancia**. Debe revisarse con quien lleva el registro antes de usar los resultados como regla de negocio definitiva. Las pruebas documentan tanto el resultado de la fórmula como la incompatibilidad con el ejemplo 8; no presentan ese ejemplo como satisfecho.

## Fórmula implementada

Desde la derecha del número se aplican, en orden, los pesos:

`3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`.

Se suman los productos y se obtiene el residuo módulo 11. Para residuo 0 o 1, el dígito es el residuo; en otro caso, es 11 menos el residuo. El límite de 15 cifras deriva de los 15 pesos proporcionados.

## Ejecución

Requiere Python 3.11 y los paquetes ya disponibles `fastapi`, `pydantic` y `uvicorn`. Las pruebas usan `pytest`. No necesita base de datos, acceso a Internet ni instalación adicional.

Desde la raíz de los archivos entregados, en una consola POSIX:

```sh
PYTHONPATH=src python -m uvicorn servicio_nit:app --host 127.0.0.1 --port 8000
PYTHONPATH=src python -m pytest tests
```

El servidor se inicia únicamente mediante ese comando; importar el paquete no abre conexiones. Las pruebas invocan ASGI directamente, sin sockets ni solicitudes por la red.

La documentación interactiva está en `/docs` y `/redoc`; el contrato generado, en `/openapi.json`. Las interfaces interactivas estándar de FastAPI pueden necesitar recursos web externos; `/openapi.json` y este documento se pueden consultar sin ellos.

## Contrato HTTP

Enviar cuerpos JSON con `Content-Type: application/json`. Los campos son cadenas de texto, no números JSON. No se admiten campos adicionales. Todas las respuestas de las dos operaciones son JSON.

### POST /calcular

Entrada:

```json
{"nit": "123.456.789"}
```

Respuesta HTTP 200:

```json
{"nit": "123456789", "digito": "6"}
```

### POST /validar

Entrada:

```json
{"nit": "123.456.789-", "digito": "5"}
```

Respuesta HTTP 200:

```json
{"nit": "123456789", "valido": false, "digito_esperado": "6"}
```

Un dígito de formato correcto que no coincide no es un error HTTP. Se devuelve `valido: false` y siempre el esperado. Si coincide, se devuelve `valido: true` con el mismo campo `digito_esperado`.

**El campo `nit` debe contener solo el número base, sin su dígito de verificación.** Si el dato original es `123.456.789-6`, el consumidor debe separar el 6 y enviar `{"nit":"123.456.789", "digito":"6"}`. El servicio elimina puntos y guiones; no interpreta el último carácter como dígito ni divide automáticamente un NIT completo.

## Entradas y decisiones para puntos no definidos

Las siguientes decisiones completan el contrato de esta entrega; no fueron acordadas como reglas de negocio por el cliente:

- Rutas `/calcular` y `/validar`, método POST y nombres de campos indicados arriba.
- Número obligatorio como texto. Se eliminan todos los puntos y guiones antes de validar y calcular.
- Tras normalizar, se exige entre 1 y 15 cifras ASCII `0` a `9`. No se aceptan espacios, signos distintos de guion, ni cifras Unicode.
- Los ceros iniciales se conservan en la respuesta y cuentan para el límite de longitud. No se convierten los números completos a enteros.
- El dígito separado debe ser exactamente una cifra ASCII como texto. No se eliminan separadores ni espacios de ese campo.
- Número vacío o compuesto únicamente por separadores: error de número vacío.
- Los errores de contenido tienen HTTP 400. Los errores de estructura, tipos, campos ausentes o JSON mal formado se unifican bajo un mensaje genérico.
- Primero se valida la estructura de la solicitud; después, el número: vacío, caracteres y longitud, en ese orden. En validación, el formato del dígito se comprueba después del número. No se garantiza la acumulación de varios errores.

## Errores

Formato de error HTTP 400:

```json
{"error": "El NIT solo admite dígitos"}
```

| Condición | Mensaje |
| --- | --- |
| Letras u otros caracteres no admitidos en el número | `El NIT solo admite dígitos` |
| Más de 15 cifras tras eliminar puntos y guiones | `El NIT admite como máximo 15 dígitos` |
| Número vacío tras eliminar separadores | `El NIT no puede estar vacío` |
| Dígito vacío, letras, varias cifras u otro formato no admitido | `El dígito de verificación debe ser una sola cifra` |
| JSON inválido, campos ausentes, tipos incorrectos o campos adicionales | `Solicitud JSON inválida o incompleta` |

Los dos primeros mensajes son los acordados con el cliente. Los restantes son decisiones de esta entrega.

Una ruta desconocida devuelve el HTTP 404 estándar de FastAPI con `{"detail":"Not Found"}`. Un método no admitido devuelve HTTP 405 con `{"detail":"Method Not Allowed"}`.

## Uso desde Python

```python
from servicio_nit import calcular_digito, validar_nit

assert calcular_digito("123.456.789") == "6"
resultado = validar_nit("123456789", "5")
print(resultado.nit, resultado.valido, resultado.digito_esperado)
# 123456789 False 6
```

`normalizar_nit(nit)` devuelve el número normalizado. `calcular_digito(nit)` devuelve una cadena de una cifra. `validar_nit(nit, digito)` devuelve una instancia inmutable de `Validacion`, con `nit`, `valido` y `digito_esperado`. Las funciones lanzan `ErrorNit`, una subclase de `ValueError`, con los mensajes de contenido de la tabla. La llamada directa con un número de tipo distinto de texto produce `El NIT debe ser una cadena de texto`; por HTTP, los tipos incorrectos producen el error genérico de estructura.

## Acceso y límites del alcance

No están definidos la exposición por Internet ni el control de acceso. Por ello, el ejemplo escucha solo en la interfaz local, sin autenticación, TLS ni CORS habilitado. Para consultas desde otros sistemas se debe acordar y configurar la dirección de escucha y la protección de la red. No se debe publicar directamente como servicio abierto sin resolver esas condiciones.

No se implementan consultas de existencia, almacenamiento, gestión de usuarios, reglas por país, excepciones al algoritmo, separación automática de un número completo ni controles de infraestructura como cuotas o límites de tamaño de cuerpo. La aprobación del cálculo contradictorio sigue pendiente.

## Cobertura

Las pruebas cubren las tres ramas del residuo, los quince pesos y su orden, ambos ejemplos y su discrepancia, coincidencia y no coincidencia, puntos y guiones, ceros iniciales, límites y errores de contenido. También cubren JSON, campos, tipos, respuestas HTTP y presencia de las operaciones en OpenAPI. Se ejecutan completamente en memoria y sin red.

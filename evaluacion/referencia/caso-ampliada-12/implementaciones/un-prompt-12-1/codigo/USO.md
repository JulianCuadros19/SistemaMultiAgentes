# Servicio HTTP de verificación del NIT

Calcula el dígito de verificación y comprueba si coincide con el recibido. Lo pueden consultar el portal de registro y el sistema de facturación sin duplicar la lógica. No registra empresas, no emite facturas y no comprueba la existencia del NIT en una entidad oficial. No usa base de datos ni servicios externos.

## Discrepancia en los requisitos

**El ejemplo de `900123456` contradice la fórmula suministrada.** Con los pesos indicados, de derecha a izquierda:

```text
6×3 + 5×7 + 4×13 + 3×17 + 2×19 + 1×23 + 0×29 + 0×37 + 9×41 = 686
686 % 11 = 4
11 - 4 = 7
```

Por tanto, la fórmula da **7, no 8**. Esta entrega aplica la fórmula de manera uniforme, sin excepciones por número: `900.123.456-8` es inválido, con dígito esperado 7; `900123456-7` es válido. No es posible cumplir simultáneamente esa fórmula y esos dos resultados del ejemplo. Las pruebas dejan explícita la discrepancia. El ejemplo `123456789 → 6` sí coincide con la fórmula.

## Puesta en marcha

Requiere Python 3.11 y los paquetes del entorno proporcionado. Desde la raíz de la entrega:

```sh
PYTHONPATH=src python -m uvicorn nit_service.api:app --host 0.0.0.0 --port 8000
```

El servidor escucha en el puerto 8000; los consumidores usan el nombre o dirección del servidor, no `0.0.0.0` como destino. La dirección de escucha es configurable mediante Uvicorn. No hay autenticación ni TLS implementados, porque no se especificaron; no debe exponerse directamente a Internet sin la protección apropiada del despliegue.

Contrato generado: `GET /openapi.json`. Documentación interactiva: `/docs` y `/redoc`. Estas interfaces pueden requerir recursos externos del navegador; el servicio y sus pruebas no requieren red externa. Este documento y `/openapi.json` permiten consultar el contrato sin esos recursos.

## Contrato HTTP, versión 1.0.0

Las dos operaciones reciben `Content-Type: application/json` y devuelven JSON. Todos los campos de entrada son **cadenas**, no números JSON: esto conserva ceros iniciales y evita conversiones implícitas. Los campos son obligatorios y no se admiten campos adicionales.

### POST /calcular

Enviar el número **sin** su dígito de verificación:

```json
{"numero": "123.456.789"}
```

Respuesta HTTP 200:

```json
{"numero": "123456789", "digito": 6}
```

`numero` es la cadena normalizada; `digito` es un entero entre 0 y 9. No se intenta separar un dígito en esta operación: todos los dígitos del campo pertenecen al número.

### POST /validar

Se admite exactamente una de estas dos formas:

```json
{"numero": "123.456.789", "digito": "6"}
```

```json
{"nit": "123.456.789-6"}
```

En la forma completa, el **último guion** separa el número del dígito de verificación. No se aceptan ambas formas mezcladas.

Respuesta HTTP 200:

```json
{"numero": "123456789", "digito": 6, "valido": true, "digito_esperado": 6}
```

Para `{"nit":"123456789-5"}`:

```json
{"numero": "123456789", "digito": 5, "valido": false, "digito_esperado": 6}
```

Un dígito bien formado pero incorrecto es un resultado de negocio, **no un error HTTP**. `digito_esperado` se incluye siempre, también cuando el NIT es válido.

Ejemplo de consulta desde otro sistema:

```sh
curl -X POST http://localhost:8000/validar \
  -H 'Content-Type: application/json' \
  -d '{"nit":"123.456.789-6"}'
```

### Reglas de entrada y cálculo

1. Se eliminan todos los puntos y guiones del número, sin exigir agrupaciones específicas.
2. Deben quedar entre 1 y 15 caracteres ASCII `0` a `9`. Se conservan ceros iniciales; cuentan para el límite de longitud.
3. No se eliminan espacios ni otros caracteres. Los dígitos Unicode distintos de `0` a `9` no se aceptan.
4. El dígito recibido debe ser exactamente un carácter ASCII de `0` a `9`, sin separadores.
5. Desde la derecha, se multiplican los dígitos por `3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`. Se suman los productos y se toma el residuo módulo 11. Para residuo 0 o 1 se devuelve el mismo; para los demás, `11 - residuo`.

### Errores

Los errores de las operaciones tienen la forma `{"error":"mensaje"}`.

**HTTP 400:** entrada textual que incumple una regla del NIT.

| Situación | Mensaje |
| --- | --- |
| Letras u otros caracteres no admitidos en el número | `El NIT solo admite dígitos` |
| Más de 15 dígitos después de quitar separadores | `El NIT admite como máximo 15 dígitos` |
| Número vacío después de quitar separadores | `El NIT debe contener al menos 1 dígito` |
| Dígito vacío, múltiple o no admitido | `El dígito de verificación debe ser un dígito de 0 a 9` |
| NIT completo sin guion separador | `El NIT completo debe separar el dígito con un guion` |

Si el número tiene caracteres incorrectos y además excede el límite, se informa primero el error de caracteres. En validación se comprueba el número antes del dígito.

**HTTP 422:** JSON malformado, campos ausentes o adicionales, estructura incorrecta o valores que no sean cadenas:

```json
{"error":"Solicitud inválida: envíe JSON con los campos documentados, todos como cadenas y sin campos adicionales"}
```

Las rutas inexistentes y los métodos no admitidos usan las respuestas estándar de FastAPI; no son errores de las operaciones del NIT.

## Uso directo desde Python

Con `src/` en la ruta de importación:

```python
from nit_service import calcular_digito, validar_nit, validar_nit_completo

assert calcular_digito("123.456.789") == 6
resultado = validar_nit("123456789", "5")
assert not resultado.valido
assert resultado.digito_esperado == 6
assert validar_nit_completo("123.456.789-6").valido
```

`normalizar_numero(numero: str) -> str` también es público. Las funciones de validación devuelven un `ResultadoValidacion` inmutable con `numero: str`, `digito: int`, `valido: bool` y `digito_esperado: int`. Las entradas incorrectas lanzan `NitError`, subclase de `ValueError`. Las entradas no textuales a la biblioteca generan un mensaje específico; por HTTP se rechazan antes, con 422.

## Decisiones sobre aspectos no definidos

Se eligieron operaciones POST con JSON, campos textuales estrictos, dígitos ASCII, ausencia de recorte de espacios, validación del formato completo mediante el último guion y errores 400/422. Se conserva el dígito esperado en todas las respuestas de validación. No se añaden restricciones sobre el primer dígito, números compuestos solo de ceros o posiciones de los separadores, porque el cliente no las indicó. La fórmula tiene prioridad sobre el ejemplo incompatible documentado arriba.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas importan `nit_service` y verifican cálculo, pesos hasta el límite de 15 dígitos, las ramas del residuo, normalización, ejemplos, discrepancia matemática, validación y errores. Las pruebas HTTP ejecutan la aplicación mediante ASGI y comprueban estados, cuerpos y OpenAPI: no abren sockets, no usan servicios externos y no requieren `httpx`.

# Servicio de dígito de verificación del NIT

## Qué hace

Ofrece un único servicio HTTP para calcular el dígito de verificación y comprobar si el dígito recibido coincide. Incluye funciones Python reutilizables y una aplicación WSGI. No consulta registros ni determina la existencia, inscripción o situación fiscal del NIT. `valido` significa únicamente coincidencia del dígito.

Requiere Python 3.11. El servicio usa solo la biblioteca estándar; las pruebas requieren pytest. No realiza conexiones salientes ni necesita red para ejecutar las pruebas.

## Requisitos confirmados

- Dos operaciones por HTTP: calcular y validar.
- Eliminar todos los puntos y guiones del número antes del cálculo.
- Número de entre 1 y 15 dígitos.
- Multiplicar desde la derecha por los pesos `3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`; sumar y obtener el residuo módulo 11. Si es 0 o 1, devolverlo; en otro caso, devolver 11 menos el residuo.
- Ejemplos: `900123456 → 8` y `123456789 → 6`.
- Mensajes exactos para letras y exceso de longitud: `El NIT solo admite dígitos` y `El NIT admite como máximo 15 dígitos`.

No se ha establecido un país: la fórmula implementada es la proporcionada por el cliente, sin atribuirle reglas nacionales adicionales.

## Decisiones de implementación, no requisitos del caso

El cliente autorizó documentar los aspectos no definidos. Para esta entrega se decidió:

- Usar POST, JSON UTF-8 y las rutas `/calcular` y `/validar`.
- Recibir el número en `nit` y el dígito en un campo separado `digito`; ambos deben ser texto. No se separa automáticamente el último carácter del número.
- El límite de 15 corresponde al número, sin incluir el dígito de verificación.
- Admitir únicamente dígitos ASCII (`0` a `9`) después de quitar puntos y guiones. No se exige una ubicación particular de esos separadores.
- Rechazar espacios, incluso al principio o al final; no se recortan. Otros caracteres no admitidos usan el mismo mensaje que las letras.
- Conservar ceros iniciales y contarlos para el límite. No se añaden restricciones sobre el valor del número: `0` y números compuestos solo por ceros son admisibles.
- Devolver el dígito esperado tanto cuando la validación coincide como cuando no coincide.
- Usar HTTP 400 para errores de entrada, 404 para ruta desconocida y 405 para método incorrecto.
- Rechazar campos faltantes o adicionales; los valores numéricos JSON no sustituyen a los campos de texto.
- No incluir autenticación ni TLS en este módulo. El servidor incluido escucha por defecto solo en la máquina local.
- No definir un límite de cuerpo HTTP adicional al límite del número. El despliegue debe establecer los límites, tiempos de espera y controles de acceso necesarios.

## Arranque

Desde la raíz de la entrega, en una terminal tipo Unix:

```sh
export PYTHONPATH=src
python -m nit_service --host 127.0.0.1 --port 8000
```

Para admitir conexiones desde otros equipos, se puede indicar una interfaz accesible, por ejemplo `--host 0.0.0.0`. Esto expone el servicio sin autenticación: debe hacerse únicamente dentro de un entorno de red controlado.

El servidor de `wsgiref` incluido es sencillo y atiende secuencialmente. Para un despliegue con otros requisitos de concurrencia, la aplicación WSGI es `nit_service.http:application`; la selección del servidor y la infraestructura de producción quedan fuera de este módulo.

## Contrato HTTP

Enviar `Content-Type: application/json` (también se acepta un parámetro `charset`). El cuerpo se interpreta siempre como UTF-8. El servidor WSGI debe proporcionar `Content-Length`; los clientes deben enviar una longitud conocida, no cuerpos mediante transferencia fragmentada. La longitud ausente se interpreta como cero y genera el error de JSON vacío.

Las respuestas son JSON UTF-8 con `Content-Type: application/json; charset=utf-8` y `Content-Length`.

### Calcular

`POST /calcular`

Entrada, exactamente un campo:

```json
{"nit":"900.123.456"}
```

Respuesta HTTP 200:

```json
{"digito":8}
```

`digito` es un entero entre 0 y 9.

```sh
curl -X POST http://127.0.0.1:8000/calcular \
  -H 'Content-Type: application/json' \
  -d '{"nit":"900123456"}'
```

### Validar

`POST /validar`

Entrada, exactamente dos campos:

```json
{"nit":"900123456","digito":"8"}
```

Respuesta HTTP 200:

```json
{"valido":true,"digito_esperado":8}
```

Para el mismo número y `"digito":"7"`:

```json
{"valido":false,"digito_esperado":8}
```

La discrepancia es un resultado normal, no un error HTTP. `digito` de entrada debe contener exactamente un carácter ASCII entre `0` y `9`, sin separadores ni espacios.

### Errores

La forma común es `{"error":"mensaje"}`. Los mensajes distintos de los dos indicados como confirmados son decisiones de implementación.

| Situación | HTTP | Mensaje |
| --- | --- | --- |
| Letras u otros caracteres no admitidos en el número | 400 | El NIT solo admite dígitos |
| Más de 15 dígitos tras eliminar puntos y guiones | 400 | El NIT admite como máximo 15 dígitos |
| Número vacío, incluso después de quitar separadores | 400 | El NIT debe contener al menos un dígito |
| Número no enviado como texto | 400 | El NIT debe ser texto |
| Dígito no textual, vacío o con formato incorrecto | 400 | El dígito de verificación debe ser un único dígito de texto |
| Campos faltantes o adicionales en cálculo | 400 | Campos requeridos y únicos: nit |
| Campos faltantes o adicionales en validación | 400 | Campos requeridos y únicos: digito, nit |
| Content-Type incorrecto o ausente | 400 | La solicitud debe usar Content-Type application/json |
| Content-Length no entero o negativo | 400 | Content-Length inválido |
| JSON vacío, mal formado o UTF-8 inválido | 400 | El cuerpo debe ser JSON válido en UTF-8 |
| JSON válido que no es un objeto | 400 | El cuerpo debe ser un objeto JSON |
| Ruta desconocida | 404 | Ruta no encontrada |
| Método distinto de POST en una ruta conocida | 405 | Método no permitido; use POST |

El error 405 incluye `Allow: POST`. Se informa el primer error detectado: ruta, método, formato del cuerpo, campos y valores. En el número se comprueban tipo, vacío, caracteres y longitud, en ese orden.

## Uso como biblioteca

Con `src/` en la ruta de importación:

```python
from nit_service import NitInvalido, calcular_digito, normalizar_nit, validar_nit

assert normalizar_nit("000.123-456") == "000123456"
assert calcular_digito("900123456") == 8
assert validar_nit("123456789", "6") == (True, 6)
assert validar_nit("900123456", "7") == (False, 8)

try:
    calcular_digito("ABC")
except NitInvalido as error:
    print(str(error))
```

Las funciones de dominio lanzan `NitInvalido`, derivada de `ValueError`, cuando no pueden procesar los datos. La validación devuelve una pareja `(coincide, esperado)`; el adaptador HTTP la convierte al objeto JSON documentado.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas verifican los ejemplos confirmados, cada uno de los 15 pesos desde la derecha, las ramas del residuo, separadores, límites, ceros iniciales, coincidencias y discrepancias, y todos los errores documentados. Las pruebas HTTP invocan la aplicación por su interfaz WSGI, comprobando estado, cabeceras y cuerpo, sin abrir sockets ni realizar conexiones de red.

## Fuera de alcance

Consulta de registros oficiales, determinación del país, persistencia, autenticación, certificados TLS, restricciones de acceso y operación de infraestructura de producción. No se interpreta un NIT completo concatenado en un único campo: el contrato de esta entrega requiere número y dígito separados.

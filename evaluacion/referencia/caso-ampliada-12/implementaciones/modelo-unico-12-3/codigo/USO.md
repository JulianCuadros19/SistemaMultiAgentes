# Servicio de dígito de verificación de NIT

## Alcance acordado

Servicio único HTTP para el portal de registro y el sistema de facturación. Calcula el dígito de un NIT base o comprueba el dígito de un NIT completo. No consulta registros, no verifica existencia y no presupone un país. `valido: true` significa únicamente que el dígito coincide.

Se multiplican las cifras de derecha a izquierda por los pesos `3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71`. Se suma y se obtiene el residuo módulo 11. Para residuos 0 o 1, el dígito es el residuo; en otro caso, es `11 - residuo`.

## Ejecutar

Requiere Python 3.11. El servicio utiliza únicamente la biblioteca estándar; las pruebas requieren pytest.

Desde la raíz de la entrega:

```sh
PYTHONPATH=src python -m nit_service --host 127.0.0.1 --port 8000
PYTHONPATH=src python -m pytest tests
```

Para acceso desde otros equipos, indique con `--host` la dirección de la interfaz accesible en su red. La escucha predeterminada es exclusivamente local. Termine el servicio con Ctrl+C.

El servidor incluido sirve HTTP sin TLS ni autenticación. No proporciona despliegue de alta disponibilidad, persistencia ni controles de acceso. Si la red exige esas capacidades, debe publicarse mediante infraestructura apropiada; no es necesario ningún servicio externo para calcular ni para ejecutar las pruebas. Las pruebas HTTP usan exclusivamente conexiones locales.

## Decisiones mínimas sobre aspectos no definidos

Estas son decisiones de implementación, **no requisitos confirmados por el cliente**:

- Mensajes JSON UTF-8 y dos rutas: `POST /calcular` y `POST /validar`.
- Cuerpo con exactamente un campo `nit`, obligatoriamente texto. Los números JSON no se convierten automáticamente.
- Cifras ASCII `0` a `9`. Se conservan los ceros iniciales y cuentan para el límite de longitud.
- Se rechazan espacios y valores vacíos; no se recortan espacios automáticamente.
- El dígito recibido debe ser exactamente una cifra ASCII.
- Para validar se utiliza únicamente el formato `base-dígito`. El último guion separa el dígito; no se ofrece un campo de dígito separado.
- Los puntos y guiones de la base se eliminan en ambas operaciones. El límite de 1 a 15 cifras se aplica después de esa eliminación y no incluye el dígito recibido.
- Primero se revisan los caracteres y después la longitud. Una entrada con letras y exceso de longitud devuelve el error de caracteres.
- Las rutas son exactas: no admiten barra final ni parámetros de consulta.
- El transporte requiere `Content-Length` no negativo y no acepta `Transfer-Encoding`. Los clientes deben enviar JSON con `Content-Type: application/json`; el servidor interpreta el cuerpo como JSON sin condicionar la lectura al encabezado de tipo.

## Contrato HTTP

### Calcular

Solicitud:

```http
POST /calcular
Content-Type: application/json

{"nit":"900123456"}
```

Respuesta HTTP 200:

```json
{"nit":"900123456","digito":"8"}
```

También se aceptan bases como `900.123.456` o `900-123-456`. Esta operación siempre interpreta la entrada como **base**: no extrae un dígito final aunque aparezca un guion.

### Validar

Solicitud:

```http
POST /validar
Content-Type: application/json

{"nit":"900123456-8"}
```

Respuesta HTTP 200:

```json
{"nit":"900123456","digito_recibido":"8","digito_esperado":"8","valido":true}
```

Para `900123456-7`, también se responde HTTP 200:

```json
{"nit":"900123456","digito_recibido":"7","digito_esperado":"8","valido":false}
```

Los dígitos se devuelven como texto. `nit` es la base normalizada, sin puntos ni guiones y conservando ceros iniciales. Todas las respuestas de las operaciones son JSON UTF-8 e incluyen `Content-Length`.

Ejemplo con un cliente HTTP:

```sh
curl -X POST http://127.0.0.1:8000/validar \
  -H 'Content-Type: application/json' \
  --data '{"nit":"900123456-7"}'
```

## Errores

Una entrada mal escrita devuelve HTTP 400 y un objeto `{"error":"mensaje"}`. No se confunde con un dígito que simplemente no coincide, que devuelve HTTP 200 y `valido: false`.

| Situación | Mensaje exacto |
| --- | --- |
| Letras, espacios u otros caracteres en la base | El NIT solo admite dígitos |
| Base de más de 15 cifras | El NIT admite como máximo 15 dígitos |
| Base vacía, incluso después de quitar separadores | El NIT debe contener al menos un dígito |
| NIT enviado con un tipo distinto de texto | El NIT debe enviarse como texto |
| Validación sin guion separador | Para validar, envíe el NIT en formato NIT-dígito |
| Dígito recibido vacío, múltiple o no numérico | El dígito de verificación debe ser una sola cifra |
| JSON inválido o codificación inválida | El cuerpo debe ser JSON válido en UTF-8 |
| Campo ausente, campos adicionales o documento que no sea objeto | El cuerpo debe contener únicamente el campo nit |
| Content-Length ausente, negativo o no entero | Se requiere Content-Length válido |
| Transfer-Encoding presente | Transfer-Encoding no está soportado |

Una ruta POST desconocida devuelve HTTP 404 con `{"error":"Ruta no encontrada"}`. GET devuelve HTTP 405 con `{"error":"Use POST"}`. Otros métodos HTTP no forman parte del contrato y reciben la respuesta estándar 501 del servidor de Python, que no es JSON.

## Uso directo desde Python

Con `src/` en la ruta de importación:

```python
from nit_service import calcular, validar

assert calcular("900123456") == "8"
resultado = validar("900123456-7")
assert resultado["valido"] is False
assert resultado["digito_esperado"] == "8"
```

`calcular(nit: str) -> str` y `validar(nit: str) -> ResultadoValidacion` lanzan `ValueError` con los mensajes de datos indicados arriba.

También se expone `crear_servidor(host="127.0.0.1", puerto=8000)`, que devuelve un `ThreadingHTTPServer` sin iniciar. Se inicia con `serve_forever()` y se cierra con `server_close()`; desde otro hilo se puede detener con `shutdown()`. Si la dirección no se puede abrir, se propaga `OSError`.

## Pruebas incluidas

Se cubren los tres ejemplos del cliente, cada uno de los 15 pesos, las tres ramas del cálculo, los límites, puntos y guiones, los mensajes acordados, las decisiones documentadas de formato y los errores del contrato HTTP. No se hacen consultas a registros ni conexiones externas.

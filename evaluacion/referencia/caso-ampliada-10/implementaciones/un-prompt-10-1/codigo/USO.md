# Servicio de impuesto predial

## Qué hace

Ofrece dos operaciones HTTP para que los sistemas de pagos y liquidación compartan la misma tabla: consultar la tarifa y calcular el impuesto. No calcula el avalúo, no gestiona facturas ni pagos y no necesita base de datos ni servicios externos.

| Destino | Estrato | Tarifa, pesos por cada mil pesos de avalúo |
| --- | --- | ---: |
| residencial | 1 | 5 |
| residencial | 2 | 6 |
| residencial | 3 | 8 |
| residencial | 4 | 10 |
| residencial | 5 | 12 |
| residencial | 6 | 14 |
| comercial | No aplica | 11 |
| industrial | No aplica | 12 |
| lote urbanizable no edificado | No aplica | 33 |

El impuesto es `avaluo × tarifa / 1000`, redondeado al peso con las mitades hacia arriba. Se calcula con enteros mediante `(avaluo * tarifa + 500) // 1000`: no hay pérdida de precisión por punto flotante. Un avalúo positivo pequeño puede producir un impuesto de cero.

## Entorno y ejecución

Python 3.11. El servicio utiliza FastAPI, Pydantic y Uvicorn, disponibles en el entorno indicado. No hay dependencias adicionales. Las pruebas usan pytest y la interfaz ASGI directamente, sin httpx, sockets ni red.

Desde la raíz de la entrega, con esos paquetes instalados:

```sh
PYTHONPATH=src python -m uvicorn predial.api:app --host 127.0.0.1 --port 8000
```

Esta dirección solo escucha conexiones locales. Para recibir conexiones de otros equipos, sustituya el host por la dirección de la interfaz de la red municipal y configure el acceso correspondiente. No se implementan autenticación ni TLS porque no se especificaron; antes de exponerlo fuera de una red controlada deben configurarse en la infraestructura de despliegue.

Ejecutar las pruebas:

```sh
PYTHONPATH=src python -m pytest tests
```

La documentación interactiva está en `/docs` y `/redoc`; el contrato OpenAPI en `/openapi.json`. El contrato completo también se describe aquí, por lo que los consumidores no necesitan abrir documentación interactiva ni acceder a Internet.

## Contrato HTTP

Base de ejemplo: `http://127.0.0.1:8000`.

Ambas operaciones reciben un objeto JSON con `Content-Type: application/json` y responden JSON. Se usa POST para enviar los parámetros en el cuerpo. No hay parámetros de consulta. Los importes se representan como números JSON enteros en pesos, sin separadores de miles, sin símbolos monetarios y sin decimales.

### POST /tarifa

Entrada:

| Campo | Tipo JSON | Obligatorio | Significado |
| --- | --- | --- | --- |
| `destino` | string | Sí | Uno de los cuatro nombres exactos de la tabla |
| `estrato` | integer o null | Para residencial | Entero entre 1 y 6 para residencial |

Solicitud:

```json
{"destino":"residencial","estrato":3}
```

Respuesta **200 OK**:

```json
{"tarifa":8}
```

`tarifa` es un entero en pesos por cada mil pesos de avalúo, no un porcentaje ni una fracción decimal.

Para un destino no residencial:

```json
{"destino":"comercial"}
```

Respuesta **200 OK**:

```json
{"tarifa":11}
```

### POST /impuesto

Recibe los mismos campos de `/tarifa` y además:

| Campo | Tipo JSON | Obligatorio | Significado |
| --- | --- | --- | --- |
| `avaluo` | integer | Sí | Avalúo mayor que cero en pesos enteros |

Solicitud del ejemplo de verificación:

```json
{"avaluo":120000000,"destino":"residencial","estrato":3}
```

Respuesta **200 OK**:

```json
{"tarifa":8,"impuesto":960000}
```

`impuesto` es el valor en pesos enteros ya redondeado. Por ejemplo, con destino residencial, estrato 4 y avalúo de 50 pesos, el valor previo al redondeo es 0,5 pesos y la respuesta es `{"tarifa":10,"impuesto":1}`.

Ejemplo de llamada:

```sh
curl -X POST http://127.0.0.1:8000/impuesto \
  -H 'Content-Type: application/json' \
  -d '{"avaluo":120000000,"destino":"residencial","estrato":3}'
```

### Errores

Los errores de entrada devuelven **400 Bad Request**, con un único campo `error` de tipo string:

| Caso | Cuerpo |
| --- | --- |
| Estrato residencial fuera de 1 a 6 | `{"error":"Estrato inválido"}` |
| Estrato residencial omitido o null | `{"error":"Estrato inválido"}` |
| Destino desconocido | `{"error":"Destino económico no reconocido"}` |
| Avalúo entero de cero o negativo | `{"error":"El avalúo debe ser mayor que cero"}` |
| JSON mal formado, estructura incorrecta, campos obligatorios faltantes, campos extra o tipos incorrectos | `{"error":"Solicitud inválida: envíe un objeto JSON con los campos y tipos documentados"}` |

Una ruta inexistente devuelve **404** y un método no permitido **405**, también con un campo `error`. No debe dependerse del texto de esos dos errores de transporte.

## Decisiones para aspectos no definidos

- Los nombres de destinos se aceptan exactamente como aparecen en la tabla, en minúsculas y con espacios. No se normalizan mayúsculas ni espacios sobrantes.
- Se eligen las rutas POST `/tarifa` y `/impuesto`, los nombres de campo sin tildes y el formato de error anterior como contrato explícito.
- El estrato residencial omitido o null se trata como inválido. Para otros destinos, un estrato entero o null se ignora incluso si está fuera del rango residencial. Si se envía un tipo distinto, se rechaza por estructura inválida.
- Los números deben ser enteros JSON: `3.0`, `"3"` y `true` no son enteros aceptados por el contrato. Esto evita conversiones implícitas y respeta el manejo del dinero sin decimales.
- Se rechazan campos extra para detectar errores de integración. No se fija un tope de negocio al avalúo.
- Cuando hay varios errores, primero se valida la estructura y los tipos. En `/impuesto`, después se valida el avalúo, luego el destino y finalmente el estrato residencial. En `/tarifa`, se valida primero el destino y después su estrato.
- No se incorporan reglas de descuentos, exenciones, vigencias o autenticación que no fueron solicitadas.

## Uso como biblioteca

También se pueden reutilizar las mismas reglas dentro de Python:

```python
from predial import ErrorConsulta, calcular_impuesto, consultar_tarifa

try:
    tarifa = consultar_tarifa("residencial", 3)
    impuesto = calcular_impuesto(120_000_000, "residencial", 3)
except ErrorConsulta as error:
    print(str(error))
```

`consultar_tarifa(destino: str, estrato: int | None = None) -> int` devuelve la tarifa por mil. `calcular_impuesto(avaluo: int, destino: str, estrato: int | None = None) -> int` devuelve solo el impuesto en pesos. Ambas lanzan `ErrorConsulta`, subclase de `ValueError`, ante errores del dominio. La biblioteca rechaza un avalúo no entero con el mensaje `El avalúo debe ser un entero en pesos`; el transporte HTTP detecta esos tipos antes de invocar la biblioteca y usa el mensaje de estructura inválida documentado arriba.

# Servicio de impuesto predial

## Qué hace

Servicio HTTP para los sistemas de la alcaldía, con dos consultas independientes:

- `POST /tarifa`: consulta únicamente la tarifa.
- `POST /impuesto`: calcula el impuesto y devuelve la tarifa utilizada; exige avalúo.

No consulta otros sistemas ni datos de predios, no guarda consultas en una base de datos y no aplica descuentos ni exenciones. No incorpora identificación ni permisos. Esos asuntos no fueron definidos y no se añadieron al alcance. Los registros de acceso de Uvicorn no constituyen almacenamiento de consultas del módulo.

## Ejecución

Requiere Python 3.11 y los paquetes FastAPI y Uvicorn del entorno recibido. No usa servicios externos ni descarga datos.

Desde la raíz de la entrega:

```sh
PYTHONPATH=src python -m uvicorn predial:app --host 127.0.0.1 --port 8000
```

Para permitir conexiones desde otros equipos de la red municipal, cambiar `--host 127.0.0.1` por `--host 0.0.0.0`. Ese comando expone el servicio en todas las interfaces: la institución debe controlar su acceso en la infraestructura. Esta entrega no incorpora autenticación, TLS ni políticas de red.

Contrato OpenAPI: `GET /openapi.json`. Las interfaces de documentación generadas están en `/docs` y `/redoc`; sus recursos visuales predeterminados pueden requerir Internet. `USO.md`, el contrato JSON y el servicio no requieren Internet.

Pruebas:

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas invocan la aplicación ASGI en memoria, sin abrir puertos, hacer conexiones HTTP reales ni requerir paquetes de cliente HTTP adicionales.

## Contrato de entrada

Ambas consultas reciben un objeto JSON con `Content-Type: application/json` (se admite `charset=utf-8`). Las claves no llevan tildes.

| Campo | Formato y regla |
| --- | --- |
| `destino` | Obligatorio. Texto exacto: `residencial`, `comercial`, `industrial` o `lote urbanizable no edificado`. |
| `estrato` | Obligatorio exclusivamente para residencial. Número JSON entero de 1 a 6. Para otros destinos se debe omitir por completo. |
| `avaluo` | Exclusivamente en `/impuesto`, donde es obligatorio. Número JSON entero mayor que cero, en pesos, sin separadores de miles ni decimales. |

No se convierten cadenas a números. `1.0`, `true` y `"1"` no son enteros válidos para este contrato. `null` no sustituye la omisión de un campo. No se normalizan mayúsculas ni espacios del destino. No se admiten campos adicionales ni avalúo en `/tarifa`.

No existe un máximo de negocio para el avalúo. El cálculo usa enteros de Python, no números de coma flotante ni un contexto decimal de precisión limitada. Persisten límites técnicos del entorno: memoria y límite de conversión de enteros de Python 3.11 (por defecto, 4.300 dígitos decimales). No se configura ni se impone un máximo monetario adicional. Un entero de entrada que supere ese límite técnico produce `400` con `JSON inválido`.

### Tarifas

Unidad: pesos de impuesto por cada mil pesos de avalúo.

| Destino | Estrato | `tarifa_por_mil` |
| --- | --- | ---: |
| residencial | 1 | 5 |
| residencial | 2 | 6 |
| residencial | 3 | 8 |
| residencial | 4 | 10 |
| residencial | 5 | 12 |
| residencial | 6 | 14 |
| comercial | No se envía | 11 |
| industrial | No se envía | 12 |
| lote urbanizable no edificado | No se envía | 33 |

## Respuestas exitosas

Estado `200`, cuerpo JSON. No se devuelve impuesto en la consulta de tarifa.

Consulta de tarifa:

```http
POST /tarifa
Content-Type: application/json

{"destino":"residencial","estrato":3}
```

Respuesta:

```json
{"tarifa_por_mil":8}
```

Consulta del ejemplo confirmado por el cliente:

```http
POST /impuesto
Content-Type: application/json

{"destino":"residencial","estrato":3,"avaluo":120000000}
```

Respuesta:

```json
{"tarifa_por_mil":8,"impuesto_pesos":960000}
```

Para comercial, por ejemplo:

```json
{"destino":"comercial","avaluo":1000000}
```

En `/impuesto` responde:

```json
{"tarifa_por_mil":11,"impuesto_pesos":11000}
```

Cálculo: `avaluo × tarifa_por_mil ÷ 1000`, redondeado al peso, con mitades hacia arriba. Se implementa exactamente como `(avaluo * tarifa_por_mil + 500) // 1000`. Con residencial estrato 1, avalúos de 99, 100 y 101 producen respectivamente 0, 1 y 1 pesos. Un avalúo positivo puede producir impuesto cero después del redondeo; no se añade un impuesto mínimo.

## Errores

Los errores de lectura y validación tienen esta forma, sin resultado parcial:

```json
{"error":"Estrato inválido"}
```

| Estado | Situación | Mensaje exacto |
| --- | --- | --- |
| 415 | Falta Content-Type o no es application/json | `El contenido debe ser application/json` |
| 400 | Cuerpo vacío o JSON mal formado | `JSON inválido` |
| 400 | La raíz del JSON no es un objeto | `El cuerpo debe ser un objeto JSON` |
| 422 | Hay campos adicionales | `La consulta contiene campos no permitidos` |
| 422 | Falta destino | `El destino es obligatorio` |
| 422 | Destino inexistente o tipo inválido | `Destino económico no reconocido` |
| 422 | Falta estrato para residencial | `El estrato es obligatorio para residencial` |
| 422 | Estrato residencial no entero o fuera de 1 a 6 | `Estrato inválido` |
| 422 | Se envía estrato para otro destino, incluso null | `El estrato solo aplica para residencial` |
| 422 | Falta avalúo en /impuesto | `El avalúo es obligatorio` |
| 422 | Avalúo no entero | `El avalúo debe ser un entero en pesos` |
| 422 | Avalúo entero cero o negativo | `El avalúo debe ser mayor que cero` |

Los tres mensajes acordados con el cliente se conservan literalmente. Los demás mensajes, estados HTTP, rutas, claves y política de campos adicionales son decisiones simples de esta entrega para completar lo que quedó sin definir.

Si hay varios errores, se devuelve solo el primero. Orden: tipo de contenido, lectura JSON, raíz objeto, campos adicionales, destino, reglas de estrato y, en `/impuesto`, avalúo. Para un avalúo no entero se informa el error de formato antes de evaluar su signo.

Las rutas inexistentes y los métodos no admitidos usan las respuestas estándar de FastAPI: `404 {"detail":"Not Found"}` y `405 {"detail":"Method Not Allowed"}`. No se transforma ese comportamiento en errores de negocio.

## Uso directo desde Python

Con `src/` en la ruta de importación:

```python
from predial import ErrorConsulta, calcular_impuesto, consultar_tarifa

print(consultar_tarifa({"destino": "industrial"}))
# {'tarifa_por_mil': 12}

print(calcular_impuesto({"destino": "industrial", "avaluo": 1000000}))
# {'tarifa_por_mil': 12, 'impuesto_pesos': 12000}

try:
    calcular_impuesto({"destino": "industrial", "avaluo": 0})
except ErrorConsulta as error:
    print(str(error))
# El avalúo debe ser mayor que cero
```

Las funciones reciben diccionarios con claves de texto, aplican las mismas reglas de negocio que HTTP, devuelven diccionarios y lanzan `ErrorConsulta` ante datos inválidos. La comprobación del cuerpo JSON y su tipo de contenido corresponde únicamente a la interfaz HTTP.

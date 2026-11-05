# Avisos catastrales

Módulo para Python 3.11, sin dependencias de ejecución fuera de la biblioteca estándar. Incluye un canal en memoria y tres consumidores independientes: bitácora, indicador de tiempos y preparación de mensajes. No realiza el envío al ciudadano.

## Uso

Desde la raíz, con `src/` en la ruta de importación:

```sh
PYTHONPATH=src python -m pytest tests
```

Ejemplo completo:

```python
from datetime import date, datetime
from avisos_catastrales import Aviso, Sistema

sistema = Sistema()
try:
    # Integración auxiliar: suministrar la fecha REAL en que quedó radicado.
    # No es una transición de estados ni una regla de negocio confirmada.
    sistema.indicador.guardar_fecha_radicacion("T-0001", date(2026, 11, 2))

    sistema.publicar(Aviso(
        numero="T-0001",
        tipo="mutación",
        estado_anterior="radicado",
        estado_nuevo="en revisión",
        fecha_hora=datetime(2026, 11, 3, 9, 0),
        funcionario="Marta Pérez",
    ))
    sistema.publicar(Aviso(
        numero="T-0001",
        tipo="mutación",
        estado_anterior="en revisión",
        estado_nuevo="aprobado",
        fecha_hora=datetime(2026, 11, 6, 10, 30),
        funcionario="Marta Pérez",
    ))

    # Solo para pruebas, consultas sincronizadas o cierre;
    # el sistema de radicación NO necesita hacer esta espera.
    sistema.esperar()
    print(sistema.indicador.promedios)  # {'mutación': 4.0}
    print(sistema.bitacora.registros)
    print(sistema.mensajes.mensajes)
    print(sistema.canal.fallos)
finally:
    sistema.cerrar()
```

El publicador solo necesita una referencia al canal o a `sistema.publicar`; no conoce los consumidores. `publicar` valida la estructura y encola, pero no espera al trabajo de los consumidores. Cada consumidor tiene un hilo y una cola independientes, conserva su orden de recepción y puede fallar o bloquearse sin detener a los demás. No se promete paralelismo de CPU ni distribución entre aplicaciones.

Puede conectar otro consumidor con `sistema.canal.suscribir(nombre, funcion)`. La función recibe un `Registro`; debe respetar su marca `valida` si realiza trabajo de negocio. Los consumidores incorporados solo procesan transiciones válidas, salvo la bitácora, que registra todas. Las suscripciones nuevas no reciben avisos anteriores.

## Entradas y reglas confirmadas

`Aviso` es una clase de datos inmutable con:

| Campo | Formato |
| --- | --- |
| `numero` | Texto no vacío, por ejemplo `T-0456` |
| `tipo` | Texto no vacío, por ejemplo `mutación` |
| `estado_anterior` | Texto; `None` permite representar un antecedente no informado |
| `estado_nuevo` | Texto no vacío |
| `fecha_hora` | `datetime.datetime`, por ejemplo `datetime(2026, 11, 5, 10, 30)` |
| `funcionario` | Texto no vacío, por ejemplo `Marta Pérez` |

Solo son válidos estos pares exactos:

- `radicado` → `en revisión`.
- `en revisión` → `aprobado`.
- `en revisión` → `rechazado`.

La bitácora conserva cada aviso completo con `valida=True` o `False`. Una transición inválida no produce medición ni mensaje. Los estados desconocidos también resultan inválidos. No se comprueba el historial del trámite ni se agregan otras restricciones de transición.

El indicador utiliza la fecha real de radicación y calcula al recibir un aviso válido de aprobación o rechazo. Agrupa por el texto exacto del tipo. El ejemplo de control, del lunes 2 al viernes 6 de noviembre de 2026, produce 4 días hábiles.

Los mensajes tienen `numero` y `texto`, sin puntuación adicional:

- `Su trámite N está en revisión`
- `Su trámite N fue aprobado`
- `Su trámite N fue rechazado; puede consultar el motivo en la oficina`

Se prepara uno por cada aviso válido, incluidos los repetidos.

## Salidas

- `bitacora.registros`: tupla de `Registro(aviso, valida)`.
- `indicador.mediciones`: tupla de `Medicion(aviso, fecha_radicacion, dias)`.
- `indicador.promedios`: diccionario nuevo `{tipo: promedio_en_dias}`, con valores `float`, sin redondeo adicional. Los tipos sin mediciones no aparecen.
- `mensajes.mensajes`: tupla de `Mensaje(numero, texto)`.
- `canal.fallos`: tupla de `Fallo(consumidor, registro, tipo, mensaje)`.

Son instantáneas seguras para consultas concurrentes, pero no una transacción conjunta entre consumidores. Para consultar resultados completos sin publicaciones concurrentes, use `esperar()`.

## Puntos no definidos: decisiones mínimas de esta implementación

**Estas decisiones técnicas no son acuerdos confirmados por el cliente.** Los puntos pendientes siguen requiriendo definición para una integración definitiva.

1. **Canal y almacenamiento:** todo vive en memoria dentro de una aplicación, como permite el canal de pruebas. Las colas no tienen límite configurado y no hay persistencia, red, recuperación tras reinicios ni garantía de entrega duradera. El tamaño práctico está limitado por la memoria disponible. Publicar sin consumidores no conserva el aviso.
2. **Primer aviso y origen de la fecha de radicación:** no se inventa una transición inicial válida. Un aviso con estado nuevo `radicado`, incluso con antecedente `None`, queda en bitácora como inválido y no alimenta el indicador. Para que el cálculo sea utilizable, se ofrece `guardar_fecha_radicacion(numero, fecha)` como entrada auxiliar del integrador, independiente de los avisos. Puede llamarla al conocer la fecha real; para calcular un terminal debe estar disponible antes de que ese consumidor lo atienda. No se deduce del primer aviso, cuyo formato sigue pendiente. Guardarla otra vez reemplaza la fecha para cálculos futuros, sin recalcular los anteriores.
3. **Extremos y festivos:** se excluye la fecha de radicación y se incluye la fecha terminal; cuentan lunes a viernes, sin calendario de festivos. Esta convención satisface el ejemplo confirmado, pero no confirma reglas para otros extremos o festivos. Misma fecha da cero; fin anterior produce error. Se ignora la hora y se usa la fecha local representada por el `datetime`, sin convertir zonas horarias.
4. **Fecha faltante:** el consumidor indicador registra un fallo y omite esa medición. No la deja pendiente ni reintenta automáticamente. Bitácora y mensajes continúan. Esta es una elección técnica, no una política de negocio acordada.
5. **Duplicados:** no hay identificador de evento ni deduplicación. Cada terminal válido con fecha conocida añade una medición al promedio, incluso si es repetido. Bitácora y mensajes conservan cada aviso, como sí fue solicitado.
6. **Datos mal formados:** se rechazan antes de publicar. No se parsean fechas ni se normalizan mayúsculas, acentos o espacios. No se imponen longitudes máximas ni catálogos para tipo, funcionario o número. `None` en el antecedente y el antecedente vacío no crean una transición válida.
7. **Fallos:** se capturan excepciones ordinarias de consumidores, se guardan sus detalles y el trabajador continúa con el aviso siguiente. No hay reintentos automáticos ni reversión de efectos parciales. `KeyboardInterrupt`, `SystemExit` y otras excepciones de control no se capturan. Un consumidor que nunca termina no bloquea la publicación ni los demás, pero sí puede impedir `esperar()` o `cerrar()`.

## Errores de la API

- Campo textual obligatorio vacío o de tipo incorrecto: `ValueError("<campo>: se requiere texto no vacío")`.
- Antecedente de tipo incorrecto: `ValueError("estado_anterior: se requiere texto o None")`.
- Fecha y hora no `datetime`: `ValueError("fecha_hora: se requiere datetime")`. Una fecha imposible falla al construir el propio `datetime`.
- Campos obligatorios omitidos: `TypeError` del constructor de Python; no se define un texto propio.
- Publicación de otro objeto: `ValueError("aviso: se requiere Aviso")`.
- Fecha auxiliar que no es exactamente `date`: `ValueError("fecha: se requiere date, sin hora")`.
- Número auxiliar vacío: `ValueError("numero: se requiere texto no vacío")`.
- Sin fecha de radicación: fallo del indicador con tipo `ValueError` y mensaje `No hay fecha de radicación para N`.
- Fecha terminal anterior: fallo del indicador con mensaje `La fecha final es anterior a la radicación`.
- `dias_habiles` con entradas distintas de `date`: `ValueError("Las fechas deben ser date, sin hora")`.
- Suscripción sin nombre: `ValueError("nombre: se requiere texto no vacío")`.
- Consumidor no invocable: `ValueError("atender: se requiere una función")`.
- Nombre duplicado: `ValueError("Consumidor ya suscrito: N")`.
- Publicar o suscribir tras cerrar: `RuntimeError("El canal está cerrado")`.

Las transiciones inválidas no lanzan excepción: quedan marcadas en bitácora. Los fallos asíncronos se consultan en `canal.fallos`, no se devuelven como excepciones de `publicar()`.

`cerrar()` procesa las colas pendientes y libera los hilos; puede repetirse. No llame a `esperar()` ni `cerrar()` desde un consumidor. Para un cierre definitivo, detenga primero los productores externos.

## Fuera de alcance

Envío real al ciudadano, destinatarios y contactos, almacenamiento durable, festivos oficiales, comunicación entre aplicaciones, reintentos, deduplicación y obtención automática de la fecha de radicación. El módulo no cambia estados en el sistema de radicación: recibe los avisos que este publica.

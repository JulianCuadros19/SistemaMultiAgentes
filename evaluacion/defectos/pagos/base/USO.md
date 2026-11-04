# Procesamiento de avisos de pagos

Módulo de eventos, productores, consumidores independientes y almacenamiento volátil para aplicar pagos confirmados y reversos a facturas, recibos y cartera.

## Requisitos

Python 3.11. Dependencia externa declarada: `pydantic`, destinada a validación de esquemas. Esta implementación realiza las validaciones explícitamente con dataclasses y biblioteca estándar, sin requerir una versión concreta de Pydantic. Para ejecutar las pruebas se necesita `pytest`.

## Instalación

Desde la raíz del código:

```sh
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

El sistema genera `requirements.txt` al exportar; no forma parte de los archivos entregados.

## Configuración

No requiere archivos, variables de entorno ni servicios. Antes de publicar, registre las facturas y las carteras de sus familias. Los datos viven en memoria durante el proceso. Registre explícitamente los consumidores que deban reaccionar en cada bus.

## Ejecución

No existe punto de entrada de terminal. Invoque las interfaces desde Python, con `src` en la ruta de importación; por ejemplo, abra el intérprete mediante `PYTHONPATH=src python` y ejecute:

```python
from datetime import date
from decimal import Decimal

from consumidores.cartera import (
    manejar_pago_confirmado_cartera,
    manejar_pago_reversado_cartera,
)
from consumidores.factura import (
    manejar_pago_confirmado_factura,
    manejar_pago_reversado_factura,
)
from consumidores.recibo import manejar_pago_reversado_recibo
from consumidores.recibo_emision import manejar_pago_confirmado_emitir_recibo
from infraestructura.bus_eventos_memoria import BusEventosMemoria
from infraestructura.repos_facturacion_memoria import (
    registrar_factura_inicial,
    registrar_cartera_familia,
)
from productores.publicador_avisos import (
    construir_aviso_confirmado,
    construir_aviso_reversado,
)

registrar_factura_inicial("2024-000123", "F1", Decimal(250000), "pendiente")
registrar_cartera_familia("F1", "en mora")
bus = BusEventosMemoria()
bus.suscribir_pago_confirmado(manejar_pago_confirmado_factura)
bus.suscribir_pago_confirmado(manejar_pago_confirmado_emitir_recibo)
bus.suscribir_pago_confirmado(manejar_pago_confirmado_cartera)
bus.suscribir_pago_reversado(manejar_pago_reversado_factura)
bus.suscribir_pago_reversado(manejar_pago_reversado_recibo)
bus.suscribir_pago_reversado(manejar_pago_reversado_cartera)
bus.publicar_pago_confirmado(construir_aviso_confirmado(
    "P1", "2024-000123", Decimal(250000), date(2026, 10, 31)
))
bus.publicar_pago_reversado(construir_aviso_reversado(
    "P1", date(2026, 10, 31), "reverso por contracargo"
))
```

Un duplicado lanza `EventoDuplicadoIgnorado` sin volver a ejecutar consumidores ni aplicar resultados. El llamador puede capturar específicamente esa excepción para continuar su recepción de avisos.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas usan únicamente memoria y no requieren red.

## Interfaces

Los siguientes ejemplos usan `D = Decimal`, `f = date(2026, 10, 31)` y los módulos importados con sus nombres o alias. Los importes deben suministrarse como `Decimal`, nunca como `float`.

### Eventos brutos: `eventos.aviso_pago`

- `AvisoPagoConfirmado`: `AvisoPagoConfirmado("P1", "N1", D(100), f)`.
- `AvisoPagoReversado`: `AvisoPagoReversado("P1", f, "contracargo")`.
- `ValidacionEventoInvalido`: excepción para restricciones inválidas del aviso bruto; por ejemplo, capture esta excepción al construir un pago con `D("0.5")`.

### Eventos enriquecidos: `eventos.aviso_pago_enriquecido`

- `AvisoPagoConfirmadoEnriquecido`: `confirmado = AvisoPagoConfirmadoEnriquecido("P1", "N1", D(100), f, D(100), "pendiente", "F1")`.
- `AvisoPagoReversadoEnriquecido`: `reversado = AvisoPagoReversadoEnriquecido("P1", f, "contracargo", "N1", "pendiente", "F1")`.
- `ValidacionEventoInvalido`: excepción de este módulo para restricciones inválidas del contexto; también es la excepción expuesta por los consumidores. Es distinta de la excepción homónima de eventos brutos, para respetar las dependencias permitidas.

### Resultados: `eventos.resultados`

- `AjusteFacturaResultado`: `AjusteFacturaResultado("N1", "pagada", D(100), D(0), "confirmado:P1:N1")`.
- `EmisionReciboResultado`: `EmisionReciboResultado("N1", "P1", D(100), f, "confirmado:P1")`.
- `AnulacionReciboResultado`: `AnulacionReciboResultado("P1", "contracargo", "anulado", "reversado:P1")`.
- `ActualizacionCarteraResultado`: `ActualizacionCarteraResultado("P1", "F1", "al día", "confirmado:P1")`.

### Productor: `productores.publicador_avisos`

- `construir_aviso_confirmado`: `construir_aviso_confirmado("P1", "N1", D(100), f)`.
- `construir_aviso_reversado`: `construir_aviso_reversado("P1", f, "contracargo")`.
- `AvisoIncompleto`: capture esta excepción al enviar un campo obligatorio ausente, `None` o texto vacío.
- `ValidacionEventoInvalido`: importada del módulo de avisos brutos; capture esta excepción cuando un campo presente tiene tipo o valor inválido.

### Consumidores

Todos devuelven decisiones sin modificar los eventos ni acceder al repositorio:

- `consumidores.factura.manejar_pago_confirmado_factura`: `ajuste = manejar_pago_confirmado_factura(confirmado)`.
- `consumidores.factura.manejar_pago_reversado_factura`: `ajuste_reverso = manejar_pago_reversado_factura(reversado)`.
- `consumidores.recibo_emision.manejar_pago_confirmado_emitir_recibo`: `emision = manejar_pago_confirmado_emitir_recibo(confirmado)`.
- `consumidores.recibo.manejar_pago_reversado_recibo`: `anulacion = manejar_pago_reversado_recibo(reversado)`.
- `consumidores.cartera.manejar_pago_confirmado_cartera`: `actualizacion = manejar_pago_confirmado_cartera(confirmado)`.
- `consumidores.cartera.manejar_pago_reversado_cartera`: `actualizacion_reverso = manejar_pago_reversado_cartera(reversado)`.

Cada consumidor expone `ValidacionEventoInvalido`, importada del módulo de eventos enriquecidos.

### Repositorio: `infraestructura.repos_facturacion_memoria`

Usando `from infraestructura import repos_facturacion_memoria as repos`:

- `registrar_factura_inicial`: `repos.registrar_factura_inicial("N1", "F1", D(100), "pendiente")`.
- `obtener_factura_por_numero`: `factura = repos.obtener_factura_por_numero("N1")`.
- `registrar_mapeo_referencia_factura`: `repos.registrar_mapeo_referencia_factura("P1", "N1")`.
- `obtener_numero_factura_por_referencia`: `numero = repos.obtener_numero_factura_por_referencia("P1")`.
- `registrar_cartera_familia`: `repos.registrar_cartera_familia("F1", "en mora")`.
- `obtener_cartera_por_familia`: `cartera = repos.obtener_cartera_por_familia("F1")`.
- `aplicar_ajuste_factura`: `factura = repos.aplicar_ajuste_factura(ajuste)`.
- `aplicar_emision_recibo`: `recibo = repos.aplicar_emision_recibo(emision)`.
- `aplicar_anulacion_recibo`: `recibo = repos.aplicar_anulacion_recibo(anulacion)`.
- `actualizar_cartera`: `cartera = repos.actualizar_cartera(actualizacion)`.
- `Factura`: `repos.Factura("N1", "F1", D(100), "pendiente", "pendiente")`.
- `Recibo`: `repos.Recibo("REC-000001", "N1", D(100), "emitido", "P1")`; después de una anulación, consulte `recibo.motivo`.
- `Cartera`: `repos.Cartera("F1", "en mora")`.
- `FacturaNoExiste`, `ReferenciaNoAsociada`, `ReciboNoExiste`: capture específicamente la excepción correspondiente a la búsqueda o aplicación fallida.

### Bus: `infraestructura.bus_eventos_memoria`

- `BusEventosMemoria`: `bus = BusEventosMemoria()`.
- `suscribir_pago_confirmado`: `bus.suscribir_pago_confirmado(manejar_pago_confirmado_factura)`.
- `suscribir_pago_reversado`: `bus.suscribir_pago_reversado(manejar_pago_reversado_factura)`.
- `publicar_pago_confirmado`: `bus.publicar_pago_confirmado(construir_aviso_confirmado("P1", "N1", D(100), f))`.
- `publicar_pago_reversado`: `bus.publicar_pago_reversado(construir_aviso_reversado("P1", f, "contracargo"))`.

Las cuatro operaciones también están disponibles como funciones de nivel superior, pasando el bus como primer argumento: por ejemplo, `suscribir_pago_confirmado(bus, manejar_pago_confirmado_factura)`.

El bus expone `EventoDuplicadoIgnorado`, `FacturaNoExiste` y `ReferenciaNoAsociada` para su captura por el llamador.

## Supuestos

- Los textos con solo espacios se consideran vacíos. No se normalizan los identificadores ni el motivo.
- Se aceptan representaciones como `Decimal("100.00")` porque su valor es entero; las decisiones y los importes calculados se cuantizan a cero decimales con `ROUND_HALF_UP`. No se admiten fracciones de peso, valores negativos ni valores no finitos.
- El importe aplicado es el mínimo entre pago y saldo; el excedente se entrega como saldo a favor en el resultado. No se añade un saldo a favor a la entidad Factura porque no figura en su modelo.
- Como no se especifica una agregación de varias facturas, la cartera se calcula a partir de la factura del aviso: al día si el pago cubre su saldo; en mora en otro caso. En el reverso se usa el estado restaurado: pagada implica al día.
- El repositorio conserva el saldo inicial de cada factura y el importe efectivamente aplicado por referencia y factura. Un reverso devuelve solo ese importe, sin deshacer otros pagos ni sumar el excedente. El estado de factura se deriva del saldo resultante: pagada si es cero, pendiente si vuelve al saldo inicial positivo y abonada si queda un saldo positivo menor. El campo `estado_anterior` continúa representando el estado anterior al último ajuste.
- Se agrega al recibo el atributo opcional `motivo`, inicialmente ausente, para registrar el motivo exigido por RF-02 sin crear otra interfaz de consulta.
- La cartera debe existir previamente. Consultar o actualizar una familia no registrada produce `KeyError`; no se inventa un estado inicial.
- Donde no hay una excepción de validación declarada para resultados o registros iniciales, se utiliza `ValueError`. La validación de eventos enriquecidos también ocurre al construirlos y se repite al entrar a los consumidores.
- Las claves usan los prefijos `confirmado:` y `reversado:`. La infraestructura distingue los resultados además por su clase para no confundir, por ejemplo, emisión y actualización de cartera con la misma clave. Confirmación y reverso de una referencia son eventos diferentes.
- La idempotencia de publicación pertenece a cada instancia del bus. Reutilice una misma instancia para toda la recepción de avisos del proceso. La emisión del repositorio también reutiliza el recibo ya registrado para una referencia.
- Las suscripciones son explícitas y el despacho es síncrono. Todos los consumidores reciben el mismo contexto previo al ajuste. Un consumidor debe devolver uno de los cuatro resultados declarados.
- El repositorio es compartido en el proceso y no tiene persistencia ni control de concurrencia. No se ofrecen transacciones ni recuperación automática de fallos durante la aplicación de resultados.

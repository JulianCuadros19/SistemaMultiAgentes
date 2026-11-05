# Avisos catastrales

Módulo para Python 3.11, sin dependencias de ejecución externas y sin acceso a red. Distribuye avisos a una bitácora, un indicador de tiempos y un preparador de mensajes. No radica trámites ni envía mensajes al ciudadano.

## Uso

Con `src/` en la ruta de importación:

```python
from datetime import date, datetime

from avisos_catastrales import Aviso, Estado, SistemaAvisos, TipoTramite

sistema = SistemaAvisos()
try:
    # Dato externo conocido; esto no radica el trámite.
    sistema.indicador.registrar_radicacion("T-0001", date(2026, 11, 2))

    # El publicador solo necesita el canal, no referencias a los consumidores.
    publicar = sistema.canal.publicar
    publicar(Aviso(
        numero="T-0001",
        tipo=TipoTramite.MUTACION,
        estado_anterior=Estado.RADICADO,
        estado_nuevo=Estado.EN_REVISION,
        fecha_hora=datetime(2026, 11, 3, 10),
        funcionario="Ana",
    ))
    publicar(Aviso(
        numero="T-0001",
        tipo=TipoTramite.MUTACION,
        estado_anterior=Estado.EN_REVISION,
        estado_nuevo=Estado.APROBADO,
        fecha_hora=datetime(2026, 11, 6, 15, 30),
        funcionario="Ana",
    ))

    # Solo para consultar resultados completos; publicar no espera este trabajo.
    sistema.canal.esperar()
    assert sistema.indicador.mediciones[0].dias == 4
    assert sistema.indicador.promedios[TipoTramite.MUTACION] == 4.0
    assert sistema.mensajes.mensajes[-1].texto == "Su trámite T-0001 fue aprobado"
    registros = sistema.bitacora.registros
    errores = sistema.canal.fallos
finally:
    sistema.cerrar()
```

## Entradas

`Aviso` es una dataclass inmutable con seis datos obligatorios:

- `numero: str`: número del trámite.
- `tipo: TipoTramite`: `MUTACION`, `RECTIFICACION` o `CERTIFICADO`.
- `estado_anterior` y `estado_nuevo: Estado`: `RADICADO`, `EN_REVISION`, `APROBADO` o `RECHAZADO`.
- `fecha_hora: datetime`: instante informado por el sistema de radicación.
- `funcionario: str`: funcionario informado.

Se espera que el adaptador externo construya estos objetos con los tipos declarados. No se incluye un parser de JSON ni validación de formatos de número o funcionario: no se especificaron. Los enums pueden construirse a partir de sus valores, por ejemplo `Estado("en revisión")` y `TipoTramite("mutación")`; un valor desconocido produce `ValueError` del enum.

La fecha original se carga mediante `indicador.registrar_radicacion(numero, fecha)` con un `date`, antes de publicar avisos terminales. El aviso de salida de `radicado` no contiene la fecha en que se radicó; no se usa su hora como sustituto. Obtener ese dato del sistema externo queda fuera del módulo. Una nueva carga del mismo número reemplaza la fecha para cálculos posteriores, sin recalcular resultados históricos.

## Reglas y salidas

Solo son válidas las transiciones:

1. radicado → en revisión;
2. en revisión → aprobado;
3. en revisión → rechazado.

La validación considera el par de estados del aviso, no reconstruye el historial del trámite. Los inválidos se registran con `valido=False` y no se entregan al indicador ni a mensajes.

Las propiedades de resultados devuelven instantáneas protegidas frente a concurrencia:

- `bitacora.registros`: tupla de `RegistroBitacora`, cada uno con el aviso completo y `valido`.
- `indicador.mediciones`: tupla de `Medicion(numero, tipo, dias)` para avisos terminales válidos que pudieron calcularse.
- `indicador.promedios`: diccionario de tipo a promedio `float`. Los tipos sin mediciones no aparecen.
- `mensajes.mensajes`: tupla de `Mensaje(numero, texto)`, sin envío:
  - aprobado: `Su trámite N fue aprobado`;
  - rechazado: `Su trámite N fue rechazado; puede consultar el motivo en la oficina`;
  - en revisión: `Su trámite N está en revisión`.
- `canal.fallos`: tupla de `Fallo(consumidor, aviso, descripcion)`.

Los días hábiles son lunes a viernes, excluyendo la fecha inicial e incluyendo la final. Se ignoran horas y festivos; se usa la fecha tal como viene en `datetime`, sin conversión de zona horaria. Esto da cuatro días del lunes 2026-11-02 al viernes 2026-11-06. Una finalización el mismo día da cero. `dias_habiles(inicio, fin)` expone el cálculo por separado.

No se especificó identificación de duplicados: cada aviso publicado se procesa una vez por consumidor destinatario, aunque repita datos anteriores. Cada aviso terminal calculado aporta una observación al promedio.

## Asincronía y extensión

Cada consumidor tiene una cola FIFO sin límite y un hilo propio. `publicar()` solo distribuye a las colas: no ejecuta callbacks ni espera su finalización. No es una garantía de tiempo real: hay un bloqueo breve para coordinar publicaciones y cierre. Un consumidor lento no bloquea el trabajo de los otros.

`CanalAvisos` permite añadir consumidores sin cambiar el publicador:

```python
from avisos_catastrales import Aviso, CanalAvisos


def reaccionar(aviso: Aviso) -> None:
    """Reaccionar a un aviso válido."""
    print(aviso.numero)


canal = CanalAvisos()
canal.suscribir("otro proceso", reaccionar)
# Publicar avisos aquí y cerrar al terminar.
canal.cerrar()
```

Las suscripciones reciben publicaciones futuras, no avisos anteriores. Por defecto no reciben inválidos. `incluir_invalidos=True` se reserva para consumidores de auditoría; `SistemaAvisos` lo activa únicamente para la bitácora. Un canal vacío no conserva avisos para futuros suscriptores.

`esperar()` permite sincronizar pruebas o consultas después de detener las publicaciones. `cerrar()` impide nuevas operaciones, drena lo pendiente y une los hilos; es idempotente. Ambos deben usarse fuera de callbacks. Si un callback no retorna, las operaciones de espera/cierre pueden esperar indefinidamente. Siempre cierre el sistema al finalizar.

## Errores y límites

- Transición inválida: no lanza una excepción; queda marcada en la bitácora.
- Falta de fecha de radicación o fecha final anterior: el indicador lanza `ValueError`; el canal lo registra como fallo y los otros consumidores continúan.
- Cualquier `Exception` de un consumidor se captura en la frontera del hilo, se registra también mediante `logging` y no interrumpe otros consumidores ni futuros avisos del mismo consumidor. No se capturan señales de terminación derivadas directamente de `BaseException`.
- Suscripción con nombre duplicado: `ValueError`.
- Publicación o suscripción después del cierre: `RuntimeError`.

No hay reintentos, persistencia, deduplicación ni entrega entre procesos del sistema operativo. El canal en memoria simula los procesos independientes para pruebas y requiere que el productor esté en el mismo proceso Python. Una integración real entre procesos requiere un transporte externo, no definido por el cliente. Las colas y resultados se pierden al terminar el proceso; un consumidor rezagado puede aumentar el uso de memoria. La garantía de registro en bitácora presupone que su consumidor funciona: si este falla, el error se conserva en `canal.fallos` y los otros dos siguen trabajando.

## Pruebas

Desde la raíz del proyecto:

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas cubren todas las combinaciones de estados, los tres tipos, cada texto, el ejemplo de cuatro días, fines de semana, promedios, errores de fechas, fallos de cada consumidor y la independencia ante un consumidor bloqueado. No necesitan red.

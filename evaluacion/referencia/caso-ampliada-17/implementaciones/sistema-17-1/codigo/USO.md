# Seguimiento de trámites catastrales

Publica avisos de cambio de estado y permite procesarlos posteriormente para registrar bitácora, calcular tiempos hábiles y preparar mensajes al ciudadano.

## Requisitos

- Python 3.11 o superior; el módulo se probó con Python 3.11.
- Sin dependencias externas: `requirements.txt` fija la versión de pytest.

## Instalación

Desde la carpeta del código, cree un entorno e instale las dependencias:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, el entorno se activa con `.venv\Scripts\activate`. `requirements.txt` acompaña al código: fija las versiones con que se probó e incluye pytest.

## Configuración

No requiere archivos de configuración ni variables de entorno. Prepare instancias del canal y de los registros en memoria. Para calcular tiempos, registre previamente la fecha de radicación de cada trámite.

## Ejecución

No hay punto de entrada de terminal. Invoque las interfaces desde Python con `src` en la ruta de importación, por ejemplo iniciando `PYTHONPATH=src python` desde la raíz del código.

```python
from datetime import date, datetime

from consumidores.bitacora import BitacoraConsumidor
from consumidores.indicador import IndicadorConsumidor
from consumidores.mensajes import MensajesConsumidor
from infraestructura.bitacora_memoria import RegistroBitacoraMemoria
from infraestructura.calendario_tramite_memoria import RegistroFechasTramiteMemoria
from infraestructura.canal_memoria import CanalEventosMemoria
from infraestructura.indicadores_memoria import RegistroIndicadoresMemoria
from infraestructura.mensajes_memoria import RegistroMensajesMemoria
from productores.cambios_estado import publicar_cambio_estado

canal = CanalEventosMemoria()
bitacora = RegistroBitacoraMemoria()
indicadores = RegistroIndicadoresMemoria()
fechas = RegistroFechasTramiteMemoria()
mensajes = RegistroMensajesMemoria()

fechas.registrar_radicado("T-0001", date(2026, 11, 2))
canal.suscribir(BitacoraConsumidor(bitacora).manejar)
canal.suscribir(IndicadorConsumidor(indicadores, fechas).manejar)
canal.suscribir(MensajesConsumidor(mensajes).manejar)

aviso = publicar_cambio_estado(
    canal, "T-0001", "mutación", "en revisión", "aprobado",
    datetime(2026, 11, 6, 10, 30), "F-01",
)
# Publicar no ejecuta los consumidores.
canal.despachar_pendientes()
assert indicadores.consultar_dias_calculados("T-0001") == 4
assert mensajes.consultar_por_tramite("T-0001")[0].texto == "Su trámite T-0001 fue aprobado"
```

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Entidades de `eventos.aviso`

Las entidades son dataclasses inmutables y exponen sus campos directamente.

- `AvisoCambioEstado`: `AvisoCambioEstado("T", "mutación", "radicado", "en revisión", datetime(2026, 11, 2), "F", True)`.
- `AsientoBitacora`: `AsientoBitacora("T", "mutación", "radicado", "en revisión", datetime(2026, 11, 2), "F", True)`.
- `MensajeCiudadano`: `MensajeCiudadano("T", "Su trámite T está en revisión")`.

### Contratos de `eventos.aviso` e implementaciones

Los contratos son clases abstractas; use sus implementaciones en memoria. Las siguientes operaciones pertenecen tanto al contrato como a la implementación indicada:

- `CanalEventos` / `CanalEventosMemoria()`: crea una cola vacía.
  - `suscribir(manejador)`: `canal.suscribir(BitacoraConsumidor(bitacora).manejar)`.
  - `publicar(aviso)`: `canal.publicar(aviso)` encola un aviso ya construido.
  - `obtener_pendientes()`: `pendientes = canal.obtener_pendientes()` obtiene una copia.
  - `despachar_pendientes()`: `canal.despachar_pendientes()` entrega y consume la cola. Un fallo de receptor produce una advertencia sin datos personales y no impide las demás entregas.
- `RegistroBitacora` / `RegistroBitacoraMemoria()`: crea una bitácora vacía.
  - `registrar(asiento)`: `bitacora.registrar(asiento)`.
  - `consultar_por_tramite(numero_tramite)`: `asientos = bitacora.consultar_por_tramite("T-0001")`.
- `RegistroIndicadores` / `RegistroIndicadoresMemoria()`: crea un registro de tiempos vacío.
  - `registrar_dias(numero_tramite, tipo_tramite, dias_habiles)`: `indicadores.registrar_dias("T", "mutación", 4)`.
  - `consultar_dias_calculados(numero_tramite)`: `dias = indicadores.consultar_dias_calculados("T")`; devuelve `None` si falta el cálculo.
  - `promedio_por_tipo(tipo_tramite)`: `promedio = indicadores.promedio_por_tipo("mutación")`; devuelve `Decimal(0)` si no hay datos.
- `RegistroFechasTramite` / `RegistroFechasTramiteMemoria()`: crea un calendario vacío.
  - `registrar_radicado(numero_tramite, fecha)`: `fechas.registrar_radicado("T", date(2026, 11, 2))`.
  - `obtener_fecha_radicado(numero_tramite)`: `fecha = fechas.obtener_fecha_radicado("T")`; devuelve `None` si no existe.
- `RegistroMensajes` / `RegistroMensajesMemoria()`: crea un registro de mensajes vacío.
  - `registrar(mensaje)`: `mensajes.registrar(MensajeCiudadano("T", "Su trámite T fue aprobado"))`.
  - `consultar_por_tramite(numero_tramite)`: `lista = mensajes.consultar_por_tramite("T")`.

### Productor y consumidores

- `productores.cambios_estado.publicar_cambio_estado(canal, numero_tramite, tipo_tramite, estado_anterior, estado_nuevo, fecha_hora, funcionario)`: el ejemplo de ejecución muestra todos sus argumentos. Devuelve el aviso publicado con su marca de validez.
- `consumidores.bitacora.BitacoraConsumidor(registro)`: `receptor = BitacoraConsumidor(bitacora)`.
  - `manejar(aviso)`: `receptor.manejar(aviso)` registra todos los datos, incluso para una transición inválida.
- `consumidores.indicador.IndicadorConsumidor(registro, fechas)`: `receptor = IndicadorConsumidor(indicadores, fechas)`.
  - `manejar(aviso)`: `receptor.manejar(aviso)` calcula tiempos únicamente para una transición válida a aprobado o rechazado.
- `consumidores.mensajes.MensajesConsumidor(registro)`: `receptor = MensajesConsumidor(mensajes)`.
  - `manejar(aviso)`: `receptor.manejar(aviso)` prepara el mensaje correspondiente a un cambio válido.
- `consumidores.falla.ConsumidorFalla()`: `receptor = ConsumidorFalla()` crea un receptor de comprobación.
  - `manejar(aviso)`: `receptor.manejar(aviso)` lanza siempre `Exception`; suscríbalo al canal para comprobar el aislamiento de fallos.

## Supuestos

- Como no se especifica una excepción para datos inválidos, se utiliza `ValueError`. Una transición entre estados conocidos pero no permitida no lanza esa excepción: se publica con `es_valida=False` para registrarla en bitácora.
- Un texto formado únicamente por espacios se considera vacío. No se recortan ni se normalizan los textos válidos. Los estados requieren la grafía exacta indicada, incluida la tilde de `en revisión`.
- Las fechas y horas se interpretan como locales tal como se reciben; no se convierten zonas horarias ni se consulta la configuración del sistema.
- El cálculo excluye el día de radicación e incluye el día final si es de lunes a viernes. No se excluyen festivos. Radicación y terminación en la misma fecha producen cero días.
- Si no existe fecha de radicación, el indicador no registra un cálculo. Si la fecha final precede a la radicación, lanza `ValueError`; durante un despacho el canal registra la advertencia y continúa.
- Cada trámite mantiene un único cálculo vigente. Volver a registrar sus días reemplaza el cálculo anterior sin contar dos veces el mismo trámite en el promedio. El promedio se obtiene de esos cálculos vigentes, sin una cantidad fija de decimales.
- Las transiciones inválidas solo producen bitácora, no indicadores ni mensajes. No hay una entidad de trámite ni una operación de modificación de su estado: el rechazo del cambio se observa mediante la marca inválida y la ausencia de efectos en los otros consumidores.
- La publicación diferida no implica hilos ni ejecución automática: el llamador debe invocar el despacho. Los fallos de consumidores no se reintentan; los avisos despachados salen de la cola.
- Toda la información vive en las instancias y se pierde al descartarlas. Los registros de bitácora y mensajes conservan cada recepción; no se define deduplicación para ellos.

# Arrendamientos

Módulo para el área jurídica que valida y registra el ciclo de vida de los contratos. No incluye cobros, firmas, autorización de usuarios, base de datos ni gestión de archivos del sistema existente.

Requiere Python 3.11. La implementación usa únicamente la biblioteca estándar; las pruebas usan pytest. No necesita red.

## Uso del servicio

Con `src/` en la ruta de importación:

```python
from datetime import date
from arrendamientos import (
    Contrato,
    Estado,
    RechazoContrato,
    RepositorioEnMemoria,
    ServicioContratos,
)

servicio = ServicioContratos(RepositorioEnMemoria())
servicio.registrar(Contrato(
    codigo="CON-1",
    codigo_inmueble="INM-100",
    documento_arrendatario="12345678",
    canon_mensual=1_200_000,
    fecha_inicio=date(2026, 1, 1),
    fecha_fin=date(2026, 12, 31),
))

try:
    vigente = servicio.cambiar_estado("CON-1", Estado.VIGENTE, "juridica-ana")
    terminado = servicio.cambiar_estado(
        "CON-1",
        Estado.TERMINADO,
        "juridica-ana",
        motivo="Terminación por mutuo acuerdo",
        fecha_terminacion=date(2026, 9, 30),
    )
    print(terminado.estado.value)
    print(terminado.historial)
except RechazoContrato as rechazo:
    print(str(rechazo))
```

Para anular un borrador: `servicio.cambiar_estado(codigo, Estado.ANULADO, usuario)`.
Para consultar: `servicio.obtener(codigo)`.

## Entradas

- `Contrato`: códigos de contrato e inmueble obligatorios, como texto no vacío. El código de contrato es único en el repositorio.
- `documento_arrendatario`: texto; puede faltar en borrador, pero debe ser no vacío al activar.
- `canon_mensual`: `int` en pesos, sin decimales. Puede faltar, ser cero o negativo en borrador; al activar debe ser mayor que cero. No se aceptan flotantes, cadenas ni booleanos como canon.
- `fecha_inicio`, `fecha_fin`: objetos `datetime.date`, opcionales en borrador y obligatorios al activar. No se aceptan cadenas ni objetos `datetime.datetime` como fechas de periodo.
- `nuevo_estado`: miembro de `Estado`, no una cadena libre.
- `usuario`: texto no vacío para cualquier cambio. El módulo registra el identificador recibido; no autentica ni comprueba pertenencia al área jurídica.
- Para terminar: `motivo` no vacío y `fecha_terminacion` de tipo `date`, dentro del periodo.
- `ServicioContratos` admite un `reloj: Callable[[], datetime]` para pruebas. Por defecto registra fecha y hora en UTC. Un reloj inyectado debe devolver `datetime`; se conserva su zona horaria tal como se recibe.

No se modifican ni normalizan los códigos, documentos o usuarios. Se consideran vacíos los textos que solo contienen espacios; la identidad de códigos se compara exactamente, incluyendo mayúsculas y espacios.

## Salidas y errores

Una operación correcta devuelve el `Contrato` inmutable resultante, también guardado en el repositorio. Cada transición añade un `CambioEstado` inmutable con estado anterior, nuevo estado, momento y usuario. La terminación añade además su motivo y fecha efectiva tanto al contrato como al registro.

Un rechazo lanza `RechazoContrato`, cuya conversión a texto proporciona el motivo. El servicio no escribe cambios ni añade auditoría ante un rechazo. No se registran los intentos fallidos, porque no son cambios de estado.

Ejemplos de motivos:

- `El inmueble ya tiene un contrato vigente en ese periodo`
- `Transición no permitida: estado actual terminado; estado solicitado vigente`
- `Para activar el canon mensual debe ser mayor que cero`
- `La duración mínima del contrato es de seis meses`
- `Para terminar se requiere un motivo`
- `La fecha de terminación debe estar dentro del periodo del contrato`
- `No existe el contrato CON-X`
- `Ya existe el contrato CON-1`

También se rechazan identificadores vacíos y tipos incompatibles en los datos del contrato. Si concurren varios errores, se devuelve el primero: transición, usuario y momento; después los requisitos de la operación. En activación se comprueban arrendatario, canon, periodo y solapamientos, en ese orden.

## Reglas y decisiones sobre lo no definido

1. Solo se permiten `borrador → vigente`, `vigente → terminado` y `borrador → anulado`. Incluso solicitar el mismo estado es una transición no permitida. Terminado y anulado son definitivos.
2. Los periodos incluyen ambos extremos. Compartir una fecha de frontera constituye un cruce. Un contrato que termina el 2026-12-31 permite otro que comience el 2027-01-01, pero no otro que comience el 2026-12-31.
3. Seis meses significa **seis meses calendario**: la fecha de fin debe alcanzar la fecha de inicio más seis meses. Si el día no existe en el mes de destino, se usa su último día. Así, 2026-01-01 a 2026-07-01 alcanza el mínimo; a 2026-06-30 no. 2026-08-31 a 2027-02-28 también lo alcanza. Esta interpretación se eligió porque no se definió cómo contar los meses ni cómo aplicar el conteo inclusivo al mínimo.
4. La fecha efectiva de terminación admite el inicio y el fin del periodo. No se exige que coincida con la fecha del registro ni con el día actual.
5. La terminación no modifica las fechas originales del periodo. Solo los contratos cuyo estado actual es vigente bloquean nuevas activaciones. No se reconstruyen derechos históricos ni se añade una regla de solapamiento entre contratos terminados.
6. La creación produce un borrador sin historial: no es una transición. El registro del servicio no permite importar contratos ya vigentes ni con historial. Los adaptadores de almacenamiento pueden rehidratar contratos previamente guardados, conservando su estado e historial.
7. Un borrador puede anularse aunque le falten los datos requeridos para activar. No se exige motivo para anular. Los argumentos de terminación se ignoran en otras transiciones.
8. No se implementa edición de borradores porque no se pidió un flujo de edición. Puede construirse el borrador completo antes de registrarlo. No se inventan formatos para documentos, códigos ni un canon máximo.

## Reglas sin infraestructura

`arrendamientos.cambiar_estado` es la función de dominio. No accede a almacenamiento ni al reloj y no modifica sus entradas:

```python
from datetime import datetime, timezone
from arrendamientos import Estado, cambiar_estado

nuevo = cambiar_estado(
    borrador,
    Estado.VIGENTE,
    "juridica-ana",
    datetime(2026, 1, 1, tzinfo=timezone.utc),
    contratos=contratos_existentes,
)
```

El llamador debe aportar una vista completa de los contratos potencialmente competidores. La función filtra por inmueble y estado vigente, excluyendo el propio código. Un competidor vigente del mismo inmueble con fechas ausentes provoca rechazo, no se ignora silenciosamente.

La función pura no puede prevenir que un llamador omita contratos ni coordinar escrituras externas. Para operar con almacenamiento debe utilizarse el servicio y cumplir el contrato de atomicidad del repositorio.

## Cambio de almacenamiento

La separación es:

- `dominio.py`: datos y reglas puras.
- `servicio.py`: coordinación con el reloj y el puerto.
- `repositorio.py`: `RepositorioContratos` y adaptador de referencia en memoria.

El almacenamiento actual de archivos y la futura base de datos se integran implementando `RepositorioContratos`; las reglas no se cambian. No se entrega un formato de archivo ni un adaptador concreto de archivos porque no se conoce el formato del sistema existente.

El puerto exige:

- `agregar`: insertar únicamente borradores nuevos sin historial, rechazando duplicados sin sobrescribir.
- `obtener`: devolver una instantánea inmutable o `RechazoContrato` si no existe.
- `actualizar`: leer el contrato y una vista completa y consistente de sus competidores, ejecutar la función proporcionada y guardar su resultado **en una sola operación atómica**. Si la función falla, no escribir.

No basta con hacer una consulta y luego una escritura independientes: dos activaciones podrían pasar la validación simultáneamente. El adaptador de archivos deberá mantener un bloqueo compartido por todos sus escritores durante toda la operación y garantizar escritura atómica. El futuro adaptador de base de datos deberá proporcionar aislamiento o bloqueo equivalente para las activaciones del mismo inmueble, incluyendo contratos todavía no vigentes. Un bloqueo solo sobre el contrato solicitado no basta.

`RepositorioEnMemoria` serializa las operaciones mediante un bloqueo. Protege hilos y servicios que comparten **la misma instancia**, no procesos, instancias separadas ni archivos externos. Sus datos desaparecen al finalizar el proceso.

Los adaptadores y sus funciones de transformación son componentes de confianza: las transiciones deben pasar por el servicio. No se deben escribir estados directamente ni ejecutar transformaciones arbitrarias desde código cliente. Dentro de una transformación no se debe volver a llamar al mismo repositorio.

## Pruebas

Desde la raíz del proyecto, con `src/` en la ruta de importación:

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas cubren las tres transiciones permitidas y todas las no permitidas; estados definitivos; campos obligatorios; tipos monetarios y fechas; duración mínima y meses de distinta longitud; motivo y fecha efectiva de terminación; auditoría; ambos ejemplos del cliente; intersecciones y periodos separados; otros inmuebles y estados; rechazos sin cambios; errores de almacenamiento y dos activaciones competidoras entre hilos. Las reglas se prueban directamente sin base de datos, archivos ni servicios externos.

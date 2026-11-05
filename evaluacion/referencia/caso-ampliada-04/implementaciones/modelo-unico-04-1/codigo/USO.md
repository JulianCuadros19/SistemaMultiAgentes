# Control de contratos de arrendamiento

Módulo Python 3.11 para jurídica. No requiere base de datos, red ni dependencias de ejecución externas. Las reglas usan un puerto de almacenamiento reemplazable; se incluye un adaptador en memoria como herramienta técnica para ejecutar y probar el módulo, no como requisito de almacenamiento confirmado por el cliente.

## Uso

Con `src/` en la ruta de importación:

```python
from datetime import date
from arrendamientos import RepositorioMemoria, ServicioContratos

repositorio = RepositorioMemoria()
servicio = ServicioContratos(repositorio)

resultado = servicio.crear_borrador(
    codigo="C-100",
    inmueble="INM-100",
    canon=1_000_000,
    inicio=date(2026, 1, 1),
    fin=date(2026, 12, 31),
    usuario="juridica",
    identificacion_arrendatario="AR-100",
    documento_arrendatario="DOC-100",
)
if resultado.aceptado:
    resultado = servicio.activar("C-100", "juridica")

if resultado.aceptado:
    print(resultado.contrato.estado.value)
else:
    print(resultado.motivo)

resultado = servicio.terminar(
    "C-100", "juridica", "Mutuo acuerdo", date(2026, 10, 15)
)
```

Para anular un borrador: `servicio.anular(codigo, usuario)`.

Un documento ausente puede completarse mediante `activar(codigo, usuario, documento_arrendatario="DOC")`. También se admite `identificacion_arrendatario="AR"`. Ambos argumentos son opcionales: `None` conserva el valor existente. Los datos aportados solo se guardan si la activación completa tiene éxito.

## Reglas confirmadas

- Se crea en BORRADOR, se activa a VIGENTE, se termina un VIGENTE a TERMINADO y se anula exclusivamente un BORRADOR a ANULADO. No hay otras transiciones ni reapertura.
- La activación exige identificación del arrendatario y documento, canon mayor que cero, fin posterior al inicio y al menos seis meses.
- Se rechaza la activación si se solapa con otro VIGENTE del mismo inmueble. Borradores, terminados y anulados no bloquean.
- La terminación exige motivo y fecha dentro del periodo contractual. Se guardan ambos datos sin modificar las fechas originales de inicio y fin.
- Cada gestión exitosa, incluida la creación, registra fecha de gestión y usuario. La fecha de terminación es distinta de la fecha de auditoría.
- Los códigos de contrato son únicos, incluso si el contrato anterior fue terminado o anulado.
- Las gestiones rechazadas no guardan cambios, no añaden auditoría y devuelven el motivo.

## Decisiones técnicas para puntos no definidos

Estas decisiones permiten ejecutar el módulo; **no son reglas aprobadas por el cliente**:

1. Códigos de contrato e inmueble, usuario, identificación y documento se representan con texto. Los códigos y el usuario no pueden estar vacíos ni contener solo espacios. Identificación y documento se comprueban como texto no vacío al activar; la identificación es un valor separado del documento, no se interpreta como un nombre. No se validan documentos contra autoridades externas.
2. No se normalizan códigos: son sensibles a mayúsculas y espacios y se conservan tal como llegan. No se imponen longitudes máximas ni catálogos no solicitados.
3. El canon es un `int` de Python; no admite decimales, cadenas, `float` ni booleanos. No se impone máximo. Un canon cero o negativo puede estar en borrador, pero impide activarlo.
4. Las fechas son objetos `datetime.date`, no cadenas ni `datetime.datetime`. Su intervalo es el de Python: años 1 a 9999. Si se parte de ISO, convertir previamente con `date.fromisoformat("2026-01-01")`; los errores de esa conversión pertenecen al llamador.
5. Los seis meses se cuentan como meses de calendario: se suma seis al mes de inicio y, si el día no existe, se usa el último día del mes destino. El mínimo es inclusivo. Ejemplos: 2026-01-01 → 2026-07-01; 2026-08-31 → 2027-02-28. Si el mínimo rebasa el año 9999, se rechaza por duración insuficiente.
6. Para detectar cruce se usan periodos semiabiertos `[inicio, fin)`: hay solapamiento si `inicio_a < fin_b` y `inicio_b < fin_a`. Por ello se permite empezar exactamente el día en que termina otro contrato. Esto no fue definido por el cliente.
7. Para terminar, se admite la fecha en cualquiera de los extremos: `inicio <= fecha_terminacion <= fin`. Esta elección es independiente del criterio de cruce y tampoco fue definida por el cliente.
8. Como no se definió cómo aportar o corregir el arrendatario, ambos datos pueden faltar en el borrador y se pueden aportar o sustituir al activar. No existe edición general de borradores. Canon, inmueble y fechas no se editan mediante el servicio.
9. La creación valida presencia y tipos de los datos estructurales; positividad del canon, orden de fechas y duración se verifican al activar. Se admite que el borrador tenga esos valores pendientes de corrección, aunque la edición general no forma parte de esta entrega.
10. El reloj de auditoría predeterminado es UTC y registra fecha y hora. Se puede inyectar un `Callable[[], datetime]` para pruebas; ese reloj debe devolver instantes de auditoría válidos, preferiblemente con zona horaria.
11. No hay activación o terminación automática por el paso del tiempo. VIGENTE es un estado explícito, no una comparación con la fecha actual.
12. Los mensajes distintos del cruce y la obligación de indicar el estado son elecciones de esta implementación. Se devuelve el primer rechazo, no una lista acumulada. En transiciones se comprueba primero existencia y estado.

## Entradas y salidas

`crear_borrador(codigo, inmueble, canon, inicio, fin, usuario, identificacion_arrendatario=None, documento_arrendatario=None)` recibe los datos descritos arriba.

`activar(codigo, usuario, identificacion_arrendatario=None, documento_arrendatario=None)`, `terminar(codigo, usuario, motivo, fecha_terminacion)` y `anular(codigo, usuario)` devuelven `Resultado`:

- Éxito: `aceptado == True`, `contrato` contiene el contrato actualizado y `motivo is None`.
- Rechazo: `aceptado == False`, `contrato is None` y `motivo` contiene la explicación.

El contrato incluye códigos, canon, fechas, los dos datos del arrendatario, estado, datos de terminación e historial. No se exige al consumidor mostrar el historial; se incluye para evitar un segundo modelo de respuesta innecesario. Contrato, cambios e historial son inmutables, de modo que el llamador no puede alterar el almacenamiento accidentalmente.

## Errores

Mensajes principales:

| Situación | Motivo |
| --- | --- |
| Cruce | `El inmueble ya tiene un contrato vigente en ese periodo` |
| Acción incompatible | `La gestión no corresponde al estado actual: <ESTADO>` |
| Código duplicado | `Ya existe un contrato con el código: <codigo>` |
| Contrato inexistente | `No existe el contrato: <codigo>` |
| Falta identificación | `La identificación del arrendatario es obligatorio` |
| Falta documento | `El documento del arrendatario es obligatorio` |
| Canon no entero | `El canon debe ser un número entero de pesos` |
| Canon no positivo | `El canon debe ser mayor que cero` |
| Fin no posterior | `La fecha de fin debe ser posterior a la de inicio` |
| Duración insuficiente | `La duración debe ser de al menos seis meses` |
| Falta motivo | `El motivo de terminación es obligatorio` |
| Terminación fuera de periodo | `La fecha de terminación debe estar dentro del periodo del contrato` |

Las entradas de texto obligatorias inválidas producen `<etiqueta> es obligatorio`. Los datos opcionales con tipo incorrecto producen `<etiqueta> debe ser texto o None`. Las fechas con tipo incorrecto producen `<etiqueta> debe ser una fecha de calendario`.

Los fallos de programación, reloj o almacenamiento no se convierten en rechazos de negocio: se propagan. Los argumentos obligatorios omitidos en una llamada Python provocan el `TypeError` habitual.

## Sustituir el almacenamiento

Implementar el protocolo `Repositorio`:

- `obtener(codigo)`: devolver `Contrato` o `None`.
- `vigentes(inmueble)`: devolver todos los contratos VIGENTES del inmueble, sin omitir periodos.
- `guardar(contrato)`: insertar o reemplazar el contrato completo con su historial.

Después, pasar ese adaptador a `ServicioContratos`. El servicio no conoce SQL ni archivos. El adaptador debe guardar cada contrato de forma íntegra y entregar objetos que respeten el modelo. `guardar` es un puerto de persistencia, no una API de negocio: las gestiones deben realizarse por el servicio. El adaptador en memoria pierde los datos al destruirse.

No se implementa control concurrente: la consulta de cruces y el guardado no forman una transacción común. Dos activaciones simultáneas podrían competir. Antes de uso concurrente en producción debe definirse y añadir coordinación transaccional o bloqueo apropiado; la entrega no garantiza exclusión entre procesos o hilos.

Fuera del alcance: base de datos real, API HTTP, interfaz gráfica, autenticación del usuario, edición general, nombres de arrendatarios, pagos, prorrateos y renovaciones automáticas.

## Pruebas

Desde la raíz, con pytest instalado:

```sh
PYTHONPATH=src python -m pytest tests
```

Las pruebas no requieren red ni base de datos. Cubren las transiciones válidas e inválidas, auditoría, datos incompletos y mal tipados, duración, canon, solapamientos y límites, terminación, códigos duplicados e inexistentes, inmutabilidad, un almacenamiento alternativo y los dos ejemplos del cliente para INM-100: aceptación del periodo 2027 con canon de $1.200.000 y rechazo del periodo 2026-06-01 a 2027-05-31 frente al vigente de 2026 con canon de $1.000.000.

# Ciclo de vida de contratos

Gestiona la activación, terminación y transición de estados de contratos de arrendamiento mediante un repositorio en memoria.

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

No requiere archivos de datos ni variables de entorno. Prepare una instancia del repositorio y registre los contratos iniciales. Los valores monetarios deben ser `Decimal`, creados desde texto o enteros.

## Ejecución

No tiene un punto de entrada de terminal. Desde la raíz del código, puede abrir el intérprete con `PYTHONPATH=src python` y ejecutar:

```python
from datetime import date
from decimal import Decimal

from adaptadores.salida.repositorios_memoria import RepositorioContratosMemoria
from aplicacion.contratos import activar_contrato
from dominio.contratos import Contrato

repo = RepositorioContratosMemoria()
contrato = Contrato(
    "C-100", "INM-100", date(2026, 1, 1), date(2026, 12, 31),
    "DOC-1", Decimal("1200000"), "borrador",
)
repo.registrar(contrato)
resultado = activar_contrato(
    contrato.codigo, contrato.inmueble, contrato.fecha_inicio, contrato.fecha_fin,
    contrato.documento_arrendatario, contrato.canon_mensual, "operador", repo,
)
print(resultado.contrato.estado)
```

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

Los ejemplos siguientes continúan con los objetos del ejemplo anterior.

### Entidades y puerto

- `Contrato(codigo, inmueble, fecha_inicio, fecha_fin, documento_arrendatario, canon_mensual, estado)`: registro inmutable. Ejemplo: `Contrato("C-2", "INM-2", date(2026, 1, 1), date(2026, 12, 31), None, Decimal("900000"), "borrador")`.
- `CambioEstado(fecha_cambio, usuario, contrato)`: resultado inmutable. Ejemplo: `CambioEstado(date.today(), "operador", resultado.contrato)`, importándolo de `dominio.contratos`.
- `RepositorioContratos()`: puerto abstracto, no se instancia directamente. Ejemplo de referencia tipada: `repositorio: RepositorioContratos = repo`, importando el puerto de `dominio.contratos`.
- `RepositorioContratos.registrar(contrato)`: prepara un registro. Ejemplo: `repositorio.registrar(contrato)`.
- `RepositorioContratos.consultar_por_codigo(codigo)`: obtiene un registro. Ejemplo: `repositorio.consultar_por_codigo("C-100")`.
- `RepositorioContratos.existe_vigencia_en_inmueble(inmueble, desde, hasta)`: consulta intersecciones. Ejemplo: `repositorio.existe_vigencia_en_inmueble("INM-100", date(2026, 1, 1), date(2026, 12, 31))`.
- `RepositorioContratos.actualizar(contrato)`: persiste un registro existente. Ejemplo: `repositorio.actualizar(resultado.contrato)`.

### Repositorio en memoria

- `RepositorioContratosMemoria()`: crea un almacén vacío. Ejemplo: `otro_repo = RepositorioContratosMemoria()`.
- `RepositorioContratosMemoria.registrar(contrato)`: registra por código. Ejemplo: `otro_repo.registrar(contrato)`.
- `RepositorioContratosMemoria.consultar_por_codigo(codigo)`: consulta por código. Ejemplo: `otro_repo.consultar_por_codigo("C-100")`.
- `RepositorioContratosMemoria.existe_vigencia_en_inmueble(inmueble, desde, hasta)`: comprueba cruces de contratos vigentes. Ejemplo: `repo.existe_vigencia_en_inmueble("INM-100", date(2026, 1, 1), date(2026, 12, 31))`.
- `RepositorioContratosMemoria.actualizar(contrato)`: reemplaza un contrato existente. Ejemplo: `otro_repo.actualizar(resultado.contrato)`.

### Operaciones

Importe las funciones de `aplicacion.contratos`.

- `activar_contrato(codigo, inmueble, fecha_inicio, fecha_fin, documento_arrendatario, canon_mensual, usuario, repo)`: el ejemplo completo aparece en Ejecución. Solo activa un borrador y persiste los datos suministrados tras validarlos.
- `terminar_contrato(codigo, motivo, fecha_terminacion, usuario, repo)`: ejemplo: `terminar_contrato("C-100", "vencimiento", date(2026, 8, 15), "operador", repo)`.
- `cambiar_estado(codigo, nuevo_estado, usuario, repo)`: ejemplo: `cambiar_estado("C-100", "terminado", "operador", repo)` cuando el contrato está vigente. Esta operación valida únicamente las transiciones de RF-03, no las condiciones específicas de activar o terminar.

### Excepciones de negocio

Todas se importan de `dominio.contratos`, se construyen sin argumentos y derivan de `ValueError`:

- `DocumentoArrendatarioObligatorio()`: falta el documento para activar.
- `CanonInvalido()`: canon no finito, no positivo o con parte fraccionaria.
- `FechasInvalidas()`: periodo incorrecto o inferior a seis meses.
- `CruceDeVigencias()`: existe otra vigencia en el inmueble y periodo.
- `TransicionNoPermitida()`: transición inválida o falta un identificador obligatorio.
- `EstadoNoModificable()`: contrato terminado o anulado.
- `MotivoObligatorio()`: falta el motivo de terminación.
- `FechaTerminacionFueraDePeriodo()`: terminación fuera del periodo contractual.

Ejemplo de manejo:

```python
from aplicacion.contratos import cambiar_estado
from dominio.contratos import EstadoNoModificable, TransicionNoPermitida

try:
    cambiar_estado("C-100", "borrador", "operador", repo)
except (EstadoNoModificable, TransicionNoPermitida) as error:
    print(str(error))
```

## Supuestos

- Las entidades son registros inmutables sin validaciones de negocio en su constructor: permiten preparar borradores incompletos. Los casos de uso validan las restricciones correspondientes antes de persistir cambios. El repositorio recibe registros tipados; los estados normales son `borrador`, `vigente`, `terminado` y `anulado`.
- Seis meses significa seis meses calendario. Si el día no existe en el mes de destino, se usa su último día. El aniversario exacto cumple el mínimo.
- Los periodos son cerrados: compartir una fecha extrema constituye cruce y las fechas extremas son válidas para terminar.
- La fecha del cambio es la fecha local actual obtenida con `date.today()`, también al terminar. La fecha de terminación se valida, pero no sustituye el fin contractual. El modelo no declara campos para guardar el motivo ni la fecha efectiva de terminación.
- Los textos obligatorios rechazan cadenas vacías o formadas solo por espacios. Se conserva el texto original de los datos válidos.
- Como no se declara una excepción específica para código, usuario o inmueble ausentes, las operaciones los rechazan mediante `TransicionNoPermitida` con un mensaje explicativo.
- Se acepta `Decimal("1.00")` como un peso entero: se valida la ausencia de parte fraccionaria, no el número de dígitos escritos.
- La activación toma los datos suministrados como los datos que se deben persistir; no se exige que coincidan con los del borrador inicial.
- Las operaciones suponen un código previamente registrado. El repositorio lanza `KeyError` si se consulta o actualiza un código inexistente. Registrar de nuevo el mismo código reemplaza sus datos.
- Cada repositorio empieza vacío. No hay persistencia fuera de la instancia ni coordinación de operaciones concurrentes.

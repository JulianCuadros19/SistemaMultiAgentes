# Organización de escaneos

Operaciones independientes para revisar carpetas, validar nombres, normalizar archivos y generar reportes de expedientes.

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

Prepare una carpeta local de escaneos y permisos de lectura. El renombrado efectivo requiere permisos para modificar sus nombres. No requiere variables de entorno ni archivos de configuración.

La convención es `TIPO_AAAA_NNNNN.pdf`: tipos `ESC`, `CER` o `PAZ`, año desde 1950 hasta el actual y consecutivo entre `00000` y `99999`.

## Ejecución

Desde la raíz del código:

```sh
PYTHONPATH=src python -m comandos.revisar /archivos/escaneos/expedientes
PYTHONPATH=src python -m comandos.validar /archivos/escaneos/expedientes
PYTHONPATH=src python -m comandos.renombrar /archivos/escaneos/expedientes --simulacion
PYTHONPATH=src python -m comandos.renombrar /archivos/escaneos/expedientes
PYTHONPATH=src python -m comandos.reporte /archivos/escaneos/expedientes
```

Cada comando puede ejecutarse de forma independiente desde una tarea programada. Una carpeta inexistente produce un mensaje en la salida de errores y código de salida 1. Una operación completada devuelve código 0; los incumplimientos y conflictos aparecen en sus resultados.

El renombrado sin `--simulacion` modifica los nombres. Por ejemplo, `esc-2019-42.PDF` pasa a `ESC_2019_00042.pdf`. Si el destino ya existe, se conserva el original y se muestra `Conflicto`.

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

### Comandos

```python
from comandos.revisar import ejecutar_revisar
from comandos.validar import ejecutar_validar
from comandos.renombrar import ejecutar_renombrar
from comandos.reporte import ejecutar_reporte

ruta = '/archivos/escaneos/expedientes'
archivos = ejecutar_revisar(ruta)
incumplimientos, totales_por_motivo = ejecutar_validar(ruta)
cambios, conflictos, errores = ejecutar_renombrar(ruta, True)
reporte = ejecutar_reporte(ruta)
```

### Servicios

Los servicios reciben el gestor por parámetro:

```python
from entrada_salida.archivos import GestorArchivos
from servicios.revision import revisar_carpeta
from servicios.validacion import validar_nombres
from servicios.renombrado import renombrar_archivos
from servicios.reporte import generar_reporte

gestor = GestorArchivos()
archivos = revisar_carpeta(ruta, gestor)
incumplimientos, totales = validar_nombres(ruta, gestor)
cambios, conflictos, errores = renombrar_archivos(ruta, True, gestor)
reporte = generar_reporte(ruta, gestor)
```

### Gestor de archivos

```python
gestor = GestorArchivos()
gestor.crear_carpeta('/tmp/expedientes')
gestor.crear_archivo('/tmp/expedientes', 'esc-2019-42.PDF', b'documento')
existe = gestor.existe_carpeta('/tmp/expedientes')
nombres = gestor.listar_archivos('/tmp/expedientes')
gestor.renombrar('/tmp/expedientes', 'esc-2019-42.PDF', 'ESC_2019_00042.pdf')
```

`crear_archivo` recibe `None` para crear un archivo vacío. Los nombres recibidos no pueden contener componentes de ruta. `renombrar` rechaza destinos existentes con `FileExistsError`.

### Convención y modelos

```python
from dominio.convencion import (
    EstructuraNombre, ResultadoValidacion, CambioNombre,
    ConflictoRenombrado, ErrorRenombrado, Reporte,
    analizar_nombre, normalizar_nombre,
)

estructura = analizar_nombre('ESC_2019_00042.pdf', None)
normalizado = normalizar_nombre('esc-2019-42.PDF')
estructura = EstructuraNombre('ESC', 2019, 42, 'pdf')
incumplimiento = ResultadoValidacion('incorrecto.pdf', 'Formato incorrecto')
cambio = CambioNombre('esc-2019-42.PDF', 'ESC_2019_00042.pdf')
conflicto = ConflictoRenombrado('esc-2019-42.PDF', 'Conflicto')
error = ErrorRenombrado('XYZ_2019_00001.pdf', 'Tipo desconocido')
reporte = Reporte(['ESC_2019_00042.pdf'], {2019: {'ESC': 1}}, 1)
```

El segundo argumento de `analizar_nombre` permite establecer un límite de año explícito. `None` usa el calendario local.

Las excepciones públicas admiten un mensaje:

```python
from dominio.convencion import (
    FormatoInvalido, TipoDesconocido, AnioFueraDeRango,
    ExtensionInvalida, CarpetaNoExiste,
)

formato = FormatoInvalido('Formato incorrecto')
tipo = TipoDesconocido('Tipo desconocido')
anio = AnioFueraDeRango('Año fuera de rango')
extension = ExtensionInvalida('Extensión distinta de pdf')
carpeta = CarpetaNoExiste('La carpeta no existe')
```

Los comandos y servicios propagan la excepción `CarpetaNoExiste` expuesta por su respectivo módulo. La validación y el renombrado convierten los errores de nombres en elementos de sus resultados.

## Supuestos

- El acceso físico a archivos queda exclusivamente en `entrada_salida.archivos`; los servicios operan mediante el gestor recibido.
- `dominio.convencion.CarpetaNoExiste` es una clase derivada de `FileNotFoundError`. El gestor y la revisión exponen `FileNotFoundError` con el alias `CarpetaNoExiste`, porque sus dependencias permitidas no incluyen el dominio. Para capturar la excepción concreta, impórtela del módulo que invoca; `FileNotFoundError` permite capturar ambos casos.
- El listado no es recursivo y se ordena alfabéticamente. Las subcarpetas no se cuentan como archivos.
- Se admiten guiones, guiones bajos y espacios simples como separadores corregibles. Solo las extensiones `pdf` y `PDF` son normalizables; no se cambia una extensión de otro formato.
- Si varias propuestas producen el mismo destino, solo la primera queda disponible y las siguientes se reportan como conflictos, también en simulación.
- Los nombres inválidos aparecen como líneas de error en el reporte, pero no contribuyen a los conteos por año y tipo. El total es la suma de esos conteos.
- Los motivos de validación se agrupan por su texto; cada archivo aporta su primer incumplimiento detectado. Para `esc-2019-42.PDF`, la validación estricta informa que no cumple la convención porque los separadores deben ser guiones bajos, antes de comprobar la extensión. El renombrado sí admite corregir sus separadores y `.PDF`.
- No se declara una interfaz para configurar, disparar u observar un planificador del sistema operativo. RF-01 ESC-02 no queda demostrado íntegramente: la prueba parcial comprueba únicamente que la revisión invocable devuelve los archivos de la carpeta indicada. No demuestra que una tarea nocturna la dispare sin intervención manual. No se simula un planificador ni se añade una interfaz de programación de tareas. La programación debe realizarla quien instala la herramienta, y su verificación requiere una integración de planificador que no está disponible en estas interfaces.
- Las pruebas usan carpetas temporales en lugar de la ruta ilustrativa `/archivos/escaneos/expedientes`. Para revisión y reporte, ejercitan los puntos de entrada de terminal mediante `runpy`, con argumentos de terminal, y observan la salida emitida y `SystemExit`; no crean un proceso de terminal externo.
- Se presupone que no hay modificaciones concurrentes de la carpeta durante una operación.

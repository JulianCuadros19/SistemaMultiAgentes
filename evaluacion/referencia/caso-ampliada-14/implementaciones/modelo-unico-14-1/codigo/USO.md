# Herramienta de nombres de expedientes

## Qué hace

Revisa los nombres de los archivos de una carpeta, propone o aplica las únicas correcciones permitidas y genera cantidades por año y por tipo. No abre ni valida el contenido de los documentos: un archivo puede tener cualquier contenido y aun así tener un nombre correcto.

Convención: `TIPO_AAAA_NNNNN.pdf`.

- Tipo: `ESC`, `CER` o `PAZ`.
- Año: cuatro dígitos, entre 1950 y el año actual del equipo, inclusive.
- Consecutivo: cinco dígitos.
- Extensión: `.pdf` en minúsculas.

Las únicas correcciones son poner el tipo en mayúsculas, sustituir guiones por guiones bajos, completar por la izquierda el consecutivo con ceros y convertir la extensión PDF a minúsculas. Por ejemplo, `esc-2019-42.PDF` pasa a `ESC_2019_00042.pdf`. `XYZ_2019_00001.pdf` produce un error sin cambio.

## Ejecución

Requiere Python 3.11. No necesita paquetes externos ni conexión de red. Desde el directorio de la entrega, añada `src` a la ruta de importación:

```sh
export PYTHONPATH="$PWD/src"
python -m expedientes validar /ruta/escaneos
python -m expedientes renombrar /ruta/escaneos --simular
python -m expedientes renombrar /ruta/escaneos
python -m expedientes reportar /ruta/escaneos
python -m expedientes --help
python -m pytest tests
```

En PowerShell, la asignación equivalente es `$env:PYTHONPATH = "$PWD/src"`. Ponga entre comillas las rutas que tengan espacios.

- `validar`: no modifica nada. Cada nombre no conforme incluye su motivo; si admite corrección, también muestra el destino propuesto.
- `renombrar --simular`: muestra los cambios posibles sin guardarlos; comprueba conflictos.
- `renombrar`: aplica las correcciones sin sobrescribir destinos.
- `reportar`: no modifica nada; muestra resultados y cantidades por año y por tipo.

## Entradas, salidas y errores

La entrada es una ruta de carpeta, un modo y, únicamente para renombrar, la opción `--simular`. Los archivos se presentan ordenados por nombre. Se incluyen todas las extensiones: las distintas de PDF se informan como error.

Cada archivo revisado produce una línea con nombre, destino cuando corresponde, estado y explicación. Los estados son `Correcto`, `No cumple`, `Cambio`, `Renombrado`, `Error` y `Conflicto`. Después aparece un resumen con el total de archivos y las cantidades de cada estado presente. El reporte añade dos líneas de cantidades: por año y por tipo. En una carpeta vacía muestra cero archivos y conteos vacíos como `0`.

Si varios nombres conducirían al mismo destino, no se cambia ninguno de los candidatos que requieren corrección. Si el destino ya existe, tampoco se cambia el candidato. El mensaje es `Conflicto`; el archivo que ya tiene un nombre correcto sigue apareciendo como `Correcto`. También bloquean el destino los directorios y los enlaces existentes. La comprobación incluye todos los candidatos antes de aplicar cambios, y la operación de escritura no reemplaza un destino que aparezca después.

Se rechazan sin corrección tipos desconocidos, años fuera de rango, extensiones distintas de PDF, consecutivos de más de cinco dígitos, letras en el consecutivo y nombres incompletos. No se recortan espacios, no se cambian otros separadores ni se acortan años o consecutivos. Se usan letras y dígitos ASCII, sin una longitud máxima adicional para el nombre.

Códigos de salida:

- `0`: no hubo errores, conflictos ni incumplimientos pendientes en validación/reporte. Los cambios previstos en simulación no son errores.
- `1`: algún archivo produjo `Error`, `Conflicto` o `No cumple`. Los demás archivos se procesan igualmente.
- `2`: carpeta inexistente, ruta que no es carpeta, fallo al leerla o argumentos incorrectos. Si la carpeta no existe se termina inmediatamente y se escribe `Error: La carpeta no existe: ...` en la salida de errores.

## Uso desde Python

```python
from expedientes import evaluar_nombre, procesar_carpeta

nombre = evaluar_nombre("esc-2019-42.PDF")
print(nombre.destino)  # ESC_2019_00042.pdf
print(nombre.motivos)

informe = procesar_carpeta("/ruta/escaneos", "renombrar", simular=True)
for resultado in informe.resultados:
    print(resultado.nombre, resultado.estado, resultado.destino, resultado.detalle)
print(informe.totales)
print(informe.codigo_salida)

reporte = procesar_carpeta("/ruta/escaneos", "reportar")
print(reporte.por_anio, reporte.por_tipo)
```

`evaluar_nombre` devuelve una `Evaluacion`: nombre original, destino o `None` si no es corregible, motivos, tipo y año cuando son válidos, y la propiedad `correcto`. `procesar_carpeta` devuelve un `Informe` con resultados y diccionarios de conteos. Fuera del modo reporte, los diccionarios por año y tipo están vacíos. La API no imprime: lanza `CarpetaError` por problemas de lectura y `ValueError` por modo u opción incompatible. Ambas funciones permiten `anio_actual=` para pruebas reproducibles; en la terminal siempre se usa el año local del equipo.

## Decisiones para puntos que quedaron sin definir

Estas decisiones son de implementación, no reglas confirmadas por el cliente:

1. Se revisan solo los archivos regulares directamente dentro de la carpeta; no se recorren subcarpetas ni se procesan enlaces simbólicos.
2. Se admite `00000`, pues cumple los cinco dígitos. Un consecutivo más corto, incluido `0`, se completa con ceros.
3. Si no se puede leer la carpeta, se termina con mensaje y código `2` sin empezar a renombrar.
4. Si falla un renombrado, se informa el error, se continúa con los restantes y se devuelve código `1`.
5. El reporte cuenta únicamente nombres que ya cumplen exactamente la convención. No cuenta propuestas, aunque sean corregibles. Los errores e incumplimientos mantienen su línea y figuran en el resumen; no se evalúan conflictos en validar o reportar porque esos modos no intentan renombrar. Se muestran únicamente años y tipos presentes.
6. El desglose de estados y los códigos de salida distintos del requisito de carpeta inexistente son los descritos arriba.

## Seguridad operativa y límites

El cambio utiliza la creación exclusiva de un enlace duro al mismo archivo y después elimina el nombre original. Así no copia ni cambia el contenido y nunca sobrescribe un destino. Requiere un sistema de archivos que permita enlaces duros; si no los permite, el archivo se informa como error y conserva su nombre original. Si falla quitar el nombre original, se intenta eliminar el enlace creado. Si también falla esa limpieza, podrían quedar ambos nombres: el resultado se informa como error y debe revisarse manualmente.

No hay transacción global, copia de seguridad, reversión de cambios ya aplicados ni archivo de reporte persistente. Evite modificaciones concurrentes de la carpeta durante una ejecución; la simulación refleja el estado observado, no reserva los destinos. No se analiza el contenido PDF, ni se buscan consecutivos únicos fuera de los conflictos de nombre descritos.

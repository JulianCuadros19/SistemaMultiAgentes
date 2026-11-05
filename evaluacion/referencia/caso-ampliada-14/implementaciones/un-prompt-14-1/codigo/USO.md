# Herramienta de escaneos

Valida, corrige y cuenta nombres de archivos conforme a `TIPO_AAAA_NNNNN.pdf`.
Funciona sin red, con Python 3.11 y la biblioteca estándar. Las pruebas requieren
pytest, disponible en el entorno indicado.

## Ejecución desde terminal

Desde la raíz de la entrega, hacer que `src/` esté en la ruta de importación.
Por ejemplo, en una terminal POSIX:

```sh
export PYTHONPATH="$PWD/src"
python -m escaneos validar /ruta/escaneos
python -m escaneos renombrar /ruta/escaneos --simular
python -m escaneos renombrar /ruta/escaneos
python -m escaneos reporte /ruta/escaneos
```

En Windows puede configurarse `PYTHONPATH` con la ruta absoluta de `src` usando
las herramientas habituales de la terminal. Las rutas con espacios se escriben
entre comillas.

Las operaciones son independientes y no solicitan confirmaciones. Para una tarea
nocturna, configurar el ejecutable de Python, `PYTHONPATH` y la carpeta mediante
rutas absolutas; capturar stdout, stderr y el código de salida. Es recomendable
simular antes del primer renombrado y conservar los respaldos habituales.

```sh
python -m escaneos --help
python -m escaneos renombrar --help
PYTHONPATH=src python -m pytest tests
```

## Reglas

- Los tipos admitidos son `ESC`, `CER` y `PAZ`.
- El año tiene cuatro dígitos y está entre 1950 y el año de la fecha local de
  ejecución, ambos incluidos. No se fija el año en el código.
- El consecutivo tiene cinco dígitos ASCII. Se permite `00000`: no se indicó un
  mínimo numérico distinto.
- La extensión canónica es `.pdf`.
- Se corrigen letras minúsculas del tipo, guiones o espacios separadores,
  consecutivos de uno a cuatro dígitos y mayúsculas de la extensión pdf.
- `esc-2019-42.PDF` se convierte en `ESC_2019_00042.pdf`.
- `XYZ_2019_00001.pdf` permanece intacto y se informa `Tipo desconocido`.
- Años fuera del rango y extensiones distintas de pdf no se corrigen. Tampoco se
  truncan consecutivos largos ni se adivinan estructuras no reconocidas.
- Si el destino está ocupado, se conserva el original y se muestra `Conflicto`.
  También ocupan destinos los directorios y los enlaces simbólicos, incluso los
  enlaces cuyo destino no existe.

## Entradas y salidas

La CLI exige una operación y una carpeta. `--simular` pertenece exclusivamente a
`renombrar`.

Cada archivo examinado produce una línea con su nombre, estado y motivo. Los
cambios y conflictos incluyen el destino propuesto. Los nombres se representan
entre comillas, escapando caracteres de control para mantener una línea física
por archivo. Al final aparece `Resumen: Total=...` con los totales por estado.

- **validar:** informa `Válido` o `Inválido`; no modifica archivos. Los nombres
  corregibles también son inválidos hasta aplicar la corrección.
- **renombrar:** informa `Sin cambios`, `Renombrado`, `Inválido`, `Conflicto` o
  `Error`. En simulación, `Simulado` sustituye a `Renombrado` y no se escribe nada.
- **reporte:** lista todos los archivos examinados y cuenta solamente nombres
  estrictamente válidos. Los inválidos se muestran con sus motivos y quedan
  excluidos. Presenta conteos separados por año y por tipo.

Los resultados y resúmenes van a stdout. Los errores de argumentos o de acceso
a la carpeta van a stderr.

### Códigos de salida

| Código | Significado |
| --- | --- |
| 0 | Operación completada sin incidencias; incluye carpetas vacías y simulaciones exitosas. |
| 1 | Hay nombres inválidos o conflictos. Los demás archivos sí se procesan. |
| 2 | Argumentos incorrectos, carpeta inaccesible/inexistente, ruta que no es carpeta o errores de E/S al renombrar. |

Si no existe la carpeta, se muestra `Error: La carpeta no existe: ...` y no se
crea. Un error individual de renombrado no impide continuar con otros archivos.

## Uso desde Python

```python
from escaneos import inspeccionar_nombre, procesar

nombre = inspeccionar_nombre("esc-2019-42.PDF")
print(nombre.destino)  # ESC_2019_00042.pdf
print(nombre.motivos)

informe = procesar("/ruta/escaneos", "renombrar", simular=True)
for archivo in informe.archivos:
    print(archivo.nombre, archivo.estado, archivo.destino, archivo.motivo)
print(informe.total, informe.totales, informe.codigo_salida)

reporte = procesar("/ruta/escaneos", "reporte")
print(reporte.por_anio, reporte.por_tipo)
```

`inspeccionar_nombre(str)` no consulta el disco: devuelve `InspeccionNombre`, con
`nombre`, `destino`, `motivos` y la propiedad `valido`. `destino=None` significa
que el nombre no es corregible con estas reglas.

`procesar(str | Path, operacion, *, simular=False)` devuelve `Informe`. Contiene
una tupla de `ResultadoArchivo`, los conteos del reporte y las propiedades
`total`, `totales` y `codigo_salida`. Fuera de `reporte`, los conteos por año y
tipo son diccionarios vacíos. Las operaciones desconocidas y la simulación de
otras operaciones provocan `ValueError`; los errores de carpeta provocan
`OSError`, incluyendo `FileNotFoundError` y `NotADirectoryError`.

## Decisiones para aspectos no definidos

- Se examinan solo archivos regulares directamente contenidos en la carpeta,
  sin recursión. Se ignoran directorios, enlaces simbólicos y archivos especiales
  como entradas a examinar. No se filtra por extensión: los archivos no PDF
  también deben aparecer como inválidos.
- Se revisan los nombres, no el contenido interno del PDF.
- Cada separador ocupa exactamente un carácter: guion bajo, guion o espacio
  ordinario. Se permiten combinaciones; no se colapsan espacios repetidos ni se
  eliminan prefijos, sufijos o espacios exteriores.
- Se normaliza cualquier combinación de mayúsculas y minúsculas de `pdf`, y
  también las mezclas de mayúsculas y minúsculas en tipos conocidos.
- El reporte cuenta nombres estrictamente conformes, no correcciones posibles.
  Solo aparecen años y tipos con al menos un archivo válido.
- El procesamiento sigue el orden lexicográfico de los nombres originales.
  Si dos correcciones comparten destino, la primera lo ocupa y la segunda
  informa conflicto. La simulación mantiene ocupaciones virtuales para reproducir
  ese comportamiento sin modificar el disco.
- Los códigos de salida diferencian incidencias de nombres y errores operativos,
  para facilitar la ejecución programada.

## Seguridad del renombrado y límites

Para no sobrescribir un destino, incluso si aparece después de listar la carpeta,
el movimiento crea primero un enlace duro exclusivo en la misma carpeta y luego
elimina el nombre original. No copia ni modifica los bytes del escaneo. Si falla
la creación del enlace, conserva el original y reporta el error; no usa una
alternativa que pueda sobrescribir archivos.

El sistema de archivos debe permitir enlaces duros y el usuario debe tener los
permisos necesarios. Si falla la eliminación del nombre original, intenta borrar
el enlace recién creado y reporta `Error`. Si también falla esa limpieza o el
proceso se interrumpe entre ambos pasos, pueden quedar ambos nombres para el mismo
archivo: revisar el informe y la carpeta antes de repetir la operación. No hay
transacción global: los cambios anteriores a un error se conservan.

La simulación representa la instantánea inicial y los cambios planeados; no
verifica permisos de escritura ni capacidad para crear enlaces duros. Evitar que
otros procesos modifiquen los archivos durante la ejecución. No se implementa
vigilancia continua, integración con escáneres ni consulta de expedientes.

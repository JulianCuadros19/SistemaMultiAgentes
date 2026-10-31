---
id: caso-ampliada-14
titulo: Herramienta para validar y renombrar escaneos de expedientes
cliente: Archivo Documental Valle Alto (sintética)
proyecto: Organización de escaneos
necesidad: Necesitamos una herramienta que nuestro técnico ejecute desde la terminal para revisar la carpeta de escaneos de expedientes, validar que los nombres de los archivos sigan la convención y renombrar los que se puedan corregir.
version: 1.0
arquitecturas_esperadas: [ARQ-05]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la jefa de un archivo documental. Conoces la convención de nombres, pero no tienes
formación técnica.

## Lo que sabes

- Quien la usa es el técnico de archivo, desde la terminal, y también una tarea programada cada
  noche. Ningún otro sistema la consulta.
- La necesitan porque los escaneos con nombres mal escritos no se encuentran después.
- Convención de nombres: `TIPO_AAAA_NNNNN.pdf`, donde:
  - TIPO es ESC (escritura), CER (certificado) o PAZ (paz y salvo);
  - AAAA es el año, entre 1950 y el año actual;
  - NNNNN es un consecutivo de cinco dígitos.
- Operaciones, que se ejecutan por separado:
  - validar: lista los archivos que no cumplen y el motivo;
  - renombrar: corrige los que se pueden corregir. Tiene un modo de simulación que muestra los
    cambios sin hacerlos;
  - reporte: cuenta los archivos por año y por tipo.
- Lo que se corrige solo:
  - minúsculas a mayúsculas en el tipo;
  - guiones o espacios como separadores, que pasan a guion bajo;
  - consecutivos de menos de cinco dígitos, que se completan con ceros a la izquierda;
  - la extensión «.PDF», que pasa a «.pdf».
- Lo que no se corrige y se reporta: tipo desconocido, año por fuera del rango y extensión
  distinta de pdf.
- Si el nombre corregido ya existe en la carpeta, no se renombra y se reporta «Conflicto».
- Datos: la carpeta de los escaneos, obligatoria; si no existe, se termina con un mensaje claro
  y un código de salida distinto de cero.
- Lo que debe mostrar: una línea por archivo y un resumen con los totales.
- Ejemplos que usan para verificar:
  - «esc-2019-42.PDF» pasa a «ESC_2019_00042.pdf»;
  - «XYZ_2019_00001.pdf» no se corrige: tipo desconocido.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se escanean los documentos ni cómo se consultan después: no son parte de esta
herramienta. No conoces detalles técnicos del sistema.

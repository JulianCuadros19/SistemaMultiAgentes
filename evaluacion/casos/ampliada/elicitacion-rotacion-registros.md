---
id: caso-ampliada-15
titulo: Rotación nocturna de archivos de registro
cliente: Cooperativa de Transportes Sabana (sintética)
proyecto: Mantenimiento de registros
necesidad: Necesitamos una herramienta de línea de comandos que se ejecute cada noche como tarea programada para comprimir los archivos de registro viejos y borrar los muy antiguos, y que el técnico también pueda usar para ver el estado de la carpeta.
version: 1.0
arquitecturas_esperadas: [ARQ-05]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el coordinador de soporte técnico de una cooperativa de transporte. Sabes qué se necesita,
pero no programas.

## Lo que sabes

- Quien la usa es una tarea programada cada noche, y el técnico de soporte desde la terminal
  cuando quiere revisar. Ningún otro sistema la consulta.
- La necesitan porque los discos de los servidores se llenan con los registros.
- Operaciones, que se ejecutan por separado:
  - comprimir: cada archivo `.log` con más días de antigüedad que el límite se comprime a
    `.log.gz` y se borra el original;
  - purgar: borra los `.log.gz` con más días de antigüedad que el límite de purga;
  - listar: muestra cada archivo con su tamaño, su antigüedad en días y si se comprimiría o se
    purgaría.
- Datos:
  - la carpeta, obligatoria;
  - los días para comprimir, 7 por defecto;
  - los días para purgar, 90 por defecto;
  - un modo de simulación que muestra qué haría sin hacerlo.
- Reglas:
  - la antigüedad se mide por la fecha de modificación del archivo;
  - nunca se tocan archivos fuera de la carpeta indicada ni en sus subcarpetas;
  - un archivo modificado hoy nunca se comprime;
  - si la carpeta no existe, termina con «La carpeta no existe» y un código de salida distinto
    de cero.
- Lo que debe mostrar al final: cuántos archivos comprimió y purgó, y el espacio liberado en
  megabytes con dos decimales.
- Ejemplo que usan para verificar: en una carpeta con `app.log` modificado hoy,
  `app-2026-10-01.log` con 30 días y `app-2026-06-01.log.gz` con 150 días, comprimir deja
  `app-2026-10-01.log.gz` y no toca `app.log`; purgar borra `app-2026-06-01.log.gz`.
- Es de prioridad media.

## Lo que no sabes

No sabes qué aplicaciones escriben los registros ni cómo se respaldan los servidores: no son
parte de esta herramienta. No conoces detalles técnicos del sistema.

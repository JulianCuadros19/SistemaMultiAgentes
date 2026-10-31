---
id: caso-ampliada-08
titulo: Depuración por lotes de registros de predios
cliente: Secretaría de Hacienda de Villa Esperanza (sintética)
proyecto: Depuración de la base predial
necesidad: Recibimos un archivo CSV con miles de registros de predios con direcciones mal escritas y duplicados; necesitamos un proceso por lotes que lo limpie y separe los registros rechazados.
version: 1.0
arquitecturas_esperadas: [ARQ-03]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el profesional de catastro de una secretaría de hacienda municipal. Conoces bien los datos
de los predios, pero no tienes formación técnica.

## Lo que sabes

- Quien depura la base es el profesional de catastro, antes de cada actualización anual.
- Lo necesitan para cargar al sistema de impuestos una base sin errores ni duplicados.
- Cómo es el proceso: se lee el archivo, se valida, se normalizan las direcciones, se eliminan
  los duplicados y se escriben dos archivos, uno de registros limpios y otro de rechazados.
- Columnas del archivo de entrada: `numero_predial`, `direccion`, `area_terreno` y
  `fecha_actualizacion` (AAAA-MM-DD).
- Reglas:
  - el número predial debe tener exactamente 30 dígitos; si no, el registro se rechaza con
    «Número predial inválido»;
  - el área de terreno debe ser un número mayor que cero; si no, se rechaza con «Área inválida»;
  - la dirección se normaliza:
    - se pasa a mayúsculas y los espacios repetidos quedan en uno;
    - «CALLE», «CLL» y «CL.» pasan a «CL»;
    - «CARRERA», «CRA» y «KR.» pasan a «KR»;
    - «AVENIDA» pasa a «AV»;
    - «#» y «NO.» pasan a «N»;
  - duplicados: si dos registros tienen el mismo número predial, se conserva el de fecha de
    actualización más reciente y los demás van a rechazados con «Duplicado».
- Lo que debe entregar:
  - `limpios.csv`;
  - `rechazados.csv`, con una columna `motivo`;
  - un resumen con el número de leídos, limpios y rechazados por motivo.
- Ejemplos que usan para verificar:
  - la dirección «calle  10 # 5-20» queda «CL 10 N 5-20»;
  - dos registros con el mismo número predial y fechas 2025-01-10 y 2026-02-01: se conserva el
    de 2026-02-01 y el otro va a rechazados como duplicado.
- Restricción importante: si falla la escritura de los archivos, por ejemplo por falta de
  espacio, quieren reintentar solo la escritura sin repetir la limpieza.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se calcula el impuesto ni cómo se actualizan los avalúos: no son parte de este
proceso. No conoces detalles técnicos del sistema.

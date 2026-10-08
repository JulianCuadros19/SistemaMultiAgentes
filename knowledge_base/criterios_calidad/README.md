# Bases de conocimiento del sistema multiagente

Corpus curado para los agentes que requieren recuperación de contexto. Cada colección se
ingesta de forma independiente y se consulta con filtro obligatorio por colección, conforme
al requerimiento RF-29 de aislamiento por agente.

## Colecciones

| Colección | Agente | Nodo | Documentos | Segmentación |
|---|---|---|---|---|
| `elicitacion` | Elicitador | N2 | 10 | Por sección |
| `dominio_negocio` | Elicitador | N2 | 7 | Por sección |
| `arquitecturas_referencia` | Arquitecto | N7 | 11 | Por unidad conceptual |
| `criterios_calidad` | Tester | N13 | 8 (31 reglas atómicas) | Una regla por fragmento |

El agente desarrollador no aparece: opera sin recuperación, tomando su entrada de los
requerimientos aprobados y de la especificación de diseño.

## Formato de los documentos

Todos los documentos son Markdown con encabezado YAML de metadatos. El encabezado alimenta
los campos de trazabilidad exigidos por el RF-30: colección, fuente, versión y fecha.

```yaml
---
id: identificador único del documento
coleccion: nombre de la colección
titulo: título legible
fuente: origen de la información
tipo_fuente: estandar_internacional | normativa_nacional | practica_industria | elaboracion_propia
version: versión del documento
fecha: fecha de construcción
agente_consumidor: agente autorizado a consultarlo
segmentacion: estrategia de fragmentación aplicable
tags: [etiquetas]
---
```

## Estrategias de segmentación

La estrategia difiere por colección porque la naturaleza del contenido difiere:

- **Por sección** (`elicitacion`, `dominio_negocio`): fragmentos de 512 a 1024 tokens con
  solapamiento, cortando en encabezados de segundo nivel.
- **Por unidad conceptual** (`arquitecturas_referencia`): cada arquitectura o patrón es un
  fragmento completo, de modo que la recuperación devuelva la alternativa entera con sus
  criterios de aplicabilidad y sus consecuencias.
- **Una regla por fragmento** (`criterios_calidad`): la segmentación corta en el delimitador
  `### REGLA`. Esta granularidad es la que permite que el veredicto del tester sea trazable
  criterio por criterio.

## Advertencia sobre las fuentes

Los documentos derivados de normas internacionales y de normativa nacional son **resúmenes
redactados con palabras propias**. No reproducen el texto de las normas, que es material
protegido por derechos de autor. Cada documento cita su fuente para trazabilidad.

Los umbrales, plazos, porcentajes y formatos concretos del dominio catastral y tributario
deben verificarse contra la fuente vigente antes de su uso en producción, ya que la normativa
colombiana en la materia cambia con frecuencia.

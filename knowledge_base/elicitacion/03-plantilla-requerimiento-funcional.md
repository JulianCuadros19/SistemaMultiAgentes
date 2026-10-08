---
id: eli-003
titulo: Plantilla del requerimiento funcional formal
fuente: Formato del Anexo A del documento de tesis; estructura alineada a ISO/IEC/IEEE 29148
tipo_fuente: elaboracion_propia
tags: [requerimiento, plantilla, anexo_a]
coleccion: elicitacion
version: 1.1
fecha: 2026-10-08
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Plantilla del requerimiento funcional formal

Cada historia de usuario aprobada se transforma en uno o más requerimientos funcionales
formales. Esta es la estructura obligatoria de salida del agente elicitador.

## Campos de identificación

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id_requerimiento` | Sí | Prefijo `RF-` y numeración correlativa dentro del proyecto |
| `version` | Sí | Versión del requerimiento, inicia en `0.1` |
| `proyecto` | Sí | Nombre del proyecto o módulo al que pertenece |
| `tipo_solicitud` | Sí | `nuevo`, `adicional`, `ajuste` o `correccion` |
| `impacto` | Sí | `alto`, `medio` o `bajo` |
| `modulo` | Sí | Módulo funcional afectado |
| `riesgo` | No | Riesgo identificado en la implementación |
| `autor` | Sí | Agente o persona que redactó el requerimiento |
| `area_funcional` | Sí | Área de negocio responsable |
| `funcional_responsable` | No | Persona que valida desde el negocio |

## Campos de contenido

**`titulo`.** Reproduce la historia de usuario en sus tres partes: `como`, `quiero`, `para`.

**`descripcion`.** Se desglosa en cuatro subcampos obligatorios:

- `precondicion`: estado que debe cumplirse antes de ejecutar la funcionalidad.
- `regla_negocio`: la lógica que gobierna el comportamiento, expresada sin ambigüedad.
  Es el campo más importante y el que más preguntas requiere durante la elicitación.
- `datos_entrada`: cada dato con su nombre, tipo, obligatoriedad y restricción de dominio.
- `datos_salida`: cada resultado con su nombre, tipo y formato.

**`criterios_aceptacion`.** Lista de escenarios en formato Gherkin. Mínimo uno, y debe
existir al menos un escenario de camino alterno o de error. Cada escenario lleva `id`
(`ESC-01`, `ESC-02`…), un `nombre` breve opcional y los campos `dado_que`, `cuando` y
`entonces`.

**`prioridad`.** Heredada de la historia de usuario.

**`requerimientos_relacionados`.** Identificadores de otros requerimientos con los que
existe dependencia.

## Regla de completitud

El requerimiento se considera completo cuando el 100 % de los campos obligatorios está
diligenciado y ningún campo contiene marcadores de pendiente como «por definir», «TBD»
o «pendiente de confirmar». Si el elicitador no obtuvo la información necesaria durante
la conversación, no debe inventarla: debe registrar el vacío en `preguntas_abiertas` de la
historia y dejar el requerimiento en estado `incompleto`.

## Ejemplo de estructura de salida

```json
{
  "id_requerimiento": "RF-014",
  "version": "0.1",
  "proyecto": "Gestión tributaria y catastral",
  "tipo_solicitud": "nuevo",
  "impacto": "alto",
  "modulo": "liquidacion",
  "riesgo": "Un cálculo con punto flotante alteraría el valor del avalúo",
  "autor": "Agente elicitador",
  "area_funcional": "Liquidación del impuesto predial",
  "funcional_responsable": "Líder del área de liquidación",
  "titulo": {
    "como": "liquidador catastral",
    "quiero": "calcular el avalúo de un predio a partir de sus características físicas",
    "para": "emitir la liquidación del impuesto predial del periodo"
  },
  "descripcion": {
    "precondicion": "El predio existe, tiene ficha catastral vigente y los valores unitarios de la vigencia están registrados",
    "regla_negocio": "El avalúo total es la suma del avalúo del terreno, que resulta del área de terreno por el valor unitario de su zona homogénea geoeconómica, y del avalúo de la construcción, que resulta del área construida por el valor unitario de su tipología constructiva, ambos para la vigencia. Un predio sin construcción tiene avalúo igual al del terreno. Los valores se expresan en pesos colombianos sin decimales.",
    "datos_entrada": [
      {"nombre": "numero_predial", "tipo": "string", "obligatorio": true, "restriccion": "30 dígitos"},
      {"nombre": "vigencia", "tipo": "entero", "obligatorio": true, "restriccion": "año de cuatro dígitos, no superior a la vigencia actual más uno"},
      {"nombre": "area_terreno", "tipo": "decimal", "obligatorio": true, "restriccion": "mayor que cero, en metros cuadrados"},
      {"nombre": "area_construida", "tipo": "decimal", "obligatorio": true, "restriccion": "mayor o igual a cero; cero implica predio sin construcción"}
    ],
    "datos_salida": [
      {"nombre": "avaluo_terreno", "tipo": "decimal", "formato": "pesos colombianos sin decimales"},
      {"nombre": "avaluo_construccion", "tipo": "decimal", "formato": "pesos colombianos sin decimales"},
      {"nombre": "avaluo_total", "tipo": "decimal", "formato": "pesos colombianos sin decimales"}
    ]
  },
  "criterios_aceptacion": [
    {
      "id": "ESC-01",
      "nombre": "Predio con construcción",
      "dado_que": "un predio con 200 m² de terreno a 500.000 pesos por m² y 100 m² construidos a 1.200.000 pesos por m² en la vigencia",
      "cuando": "se calcula el avalúo",
      "entonces": "el avalúo total es de 220.000.000 pesos"
    },
    {
      "id": "ESC-02",
      "nombre": "Predio sin construcción",
      "dado_que": "un predio con área construida igual a cero",
      "cuando": "se calcula el avalúo",
      "entonces": "el avalúo total es igual al avalúo del terreno"
    },
    {
      "id": "ESC-03",
      "nombre": "Área de terreno inválida",
      "dado_que": "un predio con área de terreno igual a cero",
      "cuando": "se calcula el avalúo",
      "entonces": "el sistema rechaza el cálculo e informa que el área de terreno debe ser mayor que cero"
    }
  ],
  "prioridad": "alta",
  "requerimientos_relacionados": ["RF-012"]
}
```

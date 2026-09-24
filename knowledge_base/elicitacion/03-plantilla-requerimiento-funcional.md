---
id: eli-003
titulo: Plantilla del requerimiento funcional formal
fuente: Formato del Anexo B del anteproyecto; estructura alineada a ISO/IEC/IEEE 29148
tipo_fuente: elaboracion_propia
tags: [requerimiento, plantilla, anexo_b]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
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
existir al menos un escenario de camino alterno o de error.

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
  "modulo": "liquidacion",
  "titulo": {
    "como": "liquidador catastral",
    "quiero": "calcular el avalúo de un predio a partir de sus características físicas",
    "para": "emitir la liquidación del impuesto predial del periodo"
  },
  "descripcion": {
    "precondicion": "El predio existe y tiene ficha catastral vigente",
    "regla_negocio": "El avalúo resulta de sumar el valor del terreno y el de la construcción...",
    "datos_entrada": [
      {"nombre": "numero_predial", "tipo": "string", "obligatorio": true, "restriccion": "30 dígitos"}
    ],
    "datos_salida": [
      {"nombre": "avaluo_total", "tipo": "decimal", "formato": "moneda COP"}
    ]
  },
  "criterios_aceptacion": [
    {"id": "ESC-01", "dado_que": "...", "cuando": "...", "entonces": "..."}
  ],
  "prioridad": "alta",
  "requerimientos_relacionados": ["RF-012"]
}
```

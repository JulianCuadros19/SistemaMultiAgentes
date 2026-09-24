---
id: arq-001
titulo: Plantilla del registro de decisión arquitectónica
fuente: MADR, Markdown Architectural Decision Records (licencia MIT / CC0)
tipo_fuente: practica_industria
tags: [adr, madr, plantilla, decision]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Plantilla del registro de decisión arquitectónica

Estructura obligatoria de salida del agente arquitecto cuando justifica su elección. Está
adaptada del formato MADR, de amplia adopción en la industria y disponible bajo licencia
permisiva.

## Estructura

```markdown
---
estado: propuesta | aceptada | rechazada | reemplazada por ADR-NNNN
fecha: AAAA-MM-DD
decisores: [roles o agentes que participaron]
---

# ADR-NNNN · Título representativo del problema y la solución

## Contexto y planteamiento del problema

Descripción del contexto en dos o tres frases. Debe hacer explícito el alcance de la
decisión, señalando qué elementos estructurales se ven afectados.

## Factores de decisión

- Factor 1: una calidad deseada, una restricción o una fuerza en tensión
- Factor 2: ...

## Opciones consideradas

- Opción A
- Opción B
- Opción C

## Resultado de la decisión

Opción elegida: «Opción A», porque [justificación referida a los factores de decisión y
a los requerimientos concretos que la motivan].

### Consecuencias

- Favorable, porque [mejora de una calidad deseada]
- Desfavorable, porque [compromiso asumido en otra calidad]

### Confirmación

Cómo se verificará el cumplimiento de la decisión. Debe nombrar una comprobación concreta:
una verificación de dependencias, una prueba de arquitectura, una revisión estructural.

## Análisis de las opciones

### Opción A
- Favorable, porque [argumento]
- Neutral, porque [argumento]
- Desfavorable, porque [argumento]

### Opción B
...
```

## Reglas obligatorias para el agente arquitecto

1. **Mínimo dos opciones consideradas.** Una decisión con una sola alternativa no es una
   decisión; es una imposición sin justificar.
2. **Al menos una consecuencia desfavorable.** Toda elección arquitectónica implica un
   compromiso. Un registro que solo enumera ventajas es señal de análisis incompleto.
3. **Justificación trazada a requerimientos.** La justificación debe citar identificadores
   concretos de requerimientos, no argumentos genéricos de buena práctica.
4. **Confirmación verificable.** La sección de confirmación debe describir una comprobación
   que el agente tester pueda ejecutar.

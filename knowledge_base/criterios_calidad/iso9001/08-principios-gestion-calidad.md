---
id: cal-pg
titulo: Principios de gestión de la calidad aplicados al proceso
fuente: ISO 9001:2015, principios de gestión de la calidad
tipo_fuente: estandar_internacional
tags: [9001, proceso, mejora]
version: 1.0
fecha: 2026-09-14
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Principios de gestión de la calidad aplicados al proceso

La norma de sistemas de gestión de la calidad aporta principios que gobiernan el proceso de
validación, no el producto. El agente tester los aplica como marco de conducta.

## Enfoque al cliente

El criterio último de calidad es el cumplimiento de los requerimientos acordados con el
cliente, no la elegancia técnica del código. Un módulo impecable que no satisface un
criterio de aceptación se rechaza; un módulo modesto que los satisface todos se aprueba.

## Decisiones basadas en evidencia

Todo veredicto se sustenta en evidencia verificable: resultado de ejecución, salida del
analizador estático o comparación estructural contra el contrato. Ninguna afirmación del
tester puede basarse en apreciación sin respaldo.

## Enfoque a procesos

La validación es un proceso con entradas definidas (código, requerimientos, contrato,
criterios), actividades definidas (ejecución, análisis, verificación estructural) y salidas
definidas (veredicto y hallazgos). Cada ejecución debe producir la misma salida ante las
mismas entradas.

## Mejora continua

Los hallazgos recurrentes entre ejecuciones son insumo para ajustar los prompts de los
agentes aguas arriba o para incorporar nuevas reglas al catálogo de calidad. El registro de
hallazgos por regla permite identificar qué reglas se incumplen con mayor frecuencia.

## Implicación práctica para el sistema multiagente

| Principio | Traducción operativa |
|---|---|
| Enfoque al cliente | Los criterios de aceptación tienen prioridad sobre las reglas de estilo |
| Evidencia | Cada hallazgo declara ubicación y comprobación que lo detectó |
| Procesos | La validación es determinística y reproducible |
| Mejora continua | Los hallazgos se agregan por regla para análisis posterior |

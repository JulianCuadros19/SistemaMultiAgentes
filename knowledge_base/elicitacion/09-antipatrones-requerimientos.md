---
id: eli-009
titulo: Antipatrones y defectos frecuentes
fuente: Requirements smells; ISO/IEC/IEEE 29148:2018
tipo_fuente: practica_industria
tags: [antipatrones, defectos, ambiguedad]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Antipatrones y defectos frecuentes en requerimientos

Catálogo de defectos que el agente elicitador debe detectar y corregir antes de cerrar.
Cada defecto incluye la señal léxica que lo delata.

## Ambigüedad por cuantificador vago

**Señal:** rápido, lento, eficiente, amigable, robusto, adecuado, suficiente, óptimo,
razonable, apropiado, fácil, simple, moderno, intuitivo.

**Problema:** no existe forma objetiva de verificar el cumplimiento.

**Corrección:** sustituir por un valor medible. «Rápido» se convierte en «responde en menos
de dos segundos para un lote de hasta mil registros».

## Ambigüedad por pronombre sin referente

**Señal:** «este», «aquel», «el mismo», «dicho proceso» sin antecedente claro.

**Corrección:** repetir el sustantivo explícitamente.

## Requerimiento compuesto

**Señal:** conjunción «y» uniendo dos verbos de acción distintos; enumeraciones con «así
como», «además de», «también».

**Corrección:** dividir en requerimientos independientes con identificador propio.

## Opcionalidad encubierta

**Señal:** «debería», «podría», «sería deseable», «de ser posible», «preferiblemente».

**Problema:** no queda claro si es obligatorio. El desarrollador no sabe si implementarlo.

**Corrección:** decidir con el cliente si es obligatorio («debe») o si se descarta.

## Generalización sin límite

**Señal:** «etcétera», «entre otros», «y demás», «cualquier», «todos los casos».

**Problema:** el alcance queda abierto y no puede estimarse ni verificarse.

**Corrección:** enumerar exhaustivamente los casos cubiertos.

## Comparativo sin referencia

**Señal:** «mejor», «mayor», «más rápido», «más seguro» sin decir respecto a qué.

**Corrección:** declarar la línea base y la magnitud de la mejora.

## Negación implícita

**Señal:** el requerimiento declara lo que el sistema no debe hacer, sin declarar qué
debe hacer en su lugar.

**Corrección:** reformular en positivo indicando el comportamiento esperado.

## Solución prescrita

**Señal:** el requerimiento nombra una tecnología, una estructura de datos o un patrón
de implementación.

**Problema:** invade la competencia del agente arquitecto y elimina alternativas de diseño.

**Corrección:** reformular en términos de capacidad; si la restricción tecnológica es real,
registrarla como requerimiento de dominio, no como funcional.

## Marcador de pendiente

**Señal:** «TBD», «por definir», «pendiente», «se confirmará», campos vacíos.

**Problema:** el requerimiento no está completo y no puede aprobarse.

**Corrección:** volver a la conversación. Nunca inventar el contenido faltante.

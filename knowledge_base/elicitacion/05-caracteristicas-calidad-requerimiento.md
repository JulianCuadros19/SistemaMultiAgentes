---
id: eli-005
titulo: Características de calidad de un requerimiento individual
fuente: ISO/IEC/IEEE 29148:2018, cláusula de criterios de calidad
tipo_fuente: estandar_internacional
tags: [29148, calidad, verificacion]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Características de calidad de un requerimiento individual

La norma ISO/IEC/IEEE 29148:2018 define nueve características que debe cumplir todo
requerimiento individual. El nodo de verificación de calidad evalúa cada una y rechaza
el requerimiento que falle cualquiera de las marcadas como bloqueantes.

## Las nueve características

| # | Característica | Definición operativa | Bloqueante |
|---|---|---|---|
| C1 | Necesario | Define un aspecto esencial; eliminarlo produce una deficiencia | Sí |
| C2 | Apropiado | El nivel de detalle corresponde al nivel del sistema descrito | No |
| C3 | No ambiguo | Admite una única interpretación posible | Sí |
| C4 | Completo | Contiene toda la información necesaria para implementarlo | Sí |
| C5 | Singular | Enuncia una sola capacidad, característica o restricción | Sí |
| C6 | Factible | Es realizable dentro de las restricciones del proyecto | No |
| C7 | Verificable | Su cumplimiento puede probarse o medirse objetivamente | Sí |
| C8 | Correcto | Representa fielmente la necesidad de la que proviene | Sí |
| C9 | Conforme | Se ajusta a la plantilla y al estilo de redacción aprobados | Sí |

## Características del conjunto

Además de las individuales, el conjunto completo de requerimientos debe ser **completo**
(no requiere ampliación y no contiene marcadores de pendiente), **consistente** (ningún
requerimiento contradice a otro), **acotado** (se mantiene dentro del alcance definido)
y **priorizado**.

## Señales de incumplimiento detectables automáticamente

Estas señales permiten al verificador rechazar sin necesidad de juicio humano:

| Señal | Característica afectada |
|---|---|
| Presencia de «TBD», «por definir», «pendiente», «etc.» | Completo |
| Cuantificadores vagos: «rápido», «eficiente», «amigable», «adecuado» | No ambiguo, Verificable |
| Conjunción «y» uniendo dos capacidades distintas | Singular |
| Ausencia de criterios de aceptación | Verificable |
| Campo obligatorio de la plantilla vacío | Completo, Conforme |
| Comparativos sin referencia: «mejor», «más rápido que antes» | Verificable |
| Verbos de opinión: «debería considerarse», «sería deseable» | Necesario, No ambiguo |

## Procedimiento de verificación

1. Ejecutar las comprobaciones automáticas de la tabla anterior.
2. Para cada característica bloqueante que falle, registrar el defecto con su identificador.
3. Si existe al menos un defecto bloqueante, rechazar el requerimiento y devolverlo con
   la lista completa de defectos, no solo el primero.
4. Si no hay defectos bloqueantes, marcar el requerimiento como apto para aprobación humana.

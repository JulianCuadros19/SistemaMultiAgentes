---
id: cal-tp
titulo: Técnicas de diseño de casos de prueba
fuente: ISO/IEC/IEEE 29119, procesos de prueba de software
tipo_fuente: estandar_internacional
tags: [29119, pruebas, tecnicas]
version: 1.0
fecha: 2026-09-14
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Técnicas de diseño de casos de prueba

El marco internacional de pruebas de software define técnicas de diseño que el agente
tester emplea para evaluar si el conjunto de pruebas generado es suficiente.

## Partición de equivalencia

Divide el dominio de entrada en clases donde el comportamiento esperado es el mismo. Se
prueba un representante de cada clase.

**Aplicación en la evaluación.** Para cada dato de entrada con restricción de dominio, debe
existir al menos una prueba con valor válido y una con valor inválido.

## Análisis de valores límite

Prueba los extremos de cada clase de equivalencia, donde se concentran los defectos.

**Aplicación en la evaluación.** Para cada dato con rango o longitud definida, deben
existir pruebas en el límite inferior, el límite superior y al menos un valor fuera.
En este dominio aplica especialmente a longitudes de identificadores, áreas y vigencias.

## Cobertura de decisiones

Verifica que cada rama condicional se ejercite en ambos sentidos.

**Aplicación en la evaluación.** Cada regla de negocio con condicional debe tener pruebas
que recorran la rama verdadera y la falsa.

## Pruebas basadas en tabla de decisión

Cuando el resultado depende de la combinación de varias condiciones, se construye la tabla
de combinaciones y se prueba cada fila relevante.

**Aplicación en la evaluación.** Requerimientos con reglas de precedencia o con varios
beneficios acumulables exigen esta cobertura.

## Pruebas de transición de estado

Cuando la entidad tiene estados, se prueban las transiciones permitidas y se verifica el
rechazo de las prohibidas.

**Aplicación en la evaluación.** Requerimientos que declaran estados, como los trámites de
mutación, exigen prueba de al menos una transición prohibida.

## Criterio de suficiencia del conjunto de pruebas

| Elemento del requerimiento | Cobertura mínima exigida |
|---|---|
| Cada criterio de aceptación | Una prueba |
| Cada dato de entrada con restricción | Un valor válido y uno inválido |
| Cada dato con rango | Los dos límites y un valor fuera |
| Cada condicional de la regla de negocio | Ambas ramas |
| Cada estado declarado | Una transición permitida y una prohibida |

Un conjunto de pruebas que no alcanza esta cobertura se reporta como hallazgo de severidad
media, con el detalle de qué elemento quedó sin cubrir.

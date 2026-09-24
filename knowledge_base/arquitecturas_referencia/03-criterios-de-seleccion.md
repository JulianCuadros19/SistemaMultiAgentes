---
id: arq-003
titulo: Criterios de selección de arquitectura
fuente: Elaboración propia
tipo_fuente: elaboracion_propia
tags: [seleccion, criterios, decision]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Criterios de selección de arquitectura

Procedimiento que el agente arquitecto sigue para elegir una opción del catálogo. El
objetivo es reducir la varianza entre ejecuciones: ante el mismo conjunto de requerimientos,
la decisión debe ser reproducible.

## Paso 1 · Clasificar la naturaleza del módulo

| Señal en los requerimientos | Naturaleza | Candidatas |
|---|---|---|
| Transforma lotes de datos de origen a destino | Procesamiento | ARQ-03 |
| Es consumido por otros sistemas o por una interfaz | Servicio | ARQ-04 |
| Se ejecuta manualmente o por tarea programada | Herramienta | ARQ-05 |
| Reacciona a hechos producidos por otros procesos | Reactivo | ARQ-06 |
| Concentra reglas de negocio complejas | Dominio | ARQ-01, ARQ-02 |

## Paso 2 · Evaluar el peso de la lógica de negocio

- **Lógica trivial** (validaciones simples, transformaciones directas): preferir la opción
  más simple de las candidatas. La arquitectura hexagonal en un módulo trivial es
  sobreingeniería y debe descartarse explícitamente en el registro de decisión.
- **Lógica moderada**: ARQ-01 en capas ofrece el mejor balance.
- **Lógica compleja con invariantes de negocio**: ARQ-02 hexagonal, porque permite probar
  las reglas sin infraestructura.

## Paso 3 · Verificar restricciones no funcionales

| Requerimiento no funcional presente | Efecto sobre la selección |
|---|---|
| Exige probar la lógica sin base de datos | Favorece ARQ-02 |
| Exige sustituir la persistencia a futuro | Favorece ARQ-02 |
| Exige reintento por etapas | Favorece ARQ-03 |
| Exige contrato de interfaz documentado | Favorece ARQ-04 |
| Exige desacoplar productor y consumidor | Favorece ARQ-06 |
| Exige mínima complejidad operativa | Penaliza ARQ-06 |

## Paso 4 · Aplicar el criterio de simplicidad suficiente

Entre dos arquitecturas que satisfacen los requerimientos, se elige la de menor número de
módulos e indirecciones. La complejidad estructural debe justificarse por un requerimiento
concreto, nunca por preferencia estilística.

## Paso 5 · Documentar la decisión

Se completa la plantilla de registro de decisión arquitectónica con:

- La opción elegida y su identificador del catálogo.
- Al menos una alternativa descartada, con el motivo del descarte referido a un
  requerimiento concreto.
- Las consecuencias favorables y desfavorables asumidas.
- La forma de confirmar el cumplimiento.

## Prohibiciones

1. No combinar dos arquitecturas base en un mismo módulo.
2. No inventar una arquitectura fuera del catálogo.
3. No elegir por familiaridad; la justificación debe ser funcional.
4. No omitir la alternativa descartada, aunque la elección parezca evidente.

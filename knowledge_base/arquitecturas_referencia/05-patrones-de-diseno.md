---
id: arq-005
titulo: Patrones de diseño aplicables
fuente: Patrones de diseño consolidados en la industria
tipo_fuente: practica_industria
tags: [patrones, diseño, repositorio]
version: 1.1
fecha: 2026-10-08
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Patrones de diseño aplicables

Subconjunto de patrones que el agente arquitecto puede parametrizar dentro de una
arquitectura base. No son arquitecturas: son soluciones locales a problemas recurrentes.

## Repositorio

**Problema.** El dominio necesita persistir y recuperar entidades sin conocer la tecnología
de almacenamiento.

**Solución.** Una interfaz que expone operaciones en términos del dominio (`obtener_por_id`,
`guardar`, `buscar_por_criterio`) y una implementación concreta por tecnología.

**Cuándo aplicarlo.** Siempre que exista persistencia en ARQ-01 o ARQ-02.

**Confirmación.** El dominio no importa la librería de acceso a datos.

## Objeto de transferencia

**Problema.** Las estructuras del dominio no deben exponerse directamente en la frontera
del sistema.

**Solución.** Objetos planos de entrada y salida, validados en la frontera y traducidos a
entidades del dominio.

**Cuándo aplicarlo.** En ARQ-04 siempre; en ARQ-05 cuando la entrada es compleja.

## Estrategia

**Problema.** Una regla de negocio tiene variantes que se eligen en tiempo de ejecución.

**Solución.** Una interfaz común y una implementación por variante, seleccionada por un
despachador.

**Cuándo aplicarlo.** Cuando el requerimiento enumera casos con lógica distinta, como
tipos de mutación o modalidades de liquidación.

**Alternativa más simple.** Si las variantes son dos y estables, una condicional explícita
es preferible. El patrón se justifica desde tres variantes o cuando se prevé crecimiento.

## Fábrica

**Problema.** La construcción de un objeto exige lógica que no pertenece al objeto mismo.

**Solución.** Una función o clase responsable de construir instancias válidas.

**Cuándo aplicarlo.** Cuando la entidad tiene invariantes que deben validarse al crearla.

## Objeto de valor

**Problema.** Un concepto del dominio se representa con un tipo primitivo y pierde sus
reglas.

**Solución.** Un tipo inmutable que encapsula el valor y valida su invariante al construirse.

**Cuándo aplicarlo.** En conceptos con formato estricto: número predial, vigencia, monto.
Es especialmente valioso en este dominio, donde los identificadores tienen estructura fija.

## Unidad de trabajo

**Problema.** Varias operaciones de persistencia deben confirmarse o revertirse juntas.

**Solución.** Un objeto que agrupa las operaciones y las confirma en bloque.

**Cuándo aplicarlo.** Cuando un requerimiento modifica más de una entidad y exige
consistencia, como una mutación que altera predio y propietario.

## Criterio general de aplicación

Un patrón se declara en la especificación solo si un requerimiento concreto lo justifica. La
aplicación de patrones sin necesidad es sobreingeniería y debe descartarse en el registro
de decisión con su motivo.

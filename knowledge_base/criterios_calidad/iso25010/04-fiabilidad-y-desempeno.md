---
id: cal-fb
titulo: Fiabilidad y eficiencia de desempeño
fuente: ISO/IEC 25010:2023
tipo_fuente: estandar_internacional
tags: [25010, fiabilidad, desempeño, reglas]
version: 1.0
fecha: 2026-09-14
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Reglas de fiabilidad y eficiencia de desempeño


### REGLA CAL-FB-001 · Ausencia de estado global mutable

- **Característica:** Fiabilidad › Ausencia de fallos
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** El módulo no debe depender de variables globales mutables compartidas entre funciones.

**Verificación.** Análisis estático buscando declaraciones de variables globales modificadas dentro de funciones.

**Evidencia esperada.** Ubicación de cada variable global mutable.


### REGLA CAL-FB-002 · Argumentos por defecto inmutables

- **Característica:** Fiabilidad › Ausencia de fallos
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Ninguna función debe declarar un valor por defecto mutable en sus parámetros.

**Verificación.** Análisis estático con las reglas de detección de errores frecuentes del linter (familia B).

**Evidencia esperada.** Ubicación de cada parámetro con valor por defecto mutable.


### REGLA CAL-FB-003 · Cierre garantizado de recursos

- **Característica:** Fiabilidad › Recuperabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo recurso externo abierto debe cerrarse de forma garantizada, incluso ante excepción, mediante gestor de contexto.

**Verificación.** Análisis estático buscando apertura de recursos fuera de un gestor de contexto.

**Evidencia esperada.** Ubicación de cada recurso abierto sin cierre garantizado.


### REGLA CAL-FB-004 · Determinismo de las pruebas

- **Característica:** Fiabilidad › Ausencia de fallos
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** pruebas generadas

**Enunciado.** Las pruebas no deben depender de la fecha actual, de valores aleatorios no fijados ni del orden de ejecución.

**Verificación.** Ejecutar la suite dos veces y comparar los resultados; analizar las pruebas buscando dependencias no deterministas.

**Evidencia esperada.** Comparación de ambas ejecuciones y listado de dependencias no deterministas.


### REGLA CAL-FB-005 · Ausencia de operaciones costosas en bucles

- **Característica:** Eficiencia de desempeño › Comportamiento temporal
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Baja
- **Aplica a:** código generado

**Enunciado.** No deben ejecutarse operaciones de entrada y salida ni consultas a base de datos dentro de bucles cuando puedan resolverse en lote.

**Verificación.** Análisis del árbol sintáctico buscando llamadas de acceso a datos dentro de estructuras iterativas.

**Evidencia esperada.** Ubicación de cada operación costosa dentro de un bucle.

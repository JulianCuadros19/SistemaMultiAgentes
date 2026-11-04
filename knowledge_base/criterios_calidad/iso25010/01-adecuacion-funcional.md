---
id: cal-fs
titulo: Adecuación funcional
fuente: ISO/IEC 25010:2023, característica de adecuación funcional
tipo_fuente: estandar_internacional
tags: [25010, funcional, reglas]
version: 1.2
fecha: 2026-11-03
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Reglas de adecuación funcional


### REGLA CAL-FS-001 · Cobertura de criterios de aceptación

- **Característica:** Adecuación funcional › Completitud funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo criterio de aceptación declarado en los requerimientos cubiertos por el módulo debe tener al menos un caso de prueba automatizado que lo ejercite.

**Verificación.** Contar los criterios de aceptación de los requerimientos asignados y contrastarlos con las pruebas presentes. La regla falla si algún criterio no tiene prueba asociada.

**Evidencia esperada.** Tabla de correspondencia entre identificador de criterio y nombre del caso de prueba.


### REGLA CAL-FS-002 · Ejecución sin fallos de las pruebas

- **Característica:** Adecuación funcional › Corrección funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** La totalidad de las pruebas automatizadas del módulo debe ejecutarse sin fallos ni errores en el entorno aislado.

**Verificación.** Ejecutar la suite completa y leer el código de salida y el resumen de resultados.

**Evidencia esperada.** Salida del ejecutor de pruebas con el conteo de pruebas superadas, fallidas y con error.


### REGLA CAL-FS-003 · Ausencia de error de sintaxis o importación

- **Característica:** Adecuación funcional › Corrección funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo módulo declarado en la especificación debe poder importarse sin producir errores de sintaxis ni de importación.

**Verificación.** Intentar la importación de cada módulo en el entorno aislado.

**Evidencia esperada.** Registro de la importación exitosa de cada módulo o el mensaje de error producido.


### REGLA CAL-FS-004 · Cobertura del camino de error

- **Característica:** Adecuación funcional › Pertinencia funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** Cada requerimiento debe tener al menos un caso de prueba que ejercite una entrada inválida o una precondición no cumplida.

**Verificación.** Verificar la presencia de pruebas que esperen excepción o resultado de rechazo.

**Evidencia esperada.** Listado de pruebas de camino de error identificadas por requerimiento.


### REGLA CAL-FS-005 · Precisión en cálculos monetarios

- **Característica:** Adecuación funcional › Corrección funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo cálculo que produzca un valor monetario o un avalúo debe emplear tipo decimal de precisión fija, nunca punto flotante.

**Verificación.** Analizar el árbol sintáctico buscando operaciones aritméticas sobre valores anotados como monetarios que usen el tipo float.

**Evidencia esperada.** Ubicación de cada operación monetaria y el tipo empleado.


### REGLA CAL-FS-006 · Pruebas que no simulan el efecto del módulo

- **Característica:** Adecuación funcional › Corrección funcional
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** pruebas generadas

**Enunciado.** Una prueba debe obtener el resultado que verifica del módulo, preparando la situación con sus interfaces públicas. No cumple si inyecta en los objetos del módulo atributos que sus clases no tienen, ni si lanza ella misma la excepción que espera: así pasa aunque el módulo no haga su trabajo.

**Verificación.** Recorrer el árbol sintáctico de las pruebas buscando atributos asignados a objetos de clases declaradas que esas clases no definen, también con `setattr` u `object.__setattr__`, y sentencias `raise` dentro de un bloque `pytest.raises`.

**Evidencia esperada.** Archivo, línea y prueba de cada inyección o excepción lanzada por la prueba.

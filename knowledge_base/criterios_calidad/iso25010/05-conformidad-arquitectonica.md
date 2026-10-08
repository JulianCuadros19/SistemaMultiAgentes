---
id: cal-ar
titulo: Conformidad arquitectónica y compatibilidad
fuente: ISO/IEC 25010:2023; especificación de diseño del proyecto
tipo_fuente: estandar_internacional
tags: [arquitectura, conformidad, especificacion, reglas]
version: 1.1
fecha: 2026-10-08
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Reglas de conformidad arquitectónica


### REGLA CAL-AR-001 · Existencia de los módulos declarados

- **Característica:** Compatibilidad › Interoperabilidad
- **Norma de referencia:** Especificación de diseño
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo módulo declarado en la especificación de diseño debe existir en la ruta indicada.

**Verificación.** Comprobar la existencia del archivo en la ruta declarada para cada módulo de la especificación.

**Evidencia esperada.** Tabla de módulos declarados con su estado de existencia.


### REGLA CAL-AR-002 · Correspondencia de interfaces públicas

- **Característica:** Compatibilidad › Interoperabilidad
- **Norma de referencia:** Especificación de diseño
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Cada interfaz pública declarada en la especificación debe existir en el módulo correspondiente con el mismo nombre y una firma compatible.

**Verificación.** Extraer las definiciones públicas de cada módulo mediante análisis del árbol sintáctico y compararlas con las firmas de la especificación.

**Evidencia esperada.** Comparación firma por firma entre especificación e implementación.


### REGLA CAL-AR-003 · Ausencia de módulos no previstos

- **Característica:** Mantenibilidad › Modularidad
- **Norma de referencia:** Especificación de diseño
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** El código no debe introducir módulos que no figuren en la especificación de diseño.

**Verificación.** Enumerar los archivos de código producidos y contrastarlos con la especificación.

**Evidencia esperada.** Listado de archivos no previstos en la especificación.


### REGLA CAL-AR-004 · Dependencias externas autorizadas

- **Característica:** Compatibilidad › Coexistencia
- **Norma de referencia:** Catálogo tecnológico autorizado
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Toda librería externa importada debe pertenecer al catálogo tecnológico autorizado y estar declarada en la especificación.

**Verificación.** Extraer las importaciones de terceros y contrastarlas con el catálogo y con las dependencias de la especificación.

**Evidencia esperada.** Listado de dependencias externas encontradas y su estado de autorización.


### REGLA CAL-AR-005 · Trazabilidad requerimiento a módulo

- **Característica:** Adecuación funcional › Completitud funcional
- **Norma de referencia:** Especificación de diseño
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo requerimiento asignado a un módulo en la especificación debe tener implementación observable en ese módulo.

**Verificación.** Verificar que cada requerimiento asignado tiene al menos una prueba que lo referencia y que dicha prueba ejercita código del módulo.

**Evidencia esperada.** Matriz de trazabilidad entre requerimiento, módulo y prueba.

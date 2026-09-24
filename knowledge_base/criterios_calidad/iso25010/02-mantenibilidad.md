---
id: cal-mt
titulo: Mantenibilidad
fuente: ISO/IEC 25010:2023, característica de mantenibilidad
tipo_fuente: estandar_internacional
tags: [25010, mantenibilidad, reglas]
version: 1.0
fecha: 2026-09-14
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Reglas de mantenibilidad


### REGLA CAL-MT-001 · Documentación de interfaces públicas

- **Característica:** Mantenibilidad › Analizabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Toda función, método y clase pública debe exponer documentación que describa su propósito, sus parámetros, su valor de retorno y las excepciones que puede lanzar.

**Verificación.** Análisis estático con las reglas de documentación del linter (familia D).

**Evidencia esperada.** Listado de elementos públicos sin documentación, con archivo y línea.


### REGLA CAL-MT-002 · Anotación de tipos en interfaces públicas

- **Característica:** Mantenibilidad › Analizabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Toda interfaz pública declarada en el contrato de diseño debe anotar los tipos de sus parámetros y de su valor de retorno.

**Verificación.** Análisis estático con las reglas de anotación del linter (familia ANN) y contraste con las firmas del contrato.

**Evidencia esperada.** Comparación entre la firma declarada en el contrato y la firma implementada.


### REGLA CAL-MT-003 · Límite de complejidad ciclomática

- **Característica:** Mantenibilidad › Modificabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** Ninguna función debe superar el umbral de complejidad ciclomática configurado para el proyecto.

**Verificación.** Análisis estático con la regla de complejidad del linter (familia C90).

**Evidencia esperada.** Nombre de cada función que supera el umbral y su valor de complejidad.


### REGLA CAL-MT-004 · Ausencia de código no utilizado

- **Característica:** Mantenibilidad › Analizabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** El módulo no debe contener importaciones, variables ni asignaciones que no se utilicen.

**Verificación.** Análisis estático con las reglas de detección lógica del linter (familia F).

**Evidencia esperada.** Listado de elementos no utilizados con su ubicación.


### REGLA CAL-MT-005 · Modularidad conforme al contrato

- **Característica:** Mantenibilidad › Modularidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Cada módulo declarado en el contrato de diseño debe existir como archivo independiente en la ruta declarada, con la responsabilidad única que el contrato le asigna.

**Verificación.** Comprobar la existencia de cada ruta declarada y que no se hayan creado módulos no previstos.

**Evidencia esperada.** Tabla de módulos declarados frente a módulos encontrados.


### REGLA CAL-MT-006 · Respeto de las fronteras de dependencia

- **Característica:** Mantenibilidad › Modularidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Ningún módulo debe importar otro módulo que no figure en su lista de dependencias permitidas dentro del contrato de diseño.

**Verificación.** Extraer las importaciones de cada módulo mediante análisis del árbol sintáctico y contrastarlas con las dependencias permitidas.

**Evidencia esperada.** Listado de importaciones no autorizadas, indicando módulo origen y módulo destino.


### REGLA CAL-MT-007 · Nomenclatura conforme a la convención

- **Característica:** Mantenibilidad › Analizabilidad
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Baja
- **Aplica a:** código generado

**Enunciado.** Los nombres de módulos, clases, funciones y variables deben seguir la convención de nombres declarada en la configuración de estilo del sistema.

**Verificación.** Análisis estático con las reglas de nomenclatura del linter (familia N).

**Evidencia esperada.** Listado de identificadores que incumplen la convención.


### REGLA CAL-MT-008 · Capacidad de prueba de la lógica de negocio

- **Característica:** Mantenibilidad › Capacidad de ser probado
- **Norma de referencia:** ISO/IEC 25010:2023
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** La lógica de negocio debe poder ejercitarse sin requerir recursos externos como red, base de datos o sistema de archivos.

**Verificación.** Verificar que las pruebas de la capa de dominio se ejecutan con éxito en el entorno aislado, que no dispone de red.

**Evidencia esperada.** Resultado de la ejecución de las pruebas de dominio en el contenedor sin red.

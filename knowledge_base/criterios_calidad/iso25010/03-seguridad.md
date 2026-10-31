---
id: cal-sg
titulo: Seguridad
fuente: ISO/IEC 25010:2023 e ISO/IEC 27001:2022, controles A.8.25 y A.8.28
tipo_fuente: estandar_internacional
tags: [25010, 27001, seguridad, reglas]
version: 1.1
fecha: 2026-10-31
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Reglas de seguridad


### REGLA CAL-SG-001 · Ausencia de credenciales embebidas

- **Característica:** Seguridad › Confidencialidad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** El código no debe contener contraseñas, claves de acceso, cadenas de conexión con credenciales ni secretos de ningún tipo escritos directamente.

**Verificación.** Análisis estático del árbol sintáctico: literales de texto asignados, comparados, pasados como argumento o usados como valor por defecto con nombres de secretos, en español o inglés. No cuentan los textos en lenguaje natural, como los mensajes, ni los nombres de variables de entorno. No se aplica a los archivos de prueba, cuyos valores son datos de prueba.

**Evidencia esperada.** Ubicación exacta de cada hallazgo, sin reproducir el valor detectado.


### REGLA CAL-SG-002 · Ausencia de ejecución dinámica de código

- **Característica:** Seguridad › Integridad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** El código no debe emplear mecanismos de evaluación o ejecución dinámica de cadenas de texto.

**Verificación.** Análisis estático buscando invocaciones de evaluación y ejecución dinámica.

**Evidencia esperada.** Ubicación de cada invocación detectada.


### REGLA CAL-SG-003 · Construcción segura de consultas

- **Característica:** Seguridad › Integridad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Las consultas a base de datos deben construirse mediante parámetros vinculados, nunca por concatenación o interpolación de cadenas con datos de entrada.

**Verificación.** Análisis estático buscando construcción de consultas por concatenación o formato de cadenas.

**Evidencia esperada.** Ubicación de cada consulta construida de forma insegura.


### REGLA CAL-SG-004 · Invocación segura de procesos del sistema

- **Característica:** Seguridad › Integridad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** La invocación de procesos del sistema operativo no debe ejecutarse a través de intérprete de comandos con entrada proveniente del usuario.

**Verificación.** Análisis estático buscando invocaciones de subprocesos con intérprete habilitado.

**Evidencia esperada.** Ubicación de cada invocación y el parámetro implicado.


### REGLA CAL-SG-005 · Validación de entrada en la frontera

- **Característica:** Seguridad › Integridad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.25 ciclo de vida de desarrollo seguro
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Todo dato que ingresa desde fuera del módulo debe validarse contra su restricción de dominio antes de ser utilizado en la lógica de negocio.

**Verificación.** Verificar que cada dato de entrada declarado en el requerimiento tiene validación explícita de tipo y restricción.

**Evidencia esperada.** Correspondencia entre cada dato de entrada del requerimiento y su punto de validación.


### REGLA CAL-SG-006 · Manejo explícito de excepciones

- **Característica:** Seguridad › Integridad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** El código no debe capturar excepciones de forma genérica sin tratarlas ni registrarlas, ni silenciar errores con bloques vacíos.

**Verificación.** Análisis estático buscando capturas genéricas sin cuerpo significativo.

**Evidencia esperada.** Ubicación de cada captura genérica o silenciada.


### REGLA CAL-SG-007 · Ausencia de datos personales en registros

- **Característica:** Seguridad › Confidencialidad
- **Norma de referencia:** ISO/IEC 27001:2022; régimen de protección de datos personales
- **Severidad:** Alta
- **Aplica a:** código generado

**Enunciado.** Los mensajes de registro no deben incluir datos personales identificables de los titulares ni valores de secretos.

**Verificación.** Analizar las llamadas de registro buscando la inclusión de campos marcados como datos personales en el modelo de datos.

**Evidencia esperada.** Ubicación de cada llamada de registro que expone un campo sensible.


### REGLA CAL-SG-008 · Aleatoriedad criptográficamente adecuada

- **Característica:** Seguridad › Autenticidad
- **Norma de referencia:** ISO/IEC 27001:2022, A.8.28 codificación segura
- **Severidad:** Media
- **Aplica a:** código generado

**Enunciado.** Cuando se generen identificadores o valores con propósito de seguridad, debe emplearse un generador criptográficamente seguro.

**Verificación.** Análisis estático buscando uso del generador pseudoaleatorio de propósito general en contextos de seguridad.

**Evidencia esperada.** Ubicación de cada uso detectado.

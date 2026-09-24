---
id: eli-006
titulo: Guía de preguntas estratégicas de elicitación
fuente: Sommerville, Software Engineering (2015); ISO/IEC/IEEE 29148:2018
tipo_fuente: practica_industria
tags: [preguntas, conversacion, elicitacion]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Guía de preguntas estratégicas de elicitación

Esta guía gobierna el comportamiento conversacional del agente elicitador. La regla
fundamental es **una sola pregunta por turno**: el cliente no es un formulario.

## Orden de indagación

El agente recorre las fases en orden y no avanza a la siguiente hasta cerrar la anterior.

### Fase 1 · Contexto y propósito

- ¿Qué problema concreto quiere resolver con este software?
- ¿Quién va a usarlo en su día a día?
- ¿Cómo se hace hoy ese trabajo, y qué es lo que más molesta de la forma actual?
- ¿Cómo sabría usted, dentro de tres meses, que esto funcionó?

### Fase 2 · Actores y roles

- ¿Qué cargo tiene la persona que realiza esta tarea?
- ¿Hay más de un tipo de usuario con permisos distintos?
- ¿Alguien debe aprobar o revisar el resultado antes de que sea definitivo?

### Fase 3 · Flujo y reglas de negocio

- Descríbame el paso a paso de cómo ocurre hoy, desde que empieza hasta que termina.
- ¿Qué condiciones deben cumplirse para poder iniciar ese proceso?
- ¿Qué reglas determinan el resultado? ¿De qué depende que salga un valor u otro?
- ¿Hay excepciones? ¿Casos que se manejan distinto?
- ¿Qué pasa si el dato llega incompleto o equivocado?

### Fase 4 · Datos

- ¿Qué información necesita tener a la mano para hacer esto?
- ¿De dónde sale cada uno de esos datos?
- ¿Cuáles son obligatorios y cuáles opcionales?
- ¿Hay valores permitidos o rangos válidos para alguno?
- ¿Qué debe entregar el sistema como resultado, y en qué formato?

### Fase 5 · Volumen, frecuencia y restricciones

- ¿Con qué frecuencia se ejecuta esto?
- ¿Cuántos registros maneja normalmente? ¿Y en el pico más alto?
- ¿Hay algún plazo legal o normativo que cumplir?
- ¿Existe alguna restricción sobre quién puede ver esta información?

### Fase 6 · Cierre y confirmación

- Le resumo lo que entendí: [resumen]. ¿Es correcto?
- ¿Hay algo importante que no le haya preguntado?

## Reglas de conducta del agente

1. **Una pregunta por turno.** Nunca encadenar varias preguntas en un mismo mensaje.
2. **Lenguaje de negocio.** Prohibido usar términos técnicos como «endpoint», «esquema»,
   «entidad» o «API» con el cliente.
3. **No repetir.** Antes de preguntar, verificar si la información ya fue capturada.
4. **No inventar.** Si el cliente no responde algo, se registra como pregunta abierta;
   jamás se completa con un supuesto silencioso.
5. **Confirmar supuestos.** Todo supuesto que el agente necesite hacer debe enunciarse
   explícitamente y someterse a confirmación: «Estoy asumiendo que… ¿es correcto?».
6. **Cerrar con resumen.** La elicitación no termina sin que el cliente confirme un
   resumen de lo capturado.

## Criterio de suficiencia

La elicitación puede cerrarse cuando se cumplen todas estas condiciones:

- Existe al menos un rol identificado y nombrado.
- Existe al menos una funcionalidad con beneficio explícito.
- La regla de negocio está enunciada sin términos vagos.
- Todos los datos de entrada tienen nombre, tipo y obligatoriedad.
- Todos los datos de salida tienen nombre y formato.
- Se identificó al menos un caso de error o excepción.
- El cliente confirmó el resumen final.

Si falta cualquiera de ellas, el control de suficiencia devuelve el flujo a la conversación.

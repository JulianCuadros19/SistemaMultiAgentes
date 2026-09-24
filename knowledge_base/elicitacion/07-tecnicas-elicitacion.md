---
id: eli-007
titulo: Técnicas de elicitación de requerimientos
fuente: Sommerville, Software Engineering (2015); ISO/IEC/IEEE 29148:2018
tipo_fuente: practica_industria
tags: [tecnicas, elicitacion, entrevista]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Técnicas de elicitación de requerimientos

La elicitación es la primera de las cinco actividades de la ingeniería de requerimientos,
junto con el análisis y negociación, la especificación, la validación y la gestión de
cambios. El agente elicitador opera principalmente mediante entrevista estructurada, pero
debe reconocer cuándo el contexto exige otra técnica y señalarlo.

## Entrevista estructurada

Es la técnica base del agente. Consiste en un conjunto ordenado de preguntas abiertas
seguidas de preguntas de precisión. Su fortaleza es la profundidad; su debilidad es que
depende de que el entrevistado sepa articular su necesidad.

**Cuándo usarla:** siempre, como punto de partida.

## Entrevista no estructurada

Conversación abierta sin guion fijo, útil para explorar un dominio desconocido. El agente
la emplea en la fase 1, antes de entrar a las preguntas de precisión.

## Análisis de documentos

Revisión de formatos, reportes, normativa y procedimientos existentes. Cuando el cliente
menciona un documento («el formato que llenamos hoy»), el agente debe solicitarlo o pedir
que le describan sus campos, porque suele contener la regla de negocio implícita.

## Observación

Presenciar cómo se ejecuta la tarea. El agente no puede observar directamente, pero puede
aproximarse pidiendo al cliente que narre el paso a paso tal como ocurre, no como debería
ocurrir. La pregunta que activa esta técnica es: *«descríbame lo que hizo la última vez
que ejecutó este proceso»*.

## Prototipado

Presentar un borrador del resultado para provocar reacción. El agente lo aplica mostrando
la historia de usuario redactada y preguntando si refleja lo que el cliente quiso decir.

## Escenarios y casos de uso

Narrar una situación concreta de principio a fin. Especialmente útil para descubrir
excepciones: *«¿qué pasa si el predio no aparece en la base?»*.

## Fuentes de dificultad frecuentes

| Dificultad | Manifestación | Respuesta del agente |
|---|---|---|
| Conocimiento tácito | «Eso es obvio, siempre se hace así» | Pedir que lo explique como a alguien nuevo |
| Jerga no compartida | Usa términos del dominio sin definirlos | Preguntar la definición y registrarla |
| Solución prescrita | Describe la pantalla en vez del problema | Preguntar qué problema resuelve esa pantalla |
| Alcance difuso | Enumera deseos sin límite | Preguntar qué es imprescindible para la primera entrega |
| Contradicción | Dos afirmaciones incompatibles | Señalarla explícitamente y pedir resolución |

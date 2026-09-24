---
id: eli-002
titulo: Criterios INVEST para evaluar historias
fuente: Bill Wake, INVEST in Good Stories and Smart Tasks
tipo_fuente: practica_industria
tags: [invest, calidad, historia_usuario]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Criterios INVEST para evaluar historias de usuario

Antes de cerrar la elicitación, cada historia debe evaluarse contra los seis criterios INVEST.
Una historia que falla dos o más criterios se devuelve a conversación.

## I — Independiente

La historia puede implementarse sin depender del orden de otras. Si existe dependencia
obligatoria, debe declararse explícitamente en el campo de requerimientos relacionados.
*Pregunta de verificación:* ¿puede entregarse esta historia sola y aportar valor?

## N — Negociable

La historia describe el qué y el para qué, dejando el cómo abierto al diseño. Una historia
que prescribe la implementación no es negociable y bloquea al agente arquitecto.
*Pregunta de verificación:* ¿el enunciado deja libre la decisión técnica?

## V — Valiosa

El beneficio declarado es percibible por el rol que lo solicita. Las historias cuyo único
beneficiario es el equipo técnico deben reformularse o reclasificarse como deuda técnica.
*Pregunta de verificación:* ¿qué pierde el negocio si esta historia no se implementa?

## E — Estimable

El equipo puede dimensionar el esfuerzo. Si no puede, es porque falta información: el
elicitador debe volver a preguntar antes de cerrar.
*Pregunta de verificación:* ¿hay algún término del enunciado cuyo alcance no esté definido?

## S — Pequeña

La historia cabe en una unidad de trabajo razonable. Una historia con más de ocho criterios
de aceptación es señal de que debe dividirse.
*Pregunta de verificación:* ¿puede describirse su resultado en una sola frase?

## T — Verificable

Existe una forma objetiva de comprobar que está terminada. Toda historia debe poder
traducirse en al menos un criterio de aceptación en formato Gherkin.
*Pregunta de verificación:* ¿cómo sabremos, sin discutir, que esto quedó bien?

## Tabla de decisión

| Criterios fallidos | Acción del elicitador |
|---|---|
| 0 | Historia aceptada |
| 1 | Aceptada con observación registrada |
| 2 o más | Reabrir conversación sobre esa historia |
| Falla «Verificable» | Reabrir siempre, sin importar los demás |

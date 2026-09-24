---
id: eli-010
titulo: Ejemplo resuelto de elicitación completa
fuente: Elaboración propia con base en el dominio catastral
tipo_fuente: elaboracion_propia
tags: [ejemplo, referencia, conversacion]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Ejemplo resuelto de elicitación completa

Caso de referencia que ilustra el recorrido completo desde la conversación hasta el
requerimiento formal. Sirve como patrón de salida para el agente.

## Fragmento de la conversación

> **Cliente:** Necesitamos algo que nos ayude con las mutaciones, porque hoy se hace a mano
> y se demora mucho.
>
> **Agente:** ¿Qué cargo tiene la persona que procesa hoy esas mutaciones?
>
> **Cliente:** El analista de conservación catastral.
>
> **Agente:** Cuando el analista recibe una solicitud de mutación, ¿cuál es el primer paso
> que hace?
>
> **Cliente:** Verifica que el predio exista y que el documento soporte esté completo.
>
> **Agente:** ¿Qué condiciones hacen que una solicitud se rechace en esa verificación?
>
> **Cliente:** Si el número predial no existe, o si falta el documento público que soporta
> el cambio de propietario.
>
> **Agente:** ¿Qué datos necesita tener a la mano para procesarla?
>
> **Cliente:** El número predial, el tipo de mutación, la fecha del documento soporte y los
> datos del nuevo propietario.
>
> **Agente:** ¿Y qué debe entregar el sistema cuando la mutación se procesa con éxito?
>
> **Cliente:** Un radicado con la fecha y el estado, para poder hacerle seguimiento.

## Historia de usuario resultante

```
HU-007
Como analista de conservación catastral
quiero registrar una solicitud de mutación con su documento soporte
para tramitar el cambio en la información del predio y hacerle seguimiento
```

**Evaluación INVEST:** cumple los seis criterios. Independiente del resto del backlog,
negociable en su implementación, valiosa para el analista, estimable, pequeña y verificable.

## Requerimiento formal resultante (extracto)

| Campo | Valor |
|---|---|
| `id_requerimiento` | RF-021 |
| `modulo` | conservación |
| `precondicion` | El predio existe en la base catastral con ficha vigente |
| `regla_negocio` | La solicitud se acepta únicamente si el número predial existe y el documento soporte está presente con fecha no posterior a la fecha de radicación. Al aceptarse, se genera un radicado único y el estado inicial es «en trámite». |
| `datos_entrada` | numero_predial (string, obligatorio, 30 dígitos); tipo_mutacion (enum, obligatorio); fecha_documento (date, obligatorio); propietario_nuevo (objeto, obligatorio) |
| `datos_salida` | radicado (string), fecha_radicacion (datetime), estado (enum) |

## Criterios de aceptación

```
ESC-01 · Solicitud válida
DADO QUE existe un predio con número predial de 30 dígitos registrado en la base
Y se adjunta un documento soporte con fecha anterior a la de radicación
CUANDO se registra la solicitud de mutación
ENTONCES el sistema genera un radicado único y deja la solicitud en estado «en trámite»

ESC-02 · Predio inexistente
DADO QUE el número predial no corresponde a ningún predio registrado
CUANDO se registra la solicitud de mutación
ENTONCES el sistema rechaza la solicitud e informa que el predio no existe

ESC-03 · Documento soporte con fecha posterior
DADO QUE el documento soporte tiene fecha posterior a la fecha de radicación
CUANDO se registra la solicitud de mutación
ENTONCES el sistema rechaza la solicitud e informa la inconsistencia de fechas
```

## Observaciones sobre el proceso

El agente formuló seis preguntas, una por turno, y no avanzó a los datos hasta cerrar el
flujo. No inventó el formato del número predial: lo obtuvo de la base de conocimiento de
dominio. Registró como pregunta abierta el detalle de los tipos de mutación admitidos,
que el cliente no enumeró.

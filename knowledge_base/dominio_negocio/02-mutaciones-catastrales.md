---
id: dom-002
titulo: Mutaciones catastrales
fuente: IGAC, normativa de conservación catastral
tipo_fuente: normativa_nacional
tags: [mutacion, conservacion, reglas_negocio]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Mutaciones catastrales

Una mutación es el cambio que sufre un predio en cualquiera de sus componentes y que debe
incorporarse a la información catastral mediante el proceso de conservación. Es uno de los
conceptos de negocio que más aparece en los requerimientos del dominio.

## Clasificación por tipo

**Mutación de primera clase.** Cambio de propietario o poseedor, conservando el predio sus
demás características. Es la más frecuente. Se soporta en documento público de transferencia
inscrito en el registro de instrumentos públicos.

**Mutación de segunda clase.** Cambio en los límites del predio por adición o disminución
de área, o modificación de linderos, sin que varíe el número de predios.

**Mutación de tercera clase.** Cambio en el valor del predio por construcción, edificación
o demolición, es decir, modificación del componente de construcción.

**Mutación de cuarta clase.** Cambio en el número de predios, por englobe de varios predios
en uno o por división de uno en varios.

**Mutación de quinta clase.** Inscripción o cancelación de predios que antes no figuraban
en el catastro, o corrección de inconsistencias en la información.

## Reglas de negocio típicas

Estas reglas aparecen con frecuencia en los requerimientos del dominio y el agente debe
reconocerlas aunque el cliente no las enuncie completas:

1. Toda mutación requiere documento soporte. La naturaleza del documento depende de la
   clase de mutación: público e inscrito para primera clase, técnico para segunda y tercera.
2. La fecha del documento soporte no puede ser posterior a la fecha de radicación.
3. Una mutación de cuarta clase por englobe exige que todos los predios a englobar
   pertenezcan al mismo propietario y sean colindantes.
4. Una mutación de cuarta clase por división genera nuevos números prediales y cancela
   el número predial original.
5. Toda mutación que altere área o construcción obliga a recalcular el avalúo catastral.
6. Las mutaciones producen efectos fiscales a partir de la vigencia siguiente a su
   inscripción, salvo disposición expresa en contrario.

## Estados del trámite

| Estado | Significado |
|---|---|
| Radicada | La solicitud fue recibida y tiene número de radicado |
| En trámite | Está en estudio técnico o jurídico |
| Requerida | Se solicitó información adicional al peticionario |
| Aprobada | Procede y se incorporó a la base catastral |
| Rechazada | No procede; se expide acto motivado |
| Desistida | El peticionario no atendió el requerimiento en el plazo |

## Datos mínimos de una solicitud de mutación

Número predial, clase de mutación, tipo de documento soporte, número y fecha del documento,
identificación del solicitante, y según la clase: nuevo propietario, nueva área, nuevos
linderos o predios involucrados en el englobe o la división.

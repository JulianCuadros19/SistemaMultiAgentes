---
id: dom-007
titulo: Patrones de reglas de negocio del dominio
fuente: Elaboración propia con base en el dominio catastral y tributario
tipo_fuente: elaboracion_propia
tags: [reglas_negocio, patrones, validacion]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Patrones de reglas de negocio del dominio

Catálogo de estructuras de regla que aparecen repetidamente en los requerimientos del
dominio catastral y tributario. El agente elicitador debe reconocerlas para formular las
preguntas correctas y para redactar la regla de negocio sin ambigüedad.

## Patrón 1 · Regla de vigencia temporal

**Forma:** un valor aplicable depende del periodo al que corresponde la operación.

**Ejemplo:** el valor unitario de terreno aplicable es el de la zona homogénea del predio
para la vigencia que se está liquidando.

**Preguntas que activa:** ¿qué pasa si no existe valor para esa vigencia? ¿se toma el
anterior, se rechaza la operación o se calcula por indexación?

## Patrón 2 · Regla de precedencia normativa

**Forma:** existe un orden de aplicación entre varias normas o beneficios.

**Ejemplo:** cuando concurren una exención y un descuento por pronto pago, primero se
aplica la exención sobre el impuesto y luego el descuento sobre el saldo.

**Preguntas que activa:** ¿en qué orden se aplican? ¿son acumulables o excluyentes?

## Patrón 3 · Regla de tope o límite

**Forma:** un valor calculado no puede superar o descender de cierto umbral.

**Ejemplo:** el impuesto de la vigencia no puede superar el de la vigencia anterior
incrementado en el porcentaje máximo autorizado.

**Preguntas que activa:** ¿qué ocurre cuando se alcanza el tope? ¿se trunca, se difiere
el excedente o se genera una alerta?

## Patrón 4 · Regla de derivación

**Forma:** un valor se calcula a partir de otros mediante una fórmula explícita.

**Ejemplo:** el avalúo catastral es la suma del avalúo de terreno y el de construcción.

**Preguntas que activa:** ¿cómo se redondea? ¿cuántos decimales? ¿qué pasa si falta un
componente?

## Patrón 5 · Regla de existencia y consistencia referencial

**Forma:** una operación exige que exista previamente otra entidad relacionada.

**Ejemplo:** no puede radicarse una mutación sobre un predio que no existe en la base.

**Preguntas que activa:** ¿la verificación es en línea o diferida? ¿qué mensaje recibe
el usuario? ¿se permite crear la entidad faltante en el mismo trámite?

## Patrón 6 · Regla de estado y transición

**Forma:** una entidad solo puede pasar de un estado a otro por caminos permitidos.

**Ejemplo:** una solicitud rechazada no puede pasar a aprobada sin un nuevo trámite.

**Preguntas que activa:** ¿cuáles son todos los estados posibles? ¿qué transiciones están
permitidas? ¿quién puede ejecutar cada transición?

## Patrón 7 · Regla de trazabilidad obligatoria

**Forma:** toda modificación debe quedar asociada a su soporte documental y a su autor.

**Ejemplo:** todo cambio en la información predial queda vinculado al acto administrativo
que lo ordena.

**Preguntas que activa:** ¿qué datos deben quedar en el histórico? ¿se conserva la
información anterior o se sobrescribe?

## Patrón 8 · Regla de formato y dominio de valores

**Forma:** un dato solo admite ciertos valores o cierta estructura.

**Ejemplo:** el número predial nacional tiene exactamente treinta dígitos numéricos.

**Preguntas que activa:** ¿cuál es la lista completa de valores admitidos? ¿qué ocurre con
los valores heredados que no cumplen el formato actual?

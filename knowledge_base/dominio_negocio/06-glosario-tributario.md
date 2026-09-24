---
id: dom-006
titulo: Glosario tributario territorial
fuente: Régimen tributario territorial colombiano
tipo_fuente: normativa_nacional
tags: [tributario, glosario, impuesto_predial]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Glosario tributario territorial

Terminología del componente tributario, especialmente del impuesto predial, que es el
tributo directamente vinculado a la información catastral.

## Elementos de la obligación tributaria

**Hecho generador.** Acontecimiento que origina la obligación de pagar el tributo. En el
impuesto predial es la propiedad, posesión o usufructo de un bien inmueble.

**Sujeto activo.** Entidad titular del derecho a percibir el tributo. En el impuesto
predial es el municipio o distrito donde se ubica el predio.

**Sujeto pasivo.** Persona obligada al pago: el propietario o poseedor del inmueble.

**Base gravable.** Magnitud sobre la cual se aplica la tarifa. En el impuesto predial es,
por regla general, el avalúo catastral vigente.

**Tarifa.** Porcentaje o valor que se aplica a la base gravable, expresado habitualmente
por mil. Es diferencial según uso, estrato, área y destinación del predio.

**Liquidación.** Operación de determinar el valor a pagar aplicando la tarifa a la base
gravable y sumando o restando los conceptos accesorios.

**Vigencia fiscal.** Periodo anual al que corresponde la obligación tributaria.

## Conceptos accesorios

**Descuento por pronto pago.** Reducción porcentual aplicable cuando el pago se realiza
antes de una fecha límite establecida por el ente territorial.

**Intereses de mora.** Recargo que se causa sobre el impuesto no pagado dentro del plazo,
calculado según la tasa que fije la autoridad competente.

**Sanción.** Valor adicional impuesto por incumplimiento de deberes formales.

**Exención.** Beneficio que libera total o parcialmente del pago, otorgado por norma.

**Exclusión.** Situación en la que el hecho no está sujeto al tributo.

**Límite de crecimiento.** Tope al incremento del impuesto respecto de la vigencia anterior,
establecido para proteger al contribuyente de alzas abruptas por actualización catastral.

## Estructura típica de una liquidación

```
base_gravable            = avalúo catastral vigente
impuesto_bruto           = base_gravable × tarifa aplicable
impuesto_con_limite      = min(impuesto_bruto, tope de crecimiento)
descuentos               = descuento por pronto pago + exenciones aplicables
recargos                 = intereses de mora + sanciones
total_a_pagar            = impuesto_con_limite − descuentos + recargos
```

## Validaciones habituales

| Concepto | Regla de validación |
|---|---|
| Base gravable | Mayor que cero; corresponde al avalúo de la vigencia liquidada |
| Tarifa | Dentro del rango autorizado por el acuerdo municipal vigente |
| Vigencia | No puede liquidarse una vigencia futura |
| Descuento | Aplica solo si la fecha de pago es anterior al plazo fijado |
| Mora | Se calcula desde el día siguiente al vencimiento |
| Total | No puede ser negativo |

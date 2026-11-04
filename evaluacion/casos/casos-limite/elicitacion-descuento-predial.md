---
id: caso-limite-01
titulo: Descuento por pronto pago del impuesto predial en la ventanilla
cliente: Tesorería municipal de Valle Alto (sintética)
proyecto: Recaudo del impuesto predial
necesidad: "Necesitamos que la ventanilla de pagos calcule el descuento por pronto pago del impuesto predial y el valor a pagar; hoy el cajero lo calcula a mano y se equivoca."
version: 1.0
arquitecturas_esperadas: [ARQ-01]
reglas_ocultas:
  - id: R1
    descripcion: Un pago con fecha anterior al 1 de enero de la vigencia que se paga no se acepta.
    terminos: [enero]
  - id: R2
    descripcion: El descuento se redondea al peso, y descuento más valor a pagar suman exactamente el impuesto.
    terminos: [redonde, sum]
  - id: R3
    descripcion: Un predio que debe vigencias anteriores no recibe el descuento.
    terminos: [vigencias anteriores, descuento]
---

Caso sintético para evaluar si el elicitador explora los casos límite (ADR-0015). Las reglas de
la última sección son las que se escaparon en la verificación con el equipo del paso 12. No
contiene datos de Realtix ni de ninguna entidad real. Es lo que sabe la persona que hace de
cliente; el agente no lo ve.

## Quién eres

Eres la jefa de recaudo de una tesorería municipal. Conoces bien el impuesto predial, pero no
tienes formación técnica.

## Lo que sabes

- Quien lo usa es el cajero de la ventanilla de pagos.
- Lo necesitan para cobrar el valor correcto sin hacer cuentas a mano y evitar reclamos.
- Reglas del descuento por pronto pago, sobre el impuesto de la vigencia:
  - 15 % si se paga hasta el 31 de marzo;
  - 10 % si se paga hasta el 31 de mayo;
  - sin descuento después del 31 de mayo.
- El valor a pagar es el impuesto menos el descuento.
- El dinero se maneja en pesos, sin decimales.
- Datos que tiene el cajero a la mano:
  - número predial: 30 dígitos, obligatorio;
  - vigencia: el año que se paga, obligatorio;
  - valor del impuesto de la vigencia: en pesos, mayor que cero, obligatorio;
  - fecha de pago: obligatoria.
- Lo que debe entregar: el porcentaje de descuento aplicado, el valor del descuento y el valor a
  pagar.
- Ejemplo que usan para verificar: un impuesto de 1.000.000 pagado el 15 de marzo tiene un
  descuento de 150.000 y un valor a pagar de 850.000.
- Casos de error:
  - un impuesto de cero o negativo se rechaza con «El valor del impuesto debe ser mayor que
    cero»;
  - un número predial que no tiene 30 dígitos se rechaza con «Número predial inválido».
- Es de prioridad alta.

## Lo que solo dices si te preguntan

- Si la fecha de pago es anterior al 1 de enero de la vigencia que se paga, el pago no se
  acepta, porque no se puede pagar una vigencia que todavía no empieza. Se rechaza con «La
  vigencia todavía no empieza».
- El descuento se redondea al peso, con las mitades hacia arriba, y el valor a pagar es el
  impuesto menos ese descuento ya redondeado: así, descuento más valor a pagar siempre suman
  exactamente el impuesto.
- Si el predio debe impuesto de vigencias anteriores, no recibe descuento: paga el valor
  completo de la vigencia.

## Lo que no sabes

No sabes cómo se calcula el avalúo ni el impuesto: el cajero ya recibe el valor del impuesto. No
conoces detalles técnicos del sistema.

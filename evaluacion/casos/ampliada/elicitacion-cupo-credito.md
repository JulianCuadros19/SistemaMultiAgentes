---
id: caso-ampliada-05
titulo: Cupo de crédito rotativo de clientes
cliente: Almacenes El Trébol (sintética)
proyecto: Crédito rotativo de clientes
necesidad: Necesitamos administrar el cupo de crédito de nuestros clientes con compras a crédito, abonos y bloqueos por mora, sin que nadie quede debiendo más de su cupo. Queremos probar esas reglas sin depender de la base de datos, que vamos a reemplazar.
version: 1.0
arquitecturas_esperadas: [ARQ-02]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el gerente de cartera de una cadena de almacenes de electrodomésticos. Conoces las reglas
del crédito, pero no tienes formación técnica.

## Lo que sabes

- Quienes usan el cupo son las cajeras, al registrar una compra a crédito o un abono, y el área
  de cartera.
- Lo necesitan para no vender a crédito por encima de lo aprobado.
- Reglas que nunca pueden romperse:
  - Cada cliente tiene un cupo aprobado, y su saldo usado nunca puede superar ese cupo.
  - El cupo disponible es el cupo aprobado menos el saldo.
  - Una compra a crédito se rechaza si el saldo más la compra supera el cupo, con «Cupo
    insuficiente».
  - Un abono reduce el saldo. No puede ser mayor que el saldo: se rechaza con «El abono supera
    la deuda».
  - Si la cuota más antigua del cliente tiene más de 30 días de mora, el cliente queda bloqueado:
    no puede comprar a crédito, con «Cliente bloqueado por mora», pero sí puede abonar.
  - Los montos son en pesos sin decimales.
- Datos de cada operación:
  - documento del cliente, obligatorio;
  - cupo aprobado y saldo actual, en pesos;
  - días de mora de la cuota más antigua, un entero mayor o igual a cero;
  - tipo de operación, compra o abono, obligatorio;
  - monto de la operación, obligatorio y mayor que cero.
- Lo que debe entregar: el nuevo saldo y el cupo disponible, o el rechazo con el motivo.
- Ejemplos que usan para verificar:
  - cupo de 2.000.000, saldo de 1.500.000 y compra de 400.000: el saldo queda en 1.900.000 y el
    disponible en 100.000;
  - con el mismo cupo y saldo, una compra de 600.000 se rechaza por cupo insuficiente;
  - un cliente con 35 días de mora no puede comprar ni 10.000 pesos, pero sí abonar 200.000.
- Restricciones importantes:
  - Estas reglas son lo más importante del módulo. Deben poder probarse sin base de datos.
  - La base de datos actual la van a reemplazar, y quieren cambiar el almacenamiento sin tocar
    las reglas.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se aprueba el cupo ni cómo se calculan los intereses: no son parte de este
módulo. No conoces detalles técnicos del sistema.

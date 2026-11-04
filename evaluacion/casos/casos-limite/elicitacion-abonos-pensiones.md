---
id: caso-limite-02
titulo: Abonos y reversos en las facturas de pensión
cliente: Colegio Los Robles (sintético)
proyecto: Cartera de pensiones
necesidad: "Necesitamos registrar los abonos que hacen las familias a las facturas de pensión y reversar los que el banco devuelve; hoy lo llevamos en una hoja de cálculo."
version: 1.0
arquitecturas_esperadas: [ARQ-01]
reglas_ocultas:
  - id: R1
    descripcion: Reversar un abono cuando la factura tiene abonos posteriores devuelve solo ese abono; los demás siguen aplicados.
    terminos: [posterior, revers]
  - id: R2
    descripcion: Un abono ya reversado no se puede reversar otra vez.
    terminos: [ya fue reversado]
  - id: R3
    descripcion: Cada abono y cada reverso quedan en el historial de la factura, que nunca se borra.
    terminos: [historial]
---

Caso sintético para evaluar si el elicitador explora los casos límite (ADR-0015). La primera
regla de la última sección es la que se escapó en la verificación con el equipo del paso 12. No
contiene datos de Realtix ni de ninguna entidad real. Es lo que sabe la persona que hace de
cliente; el agente no lo ve.

## Quién eres

Eres la tesorera de un colegio. Conoces la facturación de pensiones, pero no tienes formación
técnica.

## Lo que sabes

- Quien lo usa es la auxiliar de tesorería.
- Lo necesitan para saber el saldo real de cada factura y no cobrarle de más a una familia.
- Reglas:
  - cada factura tiene un saldo, y cada abono lo disminuye;
  - si el saldo llega a cero, la factura queda «pagada»; si queda saldo, queda «abonada»;
  - un abono mayor que el saldo deja el excedente como saldo a favor de la familia;
  - un reverso anula un abono, por su referencia, y devuelve su valor al saldo de la factura;
  - el dinero se maneja en pesos, sin decimales.
- Datos de un abono: número de factura, referencia del abono (única), valor del abono en pesos y
  fecha del abono; todos obligatorios. Datos de un reverso: la referencia del abono y el motivo,
  obligatorios.
- Lo que debe entregar: el saldo de la factura, su estado («pagada» o «abonada») y el saldo a
  favor de la familia, si lo hay.
- Casos de error:
  - una factura que no existe se rechaza con «La factura no existe»;
  - un abono de cero o negativo se rechaza con «El valor del abono debe ser mayor que cero»;
  - el reverso de una referencia que no existe se rechaza con «El abono no existe».
- Es de prioridad alta.

## Lo que solo dices si te preguntan

- Si se reversa un abono y la factura ya tiene abonos posteriores, solo se devuelve el valor de
  ese abono: los demás siguen aplicados, y el estado se recalcula con el saldo que quede.
- Un abono que ya fue reversado no se puede reversar otra vez: se rechaza con «El abono ya fue
  reversado».
- Cada abono y cada reverso quedan en el historial de la factura, con su referencia, su fecha y
  su valor, y el historial nunca se borra.

## Lo que no sabes

No sabes cómo se emiten las facturas ni cómo llegan los pagos del banco. No conoces detalles
técnicos del sistema.

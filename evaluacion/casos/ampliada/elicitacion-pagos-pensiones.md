---
id: caso-ampliada-19
titulo: Reacciones a los pagos de pensiones escolares
cliente: Colegio Campestre Los Almendros (sintética)
proyecto: Aplicación de pagos de pensiones
necesidad: "La pasarela de pagos nos avisa cuando un pago queda confirmado o se reversa. Necesitamos que varios procesos reaccionen a esos avisos de manera independiente: aplicar el pago a la factura, generar o anular el recibo y actualizar el estado de cartera de la familia."
version: 1.0
arquitecturas_esperadas: [ARQ-06]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la tesorera de un colegio. Conoces la facturación de pensiones, pero no tienes formación
técnica.

## Lo que sabes

- La pasarela de pagos publica dos avisos:
  - pago confirmado: referencia del pago, número de factura, valor y fecha;
  - pago reversado: referencia del pago, fecha y motivo.

  La pasarela no espera respuesta ni sabe quién reacciona.
- Tres procesos reaccionan a cada aviso, cada uno por su lado:
  - aplicación: suma el pago a la factura. Si cubre el saldo, la factura queda «pagada»; si no,
    «abonada». Un pago mayor que el saldo deja un saldo a favor de la familia. Un reverso
    devuelve la factura a su estado anterior;
  - recibo: genera un recibo con consecutivo REC-000001, REC-000002…, con el valor y la
    factura. Ante un reverso, el recibo de ese pago queda anulado;
  - cartera: la familia está «al día» si no tiene facturas vencidas sin pagar, y «en mora» si
    tiene alguna.
- Reglas:
  - el dinero va en pesos sin decimales;
  - un mismo pago, con la misma referencia, recibido dos veces no se aplica dos veces.
- Ejemplo que usan para verificar: la factura FAC-10 por 850.000 recibe un pago confirmado de
  850.000; queda pagada y se genera el recibo REC-000001. Si el mismo aviso llega otra vez, se
  ignora. Si después llega el reverso, la factura vuelve a pendiente con saldo de 850.000 y el
  recibo queda anulado.
- Para las pruebas, el canal de los avisos puede funcionar en memoria.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se emiten las facturas de pensión ni cómo funciona la pasarela por dentro: no son
parte de este módulo. No conoces detalles técnicos del sistema.

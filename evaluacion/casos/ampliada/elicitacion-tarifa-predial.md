---
id: caso-ampliada-10
titulo: Servicio de consulta de la tarifa del impuesto predial
cliente: Secretaría de Hacienda de San Telmo (sintética)
proyecto: Servicio de tarifas prediales
necesidad: Varios sistemas de la alcaldía, como el portal de pagos y el de liquidación, necesitan consultar por la red la tarifa del impuesto predial de un predio según su destino y estrato; queremos un servicio con un contrato de consulta documentado.
version: 1.0
arquitecturas_esperadas: [ARQ-04]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el subdirector de impuestos de una secretaría de hacienda municipal. Conoces las tarifas,
pero no tienes formación técnica.

## Lo que sabes

- Quienes consultan son otros sistemas de la alcaldía, el portal de pagos y el sistema de
  liquidación, por la red (HTTP). No lo usa directamente una persona.
- Lo necesitan para que todos los sistemas usen la misma tarifa y no repitan la tabla.
- Tarifas, en pesos por cada mil pesos de avalúo:
  - residencial: estrato 1, 5; estrato 2, 6; estrato 3, 8; estrato 4, 10; estrato 5, 12;
    estrato 6, 14;
  - comercial: 11;
  - industrial: 12;
  - lote urbanizable no edificado: 33.
- Reglas:
  - el estrato solo aplica al destino residencial, y debe estar entre 1 y 6;
  - el impuesto es el avalúo por la tarifa dividido entre mil, redondeado al peso, con las
    mitades hacia arriba;
  - el dinero se maneja en pesos sin decimales.
- Operaciones que necesitan los otros sistemas:
  - consultar la tarifa de un destino, y de un estrato si es residencial;
  - calcular el impuesto dados el avalúo, el destino y el estrato.
- Ejemplo que usan para verificar: un predio residencial de estrato 3 con avalúo de 120.000.000
  tiene tarifa de 8 por mil y un impuesto de 960.000.
- Casos de error, que deben responderse como error con un mensaje claro:
  - estrato por fuera de 1 a 6 en residencial: «Estrato inválido»;
  - destino desconocido: «Destino económico no reconocido»;
  - avalúo de cero o negativo: «El avalúo debe ser mayor que cero».
- Restricción importante: los equipos de los otros sistemas necesitan saber exactamente qué
  enviar y qué reciben, así que el contrato de la consulta debe quedar documentado.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se calcula el avalúo ni cómo se pagan las facturas: no son parte de este servicio.
No conoces detalles técnicos del sistema.

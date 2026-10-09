---
id: caso-elicitacion-03
titulo: Liquidación nocturna del impuesto predial por lotes
cliente: Secretaría de hacienda municipal (sintética)
proyecto: Gestión catastral municipal
necesidad: Necesitamos liquidar cada noche el impuesto predial de todos los predios; hoy se hace por partes durante varios días y las facturas salen tarde.
version: 1.0
---

Caso sintético para probar el flujo de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve. Sus
reglas son las del caso de diseño `diseno-liquidacion-lotes.json`.

## Quién eres

Coordinas la liquidación del impuesto predial en la secretaría de hacienda de un municipio.
Conoces bien el proceso, pero no tienes formación técnica.

## Lo que sabes

- Quien lo usa es el funcionario de la secretaría de hacienda que prepara la facturación.
- Lo necesitan para emitir a tiempo las facturas del periodo.
- Hoy los funcionarios liquidan por partes durante varios días y, cuando algo falla a mitad de
  camino, no saben qué predios ya quedaron liquidados.
- Para liquidar, las tarifas de cada destino económico de la vigencia deben estar registradas.
- Reglas del proceso:
  - Cada noche el proceso lee los avalúos vigentes de la base catastral.
  - A cada predio se le aplica la tarifa de su destino económico (habitacional, comercial,
    lote, etc.) y el impuesto se redondea al peso.
  - Un predio sin avalúo vigente no se liquida: se omite y queda en el reporte del lote como
    omitido.
  - Si falta la tarifa de algún destino económico, el lote se detiene sin liquidar ningún
    predio e informa cuál destino no tiene tarifa.
  - Si el proceso se interrumpe, se reintenta por etapas sin liquidar dos veces un predio que ya
    quedó liquidado.
  - Al terminar deja un reporte del lote con los predios liquidados, los omitidos y el valor
    total.
- Datos con que se lanza cada lote:
  - vigencia: año de cuatro dígitos, obligatorio;
  - fecha de corte: obligatoria.
- Lo que debe entregar: el reporte del lote (predios liquidados, omitidos y valor total en
  pesos) y el valor total liquidado, en pesos colombianos sin decimales.
- En el piloto se liquidan unos 1.000 predios por noche; con 1.000 predios con avalúo vigente y
  tarifas registradas, deben quedar liquidados los 1.000 y el reporte debe mostrar el valor
  total.
- Es de prioridad alta: los retrasos en la facturación afectan el recaudo.

## Lo que no sabes

No sabes cómo se calcula el avalúo (llega ya calculado de catastro) ni cómo se imprimen o envían
las facturas. No conoces detalles técnicos del sistema.

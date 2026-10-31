---
id: caso-ampliada-01
titulo: Liquidación de comisiones de corretaje inmobiliario
cliente: Inmobiliaria Andina (sintética)
proyecto: Liquidación de comisiones
necesidad: Necesitamos calcular la comisión que gana cada asesor por cada negocio cerrado; hoy la calculamos a mano y los asesores reclaman porque los valores no cuadran.
version: 1.0
arquitecturas_esperadas: [ARQ-01]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Coordinas el área administrativa de una inmobiliaria mediana. Conoces bien cómo se pagan las
comisiones, pero no tienes formación técnica.

## Lo que sabes

- Quien liquida las comisiones es la auxiliar de pagos de asesores, al cierre de cada mes.
- Lo necesitan para pagar a cada asesor lo correcto y poder explicarle cómo se calculó.
- Para liquidar, el negocio debe estar cerrado: escritura firmada en una venta o contrato
  firmado en un arriendo.
- Reglas del cálculo:
  - En una venta, la comisión de la inmobiliaria es el 3 % del valor de venta.
  - En un arriendo, la comisión de la inmobiliaria es el 100 % del primer canon mensual.
  - Los asesores reciben el 40 % de la comisión de la inmobiliaria. Si el negocio lo cerraron
    dos asesores, ese 40 % se reparte en partes iguales.
  - Cada asesor recibe como mínimo 300.000 pesos por negocio cerrado, aunque el cálculo dé
    menos. Con dos asesores, el mínimo aplica a cada uno.
  - Los valores se expresan en pesos colombianos sin decimales, redondeados al peso más cercano.
- Datos que tiene la auxiliar:
  - tipo de negocio: venta o arriendo, obligatorio;
  - valor: el valor de venta o el canon mensual, en pesos, obligatorio y mayor que cero;
  - número de asesores: 1 o 2, obligatorio;
  - estado del negocio: cerrado o abierto, obligatorio.
- Lo que debe entregar: la comisión de la inmobiliaria y la comisión de cada asesor.
- Ejemplos que usan para verificar:
  - una venta de 300.000.000 pesos con un asesor: la inmobiliaria gana 9.000.000 y el asesor
    3.600.000;
  - un arriendo con canon de 1.000.000 y dos asesores: la inmobiliaria gana 1.000.000; el 40 %
    son 400.000, que darían 200.000 a cada uno, pero cada uno recibe el mínimo de 300.000.
- Casos de error:
  - si el negocio no está cerrado, se rechaza con «El negocio aún no está cerrado»;
  - un valor de cero o negativo se rechaza;
  - más de dos asesores se rechaza.
- Cómo se usa: la auxiliar lo usa dentro de su proceso de cierre de mes. Ningún otro sistema lo
  consulta. Son pocas reglas y casi no cambian.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se paga la nómina ni qué retenciones o impuestos se descuentan de la comisión: no
son parte de este cálculo. No conoces detalles técnicos del sistema.

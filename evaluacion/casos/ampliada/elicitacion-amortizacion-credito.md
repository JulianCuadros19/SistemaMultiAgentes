---
id: caso-ampliada-16
titulo: Simulador de amortización de créditos de vivienda
cliente: Fondo de Empleados Progreso (sintética)
proyecto: Simulador de crédito de vivienda
necesidad: Nuestros asesores necesitan una herramienta de terminal para calcular la cuota mensual de un crédito de vivienda y generar su tabla de amortización cuando atienden a un asociado.
version: 1.0
arquitecturas_esperadas: [ARQ-05]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la gerente de crédito de un fondo de empleados. Conoces las fórmulas del crédito, pero no
tienes formación técnica.

## Lo que sabes

- Quien la usa es el asesor de crédito, desde la terminal de su equipo, mientras atiende a un
  asociado. Ningún otro sistema la consulta.
- La necesitan para dar al asociado una cifra exacta y la misma en todas las oficinas.
- Operaciones, que se ejecutan por separado:
  - cuota: muestra la cuota mensual;
  - tabla: muestra la tabla de amortización completa y, si el asesor lo pide, la guarda en un
    archivo CSV;
  - resumen: muestra el total pagado y el total de intereses.
- Reglas del cálculo (cuota fija):
  - la tasa mensual es (1 + tasa efectiva anual) elevado a 1/12, menos 1;
  - la cuota es el monto por la tasa mensual, dividido entre 1 menos (1 + tasa mensual) elevado
    a menos el plazo;
  - cada mes, el interés es el saldo por la tasa mensual, y el abono a capital es la cuota menos
    el interés;
  - la última cuota se ajusta para que el saldo quede exactamente en cero;
  - los valores se redondean al peso y se calculan sin errores de redondeo de punto flotante.
- Datos:
  - monto, entre 10.000.000 y 500.000.000 pesos, obligatorio;
  - plazo en meses, entre 12 y 240, obligatorio;
  - tasa efectiva anual en porcentaje, entre 1 y 30, con hasta dos decimales, obligatoria.
- Ejemplo que usan para verificar: un crédito de 100.000.000 a 120 meses con tasa del 12 %
  efectiva anual tiene una cuota de 1.399.472 pesos. En el primer mes el interés es 948.879, el
  abono a capital 450.593 y el saldo queda en 99.549.407.
- Casos de error: un valor por fuera de los rangos se rechaza con un mensaje claro y un código de
  salida distinto de cero.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se aprueba el crédito ni qué seguros se cobran: no son parte de esta herramienta.
No conoces detalles técnicos del sistema.

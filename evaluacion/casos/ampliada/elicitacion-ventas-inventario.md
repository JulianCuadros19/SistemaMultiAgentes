---
id: caso-ampliada-18
titulo: Reacciones a las ventas de la caja
cliente: Supermercado La Esquina (sintética)
proyecto: Reacciones a las ventas
necesidad: Cada vez que la caja registra o anula una venta, publica un aviso. Necesitamos que varios procesos reaccionen por separado (descontar el inventario, alertar cuando un producto quede bajo el mínimo y acumular las ventas del día) sin frenar la caja.
version: 1.0
arquitecturas_esperadas: [ARQ-06]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el administrador de un supermercado de barrio. Conoces el inventario y la caja, pero no
tienes formación técnica.

## Lo que sabes

- La caja publica un aviso por cada venta registrada o anulada. La caja no puede esperar a los
  demás procesos ni saber cuáles son.
- El aviso de venta registrada trae el número de la venta, la fecha y hora y la lista de ítems,
  cada uno con su código de producto, cantidad y precio unitario en pesos. El de venta anulada
  trae el número de la venta y sus mismos ítems.
- Tres procesos reaccionan a cada aviso, cada uno por su lado:
  - inventario: descuenta las cantidades vendidas y las devuelve si la venta se anula. Las
    existencias nunca quedan negativas: si no alcanzan, quedan en cero y se registra una
    inconsistencia;
  - alertas: si tras una venta un producto queda por debajo de su mínimo, genera una alerta, una
    sola vez por día por producto;
  - acumulado del día: lleva el total vendido del día en pesos y las unidades por producto, y
    resta las ventas anuladas.
- Reglas: el dinero va en pesos sin decimales; un aviso repetido con el mismo número de venta no
  se procesa dos veces.
- Ejemplo que usan para verificar: el producto LECHE-1L tiene 12 unidades y mínimo 10. Una venta
  de 3 lo deja en 9 y genera la alerta «LECHE-1L por debajo del mínimo (9 de 10)»; otra venta de
  1 lo deja en 8 sin una nueva alerta ese día.
- Para las pruebas, el canal de los avisos puede funcionar en memoria.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se hacen los pedidos a los proveedores ni cómo se cierra la caja: no son parte de
este módulo. No conoces detalles técnicos del sistema.

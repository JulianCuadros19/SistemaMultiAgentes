---
id: caso-ampliada-06
titulo: Despacho de inventario por lotes
cliente: Droguería Central Mayorista (sintética)
proyecto: Despachos por lote
necesidad: Necesitamos despachar los pedidos tomando primero los lotes que vencen antes, sin dejar nunca existencias negativas ni despachar lotes vencidos. Son reglas críticas y queremos probarlas sin la base de datos.
version: 1.0
arquitecturas_esperadas: [ARQ-02]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la directora de operaciones de una droguería mayorista. Conoces bien la bodega y las reglas
de despacho, pero no tienes formación técnica.

## Lo que sabes

- Quien despacha es el jefe de bodega, al preparar cada pedido.
- Lo necesitan para que nunca salga un producto vencido o próximo a vencer y para que las
  existencias siempre cuadren.
- Reglas que nunca pueden romperse:
  - Cada producto tiene varios lotes, cada uno con su cantidad y su fecha de vencimiento.
  - Se despacha primero el lote que vence antes; si no alcanza, se sigue con el siguiente.
  - No se despachan lotes vencidos ni lotes que venzan en menos de 30 días contados desde la
    fecha del despacho.
  - Si las existencias aptas no alcanzan para el pedido completo, no se despacha nada: se
    rechaza con «Existencias insuficientes». No hay despachos parciales.
  - Las existencias de un lote nunca quedan negativas.
- Datos de cada despacho:
  - código del producto, obligatorio;
  - lotes del producto: código del lote, cantidad entera mayor o igual a cero y fecha de
    vencimiento;
  - cantidad pedida, entera y mayor que cero, obligatoria;
  - fecha del despacho, obligatoria.
- Lo que debe entregar: los lotes usados con la cantidad que se tomó de cada uno, y lo que queda
  en cada lote.
- Ejemplo que usan para verificar: con los lotes A (50 unidades, vence 2026-12-01), B (30
  unidades, vence 2026-11-15) y C (100 unidades, vence 2026-11-20), un despacho de 60 unidades
  el 2026-10-01 toma 30 de B y 30 de C; quedan A con 50, B con 0 y C con 70. Un lote D que vence
  el 2026-10-20 no se usa, porque vence en menos de 30 días.
- Restricciones importantes:
  - Estas reglas deben poder probarse sin la base de datos.
  - Más adelante las existencias podrían venir de otro sistema de inventarios, y no quieren
    cambiar las reglas por eso.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se reciben las compras ni cómo se facturan los pedidos: no son parte de este
módulo. No conoces detalles técnicos del sistema.

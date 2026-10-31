---
id: caso-ampliada-13
titulo: Servicio de reservas de parqueadero por franja horaria
cliente: Centro Empresarial Torre Alameda (sintética)
proyecto: Reservas de parqueadero
necesidad: Nuestra aplicación móvil necesita un servicio para que los empleados reserven cupos de parqueadero por franjas horarias, consulten sus reservas y las cancelen, sin que dos reservas usen el mismo cupo al mismo tiempo.
version: 1.0
arquitecturas_esperadas: [ARQ-04]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el administrador de un centro empresarial. Conoces cómo funciona el parqueadero, pero no
tienes formación técnica.

## Lo que sabes

- Quien lo usa es la aplicación móvil de los empleados, que lo consulta por la red (HTTP).
- Lo necesitan para acabar con las peleas por los cupos.
- Cada cupo tiene un código, como P1-05, y un piso.
- Cada reserva tiene:
  - un código, que asigna el servicio;
  - el cupo y el documento del empleado;
  - la fecha, la hora de inicio y la hora de fin;
  - su estado, activa o cancelada.
- Reglas:
  - las franjas van de 1 a 10 horas, entre las 6:00 y las 22:00, en horas en punto;
  - no se puede reservar en el pasado;
  - un cupo no puede tener dos reservas activas cuyas franjas se crucen;
  - un empleado no puede tener más de una reserva activa el mismo día;
  - una reserva se puede cancelar solo hasta una hora antes de su inicio.
- Operaciones:
  - crear una reserva;
  - listar las reservas de un empleado;
  - cancelar una reserva;
  - consultar los cupos libres en una franja.
- Para empezar basta con guardar los datos en memoria.
- Ejemplo que usan para verificar: si el cupo P1-05 está reservado el 2026-11-03 de 8:00 a
  12:00, otra reserva del mismo cupo de 11:00 a 13:00 se rechaza con «El cupo ya está reservado
  en esa franja», y una de 12:00 a 14:00 sí se permite, porque no se cruzan.
- Casos de error, que deben responderse como error con un mensaje claro: franja inválida,
  reserva en el pasado, cupo ocupado, segunda reserva del día y cancelación tardía.
- Restricción importante: el equipo de la aplicación móvil necesita un contrato de la interfaz
  documentado.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se cobra el parqueadero a los visitantes ni cómo funcionan las talanqueras: no son
parte de este servicio. No conoces detalles técnicos del sistema.

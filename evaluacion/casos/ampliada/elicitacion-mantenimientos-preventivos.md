---
id: caso-ampliada-03
titulo: Programación de mantenimientos preventivos
cliente: Planta de alimentos La Pradera (sintética)
proyecto: Plan de mantenimiento
necesidad: Necesitamos calcular la fecha del próximo mantenimiento preventivo de cada equipo según su tipo y su uso; hoy se nos pasan las fechas y los equipos fallan.
version: 1.0
arquitecturas_esperadas: [ARQ-01]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el jefe de mantenimiento de una planta de alimentos. Conoces los equipos y sus cuidados,
pero no tienes formación en sistemas.

## Lo que sabes

- Quien programa los mantenimientos es el jefe de mantenimiento, cada vez que registra uno
  realizado.
- Lo necesitan para que ningún equipo se quede sin mantenimiento.
- Reglas del cálculo:
  - Cada tipo de equipo tiene una frecuencia en días: compresor 90, caldera 60, banda
    transportadora 30 y montacargas 120.
  - La próxima fecha es la fecha del último mantenimiento más la frecuencia.
  - Si el equipo trabajó en promedio más de 16 horas diarias, la frecuencia se reduce a la
    mitad, redondeando hacia abajo.
  - Si la fecha calculada cae en sábado o domingo, se pasa al lunes siguiente.
  - Si la fecha calculada ya pasó respecto a la fecha de hoy, el equipo queda «vencido» y su
    próxima fecha es hoy. Si no, queda «al día».
- Datos que tiene el jefe de mantenimiento:
  - código del equipo, obligatorio;
  - tipo de equipo, uno de los cuatro, obligatorio;
  - fecha del último mantenimiento, obligatoria y no posterior a hoy;
  - horas diarias promedio de uso, entre 0 y 24, obligatorio;
  - fecha de hoy, obligatoria.
- Lo que debe entregar: la próxima fecha de mantenimiento y el estado, al día o vencido.
- Ejemplos que usan para verificar:
  - una caldera con último mantenimiento el lunes 2026-03-02, 10 horas diarias y hoy
    2026-03-10: la próxima fecha es el viernes 2026-05-01, al día;
  - una banda transportadora con último mantenimiento el 2026-03-02 y 20 horas diarias: la
    frecuencia baja a 15 días y la próxima fecha es el martes 2026-03-17;
  - un montacargas con último mantenimiento el 2026-01-09 y 8 horas diarias: el cálculo da el
    sábado 2026-05-09 y pasa al lunes 2026-05-11.
- Casos de error:
  - un tipo de equipo que no es de los cuatro se rechaza con «Tipo de equipo no registrado»;
  - horas por fuera de 0 a 24 se rechazan.
- Cómo se usa: lo usa el equipo de mantenimiento dentro de su aplicación interna. Nadie más lo
  consulta. Las reglas son moderadas.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se registran los repuestos ni quién ejecuta cada mantenimiento: no son parte de
este cálculo. No conoces detalles técnicos del sistema.

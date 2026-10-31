---
id: caso-ampliada-20
titulo: Reacciones a las lecturas de los sensores de cuartos fríos
cliente: Cooperativa Lechera El Páramo (sintética)
proyecto: Monitoreo de cuartos fríos
necesidad: Los sensores de nuestros cuartos fríos publican una lectura de temperatura cada minuto. Necesitamos que varios procesos reaccionen a cada lectura por separado (detectar alarmas, guardar el histórico y contar las alarmas por turno) sin que los sensores esperen a nadie.
version: 1.0
arquitecturas_esperadas: [ARQ-06]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el jefe de calidad de una cooperativa lechera. Conoces las condiciones de frío, pero no
tienes formación técnica.

## Lo que sabes

- Cada sensor publica una lectura por minuto. Los sensores no esperan respuesta ni saben quién
  usa sus lecturas.
- La lectura trae el sensor, el cuarto, la fecha y hora y la temperatura en grados Celsius con un
  decimal.
- Tres procesos reaccionan a cada lectura, cada uno por su lado:
  - alarmas: el rango permitido es de 2,0 a 6,0 °C. Se abre una alarma cuando hay tres lecturas
    seguidas del mismo cuarto fuera del rango, y se cierra con dos lecturas seguidas dentro del
    rango;
  - histórico: guarda cada lectura y permite consultar el promedio, la mínima y la máxima por
    cuarto y por día;
  - conteo por turno: cuenta las alarmas abiertas en cada turno: de 6:00 a 14:00, de 14:00 a
    22:00 y de 22:00 a 6:00.
- Reglas: una lectura por fuera de −30 a 50 °C es un error del sensor; se descarta, se registra
  y no cuenta para las alarmas.
- Ejemplo que usan para verificar: el cuarto C1 recibe 5,5, 6,4, 6,8 y 7,0 °C a las 10:00,
  10:01, 10:02 y 10:03. La alarma se abre a las 10:03, con la tercera lectura seguida fuera de
  rango, y cuenta en el turno de 6:00 a 14:00. Si luego llegan 5,0 y 4,8, la alarma se cierra.
- Para las pruebas, el canal de las lecturas puede funcionar en memoria.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se instalan los sensores ni a quién se notifica una alarma: no son parte de este
módulo. No conoces detalles técnicos del sistema.

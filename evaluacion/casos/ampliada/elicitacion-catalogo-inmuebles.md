---
id: caso-ampliada-11
titulo: Servicio de catálogo de inmuebles en arriendo
cliente: Plataforma Arriendo Fácil (sintética)
proyecto: Catálogo de inmuebles
necesidad: Nuestro portal web necesita un servicio para registrar inmuebles en arriendo, consultarlos, buscarlos por ciudad y precio máximo, y cambiar su estado cuando se reservan o se arriendan.
version: 1.0
arquitecturas_esperadas: [ARQ-04]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la gerente de producto de una plataforma de arriendos. Sabes qué necesita el portal, pero no
tienes formación técnica.

## Lo que sabes

- Quienes lo usan son el portal web y la aplicación de los asesores. Son otros sistemas que lo
  consultan por la red (HTTP).
- Lo necesitan para mostrar a los interesados solo los inmuebles que siguen disponibles.
- Cada inmueble tiene:
  - un código, que asigna el servicio al registrarlo;
  - ciudad y barrio;
  - área en metros cuadrados, mayor que cero;
  - número de habitaciones, un entero mayor o igual a cero;
  - canon mensual en pesos sin decimales, mayor que cero;
  - estado: disponible, reservado o arrendado. Al registrarse queda disponible.
- Operaciones:
  - registrar un inmueble;
  - consultarlo por su código;
  - listar los inmuebles con filtros opcionales de ciudad y canon máximo, ordenados por canon de
    menor a mayor;
  - cambiar su estado.
- Cambios de estado permitidos: de disponible a reservado, de reservado a arrendado, de
  reservado a disponible y de arrendado a disponible. No se puede pasar de disponible a
  arrendado directamente.
- Para empezar basta con guardar los inmuebles en memoria.
- Ejemplo que usan para verificar: con tres inmuebles en Bogotá de cánones 1.800.000, 2.500.000 y
  1.200.000, listar Bogotá con canon máximo de 2.000.000 devuelve los de 1.200.000 y 1.800.000,
  en ese orden.
- Casos de error, que deben responderse como error con un mensaje claro:
  - consultar un código que no existe: «Inmueble no encontrado»;
  - un cambio de estado no permitido: error que indique el estado actual.
- Restricción importante: el equipo del portal necesita un contrato de la interfaz explícito y
  documentado.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se firman los contratos ni cómo se cobra el arriendo: no son parte de este
servicio. No conoces detalles técnicos del sistema.

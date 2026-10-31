---
id: caso-ampliada-12
titulo: Servicio de validación del dígito de verificación del NIT
cliente: Cámara de Comercio de Puerto Claro (sintética)
proyecto: Servicio de validación de NIT
necesidad: El portal de registro y el sistema de facturación necesitan consultar por la red si un NIT es válido calculando su dígito de verificación; queremos un servicio único con un contrato documentado para no repetir esa lógica en cada sistema.
version: 1.0
arquitecturas_esperadas: [ARQ-04]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres el coordinador de registros de una cámara de comercio. Conoces cómo se valida un NIT, pero
no tienes formación técnica.

## Lo que sabes

- Quienes lo usan son otros sistemas, el portal de registro y el sistema de facturación, que lo
  consultan por la red (HTTP).
- Lo necesitan para no registrar ni facturar a un NIT mal digitado.
- Cómo se calcula el dígito de verificación:
  - se toman los dígitos del número, de derecha a izquierda;
  - se multiplican por los pesos 3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67 y 71, en
    ese orden;
  - se suman los productos y se calcula el residuo de dividir la suma entre 11;
  - si el residuo es 0 o 1, el dígito es el residuo; si no, el dígito es 11 menos el residuo.
- Datos:
  - el número tiene de 1 a 15 dígitos; si llega con puntos o guiones, se quitan antes de
    calcular;
  - el dígito de verificación, cuando se valida, es un dígito de 0 a 9.
- Operaciones:
  - calcular el dígito de verificación de un número;
  - validar un NIT completo, con su número y su dígito, e informar si es válido y, si no lo es,
    cuál era el dígito esperado.
- Ejemplos que usan para verificar:
  - el número 900123456 tiene dígito 8, así que «900.123.456-8» es válido y «900123456-7» no lo
    es, con dígito esperado 8;
  - el número 123456789 tiene dígito 6.
- Casos de error, que deben responderse como error con un mensaje claro:
  - un número con letras: «El NIT solo admite dígitos»;
  - más de 15 dígitos: «El NIT admite como máximo 15 dígitos».
- Restricción importante: los equipos de los dos sistemas necesitan un contrato documentado de
  qué enviar y qué reciben.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se registra una empresa ni cómo se emite una factura: no son parte de este
servicio. No conoces detalles técnicos del sistema.

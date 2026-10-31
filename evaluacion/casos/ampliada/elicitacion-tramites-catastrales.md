---
id: caso-ampliada-17
titulo: Reacciones a los cambios de estado de trámites catastrales
cliente: Oficina de catastro de Monte Verde (sintética)
proyecto: Seguimiento de trámites
necesidad: Cuando el sistema de radicación cambia el estado de un trámite catastral, publica un aviso. Necesitamos que varios procesos reaccionen a ese aviso por separado (bitácora, indicador de tiempos y mensaje al ciudadano) sin que el sistema de radicación tenga que esperarlos ni conocerlos.
version: 1.0
arquitecturas_esperadas: [ARQ-06]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la coordinadora de atención al ciudadano de una oficina de catastro. Conoces los trámites,
pero no tienes formación técnica.

## Lo que sabes

- Otro proceso, el sistema de radicación, publica un aviso cada vez que un trámite cambia de
  estado. Ese sistema no debe esperar a nadie ni saber quién reacciona.
- El aviso trae:
  - el número del trámite;
  - el tipo de trámite: mutación, rectificación o certificado;
  - el estado anterior y el estado nuevo: radicado, en revisión, aprobado o rechazado;
  - la fecha y hora;
  - el funcionario.
- Tres procesos reaccionan al mismo aviso, cada uno por su lado:
  - bitácora: registra cada aviso con todos sus datos;
  - indicador de tiempos: cuando un trámite llega a aprobado o rechazado, calcula los días
    hábiles (lunes a viernes) desde que se radicó y lleva el promedio por tipo de trámite;
  - mensaje al ciudadano: prepara el texto del aviso, sin enviarlo:
    - aprobado: «Su trámite N fue aprobado»;
    - rechazado: «Su trámite N fue rechazado; puede consultar el motivo en la oficina»;
    - en revisión: «Su trámite N está en revisión».
- Reglas:
  - las transiciones válidas son de radicado a en revisión y de en revisión a aprobado o a
    rechazado;
  - un aviso con una transición inválida, por ejemplo de aprobado a en revisión, no se procesa y
    queda en la bitácora marcado como inválido;
  - los procesos son independientes: si uno falla con un aviso, los demás lo procesan igual.
- Ejemplo que usan para verificar: el trámite T-0001, radicado el lunes 2026-11-02 y aprobado el
  viernes 2026-11-06, tardó 4 días hábiles, y su mensaje es «Su trámite T-0001 fue aprobado».
- Para las pruebas, el canal de los avisos puede funcionar en memoria.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se radican los trámites ni cómo se envían los mensajes al ciudadano: no son parte
de este módulo. No conoces detalles técnicos del sistema.

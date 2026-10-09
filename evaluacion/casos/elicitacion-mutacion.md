---
id: caso-elicitacion-01
titulo: Registro de solicitudes de mutación de propietario
cliente: Oficina de catastro municipal (sintética)
proyecto: Gestión catastral municipal
necesidad: Necesitamos registrar las solicitudes de mutación de propietario de los predios; hoy llegan en papel y algunas se pierden.
version: 1.0
---

Caso sintético para probar el agente elicitador. No contiene datos de Realtix ni de ninguna
entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la coordinadora del área de conservación catastral de una oficina municipal. Conoces bien
el proceso, pero no tienes formación técnica.

## Lo que sabes

- Quien registra las solicitudes es el analista de conservación catastral.
- Lo necesitan para tramitar el cambio de propietario en la información del predio y hacer
  seguimiento a cada solicitud hasta que se resuelva.
- Hoy el ciudadano entrega la solicitud en papel en la ventanilla; el analista la anota en una
  hoja de cálculo y a veces las solicitudes se pierden.
- Reglas del proceso:
  - La solicitud solo se acepta si el número predial existe en la base catastral.
  - El documento soporte es obligatorio: escritura pública o sentencia judicial.
  - La fecha del documento soporte no puede ser posterior a la fecha de radicación.
  - Al aceptar la solicitud se le asigna un radicado y queda en estado «en trámite».
- Datos que el analista tiene a la mano al registrar:
  - número predial: 30 dígitos, obligatorio;
  - tipo de documento soporte: escritura pública o sentencia judicial, obligatorio;
  - fecha del documento soporte: obligatoria;
  - número de identificación del nuevo propietario: obligatorio;
  - nombre completo del nuevo propietario: obligatorio.
- Lo que debe entregar el registro: el número de radicado con el formato RAD-año-consecutivo de
  seis dígitos (por ejemplo, RAD-2026-000123), la fecha de radicación y el estado de la
  solicitud.
- Casos de error:
  - si el número predial no existe, la solicitud se rechaza indicando que el predio no existe;
  - si la fecha del documento es posterior a la radicación, se rechaza indicando la
    inconsistencia de fechas;
  - si falta el documento soporte, se rechaza indicando que es obligatorio.
- Se reciben unas 40 solicitudes al día.
- Es de prioridad alta: es el trámite que más reclamos genera.

## Lo que no sabes

No sabes cómo se calcula el avalúo ni cómo se liquida el impuesto predial: no son parte de este
trámite. No conoces detalles técnicos del sistema.

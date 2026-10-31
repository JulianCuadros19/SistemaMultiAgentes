---
id: caso-ampliada-04
titulo: Ciclo de vida de contratos de arrendamiento
cliente: Inmobiliaria Horizonte Sur (sintética)
proyecto: Ciclo de vida de contratos
necesidad: Necesitamos controlar el ciclo de vida de los contratos de arrendamiento sin que se crucen dos contratos vigentes sobre el mismo inmueble. Las reglas son delicadas y queremos probarlas sin base de datos, porque el almacenamiento lo vamos a cambiar el próximo año.
version: 1.0
arquitecturas_esperadas: [ARQ-02]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la abogada que dirige el área jurídica de una inmobiliaria. Conoces a fondo las reglas de
los contratos, pero no tienes formación técnica.

## Lo que sabes

- Quien gestiona los contratos es el área jurídica.
- Lo necesitan para que nunca haya dos arrendatarios con derecho sobre el mismo inmueble al
  mismo tiempo.
- Reglas que nunca pueden romperse:
  - Los estados son borrador, vigente, terminado y anulado. Solo se permite pasar de borrador a
    vigente, de vigente a terminado y de borrador a anulado. Un contrato terminado o anulado ya
    no cambia.
  - Un inmueble no puede tener dos contratos vigentes cuyos periodos se crucen.
  - Para activar un contrato, debe tener arrendatario, canon mayor que cero y fecha de fin
    posterior a la de inicio, con una duración mínima de seis meses.
  - Para terminar un contrato se exige un motivo y una fecha de terminación dentro del periodo
    del contrato.
  - Cada cambio de estado queda registrado con la fecha y el usuario que lo hizo.
- Datos de cada contrato:
  - código del contrato y código del inmueble, obligatorios;
  - documento del arrendatario, obligatorio para activar;
  - canon mensual en pesos sin decimales;
  - fecha de inicio y fecha de fin;
  - usuario que hace el cambio, obligatorio.
- Lo que debe entregar: el contrato con su nuevo estado, o el rechazo con el motivo.
- Ejemplo que usan para verificar: si el inmueble INM-100 tiene un contrato vigente del
  2026-01-01 al 2026-12-31, activar otro sobre INM-100 del 2026-06-01 al 2027-05-31 se rechaza
  con «El inmueble ya tiene un contrato vigente en ese periodo»; uno del 2027-01-01 al
  2027-12-31 sí se activa.
- Casos de error: una transición no permitida se rechaza indicando el estado actual del
  contrato.
- Restricciones importantes:
  - Estas reglas son el activo principal. Deben poder probarse sin base de datos ni ninguna
    infraestructura.
  - Hoy los contratos se guardan en archivos. El próximo año pasarán a otra base de datos, y no
    quieren tener que tocar las reglas por eso.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se cobra el canon ni cómo se firman los contratos: no son parte de este módulo.
No conoces detalles técnicos del sistema.

---
estado: aceptada
fecha: 2026-11-03
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (enmiendas desde N17), ADR-0008 (casos límite y enmiendas de los requerimientos), ADR-0010 (escenarios ejecutables y revisiones del registro de decisión), ADR-0011 (pruebas por interfaces públicas y versión previa tras un rediseño) y ADR-0012 (pruebas que simulan el efecto)
---

# ADR-0015 · Calidad de la primera salida y enmiendas de los requerimientos desde N17

## Contexto y planteamiento del problema

La verificación con el equipo del paso 12 (ADR-0014) dejó en claro que la primera salida del
sistema suele necesitar correcciones.

- **Corrida ampliada** (ADR-0014, 2026-10-31):
  - Solo 10 de 19 módulos se validaron en la v1.
  - Los bloqueantes de la v1 fueron:
    - CAL-FS-001, «la prueba pasa, pero no verifica el escenario», en 5 casos (05, 08, 09, 11
      y 19);
    - CAL-FS-002 en 2;
    - CAL-MT-002 en 1;
    - CAL-SG-006 en 1.
  - N10 falló la verificación estructural en 7 de 29 primeros intentos.
- **Pensiones** (`5f5d2739`, ARQ-06):
  - tres diseños seguidos pasaron N9 sin que sus escenarios se pudieran ejecutar con interfaces
    públicas: no decían dónde viven las facturas, los recibos ni las familias;
  - el juez de N14 aceptó en la v4 pruebas que pegaban al aviso atributos no declarados y
    restauraban la factura dentro de la propia prueba, el mismo patrón que había rechazado en la
    v3;
  - tras cada rediseño, N10 generó desde cero y perdió lo que ya estaba bien;
  - el almacén guardaba un solo saldo anterior por factura, y reversar el primero de dos abonos
    deshacía el segundo. Solo lo atrapó una prueba propia.
- **Predial** (`61e1e121`, ARQ-01):
  - el tester aprobó la v1;
  - los dos ciclos de N17 vinieron de reglas que el cliente no dijo: una fecha anterior a la
    vigencia, que se ocultó a propósito, y que los redondeos sumen el impuesto;
  - el elicitador no exploró casos límite;
  - las reglas agregadas en N17 quedaron en el código y en la trazabilidad, pero no en los RF
    exportados.

**Tres causas raíz:**
1. **Requerimientos sin casos límite.** El elicitador pasa al resumen apenas cada atributo tiene
   algo. dom-007 ya trae las preguntas de las tres reglas que aparecieron en N17.
2. **Diseños cuyos escenarios no son ejecutables.** Ningún prompt del arquitecto habla de
   escenarios ni de dónde vive el estado, y N9 solo valida la forma.
3. **Pruebas que simulan el efecto.** El prompt del desarrollador no lo prohíbe, y el juez no lo
   detecta: no ve la especificación, y la versión 1.1 de su prompt admite preparar el estado en la
   prueba.

## Factores de decisión

- Que la primera versión del módulo pase al tester y a la persona.
- Que lo que se agrega en N17 quede en los requerimientos y se pruebe.
- No tocar el Anexo B ni las decisiones de `CLAUDE.md` que no se revierten.
- Cuidar la convergencia y el costo de la elicitación.

## Opciones consideradas

Para la regla nueva que aparece en N17:
1. **Por el elicitador:**
   - N17 envía a N5, que agrega la regla y un escenario al RF afectado, sin renumerar;
   - N6 aprueba el RF enmendado;
   - N16 rehace el plan de pruebas;
   - N10 corrige.
2. **Enmienda directa en N17:** la persona escribe la regla y su escenario, y el código los agrega
   al RF sin modelo.
3. **Solo mejorar el elicitador.**

## Resultado de la decisión

### Decisiones del equipo (2026-11-03)

1. **Corregir los defectos de las interfaces,** salvo los nombres de revisor: las decisiones 32
   a 35 del ADR-0014.
2. **Pulir a los agentes con evidencia.** Cada hallazgo se reproduce con una prueba o un caso que
   falle antes de corregirlo, y se mide después.
3. **El elicitador explora casos límite antes del resumen,** sin romper la convergencia.
4. **Una regla nueva en N17 entra al requerimiento por el elicitador** (opción 1).
   - Mantiene que solo N5 y N6 escriban requerimientos y que solo cinco nodos usen modelo.
   - Cambia la arquitectura aprobada: N17 gana un destino, y N16 una arista hacia N10.
5. **La arquitectura puede cambiar.** La lista «Cambios para el documento de tesis» consolida la
   versión final.

### Plan

| Fase | Agente | Qué cambia |
|---|---|---|
| 2 | Tester | Detector determinista y juez con criterios para las pruebas que simulan el efecto |
| 3 | Arquitecto | Cada escenario se ejecuta con interfaces públicas, N9 lo verifica, y el registro recoge los rediseños |
| 4 | Desarrollador | Pruebas por interfaces públicas, contra las causas de reintento, y la versión previa tras un rediseño |
| 5 | Elicitador | Casos límite acotados antes del resumen |
| 6 | Orquestador y elicitador | Enmiendas desde N17: N17 → N5 → N6 → N16 → N10 |
| 7 | Todos | Medición de extremo a extremo con los 20 casos ampliados |

### Decisiones de implementación

_Se registran al cerrar cada fase._

## Verificación

_Pendiente._ Criterios, fijados antes de medir:
- validados en la v1: al menos 15 de 19 (hoy 10);
- primeros intentos de N10 rechazados: como máximo 2 de 29 (hoy 7);
- ninguna sesión escalada (hoy 1);
- costo medio por módulo: como máximo 0,35 USD (hoy 0,28);
- ningún falso positivo del patrón «prueba que simula» en el corpus de defectos;
- la elicitación no retrocede (como máximo 211 turnos y al menos 17 de 20 resúmenes confirmados)
  y captura al menos 2 de 3 reglas ocultas.

## Cambios para el documento de tesis

_Se completan en cada fase,_ con la arquitectura vigente al cierre del paso 12.

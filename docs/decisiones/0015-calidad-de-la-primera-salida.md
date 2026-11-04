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

#### Fase 2 · El tester reconoce las pruebas que simulan el efecto

6. **Detector determinista** (modifica el ADR-0012 y el ADR-0011).
   - `core/conformidad.py` marca tres patrones, compartidos por N10 y N12:
     - asignar a un objeto del módulo un atributo que su clase no tiene;
     - hacer lo mismo con `setattr` u `object.__setattr__`;
     - un `raise` dentro de un bloque `pytest.raises`.
   - **Atributos válidos de una clase:** los de su firma, los de su entidad en el modelo de datos
     y los de su implementación.
   - **Qué cuenta como objeto del módulo:** el que construye una clase declarada, el que devuelve
     una función declarada y el que devuelve un ayudante del propio archivo de pruebas.
   - **No se marca:**
     - cambiar un campo que la clase sí tiene, aunque sea con `object.__setattr__`, para probar
       que el módulo lo vuelve a validar;
     - el monkeypatch de nombres privados, que tiene usos legítimos y usa el control de avalúo;
     - los objetos que no son del módulo.
   - **Regla nueva CAL-FS-006** (alta), en cal-fs 1.2. El corpus se volvió a ingerir: 36 documentos
     y 187 fragmentos. En N12 se reporta como CAL-FS-006; en N10, como «RF-18 · pruebas», así que
     el reintento lo corrige antes de que llegue al tester.
   - **Generalidad:** se aplicó a las 55 versiones guardadas, de las seis arquitecturas.
     - Solo marca la v3 y la v4 de pensiones, las que inyectaban `saldo_factura` y
       `numero_factura`.
     - Una primera versión del detector marcaba además la v1 y la v2 por un `object.__setattr__`
       sobre un campo declarado. Era un falso positivo, y por eso existe la excepción de arriba.
7. **El juez ve la especificación y juzga con criterios generales** (modifica el ADR-0012).
   - Recibe las interfaces públicas, con su firma, y el modelo de datos.
   - **Prompt `tester.veredicto` 1.2:**
     - la prueba prepara con interfaces públicas o con dobles de las dependencias externas;
     - el «entonces» se verifica sobre lo que produjo el módulo;
     - cuatro formas nuevas de no cumplir:
       - el resultado lo arma la propia prueba;
       - la prueba aplica o restaura ella misma el efecto;
       - agrega a los objetos datos que sus clases no tienen;
       - lanza ella misma la excepción;
     - si la especificación no ofrece cómo preparar u observar, el caso no cumple, y la
       justificación lo dice para que cambie el diseño.
   - **Dos precisiones, que destapó la medición:**
     - el rechazo vale en cualquier interfaz pública de entrada, también la que construye el
       dato;
     - una prueba más precisa que el escenario cumple, si lo que agrega es coherente con él.
8. **Segunda opinión antes de rechazar** (modifica el ADR-0012).
   - Los casos que el juez marca como incumplidos se juzgan de nuevo, solos. Un caso se rechaza
     solo si las dos opiniones coinciden, y si la segunda llamada falla vale la primera.
   - **Razón:** un rechazo le cuesta al flujo un ciclo de corrección, de 0,05 a 0,2 USD y varios
     minutos, mientras que una llamada al juez cuesta unos 0,001 USD.
9. **Corpus de defectos para pruebas que simulan** (modifica el ADR-0012).
   - **Corpus nuevo de pagos** (ARQ-06, con estado), a partir de la v6 validada de `5f5d2739`.
     - Se ajustó a mano, como el de avalúo: la especificación ganó una consulta pública de
       recibos y el campo `motivo`, y las pruebas observan solo por interfaces públicas.
     - Inyecciones:
       - D01: un atributo inyectado con `object.__setattr__`, para N12;
       - J01: la factura restaurada se arma en un diccionario, para el juez;
       - J02: la cartera la actualiza una función de la prueba suscrita al bus, para el juez.
     - Casos: `evaluacion/casos/desarrollo-pagos.json` y `diseno-pagos.json`.
   - **Avalúo:**
     - D17: un atributo inyectado, para N12;
     - J04: el resultado lo arma la prueba, para el juez;
     - J03, la excepción lanzada por la propia prueba, ahora la detecta N12.
   - `scripts/evaluar_tester.py` gana la opción `--traza`.

**Verificación de la fase 2.**
- **Sin costo:** 606 pruebas unitarias, 31 de integración, 33 del entorno aislado y 19 de
  embeddings.
- **Corpus:** 3 corridas por medición, sobre 24 variantes (3 controles y 21 defectos), con la
  traza en `docs/mediciones/paso-12-tester.jsonl`.

| Medición | Defectos detectados | Controles aprobados | Casos marcados fuera de lo esperado | USD |
|---|---|---|---|---|
| Prompt 1.2, control de pagos sin ajustar | 63 de 63 | 6 de 9 | 37 | 0,029 |
| Control ajustado y precisión del rechazo | 63 de 63 | 9 de 9 | 7, de ellos 5 detecciones correctas | 0,028 |
| Con segunda opinión | 63 de 63 | 9 de 9 | 3, todas detecciones correctas del D01 | 0,037 |

- **Las 49 versiones reales guardadas,** juzgadas otra vez con el tester actual y comparadas con su
  veredicto original. La traza local está en `data/local/rejuzgar-paso-12.jsonl`; costó 0,12 USD.
  - **Coincidencia:** 39 de 49 sin la segunda opinión y 40 de 49 con ella.
  - **Cambios con la segunda opinión:**
    - **atrapa** el falso positivo, la v4 de pensiones;
    - **rechaza** una prueba que compara con un valor fabricado por ella misma (`f6c482e5`, ARQ-05);
    - **corrige** tres rechazos falsos del juez anterior (`3f4642d4`, `50cd271b` y la v1 de
      NotionSync). La v2 de NotionSync ya la corregía el detector de secretos de la decisión 26;
    - **rechaza** la v5 y la v6 de pensiones por vacíos de diseño: no tienen una consulta pública
      de recibos, el campo `motivo` no está declarado y el contexto se arma a mano. Los atiende la
      fase 3;
    - **queda variación:** `5553dabb` salió rechazada en una corrida y aprobada en otra.

**Pendientes de la fase 2.**
- El juez todavía varía entre corridas, aunque rara vez decide un veredicto.
- El corpus cuenta como rechazo falso que el juez marque el caso de una inyección determinista,
  aunque esté bien marcado.

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

Con la arquitectura vigente al cierre del paso 12. `docs/arquitectura.md` pasa a la versión 1.3.

- **Fase 2:**
  - Tabla 1, N12: además detecta las pruebas que simulan el efecto del módulo (CAL-FS-006).
  - Tabla 1, N14: el juez ve las interfaces y el modelo de datos de la especificación, y cada
    rechazo se confirma con una segunda opinión. N14 sigue siendo uno de los cinco nodos que usan
    modelo, y hace una llamada más solo cuando rechaza.
  - Criterios de calidad: regla nueva CAL-FS-006.

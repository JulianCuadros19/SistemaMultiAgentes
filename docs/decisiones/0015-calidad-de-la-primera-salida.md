---
estado: aceptada
fecha: 2026-11-03
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (enmiendas desde N17, límite de turnos y registro de información capturada), ADR-0008 (casos límite, síntesis, verificación y enmiendas de los requerimientos), ADR-0010 (escenarios ejecutables, métodos y revisiones del registro de decisión), ADR-0011 (pruebas por interfaces públicas, métodos, versión previa tras un rediseño y estilo en N10), ADR-0012 (pruebas que simulan el efecto y conformidad de métodos), ADR-0013 (rediseño desde N17) y ADR-0014 (convergencia del resumen)
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

#### Fase 3 · El arquitecto diseña escenarios ejecutables

10. **Recorrido de cada escenario** (modifica el ADR-0010).
    - **Qué declara la parametrización:** por cada escenario aprobado, en `recorridos`:
      - las interfaces que preparan su «dado que»;
      - la que ejecuta su «cuando»;
      - las que observan su «entonces».
    - **Fuera del Anexo B,** como las capacidades no cubiertas:
      - vive en `Arquitectura.recorridos`;
      - N9 lo muestra en la consola y en la web;
      - la exportación lo agrega al final de `especificacion.md`.
    - **Verificación en código** (`agentes/arquitecto/recorridos.py`), en N8 y en N9:
      - cada escenario aprobado tiene exactamente un recorrido;
      - cada nombre es una interfaz declarada. Al preparar vale también una entidad del modelo de
        datos, que la prueba construye. Un nombre repetido en dos módulos se califica con el
        módulo;
      - el «entonces» no se puede observar solo con una función que no devuelve nada ni lanza
        excepciones.
    - **En N8,** un recorrido incompleto es una salida inválida: el modelo reintenta una vez con
      los problemas, en la misma llamada. N9 lo vuelve a verificar.
    - **El desarrollador los recibe dentro de la especificación.**
      - El código anota en la descripción de cada interfaz los escenarios en que participa, por
        ejemplo «· Escenarios: RF-02 ESC-01 (ejecuta; prepara con registrar_prestamo; observa
        con consultar_prestamo)».
      - Así el Anexo B no cambia, y el desarrollador no gana un insumo (RF-15).
      - La anotación se puede aplicar dos veces con el mismo resultado. Se quita antes de mostrarle
        al modelo la especificación previa.
11. **Prompt `arquitecto.parametrizacion` 1.4** (1.3 en la primera medición). Pide:
    - recorrer cada escenario antes de cerrar el diseño;
    - declarar dónde vive el estado: un almacén con registro y consulta, que recibe quien lo usa,
      sin estado global del módulo;
    - dar una fuente declarada a cada dato que un módulo usa;
    - guardar el estado con la clave de la entidad de la que habla el requerimiento;
    - escribir tipos en las firmas, no funciones (`Callable`, no `callable`), y tipar un almacén
      con su clase, no con `object`.

    Los ejemplos nuevos del prompt son de préstamos de una biblioteca, un dominio que no está en
    ningún caso de evaluación. La 1.3 traía ejemplos de facturas y de liquidación, demasiado
    cercanos a los casos de pagos y de lotes, y la medición de pagos salía favorecida.
12. **Revisiones del registro de decisión** (modifica el ADR-0010).
    - **La selección responde:** con observaciones nuevas, `respuesta_observaciones` es
      obligatoria (`validar_seleccion`; prompt `arquitecto.seleccion` 1.2).
    - **Sección «Revisiones» del registro:** por cada rediseño que atendió observaciones, registra
      las observaciones, la respuesta y los cambios de la especificación.
      - Los cambios los calcula el código (`diferencias`, en `core/esquemas/especificacion_diseno.py`).
      - Cuentan módulos, interfaces, firmas, excepciones, entidades y dependencias, pero no las
        descripciones.
    - **La parametrización ve la revisión en curso,** con la respuesta, para cumplirla.
    - **La corrección por errores de N9 conserva las revisiones.**
13. **Regla nueva de N9:** una firma no puede usar `callable` ni `any` como tipo.
    - La destapó el caso de pagos.
    - El caso y su corpus pasan a `Callable[[AvisoPago…Enriquecido], object]`.
14. **Base de conocimiento.**
    - ARQ-06 1.1 ubica en infraestructura el almacén del estado, con registro y consulta.
    - arq-002 1.2 agrega la validación de escenarios ejecutables.
    - ARQ-03 1.1 y ARQ-05 1.1 cambian la carpeta `io/` por `entrada_salida/`. El catálogo sugería un
      paquete que N9 rechaza, porque tapa un módulo de la biblioteca estándar. Lo destapó la
      medición: con el prompt 1.3, el modelo puso los almacenes del caso de lotes en `io/`.
    - Reingesta: 36 documentos y 187 fragmentos.

**Reproducción.** `evaluacion/casos/recorridos-pagos.json` guarda las especificaciones 0.2 a 0.5 de
`5f5d2739`, con los recorridos que exigen sus nueve escenarios. Los nombres son los del diseño
completo de `desarrollo-pagos.json`.

La validación nueva rechaza cada versión y nombra lo que le faltaba
(`tests/unitarias/test_recorridos_casos.py`):

| Versión | Qué pasó | Interfaces que faltaban |
|---|---|---|
| 0.2 | Pasó N9; rechazada en N17 | Registro y consulta de facturas, emisión y consulta de recibos, registro y consulta de la cartera |
| 0.3 | Pasó N9; rechazada en N17 | Las mismas |
| 0.4 | Pasó N9; rechazada por el revisor | Emisión y consulta de recibos, registro y consulta de la cartera |
| 0.5 | Pasó N9; aprobada | Consulta de recibos, que se agregó a mano en la fase 2 |

Con los recorridos, la v0.2 no habría llegado a la persona. N9 la habría devuelto con lo mismo que
pidieron las observaciones 2 y 3, y se habrían ahorrado dos ciclos de N17.

**Verificación de la fase 3.**
- **Sin costo:** 628 pruebas unitarias, 31 de integración, 33 del entorno aislado y 19 de
  embeddings.
- **Con costo:** `python scripts/evaluar_arquitecto.py --corridas 3`, sobre los cuatro casos de
  diseño, con la traza en `docs/mediciones/paso-12-arquitecto.jsonl`. La línea base es el paso 8:
  9 de 9 primeros diseños válidos sin recorridos, a 0,05–0,08 USD por diseño.

| Medición | Primer diseño válido | Reintentos dentro de N8 | Devueltos por N9 | USD por diseño |
|---|---|---|---|---|
| Prompt 1.3, 4 casos × 3 | 9 de 12 | 1, por un nombre repetido | 3, todos de lotes | 0,108 |
| Prompt 1.3, lotes × 3 más | 1 de 3 | 0 | 2, por el paquete `io` | 0,131 |
| Prompt 1.4 y catálogo sin `io`, 4 casos × 3 | 12 de 12 | 3, por un nombre repetido en dos módulos | 0 | 0,110 |

- Con la 1.4, los tres diseños de pagos guardan la cartera por familia y declaran de dónde sale la
  familia. Con la 1.3, dos de tres la guardaban por la referencia del pago.
- Cada escenario aprobado tiene su recorrido en las 27 corridas.
- Costo de la fase: unos 3 USD, frente a 0,9 del plan, por la ronda extra que encontró el paquete
  `io` y la medición de cierre.

**Pendientes de la fase 3.**
- **Métodos como interfaces** (decisión abierta del equipo).
  - La conformidad de N12 exige interfaces de nivel superior, y N9 rechaza una interfaz llamada
    `Clase.metodo`.
  - Por eso la v0.1 de pensiones, que declaraba así los métodos del bus, volvió a N8. La v0.2 los
    declaró como funciones con `self`, y el código tuvo que definir funciones sueltas y colgarlas
    de la clase.
  - En la medición, los diseños de pagos describen en prosa los métodos de sus puertos («obtener
    (numero) -> Factura | None; guardar(factura) -> None»), porque no los pueden declarar.
  - El prompt pide declarar las operaciones como funciones que reciben la instancia. Admitir
    `Clase.metodo` en N9 y en N12 sería más natural, pero cambia una regla de conformidad de los
    pasos 9 y 10.
- **Lo que el código no verifica:** que la preparación y la observación correspondan al texto del
  escenario, o que la clave del estado sea la entidad correcta. Lo pide el prompt, lo revisa la
  persona en N9 con los recorridos a la vista, y lo juzga N14 sobre las pruebas.
- **Nombres repetidos:** en 3 de 12 corridas, el contrato y su implementación, o el servicio y el
  almacén, se llaman igual. El reintento lo corrige, pero cuesta una parametrización más, unos
  0,07 USD. Pedir nombres únicos en el prompt queda propuesto, sin medir.

#### Fase 4 · Métodos como interfaces y desarrollador guiado por los escenarios

**Decisiones del equipo (2026-11-04):**
- admitir métodos de clase como interfaces;
- un nombre único por interfaz;
- medir al desarrollador con diseños del arquitecto vigente.

15. **Métodos como interfaces** (modifica el ADR-0010, el ADR-0011 y el ADR-0012).
    - **Convención:**
      - una interfaz de tipo `funcion` llamada `Clase.metodo` es un método de `Clase`, que el
        mismo módulo declara como `clase`;
      - su firma es la del método, con `self` o `cls`: `registrar(self, prestamo: Prestamo) ->
        None`;
      - el Anexo B no cambia: es una forma de nombrar sus interfaces.
    - **N9:** exige la clase en el mismo módulo, el `self` o `cls` y un solo punto. Admite que la
      firma repita la clase.
    - **Conformidad compartida por N10 y N12:** busca el método dentro de su clase y compara
      parámetros y retorno. `self` sigue sin anotación, por la decisión del equipo del paso 12.
    - **Detector de pruebas que simulan (CAL-FS-006):**
      - sigue a los objetos que devuelven los métodos, salvo que el nombre corto sea ambiguo;
      - cuenta los métodos declarados entre los atributos de su clase.
    - **Recorridos:**
      - resuelven `Clase.metodo`, con o sin el módulo, y el nombre corto si no es ambiguo;
      - un método de otra clase no vale.
    - **Compatibilidad:** las funciones sueltas con `self` siguen valiendo, como en el caso de
      pagos y su corpus.
    - **Base de conocimiento:** arq-002 1.3 agrega la fila «Métodos», con reingesta.
    - **Por qué:**
      - la v0.1 de pensiones declaraba los métodos del bus como `BusEventosMemoria.suscribir…`, y
        N9 la devolvió;
      - las versiones siguientes los convirtieron en funciones sueltas con `self`, colgadas de la
        clase;
      - con el prompt 1.4, los contratos de pagos describían en prosa métodos que nadie
        verificaba.
16. **Prompt `arquitecto.parametrizacion` 1.5:**
    - los almacenes y los contratos declaran sus operaciones como métodos;
    - el contrato y su implementación declaran cada uno los suyos;
    - un nombre único por interfaz;
    - en los recorridos, un método se nombra `Clase.metodo`.
17. **Casos de desarrollo con recorridos** (modifica el ADR-0011).
    - `evaluacion/casos/con-recorridos/` guarda un diseño por caso de diseño, de la medición del
      prompt 1.5, con la especificación anotada y sus recorridos.
    - La prueba `nube` del desarrollador pasa a esos casos.
    - Los casos del paso 9 quedan para los corpus de defectos.
18. **Prompt `desarrollador.generacion` 1.7** (modifica el ADR-0011):
    - **Pruebas:**
      - siguen el recorrido anotado de su escenario;
      - usan solo interfaces públicas o dobles de dependencias externas que el módulo recibe por
        parámetro;
      - sin nombres privados ni atributos no declarados;
      - sin armar ni restaurar el efecto, y sin lanzar la excepción esperada;
      - lo que no se puede preparar u observar va a Supuestos.
    - **Código:**
      - los métodos van dentro de su clase, con `self` sin anotar;
      - el estado vive en las instancias, nunca en variables globales del módulo.
    - **Contra las causas medidas de reintento:**
      - sangría de 4 espacios;
      - excepciones importadas aunque solo se propaguen;
      - archivos completos.
    - **Ejemplo:** ya no escribe las secciones de `USO.md` que agrega el sistema.
19. **La versión previa como referencia tras un rediseño** (modifica el ADR-0011 y el ADR-0013).
    - **Antes:** N10 descartaba la versión previa y la retroalimentación de N17 cuando cambiaba la
      especificación, y generaba de cero.
    - **Ahora:** recibe un `Rediseno` con la versión anterior y la última revisión del registro
      de decisión.
    - **En el mensaje del modelo,** el bloque `rediseno` trae:
      - los archivos que siguen valiendo: los módulos aún declarados, las pruebas y `USO.md`;
      - la retroalimentación de N17;
      - la revisión.
    - **Resultado:** la salida se combina sobre esos archivos, y la versión declara atendida la
      retroalimentación.

**Verificación de la fase 4.**
- **Sin costo:** 653 pruebas unitarias, 31 de integración, 33 del entorno aislado y 19 de
  embeddings.
- **Arquitecto con el prompt 1.5,** cuatro casos por tres corridas:
  - 12 de 12 primeros diseños válidos;
  - ningún reintento en N8, frente a 3 con la 1.4;
  - 0,0997 USD por diseño;
  - diez diseños declaran métodos, de 4 a 36; los dos restantes son de avalúo y no tienen
    almacén;
  - ninguno usa funciones sueltas con `self` ni describe métodos en prosa.
- **Desarrollador con el prompt 1.7** sobre los casos con recorridos, con el tester real y una sola
  iteración (`scripts/evaluar_desarrollador.py`, traza en
  `docs/mediciones/paso-12-desarrollador.jsonl`):

| Medición | Corridas | Primer intento rechazado | v1 aprobada por el tester | CAL-FS-006 | CAL-MT-010 | Pruebas fallidas | USD por corrida |
|---|---|---|---|---|---|---|---|
| Dos por caso, y una de pagos | 7 | 2 | 7 | 0 | 0 | 0 | 0,122 |
| Lotes y mutación, dos más | 4 | 1 | 2 | 0 | 0 | 0 | 0,120 |

- **Los tres primeros intentos rechazados** tienen un archivo de pruebas con la sintaxis rota.
  - El que se capturó traía, después de `@pytest.fixture`, la línea ` def_placeholder = None`:
    un marcador de posición sin terminar.
  - El reintento lo corrigió en los tres casos.
  - El mensaje de sintaxis muestra ahora las líneas exactas, y el prompt 1.8 prohíbe los
    marcadores de posición. La 1.8 no se midió aparte: se mide en la fase 7.
  - Línea base: 7 de 29 primeros intentos rechazados. Ahora: 3 de 11. Esta causa no mejora.
- **Las dos v1 rechazadas** son de lotes: una por complejidad (CAL-MT-003) y otra por cinco
  docstrings incompletos (CAL-MT-001). N10 no aplica Ruff; solo lo aplica el tester.
- **Rediseño real** (`ce78c1e3`, avalúo, 0,29 USD): N17 devolvió al arquitecto con «agrega una
  consulta que liste los valores registrados de una vigencia».
  - El registro ganó la revisión: la observación, la respuesta y once cambios de la
    especificación.
  - La v2 conservó idéntico `tests/test_liquidacion.py`, cambió solo los módulos que tocaba el
    rediseño y agregó el módulo y las pruebas nuevos.
  - La v2 declara atendida la observación.
- **Revisión a mano:** las pruebas de la v1 de pagos siguen su recorrido. Preparan con el almacén,
  ejecutan con el productor y observan con la consulta, sin nombres privados.
- **Costo de la fase:** 2,82 USD, frente a 2,8 del plan.

**Pendientes de la fase 4.**
- **Verificación de estilo en N10** (propuesta para el equipo).
  - Aplicar en N10 las reglas de Ruff de severidad media que dictamina el tester (CAL-MT-001,
    CAL-MT-002 y CAL-MT-003), para que el reintento las corrija antes del tester.
  - Evitaría las dos v1 rechazadas de esta medición.
  - Cambia el reparto de los pasos 9 y 10, en el que el estilo solo lo dictamina el tester.
  - El equipo la aprobó el 2026-11-04: decisión 29.
- **Sintaxis rota:** sigue causando reintentos, 3 de 11.

#### Fase 5 · El elicitador pregunta por casos límite

20. **Casos límite acotados antes del resumen** (modifica el ADR-0008 y la invariante del
    registro del ADR-0006).
    - **Cuándo pregunta:** con los atributos capturados (salvo lo que el cliente no supo), N3
      pregunta por situaciones especiales de las reglas registradas antes del resumen.
    - **Cuánto:**
      - hasta tres preguntas (`MAX_PREGUNTAS_CASOS_LIMITE`) y al menos una;
      - cada una de un patrón de dom-007 distinto (`CategoriaCasoLimite`), sin repetirlo.
    - **Registro:**
      - lo que el cliente define queda en `RegistroCaptura.casos_limite`, con la misma fidelidad
        que las reglas;
      - el resumen lo muestra como «Casos especiales acordados»;
      - lo que el cliente no sabe de una situación especial no se vuelve pregunta abierta, porque
        no bloquea los requerimientos.
    - **Sin cambiar la suficiencia de eli-006:** `pendientes` declara `casos_limite` antes de
      `confirmacion`, y el resumen solo se confirma con la fase cerrada.
    - **Cuándo se cierra:**
      - al agotar las preguntas;
      - cuando el modelo indica, después de la primera, que no queda una categoría que aplique;
      - o cuando al cliente le quedan tres turnos o menos frente al límite
        (`RESERVA_TURNOS_CONFIRMACION`, en N3).
    - **Contexto:** N2 consulta aparte los patrones de dom-007: su introducción y sus ocho
      patrones.
    - **Simulación:** la simulación del grafo no explora casos límite.
21. **Una pregunta por algo más** (eli-006, fase 6). Cerrados los casos límite, N3 pregunta una
    sola vez, con un texto fijo, si falta algo importante: la prioridad, los mensajes de error, el
    formato de los valores o un ejemplo con cifras. Su respuesta tampoco abre preguntas.
22. **El límite de turnos pasa de 15 a 18** (decisión del equipo del 2026-11-04; modifica el
    ADR-0006). La fase de casos límite y la pregunta por algo más agregan hasta cuatro turnos.
    `MAX_TURNOS_ELICITACION` vale 18 por defecto y en `.env.example`.
23. **El resumen converge** (modifica la decisión 21 del ADR-0014 y atiende dos de sus
    pendientes). Con las decisiones 20 a 22, la corrida ampliada retrocedió (verificación de la
    fase 5): el 43 % de las preguntas repetía el resumen. Había cuatro causas:
    - **Listas parciales.** La extracción devolvía solo lo que mencionaba la respuesta, y lo demás
      se perdía. En el caso 15, la condición «se ejecuta cada noche» salía y volvía en cada
      resumen.
      - Ahora los datos se combinan por nombre.
      - En las listas de texto, una entrada que el modelo no devuelve sigue vigente. Sale si una
        entrada nueva la reformula, que la reemplaza en su lugar, o si la respuesta habla de ella.
      - «Hablar de» una entrada es repetir dos tercios de sus raíces, y al menos dos
        (`_habla_de`). Una raíz en común no basta: «falta que el tipo solo puede ser ESC, CER o
        PAZ» borraba «el tipo en minúsculas se corrige a mayúsculas» (caso 14). Con la mitad,
        dos palabras frecuentes del dominio todavía bastaban (casos 06 y 15).
      - Lo que el cliente rechaza sin reemplazo sigue saliendo por `retirar`.
    - **Ejemplos sin lugar.** El cliente daba un ejemplo con cifras que el registro no tenía dónde
      guardar, así que el resumen nunca lo mostraba.
      - `RegistroCaptura.ejemplos` los guarda, y el resumen los muestra como «Ejemplos para
        verificar».
      - La síntesis los usa como datos de los escenarios.
    - **Tipos invisibles.** El cliente pedía que un dato fuera decimal y el resumen no mostraba el
      tipo. Ahora muestra el tipo de cada dato.
    - **«Falta algo» sin el dato.** La pregunta fija «¿Qué falta o qué debo corregir del
      resumen?» se repetía (caso 06). Ahora el modelo pregunta específicamente por lo que el
      cliente señaló (`resumen_incompleto`), sin repetir el resumen.
    - **Sistemas en «A quién le sirve».** El cliente pedía la tarea programada que usa la
      herramienta en esa línea, y el rol no la admite (decisión 29 del ADR-0014), así que el
      reclamo se repetía hasta el límite (caso 14).
      - Con condiciones registradas, el resumen avisa junto al rol que los sistemas o procesos
        que lo usan aparecen en «Condiciones ya definidas».
      - Si el cliente insiste, N3 le explica dónde quedó.
24. **La síntesis y la verificación ante la exploración** (modifica el ADR-0008).
    - **Preguntas abiertas.** En la corrida ampliada, 14 de 20 historias llegaron a N6 con
      preguntas abiertas. En 4 de ellas, el registro no tenía preguntas abiertas ni atributos sin
      respuesta: N5 las sacaba de los «no sé» de la transcripción. En la repetición de los cinco
      casos que no convergían, pasó en 3 de 5.
      - Como una pregunta abierta requiere al cliente, N6 escalaba el conjunto sin intentar la
        corrección automática de los demás defectos (decisión 10 del ADR-0008).
      - Pedírselo al prompt no bastó: en 3 de 11 corridas posteriores N5 siguió agregándolas.
      - Ahora, con el resumen confirmado y nada pendiente, las preguntas abiertas de la historia
        son exactamente las del registro, y lo decide el código. Si el registro quedó sin
        confirmar o con atributos sin respuesta, N5 puede agregar lo que falte.
    - **Historias con varias capacidades.** Los requerimientos reproducen la historia como
      título, así que una historia que une capacidades deja un defecto C5 en cada uno. Si la
      funcionalidad reúne varias, la historia enuncia la que las abarca y cada requerimiento
      desarrolla una.
    - **Códigos del cliente.** C9 ya no marca como detalle de implementación un código en
      mayúsculas con guion bajo, como `ESC_2019_00042`: es un valor que dio el cliente. Los
      ejemplos lo llevaban a los escenarios.
25. **Prompts.**
    - `elicitador.dialogo` 1.9:
      - categorías de casos límite, prioridad entre ellas, pregunta abierta y salida de la fase;
      - la pregunta específica ante un resumen incompleto;
      - dónde quedan los sistemas que el cliente pide en «A quién le sirve»;
      - la pregunta de cierre pide todas las correcciones de una vez.
      - Hasta la 1.8, el ejemplo de pregunta por un caso límite («¿Qué debe pasar si el pago
        llega con una fecha anterior al inicio de la vigencia?») era la regla oculta R1 del caso
        del predial. La 1.9 usa un ejemplo de otro proceso, y la medición final es con ella.
    - `elicitador.extraccion` 1.6:
      - registra los casos límite y los ejemplos;
      - una entrada omitida se conserva;
      - la situación actual no es una condición, y no registra como regla lo que repite la
        funcionalidad.
    - `elicitador.sintesis` 1.8:
      - cada caso especial entra en la regla de su requerimiento con un escenario que lo
        verifica, y los ejemplos dan los datos de los escenarios;
      - las preguntas abiertas y la historia con varias capacidades de la decisión 24;
      - un defecto en el título de un requerimiento se corrige en la historia, porque el sistema
        la copia como título. En el caso 14 de la medición final, N5 corregía el título y el C5
        seguía tras dos correcciones. La 1.8 no se midió.
    - Las corridas intermedias usaron borradores sin cambiar la versión. La traza los distingue
      por `huella_prompt`.
26. **RF-07 de N6 alineado con eli-004:** al menos tres escenarios por requerimiento: el camino
    feliz, el alterno y el de error.
27. **Base de conocimiento:** eli-006 1.2 agrega la fase de casos límite, con reingesta.
28. **Casos con reglas ocultas y juez de evaluación.**
    - Los casos de `evaluacion/casos/casos-limite/` traen reglas que el cliente simulado solo dice
      si le preguntan por esa situación (`ReglaOculta`; cliente simulado 1.2):
      - el descuento del predial: la fecha anterior a la vigencia, el cuadre de los redondeos y
        las deudas de vigencias anteriores;
      - los abonos de pensiones: el reverso de un abono con abonos posteriores, el abono ya
        reversado y el historial.
    - `scripts/evaluar_elicitador.py` las busca en el registro y en los requerimientos, por
      términos y con un juez semántico (`evaluacion/juez_reglas_ocultas.md`). Guarda también la
      historia de cada sesión.
    - El juez es solo de evaluación: no es parte del sistema.
29. **N10 se adelanta al estilo que rechazaría el tester** (decisión del equipo del 2026-11-04;
    atiende el pendiente de la fase 4; modifica el ADR-0011).
    - `estilo_bloqueante` deriva el criterio de las reglas del tester: con
      `UMBRAL_HALLAZGOS_MEDIA=0`, rechazan las infracciones de severidad alta y media.
    - La verificación de N10 las reporta como «RF-16 · estilo», y el reintento las corrige.
    - El tester sigue dictaminando el estilo, la ejecución y la severidad.

**Verificación de la fase 5.**
- **Sin costo:** 677 pruebas unitarias, 31 de integración y 19 de embeddings.
- **Prueba `nube` del paso 7:** pasa con diálogo 1.9, extracción 1.6 y síntesis 1.7.
- **Reglas ocultas.** Los dos casos de `evaluacion/casos/casos-limite/`, con tres corridas por
  caso. El juez semántico cuenta las reglas que llegan a los requerimientos:

| Medición | Predial | Abonos | Total, de 18 |
|---|---|---|---|
| Línea base, sin casos límite | 0, 1, 0 | 0, 0, 0 | 1 |
| Límite de 15 turnos, tres iteraciones de los prompts | — | — | 7, 6 y 5 |
| Límite de 18 y decisión 23 | 2, 1, 1 | 2, 2, 2 | 10 |
| Final: decisión 24 y diálogo 1.9 | 1, 1, 2 | 2, 0, 2 | 8 |

- **Convergencia.** Los cinco casos de la corrida ampliada que no convergían (04, 06, 09, 14 y
  15), una corrida por caso:

| Medición | Cambios | Turnos | Resúmenes confirmados | En el límite | Defectos en N6 | USD, sistema y cliente |
|---|---|---|---|---|---|---|
| Corrida ampliada | decisiones 20 a 22 | 76 | 4 | 2 | 11 | 0,42 y 0,18 |
| 2 | ejemplos, tipos y datos por nombre | 76 | 4 | 2 | 7 | 0,45 y 0,20 |
| 3 | listas de texto y pregunta específica | 65 | 5 | 0 | 26 | 0,34 y 0,17 |
| 4 | dos tercios, síntesis 1.7 y C9 | 70 | 4 | 1 | 6 | 0,40 y 0,16 |
| Final | aviso de sistemas, preguntas abiertas del registro y diálogo 1.9 | 73 | 5 | 1 | 6 | 0,51 y 0,20 |

- **Lectura de la convergencia:**
  - la medición 3 llegó a 26 defectos porque las preguntas abiertas sacadas de la exploración
    impedían la corrección automática (decisión 24);
  - de los 6 defectos de la final, 3 son C5 del caso 14, que motivan la síntesis 1.8;
  - los otros 3 son del caso 09, que escaló por una pregunta abierta legítima del registro.
- **Corrida ampliada de 20 casos,** con las decisiones 20 a 22 y antes de la 23:
  - 306 turnos, 13 de 20 resúmenes confirmados y 8 sesiones en el límite;
  - 53 preguntas por casos límite;
  - 2,50 USD;
  - en la medición 2 del ADR-0014 eran 211 turnos, 17 de 20 y 3 en el límite;
  - no se repitió con las decisiones 23 y 24.
- **Criterios de terminado:**
  - Al menos 2 de 3 reglas ocultas por caso: no se cumple de forma estable. La captura pasó de 1
    a 8 y 10 de 18. En la medición final, la media es 1,33 por caso, y 3 de 6 corridas llegan a
    2.
  - La corrida ampliada no retrocede: no se midió con las decisiones 23 y 24. El tope de 211
    turnos no es alcanzable por diseño: la exploración agrega de 2 a 4 turnos por sesión, y en la
    medición final de los cinco casos sumó 19.
  - La prueba `nube` del paso 7 pasa.
- **Costo de la fase:**
  - 8,55 USD en `docs/mediciones/paso-12-elicitacion-3.jsonl`, frente a 2,3 del plan;
  - reparto: N3 4,51, N5 1,42, cliente simulado 2,53 y juez 0,10;
  - aparte, las dos corridas de la prueba `nube`, de unos 0,08 USD cada una.

**Pendientes de la fase 5** (para el equipo).
- **Corrida ampliada de 20 casos** con las decisiones 23 y 24, de unos 2,7 USD. La alternativa es
  dejarla a la fase 7, cuya corrida de extremo a extremo incluye la elicitación.
- **Criterio de turnos:** revisarlo, por ejemplo 211 turnos sin contar la exploración.
- **Captura de reglas ocultas:** aceptarla así o ampliar la exploración, por ejemplo a cuatro
  preguntas.
- **Propuesta:** que N6 corrija los defectos que N5 puede resolver aunque haya preguntas
  abiertas, y que después escale solo lo que requiere al cliente.
  - En 9 de las 20 sesiones de la corrida ampliada, N6 escaló sin corregir defectos C5, C7 o C9
    porque había al menos una pregunta abierta.
  - Cambia la implementación de la decisión 10 del ADR-0008.

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
- **Fase 3:**
  - Tabla 1, N8: además declara el recorrido de cada escenario con interfaces públicas y, si hay
    observaciones, una revisión del registro de decisión.
  - Tabla 1, N9: además verifica los recorridos y rechaza `callable` y `any` como tipos.
  - Anexo B: sin cambios. Los recorridos lo acompañan y se anotan en las descripciones.
  - Propuesta para el equipo: ampliar RF-12 de los requerimientos a los escenarios.
- **Fase 4:**
  - Anexo B: un método se declara como interfaz `Clase.metodo`, sin campos nuevos.
  - Tabla 1, N10: una prueba por escenario según su recorrido, y tras un rediseño parte de la
    versión anterior y de la retroalimentación.
  - Tabla 1, N12: la conformidad cubre los métodos.
  - Flujo: la devolución de N17 al arquitecto conserva la versión anterior como referencia para
    N10.
- **Fase 5:**
  - Tabla 1, N3: antes del resumen, pregunta por los casos límite de las reglas capturadas, hasta
    tres y cada uno de un patrón distinto, y una vez por algo más. El límite de turnos pasa a 18.
  - Registro de información capturada: casos especiales acordados y ejemplos con cifras.
  - Tabla 1, N5: con el resumen confirmado, las preguntas abiertas de la historia son las del
    registro.
  - RF-07 en N6: al menos tres escenarios por requerimiento.
  - Tabla 1, N10: antes de entregar, verifica también el estilo que rechazaría el tester.

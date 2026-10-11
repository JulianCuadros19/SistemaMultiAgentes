---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (protocolo del tester y aprobación en N15), ADR-0007 (corpus de criterios) y ADR-0011 (verificación y prompt de N10)
---

# ADR-0012 · Agente tester: veredicto determinístico, juez acotado y corpus de defectos inyectados

> El ADR-0014 (paso 12) hace que un juez que no responde deje los casos «sin juicio del modelo»,
> con una advertencia para N17, en lugar de detener la sesión. Ante un `ModuleNotFoundError`, la
> sugerencia dice que el entorno no tiene la librería.

## Contexto y planteamiento del problema

El paso 10 exige que el tester detecte defectos inyectados a propósito en código de prueba. Hay
que reemplazar la simulación de N11 a N14 por el agente real:
- ejecuta en el entorno aislado (RF-20);
- dictamina cada criterio de aceptación con su prueba como evidencia (RF-21);
- verifica la conformidad por módulo (RF-22);
- reporta hallazgos por severidad referidos a su regla de calidad (RF-23);
- devuelve retroalimentación estructurada al desarrollador (RF-24).

El tester no modifica código (decisión 6). Su conducta la fijan cal-sv y cal-pg:
- citar la regla de cada hallazgo y reportarlo todo;
- declarar lo no evaluado;
- validar de forma determinística y reproducible.

La decisión afecta a:
- `src/multiagente/agentes/tester/`, `src/multiagente/core/` y `src/multiagente/sandbox/`;
- el orquestador;
- `prompts/tester/` y la colección `criterios_calidad`;
- `evaluacion/defectos/`.

## Factores de decisión

- RF-20 a RF-24, RF-29, RNF-03 y RNF-10.
- cal-sv:
  - la escala Alta, Media y Baja;
  - la regla de veredicto: se rechaza con un hallazgo Alta, con un criterio incumplido o con
    hallazgos Media sobre el umbral;
  - la conducta: evidencia, reportar todo, citar la regla y declarar lo no evaluado.
- cal-pg: la validación es determinística y reproducible.
- Tabla 3: N14, «clasificación con justificación», tiene el perfil económico.
- Lo aprendido en los pasos 7 a 9: verificar en código todo lo que pueda verificarse y dar al
  modelo solo lo que exige juicio.

## Opciones consideradas

- A. Un tester guiado por el modelo, que lee la ejecución y el código y emite el veredicto.
- B. Un tester determinístico, con el modelo acotado a juzgar si las pruebas que pasaron
  verifican su escenario.

## Resultado de la decisión

Opción elegida: «B». La A haría el veredicto no reproducible y contradiría cal-pg. Además, un
modelo económico no puede sostener una lista exhaustiva de reglas.

### Decisiones del equipo

1. **Umbral de hallazgos Media: 0.** `UMBRAL_HALLAZGOS_MEDIA` es configurable.
2. **Dos reglas nuevas en criterios_calidad**, con cal-mt en la versión 1.2:
   - CAL-MT-009, «Conformidad con la configuración de estilo», severidad Baja. Cubre lo que
     RF-16 pide y no tenía regla, como la longitud de línea y el orden de las importaciones;
   - CAL-MT-010, «Sin importar nombres privados de otro módulo», severidad Media.

   El corpus pasa a 186 fragmentos y 33 reglas.
3. **Las pruebas propias de la persona en N17 (RF-38) quedan para el paso 12.** Este paso deja
   lista la ejecución con resultado por prueba (`EntornoAislado.probar`).
4. **N14 usa `gpt-6-luna`**, del perfil económico, versión 2026-09-22. Tarifa: entrada 0,10,
   caché 0,01, escritura de caché 0,125 y salida 0,50 USD por millón de tokens.
   - Se eligió midiendo con el corpus frente a `gpt-5.4-mini` y `gpt-5-nano`, como se ve abajo.
   - `gpt-6.1-sol` quedó descartado: es el modelo del desarrollador, y el juez compartiría sus
     puntos ciegos.

### Decisiones de implementación

5. **Análisis compartido** (`core/conformidad.py` y `core/dinero.py`). N10 y N12 usan el mismo
   informe de conformidad, con problemas tipados: así aplican la misma noción de firma compatible
   (ADR-0011).
6. **N11:** importa cada módulo declarado y corre las pruebas en el entorno aislado. Un plugin de
   pytest recoge el resultado de cada prueba y los errores de recolección, sin interrumpir las
   demás. La salida de pytest va aparte para que el resultado no se trunque.
7. **N12:** análisis estático y conformidad, sin ejecutar el código.
   - **Ruff:** con la configuración del código generado; cada código va a su regla
     (`agentes/tester/reglas.py`).
   - **Conformidad:** existencia de los módulos, interfaces, módulos no previstos,
     dependencias internas y externas, y nombres privados.
   - **Trazabilidad (CAL-AR-005):** cada requerimiento tiene una prueba que lo cita y que importa
     un módulo asignado a él.
   - **Dinero (CAL-FS-005):** `float` en nombres monetarios, `float(…)` sobre ellos y `Decimal`
     construido desde un `float`.
   - **Secretos con nombres en español (CAL-SG-001):** Ruff solo reconoce nombres en inglés.
     «clave» sola no cuenta, porque en el dominio es también la clave catastral.
   - **Severidad:** sale de la regla en la base de conocimiento, leída de los archivos como el
     catálogo del arquitecto.
   - **Lo no evaluado:** las reglas sin comprobación automática (CAL-FB-001, 003, 004 y 005,
     CAL-FS-004, CAL-SG-005 y CAL-SG-007) quedan en `no_evaluadas`.
8. **N13:** consulta cada regla citada en los hallazgos y tres consultas fijas: cobertura de
   criterios, técnicas de prueba y regla de veredicto. Solo consulta `criterios_calidad`.
9. **N14, parte determinística.** Cada caso del plan de N16 se asocia a sus pruebas por nombre y
   no se cumple si:
   - no tiene prueba (CAL-FS-001);
   - una prueba falla, da error o no se ejecutó (CAL-FS-002);
   - la prueba no tiene aserción (CAL-FS-001).

   Además se reportan los módulos que no se importan (CAL-FS-003), los archivos que no se
   recolectan y el tiempo vencido.
10. **N14, juez acotado** (`prompts/tester/veredicto.md` 1.1).
    - Solo recibe los casos cuyas pruebas pasaron, con el escenario, el código de cada prueba y
      los archivos de prueba completos, donde están los fixtures del «dado que».
    - Responde si la prueba verifica el «entonces» con la precisión que expresa el escenario.
    - El código valida que estén exactamente los casos enviados, con un reintento.
11. **Veredicto y retroalimentación.**
    - La regla de cal-sv se aplica en código.
    - La retroalimentación lleva una línea por hallazgo con campos fijos:
      `[regla · severidad] ubicación · defecto · Sugerencia: …`.
    - El reporte en Markdown queda en `Validacion.reporte` y se muestra en N17.
12. **Estado.**
    - `Validacion` guarda la ejecución por prueba, los hallazgos estructurados, la conformidad por
      módulo, las reglas no evaluadas, el veredicto y el reporte.
    - `aprobado` exige el veredicto aprobado. Antes, N15 habría pasado a N17 un módulo con
      hallazgos Alta si sus casos cumplían.
13. **N10 se alinea con el umbral 0.** Su verificación rechaza las importaciones privadas y el
    prompt de generación pasa a la versión 1.1, sin importaciones privadas ni sin uso.
14. **Corpus de defectos** (`evaluacion/defectos/`).
    - **Controles:** dos limpios, los módulos de avalúo y de mutación del paso 9, ajustados a mano
      para que no tengan hallazgos.
    - **Inyecciones:** 16 sobre el avalúo. 13 se detectan en código y 3 solo con el juez: una
      aserción debilitada, código y prueba coherentes con un valor distinto del escenario, y una
      prueba que no ejecuta el «cuando».
    - **Esperado:** cada inyección declara el veredicto, las reglas y los casos que debe marcar
      el juez.
    - **Carga:** una inyección desalineada con su base hace fallar la carga.
    - **Desarrollador fijo:** `DesarrolladorFijo` entrega versiones dadas para recorrer el ciclo
      N10–N15 con el tester real.

### Mediciones (2026-10-09)

**Tester sin juez** (`pytest -m sandbox`):
- rechaza los 13 defectos determinísticos con su regla;
- aprueba los dos controles;
- deja pasar los 3 defectos del juez, lo que muestra para qué está el modelo.

**Primera selección del juez:** controles y defectos del juez, tres corridas, con el juez viendo
solo la función de prueba.

| Juez | Defectos detectados | Rechazos falsos | Latencia media | Costo |
|---|---|---|---|---|
| gpt-6-luna | 9 de 9 | 0 | 2,9 s | 0,004 USD |
| gpt-5.4-mini | 9 de 9 | 0 | 2,9 s | 0,041 USD |
| gpt-5-nano | 7 de 9 | 0 | 7,5 s | 0,004 USD |

**Corpus completo con esa entrada:**
- en dos de tres corridas, el juez rechazó un control;
- en las variantes con pruebas intactas, marcó casos incumplidos que el veredicto ocultaba,
  porque ya había un hallazgo Alta.

La causa era la entrada. El juez no veía los fixtures que preparan el «dado que» y respondía,
por ejemplo, «no se muestra que `valores` prepare los precios de 500.000 y 1.200.000». Se le
dieron los archivos de prueba completos y se pasó a medirlo por caso.

**Segunda selección:** corpus completo, 18 variantes, tres corridas y 135 casos juzgados por
candidato.

| Juez | Variantes correctas | Defectos marcados | Rechazos falsos | Omisiones | Latencia media y máxima | Costo de 48 llamadas |
|---|---|---|---|---|---|---|
| gpt-6-luna | 54 de 54 | 9 de 9 | 0 | 0 | 2,5 s y 3,6 s | 0,0157 USD |
| gpt-5.4-mini | 54 de 54 | 9 de 9 | 0 | 0 | 2,6 s y 4,2 s | 0,1508 USD |
| gpt-5-nano | 54 de 54 | 9 de 9 | 0 | 0 | 7,0 s y 20,3 s | 0,0145 USD |

La regla fijada de antemano («el más barato sin fallos») daba `gpt-5-nano`, por 0,001 USD en
48 llamadas. El equipo eligió `gpt-6-luna`:
- fue el único sin errores en las dos mediciones;
- responde 2,8 veces más rápido;
- cuesta lo mismo, y su perfil económico respeta la Tabla 3.

**Condición de terminado** con `gpt-6-luna`, tres corridas. Las tres pasaron completas:
- los 16 defectos rechazados con su regla;
- los dos controles aprobados sin hallazgos;
- el juez marcó exactamente los casos esperados;
- el ciclo N10–N15 recorrido en el grafo.

Cada corrida dura unos 230 s, la mayor parte en la ingesta del corpus de la prueba, y el juez
cuesta 0,003 USD por corrida.

**Gasto del paso en mediciones:** cerca de 0,25 USD.

### Consecuencias

- **Favorable:** el veredicto es reproducible y trazable. Cada hallazgo cita su regla, su
  severidad leída de la base, su ubicación y una sugerencia, y lo no evaluado se declara.
- **Favorable:** el modelo solo decide lo que exige juicio, y con un juez económico se detectan
  defectos que ninguna regla estática ve.
- **Favorable:** el corpus de defectos queda como benchmark del tester para el paso 15, con su
  matriz de confusión.
- **Desfavorable: el umbral 0 hará más estricto el ciclo de corrección.** En el paso 9, los
  módulos reales traían importaciones privadas y sin uso. El paso 11 medirá cuántas iteraciones
  gasta.
- **Desfavorable: hay reglas sin comprobación automática.** Siete quedan para la persona en N17,
  entre ellas la validación de entradas en la frontera (CAL-SG-005).
- **Desfavorable: la detección de secretos y de dinero es heurística**, por nombres. Un nombre
  sin raíz conocida escapa.
- **Desfavorable: el corpus es pequeño.** Una base con 16 inyecciones y dos controles basta para
  la condición de terminado, pero no para estimar tasas de error con precisión. El RF-25, contra
  una evaluación humana, sigue en el paso 15.

### Confirmación

- `pytest`:
  - reglas y severidades de la base, y la correspondencia de cada código de Ruff;
  - N12 con un defecto por regla;
  - N14 determinístico con el umbral, el juez con cliente falso y el reintento;
  - N13 con recuperador falso;
  - la ejecución con resultado por prueba;
  - la integridad del corpus y la detección estática de sus defectos.
- `pytest -m sandbox`: el tester sin juez sobre el corpus y el ciclo de corrección con el tester
  real.
- `pytest -m "nube and embeddings and sandbox" tests/integracion/test_tester_nube.py`: es la
  condición de terminado.
- `python scripts/evaluar_tester.py --modelo-juez <despliegue> --corridas 3`: matriz de
  confusión y aciertos del juez por caso.

## Análisis de las opciones

### Opción A · Tester guiado por el modelo
- Favorable, porque el modelo podría razonar sobre cualquier regla.
- Desfavorable, porque el veredicto no sería reproducible y un modelo económico omitiría reglas.

### Opción B · Determinístico con juez acotado
- Favorable, porque todo lo verificable es reproducible y el modelo resuelve una pregunta acotada
  con evidencia a la vista.
- Desfavorable, porque cada regla automática exige código propio, y las reglas sin código
  quedan para la persona.

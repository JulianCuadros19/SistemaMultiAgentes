# Estado del paso 15 · casos de referencia y líneas base

Documento de traspaso, actualizado el 2026-11-05 a las 13:00, al terminar el modelo único. Sirve
para retomar el paso desde otra sesión. El diseño, las métricas y las hipótesis, fijados antes
de medir, están en el ADR-0019 (`docs/decisiones/0019-casos-de-referencia-y-lineas-base.md`, en
borrador).

## Ajuste del diseño (2026-11-05, 14:20): sin implementación manual

**Este ajuste manda sobre lo demás de este documento.** El detalle está en el ADR-0019.
- **Sale:** la implementación manual, la revisión humana y la tarifa por hora. H2 queda retirada.
- **Comparación:** tres enfoques en nueve casos, con el mismo oráculo: el sistema, el LLM con diálogo y
  el LLM de un solo prompt.
- **Casos nuevos:** 01, 04, 07, 10, 14 y 17, el primero de cada arquitectura.
- **Secreto de resultados:** se levanta; ya no hay implementación manual que proteger.
- **Tope:** sigue en 17 USD.

## Qué pide el paso

- **Terminado cuando:** hay métricas calculadas con un oráculo común contra líneas base de un solo
  modelo de lenguaje, que también son despliegues de Azure OpenAI.
- **Objetivo 4 de la tesis:** métricas de tiempo, costo y tasa de errores en corridas de extremo a
  extremo, contrastadas con los umbrales de los RNF.

## Decisiones del equipo (2026-11-05)

1. **Implementación manual:** la hacen Julián y Laura, cronometrando cada fase. El costo es horas ×
   una tarifa por hora que fijan antes de medir, en `evaluacion/manual/LEEME.md`.
2. **Casos de referencia sintéticos:**
   - `caso-ampliada-02`, reajuste del canon, ARQ-01;
   - `caso-ampliada-12`, dígito del NIT, ARQ-04;
   - `caso-ampliada-16`, amortización, ARQ-05.
3. **Modelo único:** `gpt-6.1-sol`, con un solo prompt.
   - Conversa con el mismo cliente simulado y entrega todo en una respuesta.
   - No usa recuperación, puntos de control ni tester.
4. **Alcance adicional:**
   - las métricas RAGs;
   - una corrida ampliada nueva de los 20 casos, para medir las decisiones 37 a 39 del ADR-0015.

   El benchmark de modelos en N3 y N5 no entra.
5. **Tope de 17 USD para todo el paso,** sumando todas las trazas `docs/mediciones/paso-15-*.jsonl`
   y lo que cuesten las corridas con revisión humana.
6. **El sistema no cambia hasta terminar de medir.** Las hipótesis se fijaron antes de medir, y la
   corrida ampliada no se puede repetir dentro del tope. Lo que destapó su investigación va al
   informe como resultado, con sus correcciones recomendadas.

**Regla de los informes durante el paso:** hasta terminar la fase 2, a los autores solo se les
informa de las salidas de 02, 12 y 16 su clasificación, costo, tiempo, turnos y errores, sin cifras,
diseño ni contenido de las entregas (`evaluacion/manual/LEEME.md`).

## Fase 1 · cerrada (commits `a8c0107`, `ec613c8` y `ef09c32`)

- **Oráculo común** (`evaluacion/referencia/`):
  - pruebas de aceptación de referencia de los tres casos, con 9, 10 y 10 verificaciones;
  - cada caso con una implementación de control y tres mutantes;
  - validado en el entorno aislado: el control pasa todo y los 9 mutantes se detectan
    (`python scripts/evaluar_referencia.py --oraculo`).
- **Paquete `multiagente.evaluacion`:**
  - `referencia`: oráculo, adaptadores y puntuación;
  - `modelo_unico`: la línea base;
  - `rag`: las tres métricas;
  - `traza`: lo gastado en una traza.
- **Guiones:** `scripts/evaluar_referencia.py`, `scripts/evaluar_modelo_unico.py` y
  `scripts/evaluar_rag.py`.
- **Prompts de evaluación:** `evaluacion/modelo_unico.md` 1.0 y `evaluacion/juez_rag.md` 1.0.
- **Plantilla de la implementación manual:** `evaluacion/manual/`.
- **Pruebas sin costo:** 790 unitarias, 34 de integración, 19 de embeddings y 38 del entorno
  aislado.

**Desvíos registrados en el ADR-0019:**
- **Análisis estático común:** solo Ruff, porque los detectores de dinero y de secretos del tester
  necesitan la especificación de diseño.
- **Costo del juez de RAGs:** juzgar las 20 sesiones cuesta unos 3,3 USD, no ~1 USD. El guion
  empieza por los 10 casos impares (unos 1,65 USD), que cubren las seis arquitecturas.
- **Alternativa sin decidir:** el equipo puede elegir `gpt-6-luna` como juez, que cubriría las 20
  sesiones por ~0,2 USD. A cambio, es el modelo de N14. Mientras no decidan, sigue `gpt-6.1-sol`.
  - Tras el modelo único, con lo estimado para lo demás, al juez le quedan unos 3,9 USD. Con
    `gpt-6.1-sol` alcanza para las 20 sesiones, así que el presupuesto ya no obliga a cambiarlo.

## Fase 2 · a cargo de Julián y Laura (pendiente)

Todo está en `evaluacion/manual/LEEME.md`:
1. Asignar los casos. Quien implementa un caso no revisa sus pruebas de referencia.
2. Fijar la tarifa por hora antes de medir.
3. Revisar las pruebas de referencia de los casos que no implementan
   (`evaluacion/referencia/<caso>/`).
4. Implementar a mano su caso, sin asistentes de IA, en `evaluacion/manual/<caso>/`, cronometrando
   en `tiempos.csv`. Sin mirar las salidas del sistema ni del modelo único de ese caso.

## Fase 3 · corridas con costo (en curso)

Orden de prioridad y tope de cada guion:

| Orden | Corrida | Estado | Tope del guion |
|---|---|---|---|
| 1 | Corrida ampliada de 20 casos | **Terminada**: de 08:52 a 11:20, 20 de 20 casos, 8,8153 USD | 8,5 USD |
| 2 | Modelo único, 3 corridas × 3 casos | **Terminado**: de 12:23 a 12:55, 9 de 9 corridas, 1,7485 USD | 4,6 USD |
| 3 | Una corrida automática más × 3 casos (`sistema-2`) | Pendiente: es lo siguiente, con el visto bueno del equipo | 1,3 USD |
| 4 | Corrida con revisión humana × 3 casos | Pendiente; va después de la manual de cada caso | ~1,2 USD |
| 5 | Juez de las métricas RAGs | Pendiente; va en la fase 4 | Lo que quede: ~3,9 USD si lo demás cuesta lo estimado |

**Gastado en el paso:** 10,5638 USD de 17; quedan **6,4362 USD**.

### Resultado de la corrida ampliada (2026-11-05, de 08:52 a 11:20)

**Costo:** 8,8153 USD, de ellos 8,0572 del sistema y 0,7580 del cliente simulado. Pasó en 0,32 USD
el tope del guion, porque el tope se revisa antes de cada caso. Tras ella quedaban 8,18 USD del tope
de 17.

**Criterios del ADR-0015,** con las mismas metas:

| Criterio | Meta | Corrida final del ADR-0015 | Paso 15 | ¿Cumple? |
|---|---|---|---|---|
| Validados en la v1 | al menos 15 de 19 | 18 de 20 | **11 de 20** | no |
| Primeros intentos de N10 rechazados | como máximo 2 de 29 | 7 de 23 | 4 de 35 | no |
| Sesiones escaladas | 0 | 0 | **4** | no |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,342 | 0,391 | no |
| Hallazgos CAL-FS-006, pruebas que simulan el efecto | 0 | 0 | 0 | sí |
| Turnos sin exploración, en la primera pausa de N6 | como máximo 211 | 210 | 205 | sí |
| Resúmenes confirmados | al menos 17 de 20 | 16 | **19** | sí |

**Otros resultados:**
- **Arquitectura:** coincide con la esperada en 20 de 20; antes, 19 de 20.
- **Sesiones en el límite de 18 turnos:** 1; antes, 5.
- **Tiempo del sistema:** 6,6 min de media y 10,3 como máximo, frente a los 20 del RNF-01.

**Lectura preliminar:**
- **Decisiones 38 y 39:** cumplieron su objetivo. Los resúmenes confirmados suben de 16 a 19 y las
  sesiones en el límite bajan de 5 a 1.
- **Decisión 37:** los primeros intentos rechazados de N10 bajan de 7 de 23 a 4 de 35.

**Resultado inesperado:** la calidad de la primera salida retrocede. Los validados en la v1 bajan de
18 a 11, y 4 sesiones escalan tras 3 iteraciones: 02, 03, 14 y 16.

### Causas del retroceso (investigadas el 2026-11-05, sin costo)

**Conclusión:** ningún cambio del sistema lo explica. La causa principal son escenarios defectuosos
de N5, que nada revisa antes de N10. Le sigue el juez de N14, que cambia de veredicto sobre pruebas
idénticas.

**Lo que no cambió entre las dos corridas:** las huellas de todos los prompts, los despliegues y sus
versiones. El consumo por nodo es casi igual. En los agentes solo cambiaron las decisiones 37 a 39.

**Los 9 casos que no salieron en la v1.** De 02 y 16, casos de referencia, solo va la clasificación:

| Caso | Causa | Desenlace |
|---|---|---|
| 02 | Escenario de N5 imposible según su propia regla | Escalado |
| 03 | N5 inventó las fechas: 2025-01-01 + 120 días da 2025-05-01, pero el escenario exige «vencido» el 2025-04-15 | Escalado |
| 13 | El ejemplo perdió su precondición (cupo reservado de 8:00 a 12:00), y N5 exige rechazar 11:00–13:00, una franja válida | Validado en la v2, con una fecha fija en `src/` |
| 19 | N5 metió una pregunta abierta en el «entonces» | Validado en la v2, con «pendiente concretar el mensaje exacto de error» como mensaje real |
| 14 | N5 agregó una capacidad de «revisión», con un escenario de tarea programada que el diseño no deja observar; además, pruebas flojas en la v1 | Escalado, con 13 de 14 casos cumplidos |
| 16 | Hallazgos reales en la v1; en la v2 y la v3, el juez rechazó pruebas idénticas que ya había aceptado | Escalado |
| 20 | Prueba floja en la v1; en la v2, el juez rechazó una prueba idéntica alegando que 1,0 y 7,0 °C no están fuera de 2,0–6,0 | Validado en la v3 |
| 10 | Una prueba falla de verdad en la v1 y la v2 | Validado en la v3 |
| 18 | Una prueba no compara los ítems de la venta | Validado en la v2 |

**Lo que se desprende:**
- **Sin los 4 escenarios defectuosos** (02, 03, 13 y 19), serían 15 de 20 en la v1.
- **Las escaladas no señalan errores de cálculo:** en ninguna de las 4 el último hallazgo lo es. La
  evaluación de referencia lo confirmará para 02 y 16.
- **Los «16 validados» sobrestiman la calidad,** porque 13 y 19 llevan el defecto del requerimiento
  al código. El analista simulado aprueba sin leer; en el caso 13, `USO.md` declara la excepción y
  una persona podría verla en N17.
- **Nada revisa la coherencia de los escenarios.** N6 mira la redacción. N10 detecta la contradicción
  y la declara en `USO.md`, pero no tiene cómo reportarla: en 02 y 03 marcó la prueba como fallo
  esperado y agotó las iteraciones; en 13 cedió y fijó el valor.
- **El juez es inestable:** cambió de veredicto en 3 de 124 rejuicios de una prueba idéntica (0 de 13
  en la corrida del ADR-0015), siempre hacia el rechazo y aun con la segunda opinión. Con un juez
  constante, 16 y 20 habrían salido en la v2.

**Lo que no se puede afirmar:**
- **Decisiones 37 a 39:** no se halló un mecanismo que las conecte con los escenarios defectuosos, y
  el defecto ya aparecía en una sesión de la corrida base (caso 01). Sí vuelven más completos los
  requerimientos, de 43 a 51 y de 160 a 183 escenarios: el caso 10 pasó de 4 a 8 escenarios, y su v1
  falló en una prueba real.
- **Azar:** con una corrida por caso no se separa de un efecto pequeño. Por sí sola, la caída de 18 a
  11 sería rara por azar (Fisher, p ≈ 0,03). La aparición de escenarios imposibles, de 0 a 4 sesiones,
  no tanto (p ≈ 0,11).

**Correcciones recomendadas, para después de medir** (van al informe):
- revisar la coherencia de los escenarios en N6;
- darle a N10 una vía para reportar un escenario imposible, y a N15 para escalarlo de inmediato;
- conservar el veredicto de una prueba que no cambió;
- una regla que detecte valores de un escenario fijados en `src/`.

**Fuentes:**
- los reportes de cada versión, en `evaluacion/resultados/paso-15/corrida-ampliada/<sesión>/v<n>/`;
- la traza, `docs/mediciones/paso-15-corrida-ampliada.jsonl`;
- los escenarios y el registro, en los puntos de control de cada sesión.

**Sesiones de los casos de referencia en esta corrida:**
- 02: `caso-ampliada-02.json`, escalada;
- 12: validada en la v1;
- 16: escalada.

Cada una es la corrida 1 del sistema para su caso.

### Resultado del modelo único (2026-11-05, de 12:23 a 12:55)

**Costo:** 1,7485 USD, de ellos 1,4900 del modelo y 0,2585 del cliente simulado. Se estimaban ~4,5:
cada corrida costó 0,166 USD de media, sin el cliente, no 0,5.

**Entregas:** 9 de 9, sin errores ni reintentos. Una corrida llegó al límite de turnos.

| Caso | Costo medio del modelo (USD) | Tiempo medio sin el cliente (min) | Turnos del cliente |
|---|---|---|---|
| 02 | 0,165 | 2,6 | 15,3 |
| 12 | 0,152 | 2,8 | 12,0 |
| 16 | 0,180 | 3,0 | 15,3 |

- **Frente al sistema:** la corrida ampliada gastó en estos tres casos 0,375 USD y 6,2 min de media,
  sin el cliente.
- **Lo que falta:** la tasa de errores, que da la evaluación de referencia (fase 4). Por la fase 2,
  nadie ha mirado el contenido de las entregas.
- **Dónde quedan:** en `evaluacion/resultados/paso-15/modelo-unico/<caso>/corrida-<n>/`, solo en esta
  máquina, porque `.gitignore` excluye `evaluacion/resultados/*`. Se versionan al recolectarlas en la
  fase 4. La traza es `docs/mediciones/paso-15-modelo-unico.jsonl`.

### Comandos

Todos desde `~/proyectos/SistemaMultiAgentes`, con `source .venv/bin/activate` y la infraestructura
arriba (`docker compose up -d --wait`).

**¿Sigue corriendo la corrida ampliada?** Sin costo:

```bash
pgrep -af evaluar_extremo_a_extremo
ls evaluacion/resultados/paso-15/corrida-ampliada/caso-*.json | wc -l
python scripts/evaluar_extremo_a_extremo.py --salida evaluacion/resultados/paso-15/corrida-ampliada --traza docs/mediciones/paso-15-corrida-ampliada.jsonl --resumen
```

**Si se detuvo antes de los 20 casos y ya no hay proceso:** se retoma con el mismo comando. Salta
los casos con resultado; el caso que quedó a medias se repite desde cero.

```bash
nohup python scripts/evaluar_extremo_a_extremo.py --salida evaluacion/resultados/paso-15/corrida-ampliada --traza docs/mediciones/paso-15-corrida-ampliada.jsonl --presupuesto 8.5 > ~/corrida-ampliada.log 2>&1 &
```

**Lo gastado en todo el paso,** sin costo:

```bash
python -c "from pathlib import Path; from multiagente.evaluacion.traza import gastado_en_traza as g; t = sorted(Path('docs/mediciones').glob('paso-15-*.jsonl')); [print(p.name, g(p)) for p in t]; print('total', sum(g(p) for p in t))"
```

**2 · Modelo único:**

```bash
python scripts/evaluar_modelo_unico.py --presupuesto 4.6
```

**3 · Corrida automática adicional del sistema:**

```bash
python scripts/evaluar_extremo_a_extremo.py --solo caso-ampliada-02 caso-ampliada-12 caso-ampliada-16 --salida evaluacion/resultados/paso-15/sistema-2 --traza docs/mediciones/paso-15-sistema-2.jsonl --presupuesto 1.3
```

**4 · Revisión humana**, cuando el caso ya se implementó a mano. La revisa quien no lo
implementó, decidiendo en N6, N9 y N17 sin pausas largas:

```bash
python scripts/producir_modulo.py --simulado evaluacion/casos/ampliada/elicitacion-reajuste-canon.md --salida evaluacion/resultados/paso-15/revision-humana
```

- **Sesión:** se anota en `evaluacion/resultados/paso-15/revision-humana/sesiones.json`, como
  `{"caso-ampliada-02": "<sesión>"}`.
- **Traza:** el guion la escribe en `docs/mediciones/paso-11-extremo-a-extremo.jsonl`, con la
  sesión de cada línea. Su costo se toma de ahí.

## Fase 4 · evaluación (pendiente)

1. **Recolectar:** `python scripts/evaluar_referencia.py --recolectar` copia cada implementación a
   `evaluacion/referencia/<caso>/implementaciones/<etiqueta>/` y escribe el manifiesto.
2. **Adaptadores:**
   - uno por implementación, en `evaluacion/referencia/<caso>/adaptadores/<etiqueta>.py`;
   - solo traducen la interfaz de `interfaz.md`, y la verificación automática rechaza los que
     calculan;
   - si falta un comportamiento, lanzan `Ausente`.
3. **Evaluar:**

   ```bash
   python scripts/evaluar_referencia.py --manifiesto evaluacion/referencia/implementaciones.json
   ```

   Después, la tabla con `--resumen`.
4. **RAGs:**

   ```bash
   python scripts/evaluar_rag.py --resultados evaluacion/resultados/paso-15/corrida-ampliada --presupuesto <lo que quede>
   ```

   Después, `--revision 5`, para que un autor revise cinco juicios.

## Fase 5 · informe y cierre (pendiente)

- **Informe:** `docs/evaluacion/informe-objetivo-4.md`. Por caso y por enfoque, con el tiempo, las
  horas-persona, el costo y la tasa de errores. Además:
  - el contraste con el RNF-01 y el RNF-10;
  - las RAGs;
  - las decisiones 37 a 39, con la tabla de criterios del ADR-0015.
- **ADR-0019:** queda aceptado, con los resultados y las hipótesis H1 a H3.
- **ADR-0015:** una columna «paso 15» en su tabla de criterios.
- **Paquete `docs/tesis/`:** se actualiza con el paso 15 y el ADR-0018.
- **CLAUDE.md:** el paso 15 cerrado.
- **Trazas:** se versionan cuando cada guion termina.
- **Commits** en español, sin atribución. El push lo hace el usuario.

# Estado del paso 15 · casos de referencia y líneas base

Documento de traspaso, actualizado el 2026-11-05 a las 09:30. Sirve para retomar el paso desde
otra sesión. El diseño, las métricas y las hipótesis, fijados antes de medir, están en el
ADR-0019 (`docs/decisiones/0019-casos-de-referencia-y-lineas-base.md`, en borrador).

## Qué pide el paso

- **Terminado cuando:** hay «métricas calculadas contra la implementación manual y contra un modelo
  único», que también es un despliegue de Azure OpenAI.
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
| 1 | Corrida ampliada de 20 casos | **En curso**: lanzada el 2026-11-05 a las 08:52 | 8,5 USD |
| 2 | Modelo único, 3 corridas × 3 casos | Pendiente | 4,6 USD |
| 3 | Una corrida automática más × 3 casos (`sistema-2`) | Pendiente | 1,3 USD |
| 4 | Corrida con revisión humana × 3 casos | Pendiente; va después de la manual de cada caso | ~1,2 USD |
| 5 | Juez de las métricas RAGs | Pendiente; va en la fase 4 | Lo que quede del tope de 17 |

**Avance de la corrida ampliada a las 09:23:** 4 de 20 casos, 1,72 USD, unos 8 minutos por caso,
con el final estimado hacia las 11:30.
- 01, 07 y 11: validados en la v1.
- **16, uno de los casos de referencia: escaló en la iteración 3,** con 18 turnos del cliente. En la
  corrida final del ADR-0015 se había validado en la v1.

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

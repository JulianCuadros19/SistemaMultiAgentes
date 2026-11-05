---
estado: aceptada
fecha: 2026-09-24
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0001 · Empaquetado del sistema y gestión de dependencias

> El ADR-0016 retira Langfuse de las dependencias: la traza por nodo vive en PostgreSQL.
> El ADR-0017 instala el paquete en la imagen de la aplicación, editable y con las versiones
> exactas del `.venv` como restricciones (`docker/aplicacion/versiones.txt`).

## Contexto y planteamiento del problema

El paso 1 del plan exige que el paquete `multiagente` se pueda importar. Hay que definir cómo
se empaqueta el código del sistema, con qué herramienta se gestiona el entorno, qué versión de
Python se usa y qué dependencias entran ahora. La decisión afecta a `pyproject.toml`, a
`src/multiagente/` y al entorno `.venv`, no al código que genera el agente desarrollador.

## Factores de decisión

- RNF-07: Python 3.11 o superior, desplegable en contenedores.
- RNF-05 y RNF-06: modificar un agente o su modelo sin alterar el resto del código.
- Decisión 3 de `CLAUDE.md`: el estilo del código del sistema y el del código generado se
  configuran por separado.
- El entorno de desarrollo es Ubuntu 26.04 sobre WSL2, cuyo Python es 3.14.4.
- Reproducibilidad durante todo el trabajo de grado, con pocas herramientas que aprender.

## Opciones consideradas

- A. `venv` y `pip` con `pyproject.toml`, backend hatchling y diseño `src/`.
- B. `uv` con archivo de bloqueo.
- C. Poetry.

## Resultado de la decisión

Opción elegida: «A», porque es la que describe `CLAUDE.md` (`.venv` activado con
`source .venv/bin/activate`), solo depende de herramientas estándar de Python y el diseño
`src/` impide importar el paquete sin instalarlo, lo que hace fiel la prueba del paso 1.

Decisiones asociadas:

1. **Python.** Piso `>=3.11` en `requires-python` y `target-version = "py311"` en Ruff, para
   que el código siga siendo compatible con 3.11 aunque se desarrolle en 3.14.
2. **Cotas de versión.** Cada dependencia lleva cota inferior en la versión resuelta el
   2026-09-24 y cota superior en la siguiente versión mayor. Ruff se fija a la versión menor
   (`<0.17`), porque sus versiones menores cambian reglas y formato.
3. **Alcance.** Entran solo las dependencias de los pasos 1 a 5: LangGraph y su checkpointer
   PostgreSQL, Pydantic, pydantic-settings, psycopg, openai y Langfuse. BGE-M3 y sus
   dependencias (torch y otras) se difieren al paso 6: pesan varios GB y la arquitectura los
   ubica en un servicio de embeddings aparte.
4. **Estilo del sistema.** `pyproject.toml` configura Ruff solo para `src/` y `tests/`, con
   anotaciones (ANN) y docstrings (D, convención google) obligatorias. Excluye
   `config/estilo_generado/`, que rige el código generado y se verifica en N12.
5. **Publicación.** El clasificador `Private :: Do Not Upload` impide subir el paquete a PyPI
   por accidente, en línea con el acuerdo de confidencialidad con Realtix.

### Consecuencias

- Favorable, porque no hay herramientas nuevas para el equipo y la versión del paquete tiene
  una sola fuente, `src/multiagente/__init__.py`.
- Favorable, porque el entorno se instala en segundos sin descargar modelos.
- Desfavorable, porque `pip` no genera archivo de bloqueo: dos instalaciones en fechas
  distintas pueden resolver versiones menores diferentes dentro de las cotas.
- Desfavorable, porque desarrollar en 3.14 con piso 3.11 no garantiza por sí solo la
  compatibilidad; una sintaxis exclusiva de 3.12 o posterior pasaría inadvertida sin una
  prueba en 3.11.

### Confirmación

- `pip install -e ".[dev]"` termina sin errores y `pip check` no reporta conflictos.
- `python -c "import multiagente"` funciona fuera de la raíz del repositorio.
- `pytest` ejecuta `tests/unitarias/test_importacion.py` sin fallos.
- `ruff check src tests` y `ruff format --check src tests` no reportan hallazgos.

## Análisis de las opciones

### Opción A · venv y pip
- Favorable, porque viene con Python y es lo que ya documenta `CLAUDE.md`.
- Desfavorable, porque no bloquea versiones transitivas.

### Opción B · uv
- Favorable, porque es rápido y produce un archivo de bloqueo reproducible.
- Desfavorable, porque añade una herramienta más que todo el equipo debe instalar y conocer.

### Opción C · Poetry
- Favorable, porque también bloquea versiones.
- Desfavorable, porque usa su propio flujo de trabajo y es más lento que las otras dos
  opciones sin aportar nada que el proyecto necesite hoy.

# Sistema multiagente de IA · Realtix

Trabajo de grado de la Universidad Católica de Colombia, semillero MAilab.
Autores: Julián Andrés Cuadros Muñoz y Laura Catalina Riveros Flórez.
Director: MsC. Juan Carlos Barrero Calixto.

Sistema de cuatro agentes que recorre la cadena completa de producción de software:
desde una conversación con el cliente hasta código Python validado.

**Responde siempre en español.**

## Documentos fuente

Léelos antes de proponer cualquier cambio de diseño. Son la fuente de verdad.

- `docs/requerimientos.md` · 39 requerimientos funcionales y 10 no funcionales. Define el QUÉ.
- `docs/arquitectura.md` · 17 nodos, 4 colecciones, modelo de datos, despliegue. Define el CÓMO.
- `docs/plan_de_trabajo.md` · pasos 0 a 15, cada uno con su condición de terminado.
- `docs/anexos.md` · Anexos A y B del documento de tesis: formato del requerimiento formal y
  de la especificación de diseño. El PDF original queda solo en local, en `docs/anexos/`.

Si una tarea contradice estos documentos, **detente y pregunta**. No resuelvas la
contradicción por tu cuenta, porque cada documento fue aprobado por el equipo técnico.

## Arquitectura en una pantalla

| Agente | Nodos | Consulta RAG | Produce |
|---|---|---|---|
| Elicitador | N1 a N6 | `elicitacion`, `dominio_negocio` | Historias de usuario y requerimientos formales |
| Arquitecto | N7 a N9 | `arquitecturas_referencia` | Registro de decisión y especificación de diseño |
| Desarrollador | N10 | **Ninguna** | Código Python, documentación y pruebas |
| Tester | N11 a N14 y N16 | `criterios_calidad` | Plan de pruebas de aceptación, veredicto por criterio y reporte de defectos |
| Orquestador | N15 y N17 | Ninguna | Decisión de enrutamiento y validación humana final |

Dos ciclos en el grafo: el conversacional entre N3 y N4, y el de corrección entre N10 y N15.
Tres puntos de control humano obligatorios: N6 aprueba requerimientos, N9 aprueba el diseño y
N17 valida el módulo final, con pruebas propias en el entorno aislado. Cada rechazo regresa al
agente anterior con observaciones. Al aprobarse los requerimientos, el tester los recibe y
deriva su plan de pruebas de aceptación (N16).
Solo 5 de los 17 nodos invocan un modelo de lenguaje: N3, N5, N8, N10 y N14.

## Decisiones que NO deben revertirse

Cada una tiene una razón. Si crees que alguna es un error, dilo y explica por qué,
pero no la cambies en silencio.

1. **El desarrollador no tiene RAG.** Su entrada, requerimientos más especificación de diseño,
   ya es una definición completa. Recuperar contexto añadiría latencia, costo y riesgo
   de contradecir la especificación. No propongas agregarle recuperación.
2. **El estilo del código generado es configuración, no conocimiento.** Vive en
   `config/estilo_generado/` y lo verifica N12 con Ruff. Nunca se recupera vía RAG.
3. **Hay dos configuraciones de estilo distintas.** `pyproject.toml` rige el código del
   sistema, el que escribimos nosotros. `config/estilo_generado/` rige el código que produce
   el agente. No las mezcles.
4. **Los agentes no conversan entre sí.** Se comunican exclusivamente leyendo y escribiendo
   el estado tipado del grafo. Nada de mensajes directos entre agentes.
5. **El arquitecto selecciona, no inventa.** Elige del catálogo cerrado en
   `knowledge_base/arquitecturas_referencia/catalogo/` y lo parametriza.
6. **El tester no modifica código.** Ejecuta, analiza y dictamina. La corrección es del
   desarrollador.
7. **La capa de modelos es agnóstica al proveedor.** Los identificadores de modelo viven en
   configuración, nunca dentro del código de un nodo. Cambiar de modelo es editar `.env`.
8. **Embeddings locales con BGE-M3, columna `vector(1024)`.** Cambiar de modelo de embeddings
   obliga a recrear la tabla y reindexar. No lo hagas sin consultar.
9. **Una sola base PostgreSQL** con filtro obligatorio por colección. No crees bases
   separadas por agente.
10. **Dinero y avalúos usan `Decimal`, nunca `float`.** Es una regla de calidad de severidad alta.
11. **Los prompts viven en `prompts/<agente>/` y se versionan.** Ningún prompt en línea
    dentro del código de un nodo.
12. **Los modelos de lenguaje son solo los desplegados en Azure OpenAI** (ADR-0017). Ningún nodo
    usa modelos locales ni de pesos abiertos, y no se propone un servidor de inferencia local.
    BGE-M3 no es un modelo de lenguaje: sigue local, porque el RNF-04 lo exige.

## Stack

Python 3.11 o superior · LangGraph · PostgreSQL 16 con pgvector · Docker · Azure OpenAI,
único proveedor de modelos de lenguaje (ADR-0017) · BGE-M3 local · traza por nodo en
PostgreSQL (ADR-0016) · pytest · Ruff.

## Entorno

- **Todo el desarrollo ocurre dentro de WSL2 con Ubuntu.** Claude Code, Python, Git y las
  herramientas del proyecto se ejecutan en Ubuntu, nunca en Windows. Propón siempre comandos
  de Linux.
- Ruta del proyecto: `~/proyectos/SistemaMultiAgentes`, en el sistema de archivos de Linux.
  **Nunca trabajar desde `/mnt/c/`**, que es lento y genera problemas de permisos.
- Docker Desktop corre en Windows con la integración WSL habilitada para Ubuntu. Los comandos
  `docker` se ejecutan desde la terminal de Ubuntu.
- `docker compose up -d --build --wait` levanta el sistema completo, con la web en
  `http://127.0.0.1:8000/` (ADR-0017). Para desarrollar con el `.venv` basta la infraestructura:
  `docker compose up -d --wait db embeddings`. La web del contenedor y `multiagente web` usan el
  mismo puerto: para usar la del `.venv`, `docker compose stop aplicacion`.
- Git y su configuración son los de Ubuntu, independientes de los de Windows.
- Entorno virtual en `.venv` en la raíz. Se activa con `source .venv/bin/activate`.
- Finales de línea LF forzados por `.gitattributes`.
- Secretos solo en `.env`, que nunca se versiona. La plantilla está en `.env.example`.
- El repositorio de GitHub es **privado** por el acuerdo de confidencialidad con Realtix.
  Todo material que entregue la empresa se trata como confidencial.

## Azure OpenAI

- Recurso de Microsoft Foundry en la suscripción Azure for Students. Regiones permitidas por
  política: southcentralus, centralus, canadacentral, brazilsouth y mexicocentral. Solo
  southcentralus y centralus cubren despliegue global, de zona de datos de EE. UU. y regional.
- Modelos desplegados, tipo Global Standard (ADR-0009):
  - `gpt-5.4-mini`, para N3 y N5, del perfil intermedio;
  - `gpt-5`, para N8, del perfil alto (ADR-0010);
  - `gpt-6.1-sol`, para N10, el perfil más alto disponible (ADR-0011);
  - `gpt-6-luna`, para N14, del perfil económico, elegido con el corpus de defectos (ADR-0012).
- Usar el paquete `openai` con la API OpenAI/v1. El paquete `azure-ai-inference` está retirado.
- **Los modelos GPT-5 son de razonamiento.** Generan tokens de razonamiento ocultos que se
  facturan como salida. En la primera prueba, una respuesta corta consumió cerca de 4.700
  tokens. Por eso cada nodo debe configurar su esfuerzo de razonamiento y su límite de tokens
  de salida, y la traza de costo debe registrar los tokens de razonamiento por separado.
- La orquestación es LangGraph. **No usar el servicio de agentes de Foundry.** El aviso del
  portal sobre permisos para crear agentes no aplica a este proyecto.
- **No habilitar la búsqueda web de Foundry.** Tiene costo adicional y envía datos fuera del
  límite de cumplimiento de Azure, lo que contradice el RNF-04.
- Con datos reales de Realtix, preferir despliegues de zona de datos de EE. UU. sobre los
  globales, porque un despliegue global puede procesar datos en cualquier región.

## Forma de trabajar

- **Un paso del plan a la vez.** No avances al siguiente sin cumplir la condición de terminado.
- **Antes de editar, propón un plan y espera aprobación.** El proyecto exige cuidado extremo.
- Cambios pequeños y verificables. Un commit por unidad lógica, con mensaje en español.
- **Sin atribución a herramientas.** Los commits, PR y documentos no llevan `Co-Authored-By`
  ni ninguna mención a Claude u otra herramienta. Los únicos autores son Julián y Laura.
  Lo refuerza `attribution` en `.claude/settings.json`.
- Toda decisión de diseño nueva se registra en `docs/decisiones/` como registro de decisión.
- Si algo falla, reporta el error completo antes de intentar arreglarlo.

## Convenciones de código

- Nombres de dominio en español: agentes, nodos, esquemas, colecciones.
- Tipado completo en toda interfaz pública. Docstring en toda función pública.
- Esquemas de datos con Pydantic. Los formatos del Anexo A y del Anexo B (`docs/anexos.md`)
  son la referencia para el requerimiento formal y la especificación de diseño.

## Estado actual

Mantener esta sección actualizada al cerrar cada paso.

- Objetivos 1 y 2: completados, documentos aprobados.
- Objetivo 3: en curso.
- **Paso 0: cerrado el 2026-09-24.** Verificado en Ubuntu 26.04.1 LTS sobre WSL2:
  Python 3.14.4 con `python3.14-venv`, Git 2.53.0, Docker 29.8.0 y Docker Compose v5.5.1
  mediante la integración WSL de Docker Desktop (`hello-world` se ejecuta).
- **Paso 1: cerrado el 2026-09-24.** `pyproject.toml` con hatchling y diseño `src/`
  (ADR-0001), `.venv` sobre Python 3.14.4, `pip install -e ".[dev]"` sin conflictos. El
  paquete `multiagente` y sus trece subpaquetes se importan; 14 pruebas pasan y Ruff no
  reporta hallazgos. BGE-M3 y sus dependencias quedan diferidos al paso 6.
- **Paso 2: cerrado el 2026-09-24.** `docker-compose.yml` con `pgvector/pgvector:0.8.6-pg16`
  (PostgreSQL 16.15, pgvector 0.8.6) en `127.0.0.1:5432`, volumen persistente y extensión
  `vector` creada por `db/init/` (ADR-0002). Se levanta con `docker compose up -d --wait`.
  Las pruebas de integración pasan con `pytest -m integracion`, también tras reiniciar el
  contenedor. Credenciales en `.env`.
- **Paso 3: cerrado el 2026-09-26.** Capa `multiagente.llm` por la API OpenAI v1 con Chat
  Completions (ADR-0003): esfuerzo de razonamiento y límite de salida obligatorios por
  llamada, costo en `Decimal` con `config/tarifas_modelos.toml`. Mediciones reales en
  `docs/mediciones/paso-03-azure-openai.jsonl`. Pruebas con costo: `pytest -m nube`.
- **Alineación con el documento de tesis: 2026-10-08** (ADR-0004). Anexos A y B transcritos
  en `docs/anexos.md`; el PDF queda solo en local. «Contrato de diseño» pasa a ser
  «especificación de diseño» (prefijo `ED-`). Flujo de 17 nodos con tres puntos de control
  humano (N6, N9 y N17) y plan de pruebas del tester (N16); nuevo RF-38, total 38 RF.
  Pendiente del equipo: actualizar el documento de tesis con el paquete de `docs/tesis/` (corte al
  paso 14, contrastado con la versión de 112 páginas del 2026-11-04), que consolida los cambios de
  los ADR-0004 y 0015 a 0017. Se actualiza al cerrar el paso 15.
- **Paso 4: cerrado el 2026-10-08.** Esquemas Pydantic en `multiagente.core.esquemas`
  (ADR-0005): `BacklogHistorias` y `RequerimientoFormal` (Anexo A) y `EspecificacionDiseno`
  (Anexo B, con la validación 1: estructura y ausencia de ciclos). Validan el backlog y el RF-27
  del Anexo A y los ejemplos de las plantillas 03 y 02; 86 pruebas unitarias pasan.
- **Paso 5: cerrado el 2026-10-08.** Grafo de 17 nodos en `multiagente.orquestador` (ADR-0006):
  - estado tipado con particiones Pydantic inmutables;
  - nodos determinísticos y puntos de control reales (`interrupt`);
  - el trabajo de cada agente entra por un `Protocol` de servicios: hoy `ServiciosSimulados`,
    en los pasos 6 a 10 los agentes reales en `agentes/<agente>/`;
  - persistencia con `PostgresSaver` (`abrir_checkpointer`), durabilidad síncrona y lista
    blanca de tipos en el serializador.

  Verificado:
  - una sesión recorre los 17 nodos, cierra ambos ciclos, ejercita los tres retornos y se
    reanuda en un proceso nuevo, tanto a mitad del diálogo como tras una caída;
  - pasan 106 pruebas unitarias y 5 de integración;
  - `python scripts/simular_sesion.py` muestra el recorrido.
- **Paso 6: cerrado el 2026-10-08.** Bases de conocimiento en `multiagente.rag` (ADR-0007):
  - **Servicios:** `embeddings` (TEI 1.9.4 en CPU, BGE-M3 ONNX, revisión fijada, sin conexión
    externa) y `descarga-modelo` (curl reanudable verificado con SHA-256). La primera vez
    descarga 2,29 GB.
  - **Tablas:** migración `0001` con `kb_documentos` y `kb_fragmentos` (`vector(1024)`, HNSW,
    léxico en español y por colección).
  - **Corpus:** 36 documentos y 184 fragmentos, segmentados según su estrategia; ingesta
    idempotente con `python scripts/ingestar_conocimiento.py`.
  - **Recuperación:** `Recuperador` por agente con filtro obligatorio por colección; el
    desarrollador no tiene recuperador. Combina búsqueda semántica y léxica con fusión por
    rango recíproco y umbral de relevancia 0,37 calibrado.
  - **Verificado:** 120 pruebas unitarias, 27 de integración y 15 con el modelo real
    (`pytest -m "embeddings and not nube"`: `-m embeddings` a secas también recolecta las pruebas
    `nube`, que llaman a Azure).
  - **Pendiente para los pasos 7, 8 y 10:** construir las consultas con los artefactos
    completos, que N7 recupere todo el catálogo de seis arquitecturas y recalibrar el umbral.
- **Paso 7: cerrado el 2026-10-09.** Agente elicitador real en `agentes/elicitador/` (ADR-0008):
  - la sesión se abre con la necesidad del cliente; N2 recupera la guía de elicitación y el
    dominio de esa necesidad;
  - N3 hace dos llamadas: extracción sin contexto de dominio y pregunta con el contexto. El
    resumen que confirma el cliente lo arma el código;
  - N5 sintetiza con el formato del Anexo A y referencias `F1…Fn` al contexto. La fidelidad se
    verifica en código: solo entra lo que respalda lo dicho por el cliente;
  - N6 verifica el RF-07 sin modelo, corrige hasta dos veces y escala al analista. Los defectos
    que requieren al cliente escalan sin corregir;
  - prompts versionados en `prompts/elicitador/` e invocación estructurada con un reintento y
    traza de costo en `multiagente.llm`.

  Verificado:
  - 224 pruebas unitarias, 27 de integración y 17 de embeddings;
  - `pytest -m nube tests/integracion/test_elicitador_nube.py`, con un cliente simulado sobre
    `evaluacion/casos/elicitacion-mutacion.md`, llega a N6 sin defectos (6 de 7 corridas);
  - `python scripts/conversar_elicitador.py` permite conversar o simular, y reproduce pausa,
    reanudación, rechazo y aprobación;
  - con `gpt-5.4-mini` (ADR-0009), 4 de 4 corridas `nube` pasan y cada llamada de N3 tarda 1,6 s
    de media; el turno más largo mide 11,6 s y el costo es de 0,018 a 0,033 USD por elicitación.
    Con `gpt-5-nano` pasaban 6 de 7, con turnos de hasta 15,3 s y 0,002 a 0,005 USD.

  Pendiente:
  - el benchmark del paso 15 compara `gpt-5-nano`, `gpt-5-mini` y `gpt-5.4-mini` en N3 y N5;
  - la interfaz del paso 12 debe acusar la confirmación antes de sintetizar.
- **Paso 8: cerrado el 2026-10-09.** Agente arquitecto real en `agentes/arquitecto/` (ADR-0010):
  - N7 recupera las seis arquitecturas del catálogo cerrado, cada una de su propio documento,
    junto con la metodología;
  - N8 hace dos llamadas con `gpt-5` (esfuerzo low, 300 s de espera): la selección, cuyo
    registro MADR verifica y arma el código, y la parametrización, cuyos campos deterministas
    asigna el código;
  - N9 aplica las tres validaciones del Anexo B y reglas de arq-002 (firmas con tipos, rutas,
    nombres que no tapen la biblioteca estándar, Decimal en dinero). Devuelve a N8 hasta dos
    veces y después solo admite el rechazo.
  - Se corrigió un defecto del paso 5: una respuesta humana inválida ya no detiene la sesión,
    sino que vuelve a pausar con un aviso.

  Verificado:
  - 276 pruebas unitarias, 27 de integración y 19 de embeddings;
  - `pytest -m nube tests/integracion/test_arquitecto_nube.py`, sobre tres casos de
    `evaluacion/casos/diseno-*.json`: 9 de 9 corridas pasan en el primer diseño, con la
    arquitectura elegida entre las candidatas de arq-003, a 0,05–0,08 USD por diseño;
  - `python scripts/disenar_arquitectura.py` reproduce el rechazo con observaciones y la
    aprobación.
- **Paso 9: cerrado el 2026-10-09.** Agente desarrollador real en `agentes/desarrollador/` (ADR-0011):
  - N10 usa `gpt-6.1-sol` con esfuerzo medium, en una llamada estructurada sin recuperación;
    recibe los requerimientos, la especificación y `config/estilo_generado/ruff.toml`;
  - la verificación estructural de RF-15, RF-17 y RF-18 corre en código, sin ejecutar nada:
    - archivos en las rutas declaradas y sintaxis 3.11;
    - firmas compatibles y excepciones declaradas;
    - dependencias permitidas y docstring en todo lo público;
    - una prueba `test_rf_NN_esc_NN` por escenario.

    Reintenta una vez con los problemas a la vista;
  - la corrección (RF-19) recibe la versión previa y la retroalimentación, y combina solo los
    archivos que cambian;
  - el entorno aislado mínimo (`multiagente.sandbox`, `docker/sandbox/`) importa el código en un
    contenedor efímero sin red, de solo lectura y sin root. Lo reutilizará N11;
  - el costo refleja la escritura en caché de GPT-6, y `VersionCodigo` conserva el contenido de
    los archivos tal cual (defecto del paso 5);
  - `ArquitectoFijo` y `evaluacion/casos/desarrollo-*.json` prueban al desarrollador con diseños
    aprobados en el paso 8.

  Verificado:
  - 358 pruebas unitarias, 27 de integración, 19 de embeddings y 5 del entorno aislado
    (`pytest -m "sandbox and not nube"`, con la imagen de `docker compose --profile sandbox build
    sandbox`);
  - `pytest -m "nube and sandbox" tests/integracion/test_desarrollador_nube.py`: 6 de 6 corridas
    finales importan cada módulo y cubren las interfaces, 5 al primer intento. Las pruebas
    generadas pasan sin red, por 0,06 a 0,21 USD y de 1 a 2 minutos por generación;
  - `python scripts/generar_modulo.py` reproduce el rechazo en N17 y la corrección.

  Pendiente para el paso 10:
  - N12 debe aplicar la misma noción de firma compatible y clasificar los hallazgos de Ruff;
  - el código generado importa funciones privadas de otros módulos.
- **Paso 10: cerrado el 2026-10-09.** Agente tester real en `agentes/tester/` (ADR-0012):
  - todo lo verificable se decide en código:
    - N11 ejecuta en el entorno aislado, con resultado por prueba;
    - N12 aplica Ruff y la conformidad compartida con N10 (`core/conformidad.py`), además de
      trazabilidad, dinero y secretos;
    - N14 dictamina cada caso y aplica la regla de cal-sv con `UMBRAL_HALLAZGOS_MEDIA=0`;
  - el modelo de N14 (`gpt-6-luna`) solo juzga si las pruebas que pasaron verifican su
    escenario, con los archivos de prueba completos a la vista;
  - cada hallazgo cita su regla con la severidad de la base; las reglas sin comprobación quedan
    como no evaluadas;
  - CAL-MT-009 (estilo) y CAL-MT-010 (nombres privados) entran a criterios_calidad. El corpus
    pasa a 186 fragmentos y 33 reglas;
  - corpus de defectos en `evaluacion/defectos/`: dos controles limpios y 16 inyecciones, 3 de
    ellas solo detectables por el juez.

  Verificado:
  - 433 pruebas unitarias, 27 de integración, 19 de embeddings y 25 del entorno aislado;
  - `pytest -m "nube and embeddings and sandbox" tests/integracion/test_tester_nube.py`: en 3 de
    3 corridas detecta los 16 defectos con su regla, aprueba los controles sin hallazgos y el juez
    no tiene rechazos falsos, a 0,003 USD por corrida;
  - `python scripts/evaluar_tester.py` da la matriz de confusión y los aciertos del juez por caso.

  Pendiente:
  - las pruebas propias de la persona en N17 (RF-38) se conectan en el paso 12;
  - el paso 11 medirá cuántas iteraciones gasta el umbral 0 con módulos reales.
- **Paso 11: cerrado el 2026-10-09.** Integración de extremo a extremo (ADR-0013):
  - `agentes/servicios.py` arma los cuatro agentes reales; el desarrollador, sin recuperador;
  - `interfaces/consola.py` presenta N6, N9 y N17, y `ejecucion.validaciones` recupera la
    validación de cada versión desde los puntos de control;
  - `python scripts/producir_modulo.py` permite a una persona operar el flujo completo por consola
    (cliente y revisores), pausar y reanudar; con `--simulado CASO` responde un cliente simulado;
  - casos sintéticos de elicitación de avalúo y de liquidación por lotes;
  - la integración destapó un defecto de la fidelidad de N3: «4 dígitos» no se respaldaba con
    «cuatro dígitos». Corregido.

  Verificado:
  - 448 pruebas unitarias, 27 de integración, 19 de embeddings y 25 del entorno aislado;
  - `pytest -m "nube and embeddings and sandbox" tests/integracion/test_extremo_a_extremo_nube.py`:
    9 de 9 corridas, sobre tres casos y cuatro arquitecturas, salen aprobadas por el tester y
    validadas en N17, en 2,7 a 14,3 min por módulo;
  - una persona operó el flujo con una necesidad propia, rechazó en N6 y en N17 y llegó a un
    módulo validado;
  - umbral 0: de 14 módulos, 11 aprobados en la v1 y 3 en la v2, todos por hallazgos Alta;
    ninguno escaló.

  Pendiente:
  - N10 falla la verificación al primer intento en 5 de 9 corridas (excepciones declaradas sin
    importar y sangría rota). El reintento lo corrige, pero duplica su costo;
  - el paso 12 debe mostrar cuántas iteraciones quedan antes de decidir en N17, porque un rechazo
    allí consume el ciclo de corrección.
- **Paso 12: cerrado el 2026-11-04.** Interfaces de consola y web (ADR-0014) y calidad de la
  primera salida (ADR-0015; `docs/arquitectura.md` 1.3, `docs/requerimientos.md` 1.2):
  - comando `multiagente` (nueva, continuar, cerrar, sesiones, ver, exportar, web) y web local
    en `http://127.0.0.1:8000/`, con panel del equipo y vista del cliente; ambas usan el
    `Operador` de `interfaces/operacion.py`;
  - flujo sin bloqueos: las fallas del modelo se vuelven decisiones, N15 escala a N17 al agotar el
    ciclo y toda sesión en pausa o detenida se puede cerrar (fase `cerrada`);
  - N17 devuelve el módulo al desarrollador o al arquitecto, o pide al elicitador una enmienda de
    los requerimientos (N17 → N5 → N6 → N16 → N10, RF-39);
  - pulido de los cuatro agentes, con el plan aprobado en
    `~/.claude/plans/lee-claude-md-y-continuemos-fluttering-shamir.md`:
    - el tester reconoce las pruebas que simulan el efecto (CAL-FS-006);
    - el arquitecto declara recorridos ejecutables y métodos `Clase.metodo`, y N9 rechaza `self`
      en las funciones de módulo;
    - el desarrollador sigue los recorridos, parte de la versión previa tras un rediseño y se
      adelanta al estilo del tester;
    - el elicitador pregunta por casos límite, con un límite de 18 turnos, y su resumen solo
      muestra el tipo y la obligatoriedad que dijo el cliente;
    - N6 corrige lo corregible aunque haya preguntas abiertas;
  - prompts vigentes: elicitador diálogo 1.10, extracción 1.7, síntesis 1.9 y enmienda 1.0;
    `arquitecto.parametrizacion` 1.6, `desarrollador.generacion` 1.9 y `tester.veredicto` 1.2.

  Verificado:
  - 731 pruebas unitarias, 31 de integración, 19 de embeddings y 33 del entorno aislado;
  - la verificación con el equipo del 2026-11-03 (sesiones `61e1e121`, `5f5d2739` y `b271c343`);
  - la prueba `nube` de la enmienda (`test_enmienda_nube.py`): el RF sube a v0.2 y el módulo
    corregido sale aprobado, por 0,20 USD;
  - la corrida ampliada final (ADR-0015, fase 7), sobre 20 casos y por 7,59 USD:
    - 20 de 20 módulos validados, 18 en la v1 (línea base: 10 de 19), y ninguno escalado;
    - 0,342 USD por módulo y 5,3 min de media.

  Sin cumplir, por decisión del equipo:
  - primeros intentos de N10 rechazados: 7 de 23, con el criterio en 2 de 29;
  - resúmenes confirmados: 16 de 20, con el criterio en 17.
  Las decisiones 37 a 39 atienden tres de sus causas, sin medir.

  Pendiente:
  - la respuesta incompleta de N10, un archivo de pruebas de relleno, en 3 de 23 primeros
    intentos;
  - lo que el cliente pide en los resultados queda en las reglas (caso 12);
  - las necesidades de eventos se plantean como «publicar un aviso»;
  - el costo por módulo está al borde del criterio, empujado por ARQ-06; el presupuesto que
    detiene la ejecución es el paso 13.
- **Paso 13: cerrado el 2026-11-04.** Control de costo y traza por nodo (ADR-0016;
  `docs/arquitectura.md` 1.4):
  - cada nodo corre envuelto (`_instrumentado`, `orquestador/grafo.py`): suma a
    `Control.costo_acumulado_usd` el costo de sus llamadas al modelo, capturadas con
    `capturar_llamadas()`, e informa su traza;
  - presupuesto por módulo `PRESUPUESTO_MAXIMO_POR_MODULO_USD`, de 1,50 USD por defecto:
    - antes de N3, N5, N8, N10 y N14, una sesión que lo alcanzó pausa en «presupuesto»;
    - una persona lo amplía, y queda registrado quién, cuánto, cuándo y por qué, o cierra la
      sesión;
  - traza por nodo en PostgreSQL (migración 0002: `ejecuciones` y `llamadas_modelo`), con
    `multiagente traza ID` y la página «Traza por nodo»; las interfaces migran al arrancar;
  - Langfuse sale del stack, por decisión del equipo: la versión autoalojada exigía cinco
    contenedores más.

  Verificado:
  - 741 pruebas unitarias, 34 de integración, 19 de embeddings y 33 del entorno aislado;
  - `pytest -m "nube and embeddings" tests/integracion/test_presupuesto_nube.py`: con el
    elicitador real y 0,005 USD de presupuesto, la sesión se detiene antes de que N3 vuelva a
    llamar al modelo; ampliado, sigue, y la traza trae por nodo prompts, tokens, costo y tiempos.
    Costó 0,011 USD.

  Límites, en el ADR-0016:
  - el exceso queda acotado a un nodo;
  - el costo de un nodo que falla por infraestructura no suma al acumulado;
  - en N3, la ampliación se escribe en el estado cuando el cliente responde.
- **Paso 14: cerrado el 2026-11-04.** Empaquetado en contenedores con Azure OpenAI (ADR-0017;
  requerimientos 1.3, arquitectura 1.5):
  - el equipo descartó el «modo local»: los modelos de lenguaje son solo los despliegues de Azure
    OpenAI, y BGE-M3 sigue local por el RNF-04. El RF-37, el RNF-06, la arquitectura y el plan de
    trabajo se corrigieron;
  - `docker compose up -d --build --wait` levanta el sistema completo:
    - la imagen de `docker/aplicacion/`, con Python 3.14.4, las versiones exactas del `.venv`
      (`scripts/congelar_aplicacion.py`) y la CLI de Docker;
    - los servicios `aplicacion` (web solo en 127.0.0.1, socket de Docker y `data/local`) e
      `ingesta`, y la comprobación de `sandbox`, que sale de su perfil;
    - el punto de entrada corre como el dueño de `data/local`, con el grupo del socket;
  - la consola se usa con `docker compose run --rm aplicacion multiagente …`. La web sigue sin
    autenticación y solo responde en la máquina.

  Verificado:
  - 754 pruebas unitarias, 34 de integración, 19 de embeddings y 33 del entorno aislado;
  - desde un clon limpio, con volúmenes nuevos, el caso 05 salió validado en N17 en la v1 dentro
    de los contenedores, por 0,245 USD. La web y la consola lo mostraron, con su traza y su
    exportación. Las dos sesiones de la verificación costaron 0,40 USD
    (`docs/mediciones/paso-14-contenedores.jsonl`).

  Límites, en el ADR-0017:
  - la primera construcción depende de PyPI: con una red lenta tardó 33 min y una vez falló;
    repetir el comando la retoma;
  - `docker compose exec` entra como root;
  - macOS no se verificó.
- **Rediseño de la interfaz web: 2026-11-05** (ADR-0018), antes del paso 15:
  - la sesión se organiza en cinco etapas con la línea del flujo, con rombos en N6, N9 y N17;
    se ve una etapa a la vez y cada una conserva lo ya aprobado;
  - el panel agrupa las sesiones según quién debe actuar, con la línea en miniatura; el cliente ve
    «Equipo» y su avance en cuatro pasos; la trazabilidad y la traza se leen en HTML;
  - IBM Plex servida por la aplicación (OFL), sin recursos externos, y huella `?v=` en los
    estáticos;
  - `python scripts/web_demostracion.py` levanta la web en `127.0.0.1:8010` con nueve sesiones
    simuladas, sin costo.

  Verificado: 771 pruebas unitarias, 34 de integración, 19 de embeddings y 33 del entorno aislado;
  capturas en claro, en oscuro y a 390 px con Edge sin ventana. La imagen de la aplicación se
  reconstruye con `docker compose up -d --build --wait` para ver la web nueva en el puerto 8000.
- **Paso 15: cerrado el 2026-11-05.** Casos de referencia y líneas base (ADR-0019, aceptado). Informe en
  `docs/evaluacion/informe-objetivo-4.md`; estado y comandos en `docs/evaluacion/estado-paso-15.md`.
  - **Decisión del equipo:** sin implementación manual. Realtix no puede compartir sus desarrollos y los autores no son
    independientes. Se compara contra un LLM independiente; el ahorro frente a lo manual queda como recomendación.
  - **Diseño:** tres enfoques, nueve casos con las seis arquitecturas y un mismo oráculo, de 90 verificaciones
    validadas con 35 mutantes (`evaluacion/referencia/`).
  - **Resultados:**
    - sistema: 3,4 % de errores, 0,358 USD y 5,9 min por módulo;
    - LLM con diálogo: 5,4 %, 0,170 USD y 2,9 min;
    - LLM de un solo prompt: 0,0 %, 0,104 USD y 2,5 min.

    H1 no se sostiene: el sistema no tiene menos errores, y cuesta y tarda el doble o más. Su aporte son los requerimientos, el
    diseño, la validación independiente, el control humano y la traza. Sus errores nacen en la síntesis y en el diseño, no al
    escribir el código.
  - **Tester:** 63 de 63 y 9 de 9 con defectos inyectados; frente al oráculo, en 21 versiones, exactitud de 0,52, con matices
    que explica el informe.
  - **Corrida ampliada de 20 casos:** 16 validados, 11 en la v1, y 4 escalados; las decisiones 37 a 39 cumplieron su objetivo.
    Los módulos 13 y 19 salieron validados con defectos del requerimiento fijados en el código.
  - **RAGs:** fidelidad de 0,81, 0,84 y 0,47 (subestimada); relevancia del contexto de `dominio_negocio`, 0,10.
  - **Despliegue de demostración (ADR-0020):** `scripts/desplegar_azure.sh` y `docker-compose.azure.yml`, en una máquina de
    Azure con TLS y contraseña, solo con datos sintéticos.
  - **Costo:** 16,74 USD de los 17 del tope.
  - **Verificado:** 812 pruebas unitarias, 34 de integración, 19 de embeddings y 44 del entorno aislado.
  - **Pendiente del equipo:**
    - revisar los oráculos frente a las fichas y 5 juicios de RAGs (`evaluacion/resultados/paso-15/rag/revision.md`);
    - aplicar `docs/tesis/` al documento, con `05-evaluacion-paso-15.md`, y resolver sus marcas `[CONFIRMAR]`;
    - rotar la clave de Azure OpenAI y borrar la máquina cuando no se necesite.
  - **Correcciones recomendadas, sin aplicar:** en la sección 10 del informe. El sistema no cambió durante la medición.
- **Push a GitHub: manual.** El remoto `origin` es HTTPS y Ubuntu no guarda credenciales.
  Claude nunca hace push; pide al usuario ejecutar `git push origin master` en su consola.
- **Azure OpenAI: operativo y conectado desde código.** Recurso en southcentralus, procesado en
  South Central US. Despliegues Global Standard:
  - `gpt-5-nano` (versión 2025-08-07): entrada 0,05, caché 0,005 y salida 0,40 USD por millón de
    tokens;
  - `gpt-5.4-mini` (versión 2026-03-17): entrada 0,75, caché 0,075 y salida 4,50 USD;
  - `gpt-5` (versión 2025-08-07): entrada 1,25, caché 0,125 y salida 10 USD;
  - `gpt-6.1-sol` (versión 2026-09-29): entrada 2,00, caché 0,10, escritura de caché 2,50 y salida
    10 USD. Los GPT-6 cobran aparte la escritura en caché, que la API reporta en
    `cache_write_tokens` (ADR-0011);
  - `gpt-6-luna` (versión 2026-09-22): entrada 0,10, caché 0,01, escritura de caché 0,125 y
    salida 0,50 USD.

  Endpoint y clave solo en `.env`. Las tarifas están en `config/tarifas_modelos.toml`. Para
  `gpt-5-nano`, medido con el mismo mensaje: minimal 80 tokens de salida y 1,7 s; low
  555 (448 de razonamiento) y 4,6 s; medium 1.340 (1.216 de razonamiento) y 8,9 s. Si el
  límite es menor que el razonamiento, la respuesta llega vacía con motivo `length` y se
  cobra igual.
- **Modelo de costos: unidad de trabajo medida en el paso 11** (ADR-0013). Un módulo cuesta de
  0,16 a 0,37 USD, con media de 0,27, sin el cliente simulado. N10 aporta el 51 %, N8 el 31 %, N3
  el 14 %, N5 el 4 % y N14 el 0,4 %. En la corrida ampliada final del paso 12 (ADR-0015), la media
  sube a 0,342 USD, de 0,18 a 0,87: N10 aporta el 41 %, N8 el 27 %, N3 el 21 %, N5 el 11 % y N14
  menos del 1 %. Desde el paso 13, el presupuesto de 1,50 USD por módulo la acota (ADR-0016).

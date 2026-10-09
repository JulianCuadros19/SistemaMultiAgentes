# Sistema multiagente de IA · Realtix

Trabajo de grado de la Universidad Católica de Colombia, semillero MAilab.
Autores: Julián Andrés Cuadros Muñoz y Laura Catalina Riveros Flórez.
Director: MsC. Juan Carlos Barrero Calixto.

Sistema de cuatro agentes que recorre la cadena completa de producción de software:
desde una conversación con el cliente hasta código Python validado.

**Responde siempre en español.**

## Documentos fuente

Léelos antes de proponer cualquier cambio de diseño. Son la fuente de verdad.

- `docs/requerimientos.md` · 38 requerimientos funcionales y 10 no funcionales. Define el QUÉ.
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

## Stack

Python 3.11 o superior · LangGraph · PostgreSQL 16 con pgvector · Docker · Azure OpenAI
durante el desarrollo, modelos locales en la entrega · BGE-M3 local · Langfuse · pytest · Ruff.

## Entorno

- **Todo el desarrollo ocurre dentro de WSL2 con Ubuntu.** Claude Code, Python, Git y las
  herramientas del proyecto se ejecutan en Ubuntu, nunca en Windows. Propón siempre comandos
  de Linux.
- Ruta del proyecto: `~/proyectos/SistemaMultiAgentes`, en el sistema de archivos de Linux.
  **Nunca trabajar desde `/mnt/c/`**, que es lento y genera problemas de permisos.
- Docker Desktop corre en Windows con la integración WSL habilitada para Ubuntu. Los comandos
  `docker` se ejecutan desde la terminal de Ubuntu.
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
  - `gpt-5-nano`, para N14, del perfil económico, y provisionalmente para N10.

  El modelo de N10 se decide al empezar el paso 9.
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
  Pendiente del equipo: actualizar el documento de tesis (RF-38, Tabla 23, Figura 7, Anexos B y C).
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
    (`pytest -m embeddings`).
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
- **Paso actual: 9.** Agente desarrollador: el código se importa sin error y cubre las interfaces
  de la especificación.
- **Push a GitHub: manual.** El remoto `origin` es HTTPS y Ubuntu no guarda credenciales.
  Claude nunca hace push; pide al usuario ejecutar `git push origin master` en su consola.
- **Azure OpenAI: operativo y conectado desde código.** Recurso en southcentralus, procesado en
  South Central US. Despliegues Global Standard:
  - `gpt-5-nano` (versión 2025-08-07): entrada 0,05, caché 0,005 y salida 0,40 USD por millón de
    tokens;
  - `gpt-5.4-mini` (versión 2026-03-17): entrada 0,75, caché 0,075 y salida 4,50 USD;
  - `gpt-5` (versión 2025-08-07): entrada 1,25, caché 0,125 y salida 10 USD.

  Endpoint y clave solo en `.env`. Las tarifas están en `config/tarifas_modelos.toml`. Para
  `gpt-5-nano`, medido con el mismo mensaje: minimal 80 tokens de salida y 1,7 s; low
  555 (448 de razonamiento) y 4,6 s; medium 1.340 (1.216 de razonamiento) y 8,9 s. Si el
  límite es menor que el razonamiento, la respuesta llega vacía con motivo `length` y se
  cobra igual.
- **Modelo de costos: pendiente de recálculo.** Ya hay datos por llamada del paso 3; falta
  estimar la unidad de trabajo por módulo cuando existan los nodos reales.

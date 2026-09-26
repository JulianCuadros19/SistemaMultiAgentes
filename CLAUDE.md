# Sistema multiagente de IA · Realtix

Trabajo de grado de la Universidad Católica de Colombia, semillero MAilab.
Autores: Julián Andrés Cuadros Muñoz y Laura Catalina Riveros Flórez.
Director: MsC. Juan Carlos Barrero Calixto.

Sistema de cuatro agentes que recorre la cadena completa de producción de software:
desde una conversación con el cliente hasta código Python validado.

**Responde siempre en español.**

## Documentos fuente

Léelos antes de proponer cualquier cambio de diseño. Son la fuente de verdad.

- `docs/requerimientos.md` · 37 requerimientos funcionales y 10 no funcionales. Define el QUÉ.
- `docs/arquitectura.md` · 15 nodos, 4 colecciones, modelo de datos, despliegue. Define el CÓMO.
- `docs/plan_de_trabajo.md` · pasos 0 a 15, cada uno con su condición de terminado.

Si una tarea contradice estos documentos, **detente y pregunta**. No resuelvas la
contradicción por tu cuenta, porque cada documento fue aprobado por el equipo técnico.

## Arquitectura en una pantalla

| Agente | Nodos | Consulta RAG | Produce |
|---|---|---|---|
| Elicitador | N1 a N6 | `elicitacion`, `dominio_negocio` | Historias de usuario y requerimientos formales |
| Arquitecto | N7 a N9 | `arquitecturas_referencia` | Registro de decisión y contrato de diseño |
| Desarrollador | N10 | **Ninguna** | Código Python, documentación y pruebas |
| Tester | N11 a N14 | `criterios_calidad` | Veredicto por criterio y reporte de defectos |
| Orquestador | N15 | Ninguna | Decisión de enrutamiento |

Dos ciclos en el grafo: el conversacional entre N3 y N4, y el de corrección entre N10 y N15.
Dos puntos de control humano obligatorios: N6 aprueba requerimientos, N9 aprueba el diseño.
Solo 5 de los 15 nodos invocan un modelo de lenguaje: N3, N5, N8, N10 y N14.

## Decisiones que NO deben revertirse

Cada una tiene una razón. Si crees que alguna es un error, dilo y explica por qué,
pero no la cambies en silencio.

1. **El desarrollador no tiene RAG.** Su entrada, requerimientos más contrato de diseño,
   ya es una especificación completa. Recuperar contexto añadiría latencia, costo y riesgo
   de contradecir el contrato. No propongas agregarle recuperación.
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
- Modelo desplegado: `gpt-5-nano`, tipo Global Standard. Probado con éxito en el playground.
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
- Esquemas de datos con Pydantic. Los contratos del Anexo A y del Anexo B de los documentos
  fuente son la referencia para requerimiento formal y contrato de diseño.

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
- **Paso actual: 4.** Contratos de datos: los esquemas validan los ejemplos de los Anexos A y B.
- **Push a GitHub: manual.** El remoto `origin` es HTTPS y Ubuntu no guarda credenciales.
  Claude nunca hace push; pide al usuario ejecutar `git push origin master` en su consola.
- **Azure OpenAI: operativo y conectado desde código.** Recurso en southcentralus, despliegue
  Global Standard de `gpt-5-nano` (versión 2025-08-07), procesado en South Central US.
  Endpoint y clave solo en `.env`. Tarifas: entrada 0,05, caché 0,005 y salida 0,40 USD por
  millón de tokens. Medido con el mismo mensaje: minimal 80 tokens de salida y 1,7 s; low
  555 (448 de razonamiento) y 4,6 s; medium 1.340 (1.216 de razonamiento) y 8,9 s. Si el
  límite es menor que el razonamiento, la respuesta llega vacía con motivo `length` y se
  cobra igual.
- **Modelo de costos: pendiente de recálculo.** Ya hay datos por llamada del paso 3; falta
  estimar la unidad de trabajo por módulo cuando existan los nodos reales.

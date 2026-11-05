---
estado: aceptada
fecha: 2026-10-08
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0007 · Bases de conocimiento: embeddings locales, segmentación y recuperación híbrida

> El ADR-0012 (paso 10) agrega a criterios_calidad las reglas CAL-MT-009 y CAL-MT-010: el corpus
> pasa a 186 fragmentos, 51 de criterios y 33 reglas.
> El ADR-0017 (paso 14) deja a Azure OpenAI como único proveedor de modelos de lenguaje y retira el
> factor del RF-37 de operar sin nube. Los embeddings siguen locales por el RNF-04 y por el costo.

## Contexto y planteamiento del problema

El paso 6 exige que cada agente recupere únicamente de sus colecciones autorizadas. Cubre:
- RF-29: aislamiento por agente.
- RF-30: ingesta y segmentación según la naturaleza del contenido.
- RF-31: recuperación híbrida.
- RF-32: evaluación de relevancia.
- RNF-04: embeddings locales.

El corpus tiene 36 documentos en cuatro colecciones. La decisión afecta a `docker-compose.yml`,
`db/migraciones/`, `src/multiagente/rag/` y `src/multiagente/persistencia/`.

## Factores de decisión

- Decisión 8 de `CLAUDE.md`: BGE-M3 local en `vector(1024)`.
- Decisión 9: una sola base con filtro obligatorio por colección.
- Decisión 1: el desarrollador no tiene RAG.
- Arquitectura, §3 y §8: segmentación diferenciada, fusión por rango recíproco y un servicio de
  embeddings aparte en la composición de contenedores.
- RF-37: la entrega debe operar sin depender de la nube.
- Equipo de desarrollo: 16 núcleos y 15 GB de RAM en WSL. Hay una GPU, pero el sistema debe
  funcionar en CPU.

## Opciones consideradas

- A. Servidor Text Embeddings Inference (TEI) en CPU, con BGE-M3 en ONNX.
- B. TEI con GPU.
- C. Imagen propia con sentence-transformers y PyTorch.

## Resultado de la decisión

Opción elegida: «A», por decisión del equipo. Es el servicio aparte que pide la vista de
despliegue, corre en cualquier equipo de Realtix con o sin GPU y evita mantener una imagen
propia con PyTorch.

1. **Servicio `embeddings`.**
   - Imagen `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9.4`, en `127.0.0.1:8081`,
     con backend ONNX Runtime.
   - Modelo `BAAI/bge-m3`, licencia MIT, revisión fijada
     `5617a9f61b028005a4858fdac845db406aefb181`.
   - TEI carga el modelo desde el volumen `modelos_embeddings`, con `HF_HUB_OFFLINE=1`: ningún
     texto del corpus ni de las consultas sale del equipo.
2. **Descarga con curl, no con TEI.**
   - El descargador interno de TEI 1.9.4 falló con el archivo de 2,27 GB
     (`onnx/model.onnx_data`): cortaba la transferencia hacia los 60 s con «error sending
     request», aunque curl alcanzaba el mismo archivo sin problema.
   - Por eso el servicio de una sola ejecución `descarga-modelo` (`curlimages/curl:8.22.0`)
     descarga los 11 archivos necesarios (2,29 GB, sin los pesos PyTorch) con reanudación.
   - Verifica cada uno contra `docker/embeddings/bge-m3.sha256`: los archivos LFS con la suma
     oficial de Hugging Face y los demás con la calculada de la revisión fijada.
   - La primera descarga tardó 252 s; las siguientes solo verifican y terminan en segundos.
3. **Esquema y migraciones.**
   - `db/migraciones/0001_bases_conocimiento.sql` crea `kb_documentos` y `kb_fragmentos`, con
     `embedding vector(1024)` e índice HNSW coseno, `lexico tsvector` generado con la
     configuración `spanish` e índice GIN, y un índice por colección.
   - Una clave foránea compuesta (documento, colección) impide que un fragmento quede en otra
     colección.
   - `aplicar_migraciones()` aplica los archivos en orden dentro de la transacción del
     llamador, los registra con su SHA-256 en `migraciones_esquema` y rechaza una migración
     aplicada que haya cambiado.
4. **Segmentación según los metadatos de cada documento.**
   - `por_seccion`: un fragmento por `##`, partido por párrafos con 400 caracteres de
     solapamiento si supera 4000 caracteres (~1024 tokens).
   - `por_unidad_conceptual`: el documento completo si no tiene secciones (cada arquitectura
     ARQ-0x es un fragmento) o una sección por unidad (cada patrón).
   - `una_regla_por_fragmento`: cada `### REGLA` con su id, severidad, característica y norma
     en los metadatos, o cada `##` en los documentos sin reglas formales.
   - Los títulos dentro de bloques de código no parten el documento.
   - Resultado: **184 fragmentos** (elicitación 62, dominio 40, arquitecturas 33 y criterios
     49, de ellos 31 reglas).
5. **Metadatos validados.**
   - La cabecera YAML se lee con `BaseLoader`, para que `version: 1.10` no se convierta en
     1.1, y se valida con Pydantic.
   - La colección debe coincidir con la carpeta y el agente consumidor debe estar autorizado
     para ella.
6. **Ingesta idempotente.** Solo reindexa los documentos cuya huella SHA-256 o modelo de
   embeddings cambió, y borra los que ya no existen.
   - Primera ingesta: 33 s. Segunda: 0 s.
7. **Aislamiento (RF-29).**
   - `ACCESO` asigna `elicitacion` y `dominio_negocio` al elicitador,
     `arquitecturas_referencia` al arquitecto, `criterios_calidad` al tester y ninguna al
     desarrollador.
   - Un `Recuperador` existe solo para un agente con colecciones: para el desarrollador lanza
     `ErrorAccesoNoAutorizado`, y pedir una colección ajena también.
   - Las tres consultas SQL llevan el filtro `coleccion = ANY(autorizadas)`; no existe camino
     de recuperación sin él.
8. **Recuperación híbrida (RF-31).**
   - Búsqueda semántica por distancia coseno y búsqueda léxica con
     `websearch_to_tsquery('spanish')` y `ts_rank_cd`, 20 candidatos cada una.
   - Fusión por rango recíproco con k = 60. A igual puntaje gana la coincidencia léxica, que
     pone los términos exactos (`CAL-MT-005`, `ARQ-04`) en primer lugar.
   - Latencia medida: unos 40 ms por consulta en CPU.
9. **Relevancia (RF-32).**
   - Un fragmento se conserva si su similitud alcanza `RAG_UMBRAL_SIMILITUD` o si coincide
     léxicamente. Los demás quedan en `descartados` con su motivo; si no queda ninguno, el
     resultado declara ausencia de contexto.
   - Umbral calibrado: **0,37** (similitud máxima por consulta):

     | Consultas | Mínimo | Máximo | Observación |
     |---|---|---|---|
     | Del dominio (10) | 0,418 | 0,773 | 9 de 10 superan 0,5 |
     | Ajenas al dominio (7) | 0,278 | 0,415 | 6 de 7 no superan 0,352 |

   - Con «procesar lotes de predios cada noche», ARQ-03 aparece con 0,389. El umbral queda
     entre ese caso legítimo y el máximo habitual de las consultas ajenas (0,352).
   - Una consulta ajena atípica («horario de la biblioteca municipal», 0,415) supera cualquier
     umbral que no descarte también consultas legítimas. Se acepta ese falso positivo.

### Consecuencias

- Favorable, porque la condición de terminado se verifica con el modelo real: con consultas
  pensadas para atraer fragmentos ajenos, cada agente solo recibe fragmentos de sus
  colecciones.
- Favorable, porque el modelo queda en local y verificado, sin depender de Hugging Face en
  operación (RF-37).
- Desfavorable, porque la descarga inicial ocupa 2,29 GB y el servicio usa ~2,5 GB de RAM.
- Desfavorable, porque las consultas cortas y coloquiales recuperan peor que las descriptivas.
  Con «lotes cada noche», ARQ-03 queda 5.º (0,389); con una consulta descriptiva queda 1.º
  (0,551).
- **Recomendaciones para los pasos 7, 8 y 10:**
  - construir las consultas a partir de los artefactos completos y no de frases sueltas;
  - como el catálogo cerrado tiene solo seis arquitecturas, N7 puede recuperarlas todas
    ordenadas, lo que asegura las dos alternativas que exige el RF-09;
  - recalibrar el umbral con las consultas reales de cada agente.

### Confirmación

- `pytest tests/unitarias/test_rag_corpus.py tests/unitarias/test_rag_recuperacion.py`:
  corpus, metadatos, segmentación, acceso y fusión.
- `pytest -m integracion tests/integracion/test_rag_postgres.py`: migraciones, ingesta
  idempotente, reindexación, clave foránea compuesta, aislamiento y términos exactos, en un
  esquema temporal con un vectorizador de prueba.
- `pytest -m embeddings`: con BGE-M3 real verifica la dimensión y la normalización, el
  aislamiento con consultas ajenas para los tres agentes, el rechazo del desarrollador, la
  calidad semántica (avalúo → `dom-003`, servicio HTTP → ARQ-04, float → `CAL-FS-005`) y la
  ausencia de contexto ante una consulta fuera del dominio.

## Análisis de las opciones

### Opción A · TEI en CPU
- Favorable, porque es portable, ligero (imagen de 938 MB) y está mantenido por Hugging Face.
- Desfavorable, porque su descargador obligó a predescargar el modelo con curl.

### Opción B · TEI con GPU
- Favorable, porque es más rápido.
- Desfavorable, porque depende de NVIDIA y de la integración de GPU de Docker Desktop.

### Opción C · Imagen propia con sentence-transformers
- Favorable, porque da control total.
- Desfavorable, porque suma PyTorch (~1 GB) y una imagen propia que mantener.

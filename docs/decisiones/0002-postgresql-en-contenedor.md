---
estado: aceptada
fecha: 2026-09-24
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0002 · PostgreSQL 16 con pgvector en contenedor

> El ADR-0017 (paso 14) fija la imagen también por digest y agrega a la composición la
> aplicación, la ingesta y la comprobación del entorno aislado.

## Contexto y planteamiento del problema

El paso 2 del plan exige que PostgreSQL acepte conexiones y que la extensión pgvector esté
activa. Hay que definir cómo se provee la base de datos en desarrollo, cómo se activa la
extensión y cómo se comprueba. La decisión afecta a `docker-compose.yml`, a `db/init/`, a la
configuración de conexión del sistema y a la organización de las pruebas.

## Factores de decisión

- RNF-07: PostgreSQL 16 o superior, desplegable en contenedores.
- RF-37: entrega empaquetada en contenedores con un archivo de composición único.
- Decisión 9 de `CLAUDE.md`: una sola base PostgreSQL con filtro obligatorio por colección.
- Decisión 8 de `CLAUDE.md`: embeddings BGE-M3 en columna `vector(1024)`.
- RNF-04: la información de dominio no debe quedar expuesta fuera de la máquina.

## Opciones consideradas

- A. Imagen oficial de pgvector (`pgvector/pgvector:0.8.6-pg16`).
- B. Imagen `postgres:16` con pgvector compilado en un Dockerfile propio.
- C. Imagen de pgvector sobre PostgreSQL 17.

## Resultado de la decisión

Opción elegida: «A», porque entrega PostgreSQL 16 con pgvector ya compilado y mantenido por
los autores de la extensión, sin un Dockerfile que mantener.

Decisiones asociadas:

1. **Versión fijada.** `pgvector/pgvector:0.8.6-pg16`, la última publicada para pg16 al
   2026-09-24 (PostgreSQL 16.15). Cambiar de versión es una edición explícita del compose.
2. **Extensión por script de inicio.** `db/init/01-extensiones.sql` ejecuta
   `CREATE EXTENSION IF NOT EXISTS vector` al inicializar el volumen. Las tablas, incluida la
   de fragmentos con `vector(1024)`, se crean en los pasos que las usan.
3. **Solo local.** El puerto se publica en `127.0.0.1`, no en todas las interfaces.
4. **Datos persistentes.** Volumen con nombre `datos_postgres`; sobrevive a
   `docker compose down` y solo se borra con `docker compose down -v`.
5. **Compose incremental.** El archivo arranca con el servicio `db`. Embeddings, inferencia
   local, sandbox, observabilidad y aplicación se agregan en sus pasos.
6. **Credenciales en `.env`.** El compose exige `POSTGRES_DB`, `POSTGRES_USER` y
   `POSTGRES_PASSWORD` y falla con un mensaje claro si faltan. El sistema las lee con
   `ConfiguracionBaseDatos` (`src/multiagente/core/configuracion.py`), que guarda la
   contraseña como `SecretStr`.
7. **Pruebas de integración separadas.** El marcador `integracion` las excluye de `pytest`
   por defecto, porque requieren los contenedores. Se ejecutan con `pytest -m integracion`.

### Consecuencias

- Favorable, porque un solo comando (`docker compose up -d --wait`) deja la base lista y
  verificada por su `healthcheck`.
- Favorable, porque la cadena de conexión se arma en un solo lugar, reutilizable por el
  checkpointer de LangGraph en el paso 5.
- Desfavorable, porque el script de inicio no se vuelve a ejecutar sobre un volumen existente:
  una extensión nueva exigirá una migración o recrear el volumen.
- Desfavorable, porque se depende del calendario de publicación de la imagen de pgvector para
  recibir parches de PostgreSQL.

### Confirmación

- `docker compose up -d --wait` deja el contenedor `db` en estado healthy.
- `pytest -m integracion` verifica que el servidor es PostgreSQL 16, que la extensión
  `vector` está instalada y que la distancia entre `[1,2,3]` y `[1,2,4]` es 1.
- Tras `docker compose down` y un nuevo `up`, las mismas pruebas pasan sin reinicializar.

## Análisis de las opciones

### Opción A · pgvector/pgvector:0.8.6-pg16
- Favorable, porque la mantienen los autores de pgvector y se publica para cada versión.
- Desfavorable, porque añade una dependencia de un tercero además de la imagen oficial.

### Opción B · postgres:16 con Dockerfile propio
- Favorable, porque parte de la imagen oficial de PostgreSQL.
- Desfavorable, porque obliga a compilar la extensión y a mantener ese Dockerfile.

### Opción C · PostgreSQL 17
- Favorable, porque es una versión más reciente, también compatible con RNF-07.
- Desfavorable, porque `CLAUDE.md` fija PostgreSQL 16 como parte del stack aprobado.

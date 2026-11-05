---
estado: aceptada
fecha: 2026-11-04
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0001 (imagen con versiones exactas), ADR-0002 (composición completa), ADR-0003 (sin modelos de lenguaje locales), ADR-0007 (los embeddings siguen locales sin el factor del RF-37), ADR-0011 (acceso de la aplicación a Docker), ADR-0014 (acceso a la web) y ADR-0016 (factor del paso 14)
---

# ADR-0017 · Entrega en contenedores con Azure OpenAI

## Contexto y planteamiento del problema

El paso 14 del plan se llamaba «Empaquetado y modo local» y terminaba cuando «el sistema corre
completo sin credenciales de nube». Lo pedían textos aprobados:
- **RF-37:** entregar el sistema en contenedores, «capaz de operar de extremo a extremo sin
  dependencia de ningún proveedor de nube, utilizando modelos de lenguaje y de embeddings
  ejecutables localmente». Su criterio lo verificaba «en una máquina sin credenciales de nube».
- **RNF-06:** la capa de modelos debía permitir «operar íntegramente con modelos locales».
- **Vista de despliegue de la arquitectura:** un «servicio de inferencia local» con modelos
  open-weights y dos «modos de operación», remoto y local.
- **Restricciones de los requerimientos (§7):** operar «sin conexión a proveedores de nube».

El código nunca usó modelos de lenguaje locales. Desde el paso 3, los cinco nodos con modelo y el
cliente simulado llaman a los despliegues de Azure OpenAI. Al planear el paso 14, el equipo
decidió no usar modelos locales en la entrega.

Además, dos decisiones quedaron para este paso:
- **ADR-0011:** cómo accede a Docker la aplicación cuando corre en contenedor, para crear el
  entorno aislado.
- **ADR-0014:** el acceso remoto a la web y su autenticación.

Antes de este paso:
- la composición levantaba la base de datos, la descarga del modelo de embeddings y el servicio
  `embeddings`;
- la aplicación corría en el `.venv` del anfitrión;
- la imagen del entorno aislado se construía aparte y el corpus se ingería con un script.

## Factores de decisión

- La decisión del equipo sobre los modelos de lenguaje.
- RF-37 y RNF-07: entrega en contenedores, desplegable en Linux, Windows y macOS.
- RNF-03: el código generado se ejecuta aislado, sin red ni acceso al anfitrión.
- RNF-04: los embeddings se generan localmente y no se transmiten a terceros.
- El acuerdo de confidencialidad con Realtix: el corpus y los secretos no salen de la máquina.
- Decisión 7 de `CLAUDE.md`: los identificadores de modelo viven en la configuración.

## Opciones consideradas

Para el acceso a Docker desde la aplicación:
1. Montar el socket de Docker del anfitrión en el contenedor de la aplicación.
2. Docker dentro de Docker, en un contenedor privilegiado.
3. Dejar la aplicación fuera de los contenedores.

Para la web:
1. Solo en la máquina donde corre y sin autenticación, como hasta ahora.
2. Acceso remoto con TLS y autenticación.

## Resultado de la decisión

### Decisiones del equipo (2026-11-04)

1. **Azure OpenAI es el único proveedor de modelos de lenguaje.**
   - Ningún nodo usa modelos locales ni de pesos abiertos, y la composición no incluye un servidor
     de inferencia.
   - Los modelos son los despliegues del recurso de Azure OpenAI:
     - `gpt-5.4-mini` en N3 y N5;
     - `gpt-5` en N8;
     - `gpt-6.1-sol` en N10;
     - `gpt-6-luna` en N14.
2. **BGE-M3 sigue local.**
   - No es un modelo de lenguaje: convierte el corpus y las consultas en vectores para la
     recuperación de N2, N7 y N13.
   - Lo exige el RNF-04.
   - Llevarlo a Azure obligaría a reindexar el corpus, recalibrar el umbral de relevancia y
     reformular el RNF-04.
3. **Documentos corregidos.**
   - **Requerimientos 1.3:** el RF-37 y su criterio, el RNF-06 y la restricción de operar sin
     conexión a proveedores de nube.
   - **Arquitectura 1.5:**
     - §3.2: la justificación de los embeddings locales;
     - §5: los identificadores de modelo;
     - §8: la vista de despliegue, sin el servicio de inferencia local ni los modos de operación;
     - §9: los datos que procesa Azure, la web y el acceso a Docker;
     - Tablas 6 y 7;
     - §12: el criterio de aprobación.
   - **Plan de trabajo:** el paso 14 pasa a «Empaquetado en contenedores». Termina cuando, desde un
     clon limpio, la composición levanta el sistema completo y un módulo sale validado con los
     modelos de Azure OpenAI.
   - **`CLAUDE.md`:** el stack, la decisión 12 y el paso actual.
   - **`.env.example`:** sale `OLLAMA_BASE_URL`, que nada usaba.
4. **Acceso a Docker por el socket del anfitrión** (opción 1). Cierra lo que el ADR-0011 dejó para
   este paso.
   - La aplicación crea el entorno aislado con la CLI de Docker, que habla con el Docker del
     anfitrión por su socket.
   - El entorno aislado no cambia: es un contenedor hermano, efímero, sin red, de solo lectura y
     sin root, que recibe el código por la entrada estándar.
   - **Riesgo:** quien controle el contenedor de la aplicación controla el Docker del anfitrión.
     Lo acotan dos cosas: el código generado nunca corre en la aplicación, solo en el entorno
     aislado, y la web solo responde en la máquina.
   - **Opciones descartadas:**
     - Docker dentro de Docker exige un contenedor privilegiado, con más alcance sobre el
       anfitrión;
     - dejar la aplicación fuera de los contenedores no cumple el RF-37.
5. **La web, solo en la máquina donde corre y sin autenticación** (opción 1). Cierra lo que el
   ADR-0014 dejó para este paso.
   - En la composición, la web escucha en todas las interfaces del contenedor, pero se publica
     solo en `127.0.0.1` del anfitrión.
   - El acceso remoto exigiría TLS, autenticación del equipo y un enlace por sesión para el
     cliente. Queda como trabajo futuro.

### Decisiones de implementación

6. **Imagen de la aplicación** (`docker/aplicacion/Dockerfile`).
   - **Base:** Python 3.14.4 slim, la versión con que corren las pruebas, con etiqueta y digest
     fijados.
   - **Instalación editable:** la imagen copia el repositorio, porque las rutas a los prompts, la
     configuración, el corpus, las migraciones, la imagen del entorno aislado y los casos se
     calculan desde la raíz.
   - **Versiones exactas:**
     - las dependencias van en su propia capa, con `versiones.txt` como restricciones, y la
       construcción corre `pip check`;
     - el archivo es el `pip freeze` del `.venv` donde pasan las pruebas, y lo regenera
       `scripts/congelar_aplicacion.py`.
   - **CLI de Docker 29.8.0:** se copia de la imagen oficial, para crear el entorno aislado.
   - **`.dockerignore`:** deja fuera `.env`, `.venv/`, `.git/`, `data/`, `docs/anexos/` y
     `evaluacion/resultados/`.
7. **Usuario sin root, elegido al arrancar** (`docker/aplicacion/entrada.sh`).
   - **Cómo:** el contenedor arranca como root solo para elegir el usuario: el dueño de
     `data/local`, con el grupo del socket de Docker. Después le cede el proceso con `setpriv`.
   - **Para qué:** los archivos de `data/local` quedan a nombre de la persona y la aplicación crea
     el entorno aislado sin root.
   - **Sin configuración:** los identificadores cambian de una máquina a otra y se leen al
     arrancar. En esta, el socket es del grupo 1001.
   - **Si `data/local` es de root,** el comando corre como root.
8. **Composición** (`docker-compose.yml`).
   - **`aplicacion`:**
     - sirve la web con `env_file: .env` y, encima, las direcciones internas: `db`, `embeddings`
       y `0.0.0.0`, en el puerto 8000;
     - monta `./data/local` y el socket de Docker;
     - su comprobación de salud pide el panel.
   - **`ingesta`:** con la misma imagen, migra la base e ingiere el corpus antes de que arranque la
     aplicación. Es idempotente: sin cambios, tarda menos de un segundo.
   - **`sandbox`:** sale de su perfil. La composición construye su imagen con las demás y la
     ejecuta una vez, sin red y de solo lectura, antes de la aplicación.
     - Su contenedor queda detenido con el nombre `multiagente-sandbox-1`.
     - Los contenedores efímeros del entorno aislado llevan, en cambio, un sufijo hexadecimal de 12
       caracteres. La prueba que verifica que se borran filtra por ese formato.
   - **Imágenes descargadas** (`db`, `descarga-modelo` y `embeddings`): quedan fijadas por versión
     y digest.
   - **`data/local/.gitkeep`:** hace que la carpeta exista en un clon limpio, con el dueño de quien
     clona.
9. **Uso.**
   - **Entrega:** `docker compose up -d --build --wait` levanta todo, y la web queda en
     `http://127.0.0.1:8000/`.
   - **Consola:** `docker compose run --rm aplicacion multiagente …` corre en otro contenedor de la
     misma imagen, que pasa por el punto de entrada. Antes de arrancar comprueba otra vez el
     modelo, el corpus y el entorno aislado, en unos 10 s; `--no-deps` lo omite.
   - **Desarrollo:** `docker compose up -d --wait db embeddings` levanta solo la infraestructura
     para el `.venv`.
10. **Prueba sin Docker** (`tests/unitarias/test_empaquetado.py`). Comprueba:
    - que los puertos se publiquen solo en `127.0.0.1`;
    - las direcciones internas y las dependencias de arranque;
    - que el socket llegue solo a la aplicación;
    - la imagen del entorno aislado y `.dockerignore`;
    - la versión y el digest de cada imagen, la versión de Python y las versiones congeladas.

### Límites

- **`docker compose exec` entra como root.** Lo que escriba en `data/local` queda a nombre de root;
  por eso la consola se usa con `run`.
- **El código va dentro de la imagen.** Un cambio exige reconstruirla con `--build`.
- **La primera construcción depende de PyPI.** Sin caché, descarga las dependencias de las dos
  imágenes. Con una red lenta puede tardar más de media hora o fallar; en ese caso basta repetirla.
- **macOS no se verificó** (RNF-07). Se verificó en Windows, con Docker Desktop y WSL2.
- **Dos procesos sobre la misma sesión,** como en el ADR-0014: la web y la consola no se
  coordinan.

### Consecuencias

- **Favorable:** el código de los nodos no cambia. La capa agnóstica ya permitía cambiar de modelo
  editando la configuración, y lo sigue permitiendo.
- **Favorable:** la vista de despliegue se simplifica: sin servidor de inferencia, sin GPU y sin
  descargar modelos de lenguaje.
- **Desfavorable:** el sistema no opera sin conexión con Azure OpenAI. Depende de su cuota, su
  disponibilidad, el retiro de versiones y su costo; es el riesgo nuevo de la Tabla 7.
- **Desfavorable:** los prompts se procesan en Azure, con la conversación, los fragmentos
  recuperados y los artefactos. Con datos reales de Realtix se prefieren los despliegues de zona
  de datos de EE. UU. sobre los globales.
- **Desfavorable:** el contenedor de la aplicación tiene acceso al Docker del anfitrión.

### Confirmación

- `pytest tests/unitarias/test_empaquetado.py`: la composición, las imágenes y `.dockerignore`, sin
  Docker.
- Desde un clon limpio, con otro nombre de proyecto, `docker compose up -d --build --wait` y una
  sesión dentro del contenedor con `scripts/evaluar_extremo_a_extremo.py --solo CASO`. Es la
  condición de terminado del paso 14 y el criterio del RF-37.

## Verificación

- **Sin costo:** 754 pruebas unitarias, 34 de integración, 19 de embeddings y 33 del entorno
  aislado. La imagen del entorno aislado, reconstruida sin caché, coincide con las versiones y los
  cierres versionados.
- **En la composición de desarrollo:**
  - `docker compose up -d --build --wait` levanta los seis servicios; la ingesta sin cambios tarda
    0,2 s;
  - la web corre con el UID 1000 y los grupos 1000 y 1001, el del socket;
  - el entorno aislado, lanzado desde la aplicación, corre con el UID 10001 y sin red.
- **Desde un clon limpio** (proyecto `multiagente-limpio`, volúmenes nuevos), el 2026-11-04:
  - **Arranque:** la imagen de la aplicación se construyó sin caché. Después se descargó y
    verificó el modelo, se migró la base y se indexaron los 36 documentos del corpus en 42,7 s, en
    unos 5 min en total.
  - **Interfaces vacías:** la web respondió desde Ubuntu y desde Windows, y la consola en
    contenedor vio la base sin sesiones.
  - **Primera sesión,** con `scripts/producir_modulo.py --simulado … --aprobar` sobre el caso de
    mutaciones: quedó en pausa en N6, como está previsto. El elicitador dejó una pregunta abierta y
    ese guion no aprueba con defectos escalados. Costó 0,088 USD.
  - **Segunda sesión,** con el analista simulado de las corridas medidas
    (`scripts/evaluar_extremo_a_extremo.py --solo caso-ampliada-05`): salió validada en N17 en la
    v1, en 3,7 min y por 0,245 USD. El tester la aprobó sin hallazgos, y sus 46 pruebas pasaron en
    el entorno aislado.
  - **Interfaces con esa sesión:**
    - la web mostró la sesión y su traza, con los prompts y sus versiones, y exportó el módulo, de
      13 archivos;
    - la consola la listó, la exportó a `data/local/` a nombre del UID 1000 y mostró su traza: 51
      ejecuciones de nodos y 30 llamadas.
  - **Costo:** las dos sesiones costaron 0,40 USD con el cliente simulado, registrados en
    `docs/mediciones/paso-14-contenedores.jsonl`.
- **Resultado inesperado: la imagen del entorno aislado y PyPI.**
  - **El fallo:** en el clon, su construcción sin caché falló a los 998 s con `ERROR: Exception`
    de pip. Estaba descargando las ruedas grandes, pandas y numpy, de PyPI, que respondía a unos
    17 KB/s. La composición siguió con la imagen que ya existía.
  - **La repetición:** terminó en 1.958 s, sin errores. La traza completa del primer fallo no se
    conservó.
  - **Atribución:** se atribuye a la red. Si la construcción falla por la red, basta repetir el
    comando, que retoma desde la última capa construida.
- **Observaciones fuera del alcance del paso,** en el caso 05:
  - el arquitecto eligió ARQ-01 donde el caso espera ARQ-02; en la corrida final del ADR-0015 había
    elegido ARQ-02;
  - el diálogo llegó al límite de 18 turnos.

## Cambios para el documento de tesis

- **Requerimientos:** el RF-37 y su criterio, el RNF-06 y la restricción de operar sin conexión a
  proveedores de nube.
- **Stack:** Azure OpenAI es el único proveedor de modelos de lenguaje y BGE-M3 corre local.
- **Vista de despliegue:**
  - salen el servicio de inferencia local y los modos de operación;
  - la aplicación usa Azure OpenAI y el Docker del anfitrión;
  - la web responde solo en la máquina.
- **Tablas 6 y 7:** la fila de la composición y el riesgo de depender de un único proveedor.
- **Plan de trabajo:** el paso 14 es «Empaquetado en contenedores».
- **Arquitectura, §12:** el criterio de aprobación de la vista de despliegue.

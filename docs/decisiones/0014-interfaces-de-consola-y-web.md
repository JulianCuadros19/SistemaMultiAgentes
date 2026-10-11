---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (decisión humana en N17, fallas del modelo, escalamiento, ciclo nuevo y cierre), ADR-0008 (N3 ante una falla y respuesta al resumen), ADR-0010 (capacidades no cubiertas y prompt 1.2), ADR-0011 (secciones de USO.md, prompt 1.5 y reintento sobre el intento rechazado), ADR-0012 (juez sin respuesta y sugerencia de instalación) y ADR-0013 (producir_modulo.py sobre el bucle de la consola)
---

# ADR-0014 · Interfaces de consola y web sobre una capa de operación compartida

## Contexto y planteamiento del problema

El paso 12 exige que un analista opere el flujo completo sin tocar código. Hasta el paso 11 el
flujo solo se operaba con `scripts/producir_modulo.py`, un script de desarrollo:
- no listaba sesiones ni mostraba su estado;
- no permitía pruebas propias en N17;
- una falla de un nodo terminaba con una traza de Python.

Lo que piden los documentos aprobados y los pasos anteriores:
- **Requerimientos §6:** una interfaz conversacional para el cliente y una de operación para el
  equipo, ambas con el estado del flujo; los tres puntos de aprobación los decide el equipo.
- **Salida:** artefactos en formatos estándar (JSON validado y documento legible, `.py` y
  Markdown); trazabilidad por sesión (RF-33) y exportación del módulo (RF-35).
- **RF-38:** en N17 la persona puede ejecutar pruebas propias en el entorno aislado (pendiente
  desde el paso 10).
- **Paso 7:** acusar la confirmación del resumen antes de la síntesis, que tarda de 6 a 16 s.
- **Paso 11:** mostrar en N17 cuántas iteraciones quedan y poder reanudar tras una falla.

La primera versión de las interfaces se verificó con el equipo, y esa verificación destapó
problemas del flujo que no eran de las interfaces (sección «Correcciones tras la verificación
con el equipo»).

La decisión afecta a:
- `src/multiagente/interfaces/` (operación, documentos, consola y web);
- `src/multiagente/orquestador/` (estado, N3, N5, N6, N8 a N10, N15, N17 y la validación de
  cada versión);
- los agentes arquitecto, desarrollador, elicitador y tester, sus prompts y el catálogo
  tecnológico;
- `src/multiagente/llm/traza.py`, `src/multiagente/persistencia/`, `src/multiagente/sandbox/`,
  `docker/sandbox/` y `pyproject.toml`;
- `docs/arquitectura.md`, que pasa a la versión 1.2.

## Factores de decisión

- RF-27, RF-28, RF-33, RF-35, RF-37, RF-38, RNF-01, RNF-08 y RNF-09.
- Decisión 4 de `CLAUDE.md`: los agentes solo se comunican por el estado. Las interfaces tampoco
  tocan el grafo: pasan por una capa de operación.
- Confidencialidad: la interfaz no debe exponer datos de Realtix fuera de la máquina.
- Sin dependencias de nube en la operación (RF-37): nada de CDN.

## Opciones consideradas

- A. FastAPI con plantillas Jinja2, CSS y JavaScript propios.
- B. Streamlit.
- C. Gradio.

## Resultado de la decisión

Opción elegida: «A», por decisión del equipo:
- se prueba con `TestClient` y servicios simulados, sin costo;
- separa bien la vista del cliente y el panel del equipo;
- las tareas largas corren aparte y la página consulta su estado.

La B vuelve a ejecutar la página en cada interacción y bloquea con una tarea larga. La C es buena
para el chat, pero débil para el panel de operación.

### Decisiones del equipo

1. **Web con FastAPI y plantillas,** sin recursos externos.
2. **Entran la trazabilidad (RF-33) y la exportación (RF-35).**
3. **Las pruebas propias de N17 quedan con la decisión.** Si la persona rechaza, las que
   fallaron se proponen como observaciones, que puede editar.

### Decisiones de implementación

4. **Capa de operación** (`interfaces/operacion.py`). El `Operador` es lo único que usan las
   interfaces:
   - **Flujo:** iniciar, responder, decidir (con el destino del rechazo en N17), reanudar y
     cerrar.
   - **Consulta:** la vista de cada sesión, que incluye:
     - fase y pausa;
     - nodos pendientes y error de la última falla;
     - iteración;
     - si la pregunta pendiente es el resumen.
   - **Sesiones:** la lista, la validación de cada versión, la trazabilidad y la exportación.
   - **N17:** las pruebas propias.
   - **Nombres comunes:** `describir()` da el estado en lenguaje de negocio, incluidas las
     sesiones escaladas y cerradas, y `NOMBRES_DE_NODO` el nombre de cada nodo; los usan la
     consola y la web.
5. **Estado (modifica el ADR-0006).**
   - `PruebasPropias` guarda los archivos `tests/test_*.py` de la persona y su ejecución.
     `RespuestaHumana.pruebas_propias` la registra con la decisión, solo en N17; en otro punto,
     el grafo vuelve a pausar con un aviso.
   - El modelo va anidado en `Sesion`, así que la lista blanca del serializador no cambia.
   - N17 publica `iteracion` y `limite_iteraciones`.
6. **Pruebas propias.**
   - Corren con `EntornoAislado.probar` junto con la versión vigente, sin red.
   - Solo se informan las de la persona.
   - Una ruta que pise un archivo del módulo se rechaza.
   - La conversión del resultado se comparte con N11 (`pruebas_ejecutadas`).
7. **Documentos y exportación** (`interfaces/documentos.py`).
   - **Documentos en Markdown:** los requerimientos (Anexo A), la especificación (Anexo B) y la
     trazabilidad, que incluye el cierre si lo hubo.
   - **Paquete del módulo validado:**
     - `requerimientos.json` y `especificacion.json`, validados contra su esquema;
     - sus versiones en Markdown;
     - el registro de decisión, con las capacidades que el catálogo no cubre;
     - el código con `USO.md` y `requirements.txt` (decisión 22);
     - el reporte de validación y la trazabilidad;
     - `LEEME.md`, con los pasos para ponerlo en marcha.
8. **Traza por sesión** (`RegistroPorSesion`).
   - Un proceso atiende varias sesiones: cada llamada a un modelo toma su sesión de una variable
     de contexto, que el `Operador` fija al avanzar.
   - Se verificó que LangGraph la propaga al hilo de N7, que corre en paralelo con N16.
   - La traza va a `data/local/traza-llamadas.jsonl`, que no se versiona.
9. **Lista de sesiones.** Se lee del checkpointer: en PostgreSQL, el último punto de control de
   cada hilo; se omiten los hilos sin estado.
10. **Consola** (comando `multiagente`, con `nueva`, `continuar`, `cerrar`, `sesiones`, `ver`,
    `exportar` y `web`).
    - **Bucle:** recibe una función por cada papel: quién responde como cliente, quién decide y
      qué hacer con una sesión detenida.
    - **Acuse del resumen:** se acusa cualquier respuesta al resumen.
    - **Fallas:** se muestran sin traza; la sesión detenida se reanuda, se cierra o se deja así.
    - **N6 y N9:** aprobar, si no está bloqueado; rechazar; cerrar.
    - **Menú de N17:** aprobar, si no escaló; rechazar, que devuelve al desarrollador; `[d]iseño`,
      que devuelve al arquitecto; probar con un archivo propio; escribir el código en
      `data/local/sesiones/`; cerrar.
    - **Cierre:** pide el motivo y una confirmación, porque es definitivo.
    - `producir_modulo.py` usa el mismo bucle con el cliente simulado y conserva sus opciones;
      una sesión escalada queda en pausa en N17 para una persona.
11. **Web** (`interfaces/web/`).
    - **Panel de operación:** sesiones y sesión nueva.
    - **Página de sesión:** un formulario por pausa:
      - diálogo;
      - N6, con los defectos escalados;
      - N9, con los errores y las capacidades no cubiertas;
      - N17, con los casos, los hallazgos, el código, las pruebas propias pegadas o subidas, y
        los botones «Aprobar», «Devolver al desarrollador» y «Devolver al arquitecto»;
      - en cada pausa y en las sesiones detenidas, «Cerrar la sesión», con motivo y
        confirmación.
    - **Aprobación bloqueada:** el grafo pone el motivo en los datos de la pausa (`bloqueo`) y
      la página no ofrece «Aprobar».
    - **Vista del cliente:** solo el diálogo y un estado en su lenguaje, también para una sesión
      escalada o cerrada.
    - **Tareas largas:** un ejecutor en segundo plano admite una tarea por sesión, contra envíos
      dobles. La página consulta `estado.json` cada 2 s y muestra el nodo en curso. Si el proceso
      se reinicia, la sesión aparece detenida con «Reanudar».
    - **Seguridad:** las plantillas escapan todo, incluido el código generado. La web escucha
      solo en `127.0.0.1`, sin autenticación; el acceso remoto se decide en el paso 14.
12. **Dependencias** (cotas del ADR-0001): `fastapi>=0.143,<1`, `uvicorn>=0.54,<1`,
    `jinja2>=3.1,<4` y `python-multipart>=0.0.32,<0.1`. `ruff>=0.16,<0.17` pasa de `[dev]` a
    las dependencias del sistema, porque N12 lo invoca. El paquete instalable incluye las
    plantillas, los estáticos y el comando `multiagente`.

### Correcciones tras la verificación con el equipo

El equipo operó dos sesiones con agentes reales:
- **Consola, `9b488126` (AlertaPrecios).** Quedó validada, pero el rechazo en N17 («Arregla los
  hallazgos que encontraste») llegó al desarrollador sin los hallazgos del tester. El
  desarrollador corrigió a ciegas, rompió una prueba y el contador terminó en 3 de 3. Costó
  0,46 USD sin el cliente simulado.
- **Web, `e7d6f80b` (NotionSync).** El cliente pidió exportar a Excel y el catálogo tecnológico
  no tenía librería de Excel. El arquitecto ocultó el hueco con `pandas` «más un motor» que no
  estaba declarado. Las tres versiones fallaron por CAL-FS-002 (`ModuleNotFoundError`), la
  sesión escaló y la interfaz no ofrecía ninguna salida. Costó 0,47 USD.

El equipo preguntó además si el flujo podía quedar atascado por el sistema y si el módulo
entregado trae un documento para ejecutarlo.

**Revisión del flujo.** Un experimento en memoria confirmó una trampa de LangGraph: si un nodo
falla después de recibir la respuesta de una pausa, cada reanudación repite esa misma respuesta.
Si N3 fallaba tras la respuesta del cliente de forma determinística, por ejemplo por el filtro de
contenido, la sesión no avanzaba nunca. El mapa completo de fallas quedó así:

| Dónde | Falla | Antes | Ahora |
|---|---|---|---|
| N3, tras la respuesta del cliente | cualquiera | repetía la respuesta y se atascaba | vuelve a preguntar (decisión 13) |
| N5 | salida del modelo inválida, filtrada, rechazada o truncada | detenida; atascada si se repetía | defecto en N6, que lo corrige y escala (decisión 14) |
| N8 | igual | igual | error en N9, con su ciclo acotado (decisión 14) |
| N10 | igual | igual | iteración fallida, de N10 a N15 (decisión 14) |
| N14, el juez | igual | igual | casos sin juicio del modelo, con advertencia (decisión 14) |
| N2, N7, N11, N13 y la red | infraestructura | detenida y reanudable | además, se puede cerrar (decisión 16) |
| Web con la base reiniciada | conexión rota | fallaba hasta reiniciar la web | se reconecta (decisión 17) |
| N12 fuera de desarrollo | Ruff solo en `[dev]` | fallaría siempre | Ruff es dependencia del sistema (decisión 12) |
| N9 con errores persistentes | aprobación bloqueada | solo rechazar | rechazar o cerrar (decisión 16) |
| Ciclo de corrección agotado | — | terminaba sin opciones | pausa en N17 para devolver o cerrar (decisión 15) |

**Documento de uso.** El desarrollador ya escribía un `USO.md` en cada versión y la exportación
agregaba un `LEEME.md`. En las dos sesiones el `USO.md` fue útil, pero tenía tres huecos: no
tenía estructura fija, no había un archivo de dependencias con versiones y, en AlertaPrecios, no
decía qué comando ejecutar.

**Principio:** toda falla termina en un reintento que puede funcionar o en una decisión humana
con salida, nunca en repetir lo mismo.

**Decisiones del equipo:**
- agregar `openpyxl` al catálogo tecnológico y al entorno aislado;
- un rechazo en N17 abre un ciclo de corrección nuevo;
- una sesión escalada se detiene en N17 para reabrirla, con el desarrollador o con el arquitecto,
  o para cerrarla;
- el costo no es restricción para estas correcciones.

**Decisiones de implementación:**

13. **N3 vuelve a preguntar** (modifica el ADR-0008).
    - Si `dialogar` falla con una respuesta nueva del cliente, sea por el modelo o por la red,
      N3 no propaga la excepción.
    - Agrega la respuesta y un turno del elicitador: «No pude procesar su respuesta en este
      momento. ¿Puede repetirla o decirla de otra forma?». La respuesta queda como procesada y
      la sesión vuelve a pausar.
    - La causa queda en el registro y la llamada fallida, en la traza.
14. **Fallas persistentes del modelo como decisiones** (modifica el ADR-0006).
    - **Clasificación:** son fallas de salida `ErrorRespuestaModelo` (límite de salida, filtro de
      contenido, rechazo del modelo y salida inválida) y `ErrorValidacionSalida`. Las de
      transporte siguen deteniendo la sesión, porque reanudar las resuelve.
    - **N5:** deja `Requerimientos.fallo_sintesis`. N6 lo cuenta como defecto, lo corrige dos
      veces y después escala al analista. Sin requerimientos, la aprobación queda bloqueada.
    - **N8:** deja el error en `errores_validacion` y `Arquitectura.fallo_diseno`. N9 aplica su
      ciclo acotado y después pide la decisión humana; sin especificación, no valida.
    - **N10:** deja `Codigo.fallo_generacion` y una validación rechazada, con los problemas como
      retroalimentación y en el reporte. Una arista condicional va de N10 a N15 sin ejecutar
      N11 a N14; al agotar el ciclo, escala.
    - **N14** (modifica el ADR-0012): si el juez falla, los casos con pruebas que pasan quedan
      «sin juicio del modelo», con una advertencia en el reporte para revisarlos en N17. No
      bloquea.
15. **Escalamiento, destino del rechazo y ciclo nuevo** (modifica el ADR-0006).
    - **Escalamiento:** al agotar el ciclo, N15 marca `requiere_intervencion_humana` y va a N17.
      La pausa trae `escalado` y admite que no haya versión. La aprobación queda bloqueada y el
      motivo va en `bloqueo`.
    - **Destino:** un rechazo en N17 lleva `destino`, el desarrollador por defecto o el
      arquitecto. El arquitecto recibe las observaciones en `Arquitectura.observaciones_revisor`
      y el flujo pasa por N8 y N9. `VersionCodigo.especificacion` hace que N10 genere de cero si
      la especificación cambió.
    - **Ciclo nuevo:** N15 reinicia la iteración tras cada devolución desde N17, contada en
      `Control.retornos_humanos`. El límite del RF-27, 3 por ciclo, se mantiene.
    - **Retroalimentación con hallazgos:** un rechazo en N17 entrega al desarrollador las
      observaciones de la persona y luego cada hallazgo de la versión, incluidos los de severidad
      baja, con `Hallazgo.como_linea()`.
16. **Cierre de una sesión** (modifica el ADR-0006).
    - `Operador.cerrar(id, revisor, motivo)` vale en una pausa (diálogo, N6, N9 o N17) o en una
      sesión detenida.
    - Usa `update_state(..., as_node=N17)`, que lleva el grafo a su fin con la fase nueva
      `cerrada` y descarta la pausa o el nodo pendiente. Se verificó en memoria y en PostgreSQL.
    - `Sesion.cierre` registra quién cerró, desde dónde, cuándo y por qué; la trazabilidad lo
      muestra.
17. **Reconexión.** `abrir_operador` usa pools de `psycopg_pool` que verifican cada conexión
    antes de entregarla (`persistencia/conexiones.py`): uno para el checkpointer y otro para la
    base de conocimiento, con un adaptador que ofrece el `execute` que usa el recuperador. Si la
    base se reinicia, la web se reconecta sola.
18. **Capacidades no cubiertas** (modifica el ADR-0010).
    - La salida de N8 trae `capacidades_no_cubiertas`, fuera de la especificación del Anexo B.
      Se guardan en `Diseno` y en `Arquitectura`. N9 las muestra como aviso y la exportación las
      agrega al registro de decisión.
    - El prompt `arquitecto.parametrizacion` pasa a la versión 1.2: aplica las reglas 3 y 4 de
      arq-004, sin dependencias transitivas implícitas, y lo que el catálogo no cubre se
      registra en lugar de esconderse.
19. **`USO.md` con secciones fijas** (modifica el ADR-0011).
    - El prompt `desarrollador.generacion` pasa a la versión 1.2: el entorno tiene solo la
      biblioteca estándar y las dependencias declaradas, y `USO.md` lleva Requisitos,
      Instalación, Configuración, Ejecución (con el comando de terminal si hay punto de
      entrada), Pruebas, Interfaces y Supuestos.
    - La verificación de N10 exige esos encabezados y reintenta si faltan.
    - El tester, ante un `ModuleNotFoundError`, dice que el entorno no tiene esa librería y
      sugiere usar solo la biblioteca estándar y las dependencias declaradas (modifica el
      ADR-0012).
20. **`openpyxl` en el catálogo y en el entorno aislado.** arq-004 pasa a la versión 1.2 con la
    fila de hojas de cálculo Excel; la imagen fija `openpyxl==3.1.5`, publicada con más de dos
    semanas y compatible con Python 3.11. El corpus se reingirió: 36 documentos y 186
    fragmentos.
21. **El elicitador pregunta qué falta** (modifica el ADR-0008). Si la respuesta al resumen no
    lo confirma y no cambia el registro, pregunta «¿Qué falta o qué debo corregir del resumen?»
    en lugar de repetirlo.
22. **Entregable listo para usar (RF-35).** El paquete exportado agrega:
    - `codigo/requirements.txt`, generado por código: las dependencias que declara la
      especificación, con la versión del entorno aislado con que el tester las probó, y
      `pytest`;
    - en `LEEME.md`, la sección «Cómo ponerlo en marcha»: crear el entorno, instalar con
      `pip install -r`, configurar y ejecutar según `USO.md`, y correr las pruebas.

23. **El desarrollador no escribe `requirements.txt`** (modifica el ADR-0011). El prompt 1.2
    decía que el paquete incluiría ese archivo, y el modelo lo escribía en `archivos`. El prompt
    `desarrollador.generacion` pasa a la versión 1.3: el sistema lo genera al exportar, y
    `archivos` no lleva nada fuera de los módulos y las pruebas. La verificación sigue estricta:
    si el modelo lo vuelve a escribir, el reintento lo corrige.
24. **En el reintento, el desarrollador entrega la respuesta completa** (modifica el ADR-0011).
    El reintento no le muestra al modelo su respuesta anterior. En una generación, el modelo
    devolvió solo el archivo corregido, como en una corrección, y a la versión le faltaron los
    demás. El prompt pasa a la versión 1.4: en el reintento entrega todo, salvo en una
    corrección, donde siguen bastando los archivos que cambian. No bastó; la reemplaza la
    decisión 25.
25. **El reintento de N10 es una corrección del intento rechazado** (modifica el ADR-0011).
    - `invocar_validado` admite un armador del reintento; los demás nodos conservan el de
      siempre, con `problemas_intento_anterior`.
    - En N10, el reintento repite los mensajes de la generación y agrega `intento_rechazado`:
      los archivos del intento ya combinados y los problemas de la verificación.
    - El modelo devuelve solo lo que cambia, y el código lo combina sobre el intento, como en la
      corrección del RF-19. Un reintento parcial ya no deja la versión incompleta.
    - Si la salida no pudo combinarse, por rutas repetidas o fuera del esquema, el intento va
      sin archivos y el modelo entrega la respuesta completa.
    - El prompt pasa a la versión 1.5.

`docs/arquitectura.md` pasa a la versión 1.2 con el flujo resultante. El RF-27 sigue cumplido: el
caso se marca «requiere intervención humana» y el flujo se detiene de forma controlada en la
pausa de N17.

### Verificación

- **Pruebas:** 507 unitarias, 30 de integración, 19 de embeddings y 26 del entorno aislado.
  Cubren:
  - el flujo completo por consola y por web con servicios simulados: rechazos en los tres puntos
    de control, pruebas propias que fallan y luego pasan, reanudación tras una falla,
    trazabilidad y exportación;
  - el escape del contenido;
  - las pruebas propias reales en el entorno aislado, también con `openpyxl`;
  - la reconexión de los pools tras terminar sus conexiones en PostgreSQL;
  - el cierre en PostgreSQL, que otro proceso lee como sesión terminada.
- **Matriz de fallas** (`tests/unitarias/test_fallas_del_flujo.py`, sin costo). Servicios
  simulados que fallan en cada nodo, de forma transitoria y persistente. Ninguna sesión queda
  atascada:
  - N3 con respuesta: vuelve a preguntar y procesa la respuesta nueva;
  - N5: llega a N6 con la aprobación bloqueada;
  - N8: llega a N9;
  - N10: escala a N17 sin versión, y se devuelve al arquitecto;
  - N11 detenida: se reanuda o se cierra;
  - cierre desde el diálogo, N6, N9, N17 y una sesión detenida.
- **Consola y web en los estados nuevos:** N17 escalado sin «Aprobar», devolución al
  arquitecto, especificación con errores, cierre con y sin confirmación y subcomando `cerrar`.
- **Contra la base real, sin costo:**
  - `multiagente sesiones` y `ver`, y el servidor web con sus páginas, `estado.json` y la
    exportación de la sesión de persona real del paso 11;
  - la exportación de `9b488126` produce `requirements.txt` con `typer==0.27.2` y
    `pytest==9.1.1`;
  - con `multiagente web` arriba, se reinició el contenedor `db` (`docker compose restart db`).
    Sin reiniciar la web, el panel, la sesión, la trazabilidad, `estado.json` y la exportación
    respondieron 200; la primera página tardó 1,0 s, lo que toma reconectar;
  - con la base apagada, `multiagente web` no queda colgada: a los 30 s sale con el mensaje que
    pide levantar los servicios y el código 2.
- **Corrida previa con agentes reales por la web** (sesión `b1b3d746`).
  - El cliente simulado respondió por HTTP y las tareas corrieron en hilos.
  - **Resultado:** módulo validado en 5,5 min, por 0,33 USD sin el cliente simulado.
  - **Costo por nodo:** N10 0,147, N8 0,095, N5 0,053, N3 0,030 y N14 0,001 USD.
  - **Hallazgos:**
    - N5 falló sus dos intentos (la falla esporádica del ADR-0008): la sesión quedó detenida y se
      reanudó con «Reanudar», sin perder nada. Con la decisión 14, ahora llega a N6 como
      defecto;
    - todas las llamadas quedaron en la traza con su sesión;
    - el acuse apareció ante cada respuesta al resumen, incluidas tres correcciones, y su texto
      afirmaba que ya se redactaban los requerimientos. Se cambió por uno válido en ambos casos.
- **Extremo a extremo con agentes reales tras las correcciones** (2026-10-09, prompts 1.2): los
  tres casos salen validados en la versión 1, sin escalar ni reanudar y sin hallazgos de
  severidad alta ni media. La corrida tardó 14,7 min.

  | Caso | Arquitectura | Módulos · RF · casos | Hallazgos | Tiempo del sistema | Costo |
  |---|---|---|---|---|---|
  | elicitacion-01 | ARQ-01 | 3 · 2 · 6 | 1 baja | 4,4 min | 0,27 USD |
  | elicitacion-02 | ARQ-01 | 2 · 1 · 3 | ninguno | 3,2 min | 0,23 USD |
  | elicitacion-03 | ARQ-03 | 6 · 1 · 3 | 2 baja | 5,2 min | 0,32 USD |

  - Los turnos de diálogo no pasaron de 4,1 s. El cierre de la elicitación tomó 9,7 y 8,3 s, y
    27,9 s en elicitacion-01; la prueba no guarda la traza, así que no se sabe si fue un
    reintento de N5 o latencia.
  - En los tres casos, N10 escribió un `requirements.txt` que la especificación no prevé y la
    verificación lo rechazó en el primer intento. El reintento lo corrigió, pero duplicó el costo
    de N10 (decisión 23).
- **Prompt 1.3 del desarrollador** (2026-10-10, `pytest -m "nube and sandbox"
  tests/integracion/test_desarrollador_nube.py` dos veces, 0,78 USD). Las 6 generaciones
  terminan en una versión válida que importa sus módulos, y ninguna escribe `requirements.txt`.
  - 4 salen válidas al primer intento.
  - 1 la corrige el reintento: sangría rota, el pendiente del paso 11.
  - 1 necesita una segunda iteración. El primer intento no importó una excepción declarada, y el
    reintento devolvió solo el archivo corregido, como en una corrección, sin los demás. La
    generación fallida pasó de N10 a N15 sin detener la sesión (decisión 14), y la segunda
    iteración salió válida.
- **Prompt 1.4 del desarrollador** (2026-10-10, la misma prueba dos veces, 0,86 USD). Las 6
  generaciones terminan en una versión válida, y ninguna escribe `requirements.txt`.
  - 3 salen válidas al primer intento.
  - 2 las corrige el reintento, que esta vez entrega la respuesta completa.
  - 1 necesita una segunda iteración: el reintento volvió a salir incompleto, sin `USO.md` ni
    todas las pruebas de los escenarios. La instrucción del prompt no basta.
  - En las 12 generaciones con los prompts 1.3 y 1.4, 4 de los 5 primeros intentos rechazados
    lo fueron por una excepción declarada que el módulo no define ni importa. Tres son la misma:
    `ejecutar_lote`, de la liquidación por lotes, declara `TarifaFaltanteError`, que solo deja
    pasar desde `preparar_lote`, y el modelo no la importa.
- **Reintento sobre el intento rechazado** (2026-10-10, prompt 1.5).
  - **Pruebas unitarias con modelo falso:**
    - un reintento parcial se combina sobre el intento;
    - una salida que no se combina se reintenta completa;
    - el reintento de una corrección parte del intento, no de la versión previa.
  - **Dos corridas de la prueba del desarrollador** (0,55 USD): las 6 generaciones salen
    válidas al primer intento, así que no ejercitan el reintento.
  - **Reintento real forzado** (0,15 USD, sin cambios en el repositorio):
    - una versión válida de la liquidación por lotes, a la que se le quitó la importación de
      `TarifaFaltanteError`, reproduce el problema de las corridas;
    - el modelo devolvió solo `src/orquestacion/ejecucion.py`, con la importación, y
      `documentacion_uso` vacía;
    - la versión combinada pasó la verificación con sus 8 archivos, 7 de ellos intactos;
    - el reintento tardó 7,5 s y costó 0,034 USD, frente a 134 s y 0,117 USD de la generación.

**Verificación con el equipo.** _Pendiente: el equipo repite una sesión tipo NotionSync por la
web y una por consola que rechace en N17; si alguna escala, ejercita reabrir y cerrar, y exporta
el paquete para revisar `USO.md` y `requirements.txt`._

### Consecuencias

- **Favorable:** el equipo opera el flujo completo sin tocar código, por consola o por web, con
  las mismas reglas, porque ambas pasan por el `Operador`.
- **Favorable:** el RF-38 queda completo: la persona prueba la versión en el entorno aislado y su
  evidencia queda con la decisión (RF-33).
- **Favorable:** ninguna falla deja una sesión sin salida. Las del modelo se vuelven decisiones,
  las de infraestructura se reanudan y cualquier sesión abierta se puede cerrar con registro.
- **Favorable:** el desarrollador corrige con los hallazgos a la vista, y una persona puede
  mandar el problema al diseño cuando no es del código.
- **Favorable:** el módulo exportado se instala con las versiones con que se probó.
- **Desfavorable: cada devolución desde N17 reinicia la cuenta de iteraciones.** Una persona
  puede extender el trabajo sobre un módulo, y su costo, más allá de tres iteraciones. Cada
  ciclo sigue acotado y cada devolución queda registrada como decisión humana; el presupuesto
  que detiene la ejecución llega en el paso 13.
- **Desfavorable: cerrar es definitivo.** Una sesión cerrada no se reabre; para retomar el caso
  hay que abrir una nueva.
- **Desfavorable: las capacidades no cubiertas dependen de que el modelo las declare.** El
  código no verifica que el diseño cubra todo lo que pidió el cliente; la persona lo revisa en
  N9 con el aviso.
- **Desfavorable: la web no tiene autenticación.** Solo escucha en la máquina local; el acceso
  remoto exige decidir autenticación en el paso 14.
- **Desfavorable: las tareas viven en el proceso.** Si el servidor se reinicia, la tarea en curso
  se pierde y la sesión aparece detenida; se reanuda, pero repite el nodo que estaba corriendo.
  Tampoco se coordinan dos procesos que operen la misma sesión a la vez, como la consola y la
  web.
- **Desfavorable: la lista de sesiones lee los puntos de control.** Basta para decenas de
  sesiones; la tabla `sesiones` del modelo de datos queda para cuando haga falta.

### Confirmación

- `pytest`: las pruebas de operación, consola, web, documentos, estado y la matriz de fallas.
- `pytest -m "integracion or sandbox" tests/integracion/test_operacion_integracion.py` y
  `pytest -m integracion tests/integracion/test_reconexion.py`.
- `pytest -m "nube and embeddings and sandbox" tests/integracion/test_extremo_a_extremo_nube.py`:
  falla con el reporte si una sesión escala, en lugar de insistir.
- `multiagente web` y `multiagente nueva`: la condición de terminado, operada por el equipo.

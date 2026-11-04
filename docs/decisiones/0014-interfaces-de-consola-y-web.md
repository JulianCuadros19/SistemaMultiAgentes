---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (decisión humana en N17, fallas del modelo, escalamiento, ciclo nuevo, cierre y confirmación con lo que el cliente no sabe), ADR-0008 (N3 ante una falla, respuesta al resumen, retiro de lo rechazado, rol, lo que el cliente no sabe, prioridad y condiciones), ADR-0010 (capacidades no cubiertas y prompt 1.2), ADR-0011 (secciones de USO.md, en parte escritas por el sistema, prompt 1.6, reintento sobre el intento rechazado e imagen con versiones transitivas fijas), ADR-0012 (juez sin respuesta, sugerencia de instalación, detección de secretos y detalle de la falla) y ADR-0013 (producir_modulo.py sobre el bucle de la consola e historial de versiones)
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

### Corrección tras la segunda verificación con el equipo

El equipo operó por la web la sesión `9da543db` (NotionSync2), con la misma necesidad que
`e7d6f80b`.
- **Lo que se corrigió desde `e7d6f80b`:** N9 declaró `openpyxl` y no hubo `ModuleNotFoundError`.
- **Resultado:** el módulo quedó validado, pero en la **iteración 3 de 3**, a punto de escalar.
- **Causa:** dos de las tres versiones se rechazaron por **falsos positivos de CAL-SG-001**, de
  severidad alta.

| Versión | Qué se marcó | Quién lo marcó |
|---|---|---|
| v1 | `_MENSAJE_TOKEN`, el mensaje «Error: No se encontró un token de Notion válido…» que pidió el cliente, en dos módulos | el detector de N12 y Ruff S105: dos hallazgos por línea |
| v1 | `assert resultado.token_notion == "token-entorno"`, en una prueba | Ruff S105 |
| v2 | el mismo mensaje, renombrado a `_MENSAJE_CREDENCIALES` | el detector de N12 |
| v3 | el mensaje renombrado a `_MENSAJE_ERROR` | nadie: aprobada |

- **Lo demás de la v1:** el otro hallazgo alto fue un CAL-FS-001 legítimo del juez.
- **Prueba debilitada:** en la v2, el desarrollador cambió `"token-entorno"` por
  `configuracion.os.environ["NOTION_TOKEN"]` para esquivar la regla.
- **Costo:** la sesión costó 0,58 USD, 0,45 de ellos en N10. La tercera generación (0,092 USD,
  59 s) solo corrigió el falso positivo.

**Causa.** Los dos detectores miraban solo el nombre:
- El de N12 marcaba cualquier texto no vacío asignado a un nombre como `token` o `credencial`.
- Ruff S105, S106 y S107 hacían lo mismo con los nombres en inglés y duplicaban los hallazgos.
- Las pruebas, cuyos valores son datos inventados, se revisaban igual.

**Decisiones del equipo:**
- un solo detector propio para CAL-SG-001;
- las pruebas quedan fuera de la regla.

26. **Un solo detector de secretos con criterio de valor** (modifica el ADR-0012).
    - **Criterio, `es_valor_secreto`:** un literal con nombre de secreto no cuenta como secreto
      si:
      - está vacío;
      - tiene espacios, porque es texto en lenguaje natural, como un mensaje;
      - es un nombre de variable de entorno, como `"NOTION_TOKEN"`.
    - **Cobertura:** el detector de N12 cubre lo que cubrían S105, S106 y S107, con nombres en
      español e inglés: asignaciones, asignaciones anotadas, argumentos por nombre, valores por
      defecto y comparaciones de igualdad. Cada secreto da un solo hallazgo.
    - **Pruebas:** no se revisan los archivos de `tests/`.
    - **Ruff:** `config/estilo_generado/ruff.toml` ignora S105, S106 y S107. CAL-SG-001 entra
      explícitamente en `EVALUADAS`, porque antes entraba por la tabla de Ruff.
    - **Base de conocimiento:** la «Verificación» de CAL-SG-001 en cal-sg (versión 1.1) describe
      el criterio. El enunciado, la severidad y la evidencia no cambian. El corpus se reingirió:
      36 documentos y 186 fragmentos.
    - **Verificación, sin costo:**
      - 524 pruebas unitarias. Las 15 nuevas cubren:
        - cada forma de secreto, con un solo hallazgo;
        - el mensaje de NotionSync y los nombres de variables de entorno, que no se marcan;
        - los datos de prueba, que no se marcan en `tests/` y sí en un módulo;
        - Ruff, que ya no reporta S105, S106 ni S107.

        Fallan 13 de ellas con el código anterior.
      - El corpus de defectos con Docker real: D05 (`CONTRASENA_BD`) sigue rechazado con
        CAL-SG-001 y los controles salen sin hallazgos.
      - Las tres versiones reales de `9da543db`, analizadas de nuevo con N12, dan cero
        CAL-SG-001. La v1 habría fallado solo por el CAL-FS-001 del juez. La v2 habría salido
        aprobada, con solo hallazgos de severidad baja: el módulo se validaba en la iteración 2.

### Correcciones tras la corrida ampliada

La corrida ampliada de extremo a extremo (sección «Verificación») destapó dos defectos. El
primero, en el caso 19, sesión `5f5d2739`:
- **Qué pasó:** el desarrollador falló sus dos intentos en la primera iteración. La sesión siguió
  como prevé la decisión 14 y escaló en N17 tras rechazarse la v1 y la v2.
- **Defecto:** `ejecucion.validaciones`, que arma el historial de versiones (ADR-0013), tomaba como
  veredicto todo punto de control que va a N15. Desde la decisión 14, a N15 también va una
  generación fallida, que no deja versión nueva:
  - **en la primera iteración,** el historial traía una versión vacía. `multiagente ver`, la
    trazabilidad de la web y el script de la corrida fallaban con `AttributeError`;
  - **en una iteración posterior,** nada fallaba, pero el historial repetía la versión anterior
    con la validación de la falla.

27. **El historial solo lista versiones dictaminadas** (completa la decisión 14 y modifica el
    ADR-0013).
    - **Criterio:** `validaciones` omite los puntos de control con `Codigo.fallo_generacion`. Es el
      mismo dato con que `ruta_tras_generacion` envía a N15.
    - **Generaciones fallidas:** cuentan como iteración y sus llamadas quedan en la traza de
      costo. No son versiones, así que la trazabilidad no las lista.
    - **Verificación, sin costo:**
      - 545 pruebas unitarias. La matriz de fallas cubre la falla en la primera iteración, en una
        corrección y en todas; las tres pruebas fallan con el código anterior.
      - `multiagente ver 5f5d2739…` lista la v1 y la v2 de la sesión real.

El segundo, en el caso 18, sesión `b271c343`:
- **Qué pasó:** N3 anotó como resultados los datos que trae el aviso. El cliente lo corrigió seis
  veces sin decir cuáles eran los resultados, y el registro no cambió. N5 sintetizó con ese
  registro, falló la fidelidad en sus 12 llamadas y N6 recibió cero requerimientos.
- **Defecto:** el prompt de extracción pide devolver la lista vigente de un atributo corregido,
  que aquí quedaba vacía. El código trata una lista vacía como «sin cambios», para que nada se
  pierda por omisión del modelo (ADR-0008). Una corrección que solo niega no tenía cómo entrar.

28. **La extracción retira lo que el cliente rechaza** (modifica el ADR-0008).
    - **Campo nuevo, `retirar`:** la extracción (prompt 1.2) lista lo que la respuesta rechaza
      sin decir el reemplazo. Cada entrada lleva su lista (`reglas_negocio`, `datos_entrada`,
      `datos_salida` o `excepciones`) y su texto tal como figura en el registro. La lista importa:
      en el caso 18, los mismos nombres eran entradas y salidas.
    - **Regla en código** (`retirar_rechazados`): una entrada sale solo si figura en esa lista y
      la respuesta nueva la menciona, con al menos una raíz o, si es un nombre corto como «NIT»,
      con la palabra entera. La lista vacía sigue conservando lo previo, y en la respuesta que
      confirma el resumen las listas solo suman (decisión 8 del ADR-0008).
    - **Efecto:** si la lista queda vacía, el atributo vuelve a estar pendiente y N3 pregunta por
      él en lugar de «¿Qué falta…?». Si no, el resumen siguiente muestra el cambio.
    - **Verificación:**
      - 552 pruebas unitarias. Las 7 nuevas cubren:
        - el caso 18;
        - lo que no se retira: sin mención, fuera del registro o de otra lista;
        - la respuesta que confirma;
        - el nombre corto;
        - la pregunta siguiente, con el modelo falso.
      - El turno exacto del caso 18, tomado de los puntos de control de `b271c343`, con el modelo
        real, tres veces (0,02 USD). En las tres:
        - la extracción retira las tres salidas y conserva las entradas;
        - suma las reglas de las alertas y del acumulado;
        - N3 pregunta por los resultados.
      - El caso 18 hasta N6, tres veces, con `scripts/conversar_elicitador.py --simulado` y la
        traza fuera del repositorio (0,27 USD). Las tres llegan a N6 con requerimientos: una sin
        defectos y dos con defectos escalados al analista. En ninguna el cliente rechazó los
        resultados, así que no pasaron por el retiro (ver «Caso 18» en «Verificación»).
      - La prueba `nube` del paso 7, sobre el caso de mutación, pasa (0,04 USD).

### Convergencia de la elicitación

Tras la decisión 28, las tres corridas del caso 18 agotaron los 15 turnos, y la corrida ampliada
mostró que el problema es general. Medida en la primera pausa de N6, la línea base tiene 9 de 20
sesiones en el límite de turnos y 7 de 20 sin el resumen confirmado, contra la regla 6 de eli-006.
Los puntos de control muestran cuatro causas:
- **Rol y funcionalidad desde quien opera:**
  - en el caso 18, desde el primer turno, el rol era «la caja» y la funcionalidad «publicar un
    aviso», cuando el cliente pedía las reacciones al aviso;
  - en los casos 10, 11, 14 y 15 el rol también era un sistema;
  - el prompt de extracción definía el rol como «quien usará» la funcionalidad, y eli-001 dice
    «quién obtiene el valor».
- **«No lo sé» repetido:** un atributo que el cliente no sabía seguía pendiente y N3 lo volvía a
  preguntar hasta el límite. El caso 12 preguntó por el cargo en 15 de sus 16 preguntas, contra el
  RF-02: «no repite preguntas ya respondidas».
- **Prioridad sin lugar en el registro:** el cliente pedía registrarla y el resumen no la
  mostraba, así que se alternaba «¿Qué falta…?» con el resumen (casos 02, 13, 18 y 20).
- **Condiciones del cliente sin lugar:** «probar sin base de datos» o «el canal puede funcionar en
  memoria» quedaban como supuestos o como reglas, y el cliente rechazaba ambas cosas (casos 04,
  13, 18 y 20). Son justo las señales de arq-003 para el arquitecto.

Decisión del equipo (2026-10-31): atender las cuatro causas. La pérdida de entradas por listas
parciales queda para otro plan.

29. **El rol es quien obtiene el valor, y la funcionalidad, lo que se pide construir**
    (modifica el ADR-0008).
    - **Extracción (prompt 1.4):**
      - el rol es el cargo de una persona del negocio, como dice eli-001, nunca un sistema,
        equipo o proceso;
      - si el cliente dice que un sistema o una tarea programada usa lo que pide, eso va a las
        condiciones (decisión 31);
      - la funcionalidad es lo que el cliente pide construir, no lo que ya ocurre;
      - las entradas incluyen lo que llega de otro sistema o en un aviso. Si el cliente no sabe
        si un dato es obligatorio, se registra como obligatorio, con su supuesto;
      - las salidas son lo que la funcionalidad entrega o deja hecho, no lo que ya produce otro
        sistema.
    - **Pregunta (prompt 1.6):** para el rol, pregunta a quién le sirve el resultado; para los
      resultados, qué debe entregar o dejar hecho lo que se pide.
    - **Resumen:**
      - dice «A quién le sirve» en lugar de «Quién lo usa»;
      - muestra los datos con el nombre que quedó en el registro. El caso 08 se atascó porque
        mostraba `numero_predial` como «numero predial» y el cliente pedía los nombres exactos.
30. **Lo que el cliente no sabe se pregunta dos veces, no sin fin** (modifica el ADR-0008 y la
    invariante del registro del ADR-0006).
    - **Registro:** `no_sabe` anota el atributo que se preguntaba cada vez que el cliente dice no
      saberlo (`fidelidad.dice_no_saber`). A la segunda vez (`INTENTOS_SIN_RESPUESTA`) queda en
      `sin_respuesta`.
    - **Pendientes:**
      - `pendientes` sigue declarando todo lo que falta (RF-03);
      - `por_preguntar` excluye lo que quedó sin respuesta;
      - `por_preguntar` gobierna la pregunta de N3, el enrutamiento de N4 y el validador de
        `Dialogo`.
    - **Confirmación:** el cliente puede confirmar el resumen con atributos sin respuesta, que el
      resumen muestra como «sin respuesta del cliente». N5 los declara «Por confirmar» y N6 escala
      las preguntas abiertas al analista (decisión 10 del ADR-0008).
    - **Pregunta (prompt 1.6):** tras un «no lo sé», N3 reformula una vez con un ejemplo concreto.
    - **eli-006, versión 1.1:** recoge la regla en su regla 4 y en el criterio de suficiencia. El
      corpus se reingirió: 36 documentos y 186 fragmentos.
31. **La prioridad y las condiciones del cliente entran al registro** (modifica el ADR-0008).
    - **Prioridad:**
      - es opcional y solo entra si el cliente la dice, con la misma fidelidad que un escalar;
      - aparece en el resumen;
      - en N5 manda sobre la que proponga el modelo.
    - **Condiciones:**
      - son opcionales: quién consume lo que se pide y por qué medio, cómo se prueba, qué
        cambiará;
      - se fusionan y se retiran como las reglas;
      - aparecen en el resumen como «Condiciones ya definidas»;
      - lo que el cliente da por definido nunca es un supuesto.
    - **Síntesis (prompt 1.4):** las condiciones van en la regla de negocio del requerimiento al
      que aplican, como hace el RF-27 del Anexo A («El número máximo de iteraciones es
      configurable…»). Así llegan a N8.

**Verificación de las decisiones 29 a 31.**
- **Sin costo:** 565 pruebas unitarias, 30 de integración y 19 de embeddings. Las 13 nuevas
  cubren:
  - el registro y la anotación del «no lo sé»;
  - el cierre con lo que el cliente no supo;
  - el resumen;
  - la prioridad, también en N5;
  - las condiciones.
- **Dos mediciones con el modelo real:**
  - **Método:** las 20 elicitaciones de la corrida ampliada hasta N6, con
    `scripts/conversar_elicitador.py --simulado`, una por caso y de una a la vez, más dos
    corridas extra del caso 18.
  - **Trazas:** `docs/mediciones/paso-12-elicitacion.jsonl` (2,26 USD) y
    `paso-12-elicitacion-2.jsonl` (2,07 USD).
  - **Comparación:** contra la línea base, en la primera pausa de N6.

| Indicador | Línea base | Medición 1 | Medición 2 |
|---|---|---|---|
| Sesiones en el límite de 15 turnos | 9 de 20 | 9 de 20 | 3 de 20 |
| Resumen confirmado | 13 de 20 | 13 de 20 | 17 de 20 |
| Sistemas como rol | 4 | 0 | 0 |
| Sin requerimientos en N6 | 2 | 0 | 0 |
| Turnos en total | 249 | 241 | 211 |
| Costo del diálogo, con el cliente simulado (USD) | 2,10 | 2,01 | 1,85 |

- **Medición 1:** no mejoró la convergencia y destapó dos causas nuevas:
  - rechazar los sistemas como rol creaba un bucle cuando el cliente decía que lo usa un sistema
    (casos 11, 12 y 15);
  - el resumen alteraba los nombres de los datos (caso 08).

  Ambas se corrigieron antes de la medición 2 (decisión 29).
- **Medición 2, caso 18:**
  - confirma el resumen en las tres corridas, con rol de persona y requerimientos; en la corrida
    ampliada no llegaba a ninguno;
  - pero en dos plantea la funcionalidad como «publicar un aviso».
- **Medición 2, rol:** en los casos 10, 11 y 12 queda sin respuesta, porque el cliente solo conoce
  los sistemas que usan el módulo. Llega al analista como pregunta abierta.
- **Diagnóstico:** se guardó en local la salida de cada extracción. De 108 respuestas que no
  confirmaban un resumen, 7 no cambiaron el registro. Casi todas señalan lo que falta sin darlo
  («faltan los formatos de cada banco»), y la pregunta fija «¿Qué falta…?» no ayuda a dárselo.
- **Prueba `nube` del paso 7:** pasa con los prompts finales (10 turnos, 0,04 USD).
- **Límites:** es una corrida por caso, así que parte de la diferencia es variación del modelo.
  Del caso 16, en la medición 2, se perdió el texto del registro de la corrida; su sesión
  `58d0cec0` y su traza están completas.

**Pendientes.**
- El planteamiento de las necesidades de eventos: el caso 18 todavía sale como «publicar un aviso»
  en 2 de 3.
- Las listas parciales que borran lo capturado: en el caso 04, las reglas pasaron de 15 a 2 en un
  turno, y también pasa en los casos 08, 09, 13 y 15. Lo atiende la decisión 23 del ADR-0015.
- Una pregunta específica, en lugar de la fija «¿Qué falta…?», cuando el cliente señala lo que
  falta sin darlo. Lo atiende la decisión 23 del ADR-0015.

### Correcciones tras la verificación con el equipo por consola

El 3 de noviembre el equipo operó tres sesiones (sección «Verificación con el equipo»). Los
hallazgos de los agentes los atiende el ADR-0015. Además aparecieron cuatro defectos de las
interfaces:
- **Observaciones sugeridas sin detalle:** en las tres devoluciones con pruebas propias que
  fallaban, la observación sugerida decía solo «archivo:línea: AssertionError», así que la persona
  la escribió a mano.
- **Una sesión en curso se veía detenida:** mientras la consola corría N10, `multiagente sesiones`
  la mostraba «Detenida antes de N10: hay que reanudarla» y la web ofrecía reanudarla. Hacerlo
  desde otro proceso habría corrido N10 dos veces.
- **`USO.md` con instrucciones que fallan:**
  - fijaba `python3.11`, que no existe en Ubuntu 26.04;
  - decía que `requirements.txt` no se entrega, una nota del prompt que copiaron 29 de los 33
    documentos generados;
  - repetía `pip install pytest`;
  - citaba «D1», una etiqueta interna.
- **`requirements.txt` sin las dependencias transitivas:** fijaba solo pytest. pip instaló
  pluggy 1.7.0, y el tester había probado con 1.6.0.

32. **El detalle de una falla sale de las líneas que marca pytest** (modifica las decisiones 6 y
    11, y el ADR-0012).
    - `sandbox.ejecutor.detalle_de_falla` une las líneas que pytest marca con `E` y tres
      espacios, el mismo criterio que usa pytest. Sin ellas toma la última línea, como en una
      traza de importación.
    - La usan el tester, sin cambiar su límite de 300 caracteres, las observaciones sugeridas, la
      consola y la web. La web muestra además el reporte completo en un desplegable.
33. **El sistema escribe Requisitos, Instalación y Pruebas de `USO.md`** (modifica la decisión 19 y
    el ADR-0011).
    - El modelo redacta el título, el propósito, Configuración, Ejecución, Interfaces y Supuestos
      (prompt `desarrollador.generacion` 1.6), sin mencionar el entorno aislado ni las etiquetas
      D1…Dn.
    - `agentes/desarrollador/uso.py` compone las otras tres secciones, en el orden de RF-18:
      - la versión de Python con que se probó, 3.11, o superior;
      - las dependencias declaradas;
      - la instalación con `pip install -r requirements.txt`, también en Windows;
      - las pruebas.
    - Se compone al generar cada versión y otra vez al exportar, así que las versiones anteriores
      también salen corregidas.
    - Lo que el modelo escribió en sus secciones se conserva: la v3 de `61e1e121` todavía dice
      «Conforme a D1» en Supuestos.
34. **`requirements.txt` fija también las dependencias transitivas** (completa la decisión 22 y
    modifica el ADR-0011).
    - En `docker/sandbox/` quedan versionados:
      - el freeze de la imagen (`versiones.txt`, 33 paquetes);
      - el cierre de dependencias de cada librería del catálogo (`cierres.json`), que calcula
        `cierres.py` dentro de la imagen.
    - La imagen se construye con `versiones.txt` como restricciones y con `pip check`, así que se
      reconstruye igual. Si cambia `requisitos.txt`, `scripts/congelar_entorno_aislado.py` copia
      lo que quedó instalado.
    - El paquete lista las dependencias declaradas, sus transitivas y pytest con las suyas, todas
      con versión fija. También se corrige el extra: `psycopg[binary]` declarado quedaba sin
      versión.
    - **Límite:** las versiones valen para Linux con Python 3.11. En Windows, pip agrega sin
      fijar las dependencias exclusivas de esa plataforma.
35. **Una sesión en curso no se reanuda ni se cierra a la vez** (modifica la decisión 4).
    - Cada operación que avanza una sesión (`iniciar`, `responder`, `decidir`, `reanudar` y
      `cerrar`) toma antes un bloqueo consultivo de PostgreSQL por sesión, en una conexión
      dedicada (`persistencia/bloqueos.py`), y valida dentro de él.
    - Si el proceso muere, PostgreSQL suelta el bloqueo junto con la conexión, y la sesión vuelve
      a verse detenida.
    - Las vistas leen en `pg_locks` qué sesiones están ocupadas:
      - la sesión se ve «En curso: N10 · …»;
      - la consola avisa sin ofrecer nada;
      - la web la sondea sin ofrecer reanudar ni cerrar.
    - Actuar sobre ella lanza `SesionEnCurso`, que la web responde con 409.
    - Sin PostgreSQL, como en las pruebas, los bloqueos son del proceso.
    - **Límite:** si PostgreSQL se reinicia a mitad de una corrida, el bloqueo se pierde con su
      conexión, y otra corrida podría reanudar la sesión.

**Decisión del equipo sobre las reglas de conformidad.** Se mantienen dos reglas de
`core/conformidad.py`: la de las excepciones declaradas y la de `self` sin anotar. En la corrida
ampliada explicaban 4 de los 7 primeros intentos rechazados de N10. El ADR-0015 las ataca en el
prompt del desarrollador, sin relajarlas.

**Verificación de las decisiones 32 a 35.**
- **Sin costo:** 585 pruebas unitarias, 31 de integración, 27 del entorno aislado y 19 de
  embeddings. Las 20 nuevas cubren:
  - el detalle con el reporte real de pytest, en el entorno aislado;
  - el documento de uso compuesto, también al exportar una versión anterior;
  - la coherencia de los archivos de versiones, y que la imagen tenga las versionadas;
  - la sesión en curso por consola, por web y entre dos procesos con PostgreSQL, incluida la
    muerte del proceso que la tiene.
- **Reexportación de `61e1e121`:**
  - `requirements.txt` fija pytest y sus cuatro dependencias, con pluggy en 1.6.0;
  - `USO.md` ya no tiene `python3.11`, `pip install pytest` ni la nota interna.

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

**Corrida ampliada de extremo a extremo** (2026-10-31, `scripts/evaluar_extremo_a_extremo.py`).
- **Método:**
  - 20 casos sintéticos nuevos en `evaluacion/casos/ampliada/`, de 3 a 4 por arquitectura del
    catálogo. Cada uno declara en su cabecera la arquitectura que espera; el cliente simulado no
    la ve y N8 elige por su cuenta;
  - el cliente simulado y la política del analista del ADR-0013 en N6, N9 y N17. Las sesiones
    escaladas quedan en pausa en N17;
  - un caso a la vez, con un tope de 15 USD;
  - la traza, `docs/mediciones/paso-12-corrida-ampliada.jsonl`, guarda las 745 llamadas solo con
    sus métricas.
- **Gasto:** 6,51 USD, 0,62 de ellos del cliente simulado, en 1 h 46 min de reloj.

| Caso | Tema | Esperada | Elegida | Desenlace | Bloqueantes de la v1 | Min | USD |
|---|---|---|---|---|---|---|---|
| 01 | Comisiones de corretaje | ARQ-01 | ARQ-01 | validado en la v2 | CAL-FS-002 | 3,24 | 0,21 |
| 02 | Reajuste del canon | ARQ-01 | ARQ-01 | validado en la v1 | — | 2,81 | 0,18 |
| 03 | Mantenimientos preventivos | ARQ-01 | ARQ-01 | validado en la v1 | — | 2,53 | 0,16 |
| 04 | Contratos de arrendamiento | ARQ-02 | ARQ-02 | validado en la v1 | — | 3,84 | 0,26 |
| 05 | Cupo de crédito rotativo | ARQ-02 | ARQ-02 | validado en la v2 | CAL-FS-001 | 3,05 | 0,20 |
| 06 | Despacho por lotes | ARQ-02 | ARQ-02 | validado en la v1 | — | 3,11 | 0,21 |
| 07 | Conciliación del recaudo | ARQ-03 | ARQ-03 | validado en la v1 | — | 4,86 | 0,31 |
| 08 | Depuración de predios | ARQ-03 | ARQ-03 | validado en la v2 | CAL-FS-001 | 4,78 | 0,32 |
| 09 | Indicadores desde Excel | ARQ-03 | ARQ-03 | validado en la v2 | CAL-FS-001 | 4,37 | 0,30 |
| 10 | Tarifa predial por HTTP | ARQ-04 | ARQ-04 | validado en la v1 | — | 4,14 | 0,27 |
| 11 | Inmuebles en arriendo | ARQ-04 | ARQ-04 | validado en la v2 | CAL-FS-001, CAL-MT-003 | 6,12 | 0,40 |
| 12 | Dígito de verificación del NIT | ARQ-04 | ARQ-04 | validado en la v2 | CAL-FS-002 | 3,83 | 0,21 |
| 13 | Reservas de parqueadero | ARQ-04 | ARQ-04 | validado en la v2 | CAL-MT-002 | 8,15 | 0,49 |
| 14 | Escaneos de expedientes | ARQ-05 | ARQ-05 | validado en la v1 | — | 4,20 | 0,30 |
| 15 | Rotación de registros | ARQ-05 | ARQ-05 | validado en la v1 | — | 5,05 | 0,33 |
| 16 | Amortización de crédito | ARQ-05 | ARQ-05 | validado en la v1 | — | 4,06 | 0,28 |
| 17 | Trámites catastrales | ARQ-06 | ARQ-06 | validado en la v2 | CAL-SG-006 | 4,62 | 0,31 |
| 18 | Ventas de la caja | ARQ-06 | — | en pausa en N6 | — | 4,03 | 0,20 |
| 19 | Pagos de pensiones | ARQ-06 | ARQ-06 | escalado en N17 | CAL-FS-001, también en la v2 | 9,01 | 0,61 |
| 20 | Sensores del cuarto frío | ARQ-06 | ARQ-06 | validado en la v1 | — | 5,94 | 0,35 |

- **Arquitectura:** N8 eligió la esperada en los 19 casos que llegaron al diseño, y salen las
  seis. ARQ-06 se usa por primera vez, en tres casos.
- **Desenlaces:** 18 validados, 10 en la v1 y 8 en la v2; 1 escalado en N17 y 1 en pausa en N6.
  Ninguna sesión se detuvo y ninguna llamada dio error.
- **Tiempo del sistema:** media de 4,6 min y máximo de 9,0 min, en el caso escalado, frente a los
  20 min del RNF-01.
  - El turno de diálogo más largo midió 9,4 s, dentro de los 15 s del RNF-01.
  - El cierre de la elicitación, que incluye la síntesis, pasó de 30 s en 5 casos: 104 s en el
    caso 13, con cinco requerimientos, y 97 s en el 18. La consola lo acusa antes (decisión 10).
- **Costo:** 0,28 USD de media por módulo validado, de 0,16 a 0,49. Del costo del sistema, 5,89
  USD, N10 lleva el 46 %, N8 el 22 %, N3 el 18 %, N5 el 14 % y N14 el 1 %.
- **Analista simulado:** devolvió los requerimientos al diálogo en 10 casos. En 9 aprobó después
  con defectos de calidad sin corregir, como prevé su política.
- **Desarrollador:** 36 llamadas para 29 generaciones.
  - Se rechazaron 7 de los 29 primeros intentos, en 6 sesiones, y el reintento corrigió 6.
  - Los motivos se combinan: sangría rota en 4, `self` anotado con su clase en 3, respuesta
    incompleta en 2 y una excepción declarada sin importar en 1.
  - La verificación de firmas (`core/conformidad.py`) trata `self: Clase` como distinto de
    `self`. Queda para decisión del equipo, como la regla de las excepciones declaradas.
  - En el caso 19, además, la especificación declaró `callable` como tipo y N9 no lo objetó.
- **`httpx`:** el riesgo no se dio. Las pruebas de ARQ-04 llaman a la aplicación ASGI
  directamente, sin `TestClient`.
- **Caso 19, escalado:**
  - N10 falló sus dos intentos en la iteración 1.
  - El juez rechazó la v1 y la v2 con CAL-FS-001: las pruebas simulaban en diccionarios locales el
    estado que el escenario pide al módulo, como el recibo anulado o la factura restaurada.
  - Destapó el defecto de la decisión 27, que hizo fallar el script al medir. Su resultado se
    rehízo sin costo desde la sesión y la traza; el cálculo del tiempo reproduce los otros 19
    casos con ±0,3 s.
- **Caso 18, en pausa en N6:**
  - el elicitador anotó como resultados los datos que trae el aviso. El cliente lo corrigió seis
    veces, pero el registro no cambió: una extracción vacía conserva lo anterior, y el cliente
    dijo qué no eran resultados, no cuáles sí;
  - la síntesis falló la verificación de fidelidad en sus 12 llamadas (0,15 USD) y N6 recibió
    cero requerimientos;
  - lo corrige la decisión 28. Sus tres corridas de verificación agotaron los 15 turnos por otro
    problema: el elicitador plantea la necesidad desde quien publica el aviso («Como la caja,
    quiero publicar un aviso»), no desde las reacciones que pidió el cliente. Por eso cada una se
    atascó en una pregunta distinta:
    - una, si los datos del aviso eran obligatorios;
    - otra, qué resultado deja publicar el aviso;
    - la tercera repitió «¿Qué falta…?», porque el cliente pedía la prioridad y el registro no la
      recoge;
  - lo atienden las decisiones 29 a 31 («Convergencia de la elicitación»). El caso 18 confirma
    ahora el resumen en 3 de 3, aunque 2 de 3 todavía plantean «publicar un aviso».
- **Sesiones para la verificación con el equipo:** `5f5d2739`, escalada en N17, y `b271c343`, en
  pausa en N6.

**Verificación con el equipo.**
- **NotionSync por la web,** `9da543db`: quedó validada y dio lugar a la decisión 26.
- **Una sesión nueva por consola,** `61e1e121` (pago del predial en ventanilla, ARQ-01), el
  2026-11-03:
  - N6 y N9 se aprobaron a la primera;
  - hubo dos rechazos en N17, el segundo con pruebas propias (3 de 4);
  - se validó en la v3 con 4 de 4 pruebas propias: 0,31 USD, 23 min y 30 llamadas;
  - el paquete exportado se instaló con Python 3.14.4 y sus 36 pruebas pasaron. Destapó las
    decisiones 33 y 34.
- **La sesión escalada,** `5f5d2739` (pagos de pensiones, ARQ-06):
  - dos devoluciones al arquitecto, un rechazo en N9 y una devolución al desarrollador: tres
    rediseños y cuatro versiones;
  - se validó en la v6 con 4 de 4 pruebas propias, tras 0,97 USD y 33 min;
  - sus hallazgos de los agentes los atiende el ADR-0015.
- **El cierre,** `b271c343`: se cerró en N6 con motivo, y quedó registrado quién, cuándo y desde
  qué punto.
- Entre las cuatro destaparon los defectos que corrigen las decisiones 32 a 35.

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
- **Desfavorable: algunos secretos escapan al detector.** No se marca:
  - un secreto con espacios, como una frase de paso;
  - uno con forma de nombre de variable de entorno;
  - uno escrito en una prueba.

  La persona los revisa en N17. El modelo no tiene secretos reales, salvo que el cliente los
  escriba en la conversación.
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

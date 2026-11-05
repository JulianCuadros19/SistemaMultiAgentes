**UNIVERSIDAD CATÓLICA DE COLOMBIA**

FACULTAD DE INGENIERÍA · PROGRAMA DE INGENIERÍA DE SISTEMAS Y COMPUTACIÓN

**DOCUMENTO TÉCNICO DE ARQUITECTURA MULTIAGENTE**

Sistema multiagente de IA para definición de requerimientos, diseño de arquitectura, generación y validación de código en Python para la empresa Realtix

| **Campo**      | **Contenido**                                               |
|----------------|-------------------------------------------------------------|
| Producto       | Entregable del Objetivo Específico 2                        |
| Versión        | 1.5                                                         |
| Fecha          | 14 de septiembre de 2026                                    |
| Autores        | Cuadros Muñoz Julián Andrés / Riveros Flórez Laura Catalina |
| Director       | MsC. Juan Carlos Barrero Calixto                            |
| Empresa        | Realidad 5.0 S.A.S. — marca comercial Realtix               |
| Base normativa | Documento de Requerimientos (39 RF, 10 RNF)                 |
| Estado         | Para revisión y aprobación del equipo técnico               |

**1. PROPÓSITO Y ALCANCE**

Este documento define la arquitectura técnica del sistema multiagente y constituye el entregable del segundo objetivo específico. Traduce los 39 requerimientos funcionales y 10 no funcionales en una estructura implementable: topología del grafo, roles y prompts de los agentes, contratos de estado, bases de conocimiento, modelo de datos y vista de despliegue.

**2. VISTA LÓGICA: TOPOLOGÍA DEL GRAFO**

**2.1 Principio de granularidad**

El grafo adopta el principio de más nodos que agentes. Cada nodo encapsula una responsabilidad única y verificable, lo que permite instrumentar el costo y la latencia por etapa, reintentar una etapa sin repetir las anteriores y sustituir la implementación de un nodo sin afectar a los demás. La separación entre nodos determinísticos y nodos que invocan un modelo de lenguaje es deliberada: concentra el gasto en cinco de los diecisiete nodos.

**2.2 Nodos del grafo**

**Tabla 1. Descripción de los diecisiete nodos**

| **Nodo** | **Agente**    | **Responsabilidad**                                                                                              | **Naturaleza**          |
|----------|---------------|------------------------------------------------------------------------------------------------------------------|-------------------------|
| **N1**   | Elicitador    | Apertura de sesión: crea el identificador, carga la plantilla e inicializa el registro de información capturada. | Determinística          |
| **N2**   | Elicitador    | Recuperación de contexto de elicitación y de dominio de negocio.                                                 | Embeddings              |
| **N3**   | Elicitador    | Diálogo: formula la siguiente pregunta estratégica y extrae la información de la respuesta. Antes del resumen, pregunta por los casos límite de las reglas capturadas y una vez por algo más. | LLM                     |
| **N4**   | Elicitador    | Control de suficiencia: decide si cerrar la elicitación o devolver el flujo a N3.                                | Determinística          |
| **N5**   | Elicitador    | Síntesis: produce historias de usuario y requerimientos formales. Con una enmienda desde N17, incorpora la regla nueva a los requerimientos vigentes, sin renumerarlos ni quitar escenarios, y sube de versión los que cambian. | LLM                     |
| **N6**   | Elicitador    | Verificación de atributos de calidad y aprobación humana. Lo que no requiere al cliente vuelve a N5 para corregirse antes, aunque haya preguntas abiertas. Durante una enmienda, lo que el analista ya había aceptado no vuelve a N5, un rechazo vuelve a N5 y la aprobación lleva a N16. | Humano                  |
| **N7**   | Arquitecto    | Recuperación del catálogo de arquitecturas de referencia aplicables.                                             | Embeddings              |
| **N8**   | Arquitecto    | Selección, justificación y parametrización: registro de decisión, especificación de diseño y recorrido de cada escenario de aceptación con interfaces públicas. Si el revisor dejó observaciones, el registro gana una revisión con la respuesta y los cambios. | LLM                     |
| **N9**   | Arquitecto    | Validación contra esquema, verificación de cobertura y de escenarios ejecutables, y aprobación humana.            | Determinística y humana |
| **N10**  | Desarrollador | Generación del módulo: código, documentación y pruebas conforme a la especificación, con una prueba por escenario que sigue su recorrido. Antes de entregarla, verifica la estructura y el estilo que rechazaría el tester. Tras un rediseño, parte de la versión anterior y de la retroalimentación que lo motivó. | LLM                     |
| **N11**  | Tester        | Ejecución del código y las pruebas en contenedor efímero sin red.                                                | Determinística          |
| **N12**  | Tester        | Análisis estático de estilo y seguridad, verificación de conformidad arquitectónica (funciones, clases y métodos `Clase.metodo`) y detección de pruebas que simulan el efecto del módulo (CAL-FS-006). | Determinística          |
| **N13**  | Tester        | Recuperación de los criterios de calidad aplicables al módulo.                                                   | Embeddings              |
| **N14**  | Tester        | Veredicto por criterio y retroalimentación estructurada. El juez ve las interfaces y el modelo de datos de la especificación, y cada caso que rechaza se confirma con una segunda opinión. | LLM                     |
| **N15**  | Orquestador   | Decisión de enrutamiento: remite el módulo aprobado por el tester a la validación humana final (N17), reabre el ciclo de corrección o, agotados los intentos, escala la sesión a N17 para que decida una persona. | Determinística          |
| **N16**  | Tester        | Plan de pruebas de aceptación: al aprobarse los requerimientos (N6), deriva un caso de prueba por cada escenario Gherkin aprobado. Corre en paralelo con N7 y es la base del veredicto de N14. Tras una enmienda aprobada, rehace el plan y pasa el control a N10. | Determinística          |
| **N17**  | Orquestador   | Validación y aprobación humana final: la persona revisa el reporte y el código, puede ejecutar pruebas propias en el entorno aislado y aprueba el módulo, lo devuelve con observaciones al desarrollador (N10) o al arquitecto (N8), pide al elicitador (N5) una enmienda de los requerimientos con una regla nueva, o cierra la sesión. Una sesión escalada no puede aprobarse. | Humano                  |

*Fuente: Elaboración propia.*

**Ausencia de nodo de recuperación en el desarrollador.** El agente desarrollador es el único que no dispone de nodo de recuperación de contexto. Su entrada —requerimientos formales y especificación de diseño— constituye una definición completa, por lo que la recuperación añadiría latencia y riesgo de introducir fragmentos que contradigan la especificación. La consecuencia arquitectónica es deseable: la calidad del código queda atribuida exclusivamente a la calidad de los artefactos producidos aguas arriba.

**2.3 Descripción del flujo**

El flujo se inicia con la apertura de sesión (N1) y la carga de contexto (N2). El ciclo conversacional se establece entre N3 y N4: el elicitador formula una pregunta, extrae la información de la respuesta y el control de suficiencia decide si continuar preguntando o avanzar. Cerrada la elicitación, N5 sintetiza los artefactos y N6 los somete a verificación de calidad y aprobación humana. Si la persona los rechaza, el flujo regresa a N3 con sus observaciones.

Aprobados los requerimientos, se entregan al arquitecto y al tester. El tester deriva de ellos el plan de pruebas de aceptación (N16), un caso por cada escenario aprobado, en paralelo con el trabajo del arquitecto. El arquitecto recupera del catálogo las alternativas aplicables (N7), selecciona y parametriza la arquitectura (N8) y somete la especificación a validación de esquema, verificación de cobertura, verificación de que cada escenario aprobado se pueda preparar, ejecutar y observar con sus interfaces, y aprobación humana (N9). Si la persona la rechaza, el flujo regresa a N8 con sus observaciones.

Con la especificación aprobada, el desarrollador genera el módulo (N10). El tester lo ejecuta en sandbox (N11), aplica el análisis estático y la verificación de conformidad arquitectónica (N12), recupera los criterios de calidad aplicables (N13) y emite el veredicto con retroalimentación (N14), un dictamen por cada caso del plan de pruebas de aceptación. El nodo de decisión (N15) remite el módulo a la validación humana final (N17) si todos los criterios se cumplen, o devuelve el control a N10 con la retroalimentación. Si el desarrollador no logra producir una versión válida, la iteración cuenta como rechazada y el flujo pasa de N10 a N15 sin ejecutar nada. Agotado el límite de iteraciones (RF-27), N15 marca la sesión para intervención humana y la detiene de forma controlada en N17, donde no puede aprobarse. En N17, la persona revisa el reporte y el código, puede ejecutar pruebas propias en el entorno aislado y aprueba el módulo, lo que cierra el flujo; o lo devuelve con sus observaciones y los hallazgos del tester al desarrollador (N10), que lo corrige, o al arquitecto (N8), que rehace el diseño y lo somete de nuevo a N9.

**Enmiendas desde la validación final.** Si la persona descubre en N17 una regla que los requerimientos no tienen, pide una enmienda: sus observaciones van al elicitador (N5), que incorpora la regla a los requerimientos vigentes sin agregar, quitar ni renumerar requerimientos ni escenarios, y sube de versión los que cambian. N6 los verifica y el analista los aprueba; si los rechaza, la enmienda vuelve a N5 con sus observaciones. Los defectos que el analista ya había aceptado no vuelven a N5, porque no los causó la enmienda. Aprobada la enmienda, N16 rehace el plan de pruebas y el desarrollador corrige el módulo (N10) con la misma especificación, en un ciclo de corrección nuevo que recibe las observaciones de N17 y los hallazgos del tester. El flujo no pasa por N7 a N9: si la regla exige otro diseño, la persona devuelve después el módulo al arquitecto desde N17.

**Cierre de una sesión.** Toda sesión en pausa o detenida por una falla puede cerrarse sin módulo validado. El cierre se aplica como una decisión de N17: termina el flujo en la fase `cerrada` y registra quién cerró, desde dónde, cuándo y por qué (RF-33). Así, ninguna sesión queda sin salida: cada falla termina en un reintento que puede funcionar o en una decisión humana.

**Lazos del grafo.** El sistema tiene dos ciclos: el conversacional entre N3 y N4, que cierra por suficiencia de información, y el de corrección entre N10 y N15, que cierra por aprobación de criterios o por agotamiento de intentos. Además, cada uno de los tres puntos de control humano (N6, N9 y N17) puede devolver el flujo al agente anterior con observaciones; desde N17, al desarrollador, al arquitecto o, con una enmienda, al elicitador, que la lleva por N5, N6 y N16 hasta N10. Cada devolución desde N17 abre un ciclo de corrección nuevo, con el mismo límite de iteraciones. Ambos ciclos y estos retornos exigen un orquestador con soporte nativo de ciclos, checkpointing y control humano.

**3. BASES DE CONOCIMIENTO**

El sistema mantiene cuatro colecciones de conocimiento en una única instancia de PostgreSQL con extensión vectorial. Cada agente consulta exclusivamente las colecciones asociadas a sus tareas, cumpliendo el RF-29. El aislamiento se implementa mediante filtro obligatorio por colección en la capa de recuperación, no mediante bases de datos separadas: esto preserva un único pipeline de ingesta, un único índice y una sola pieza de infraestructura que mantener.

**Tabla 2. Colecciones y agentes consumidores**

| **Colección**            | **Contenido**                                                                                                          | **Nodo** | **Segmentación**                        |
|--------------------------|------------------------------------------------------------------------------------------------------------------------|----------|-----------------------------------------|
| elicitacion              | Plantillas de historia de usuario y de requerimiento formal, guía de preguntas estratégicas y técnicas de elicitación. | N2       | Por sección                             |
| dominio_negocio          | Terminología y reglas del dominio tributario y catastral, glosario y requerimientos previos de referencia.             | N2       | Por sección                             |
| arquitecturas_referencia | Catálogo de arquitecturas con criterios de aplicabilidad, patrones de diseño y catálogo tecnológico autorizado.        | N7       | Una arquitectura o patrón por fragmento |
| criterios_calidad        | Reglas verificables derivadas de ISO 9001, ISO/IEC 27001 (A.8.25 y A.8.28), ISO/IEC 25010 e ISO/IEC/IEEE 29119.        | N13      | Una regla por fragmento                 |

*Fuente: Elaboración propia.*

**Segmentación diferenciada.** Las colecciones no comparten estrategia de fragmentación porque su naturaleza difiere. La prosa de dominio admite fragmentos de 512 a 1024 tokens con solapamiento. El catálogo de arquitecturas se fragmenta por unidad conceptual, de modo que cada recuperación devuelva una alternativa completa con sus criterios de aplicabilidad. Los criterios de calidad se almacenan como reglas atómicas, un fragmento por regla: es esta granularidad la que permite que el veredicto del tester sea trazable criterio por criterio, conforme al RF-21 y al RF-23.

**3.1 Configuración de estilo como restricción verificable**

Las convenciones de estilo de código no constituyen una colección de conocimiento. Se declaran como archivo de configuración versionado del sistema —longitud de línea, convenciones de nombres, orden de importaciones, obligatoriedad de documentación— y se refuerzan mediante un bloque fijo en el prompt del desarrollador. Su cumplimiento se verifica en el nodo N12 mediante herramientas de análisis estático, que fallan ante infracciones de severidad alta.

Esta decisión es preferible a la recuperación por tres razones: el estilo pasa de ser una sugerencia probabilística a una restricción objetiva y medible; no consume tokens en ninguna invocación; y elimina la posibilidad de que un fragmento recuperado fuera de contexto contradiga la especificación de diseño.

**3.2 Ingesta, recuperación y embeddings**

El pipeline de ingesta carga el documento, lo fragmenta según la estrategia de su colección, genera los embeddings de forma local y realiza la indexación vectorial y léxica. La recuperación combina búsqueda semántica y léxica con fusión por rango recíproco, aplica filtro obligatorio por colección, verifica la relevancia del contexto antes de inyectarlo en el prompt y registra en la traza el contexto descartado.

Se adopta un modelo de embeddings de ejecución local. La justificación es doble: elimina el costo por token en un proceso que se reindexa repetidamente durante el afinamiento y evita que la información de dominio salga de la infraestructura de la empresa conforme al RNF-04. La dimensión del vector queda fijada en la definición de la tabla, por lo que un cambio de modelo implica reindexar el corpus.

**4. ROLES DE LOS AGENTES Y PROMPTS**

**4.1 Agente elicitador**

**Rol.** Analista de requerimientos que conversa con el cliente.

**Entradas.** Historia conversacional, registro de información capturada y contexto recuperado de las colecciones de elicitación y dominio.

**Salidas.** Una pregunta estratégica por turno y, al cierre, historias de usuario y requerimientos formales en formato estructurado validado contra esquema.

**Reglas del prompt.** Formular una sola pregunta por turno, en lenguaje de negocio; no inventar reglas no expresadas por el cliente; declarar explícitamente qué información falta.

**4.2 Agente arquitecto**

**Rol.** Diseñador de software que selecciona y parametriza, no que inventa.

**Entradas.** Conjunto de requerimientos aprobado y catálogo de arquitecturas de referencia.

**Salidas.** Registro de decisión arquitectónica y especificación de diseño con módulos, interfaces, dependencias y modelo de datos.

**Reglas del prompt.** Elegir únicamente del catálogo; justificar la decisión citando los requerimientos que la motivan; declarar al menos una alternativa descartada; no introducir dependencias fuera del catálogo tecnológico.

**4.3 Agente desarrollador**

**Rol.** Programador Python senior que implementa una especificación.

**Entradas.** Requerimientos aprobados y especificación de diseño. No recibe contexto recuperado.

**Salidas.** Módulos de código, pruebas automatizadas, documentación de funciones públicas y documento de uso.

**Reglas del prompt.** Implementar exactamente los módulos e interfaces declarados en la especificación; no importar dependencias no declaradas; producir una prueba por criterio de aceptación; ajustarse a la configuración de estilo del sistema.

**4.4 Agente tester**

**Rol.** Verificador y auditor de calidad. No modifica código.

**Entradas.** Código y pruebas, requerimientos aprobados con su plan de pruebas de aceptación (N16), especificación de diseño, resultados de ejecución y criterios de calidad recuperados.

**Salidas.** Veredicto por criterio, reporte de conformidad arquitectónica, hallazgos por severidad y retroalimentación estructurada.

**Reglas del prompt.** Dictaminar con evidencia; no corregir; clasificar cada hallazgo por severidad; referenciar cada hallazgo al criterio de calidad que lo origina.

**4.5 Gestión de prompts**

Los prompts de sistema de cada agente y la configuración de estilo se versionan como activos del repositorio, y cada llamada a un modelo registra en la traza el identificador, la versión y la huella del prompt que usó. Cada artefacto producido queda asociado a la versión exacta que lo generó, conforme al RF-36. Ningún prompt se define en línea dentro del código de un nodo.

**5. ASIGNACIÓN DE MODELOS POR NODO**

Se adopta el principio de asignación por complejidad cognitiva: a cada nodo se le asigna el modelo más económico capaz de resolver su tarea con suficiencia. Cinco de los diecisiete nodos invocan un modelo de lenguaje.

**Tabla 3. Asignación de modelos**

| **Nodo** | **Tarea**                                   | **Naturaleza cognitiva**                          | **Perfil de modelo** |
|----------|---------------------------------------------|---------------------------------------------------|----------------------|
| N3       | Diálogo de elicitación                      | Conversación dirigida con extracción estructurada | Intermedio           |
| N5       | Síntesis y enmienda de los requerimientos   | Razonamiento y salida estructurada extensa        | Intermedio           |
| N8       | Selección y parametrización de arquitectura | Razonamiento comparativo y decisión justificada   | Alto                 |
| N10      | Generación del módulo                       | Síntesis de código, máxima exigencia              | Alto                 |
| N14      | Veredicto de validación                     | Clasificación con justificación                   | Económico            |

*Fuente: Elaboración propia.*

**Identificadores de modelo.** La tabla especifica perfiles, no identificadores concretos. Los identificadores residen en la configuración del sistema conforme al RNF-06, y su selección definitiva se realiza mediante benchmark controlado. Esta decisión permite cambiar el modelo de un nodo, o su versión, editando la configuración, sin modificación del código. Los modelos de lenguaje son los desplegados en Azure OpenAI, único proveedor de modelos de lenguaje del sistema (ADR-0017).

**Perfil del nodo N10.** Al no disponer de recuperación de contexto, el nodo de generación concentra la exigencia sobre la capacidad del modelo para seguir una especificación extensa con precisión. Se le asigna el perfil más alto disponible, lo que resulta coherente con el principio de reservar el gasto para el trabajo que realmente lo requiere.

**6. ESTADO COMPARTIDO Y FLUJOS DE COMUNICACIÓN**

Los agentes no se comunican entre sí mediante mensajes conversacionales. Toda la comunicación ocurre a través de un estado tipado y persistido que cada nodo lee y actualiza. Esta decisión hace el sistema auditable, reproducible y económico en consumo de tokens.

**Tabla 4. Particiones del estado**

| **Partición**  | **Contenido**                                                                                    | **Nodos que escriben** |
|----------------|--------------------------------------------------------------------------------------------------|------------------------|
| sesion         | Identificador, cliente, fase actual, marca de tiempo, bandera de espera de entrada del usuario, aprobaciones humanas y cierre. | N1, N4, N6, N9, N15, N17 |
| conversacion   | Historial de turnos y registro estructurado de información capturada.                            | N3                     |
| requerimientos | Historias de usuario y requerimientos formales con su estado de aprobación, y las enmiendas desde N17. | N5, N6, N16, N17       |
| arquitectura   | Registro de decisión con sus revisiones, especificación de diseño validada contra esquema y recorridos de los escenarios. | N8, N9, N17            |
| codigo         | Versiones de los módulos, pruebas y documentación generadas.                                     | N10                    |
| validacion     | Plan de pruebas de aceptación, resultados de ejecución, hallazgos estáticos, conformidad arquitectónica, veredicto y retroalimentación. | N10, N11, N12, N14, N16, N17 |
| contexto       | Fragmentos recuperados por colección y contexto descartado.                                      | N2, N7, N13            |
| control        | Número de iteración, límites configurados, costo acumulado, presupuesto y sus ampliaciones.      | N1, N3, N5, N8, N10, N14, N15 |

*Fuente: Elaboración propia.*

Los cinco nodos con modelo suman a `control` el costo de sus llamadas. Antes de correr, si la sesión alcanzó su presupuesto, pausan hasta que una persona lo amplía, lo que queda registrado, o cierra la sesión (RNF-10, ADR-0016).

N10 escribe la validación solo cuando no logra una versión válida: la deja rechazada, con los problemas como retroalimentación. N17 escribe la retroalimentación de un rechazo y, si devuelve el diseño, las observaciones para el arquitecto; si pide una enmienda, la deja en curso en los requerimientos, con los defectos que el analista ya había aceptado. N16 la pasa a las enmiendas aplicadas, que conservan quién la pidió, su texto, las observaciones del analista y la versión de cada requerimiento enmendado.

El estado se persiste mediante puntos de control tras cada transición, lo que permite reanudar una ejecución interrumpida, incluida una conversación de elicitación en curso, conforme al RF-28.

**7. MODELO DE DATOS**

**Tabla 5. Entidades principales**

| **Entidad**                | **Propósito**                                                                  |
|----------------------------|--------------------------------------------------------------------------------|
| sesiones                   | Sesión de elicitación con su cliente, fase y estado.                           |
| turnos_conversacion        | Historial completo del diálogo entre el cliente y el elicitador.               |
| historias_usuario          | Historias producidas por el elicitador con su trazabilidad a la sesión.        |
| requerimientos             | Requerimientos formales conforme al Anexo A, con estado de aprobación y las enmiendas desde N17. |
| decisiones_arquitectonicas | Arquitectura elegida, alternativas descartadas y justificación.                |
| especificaciones_diseno    | Especificación estructurada de módulos, interfaces, dependencias y modelo de datos. |
| artefactos_codigo          | Versiones de los módulos, pruebas y documentación generadas.                   |
| validaciones               | Veredictos por criterio, hallazgos y conformidad arquitectónica.               |
| aprobaciones_humanas       | Decisión, observaciones, revisor y fecha de cada punto de control humano (N6, N9 y N17). |
| ejecuciones                | Traza por nodo: inicio, duración, costo y error de cada ejecución de un nodo.  |
| llamadas_modelo            | Cada llamada al modelo de un nodo, con su prompt y versión, tokens, costo y latencia. |
| kb_documentos              | Documentos de las bases de conocimiento con su colección, fuente y versión.    |
| kb_fragmentos              | Fragmentos vectorizados con su embedding, colección y referencia al documento. |
| checkpoints                | Persistencia del estado del grafo gestionada por el orquestador.               |

*Fuente: Elaboración propia.*

La tabla de fragmentos incorpora índice vectorial para la búsqueda semántica, índice textual para la búsqueda léxica e índice sobre la columna de colección, que soporta el filtro de aislamiento exigido por el RF-29.

**8. VISTA DE DESPLIEGUE**

El sistema se entrega empaquetado en contenedores orquestados mediante un archivo de composición único, conforme al RF-37. La composición incluye los siguientes servicios:

- **Aplicación.** Orquestador, agentes, capa de recuperación e interfaces de operación. Invoca los modelos de lenguaje desplegados en Azure OpenAI y crea el sandbox mediante el Docker del anfitrión.

- **Base de datos.** PostgreSQL con extensión vectorial, que aloja el estado, los puntos de control y las bases de conocimiento.

- **Servicio de embeddings.** Modelo de vectorización de ejecución local.

- **Sandbox.** Contenedor efímero sin red, creado y destruido por cada ejecución de código.

- **Observabilidad.** Traza por nodo en la misma base de datos (`ejecuciones` y `llamadas_modelo`), consultable desde la consola y la web: prompts, tokens, costo y tiempo de cada nodo. No requiere un servicio aparte (ADR-0016).

**Proveedor de modelos.** Los cinco nodos que invocan un modelo de lenguaje usan los desplegados en un recurso de Azure OpenAI, cuyo punto de acceso y credencial residen en variables de entorno; el sistema no emplea modelos de lenguaje de ejecución local (ADR-0017). El modelo de embeddings, en cambio, se ejecuta dentro de la composición, de modo que las bases de conocimiento no salen de la infraestructura de la empresa (RNF-04).

**Arranque.** Un solo comando levanta la composición: descarga y verifica el modelo de embeddings, construye las imágenes de la aplicación y del sandbox, migra la base de datos e indexa las bases de conocimiento antes de habilitar la aplicación. La interfaz web se publica solo en la máquina donde corre la composición.

**9. SEGURIDAD Y CONFIDENCIALIDAD**

- Todo código generado se ejecuta en contenedor efímero sin acceso a red ni al sistema de archivos del anfitrión (RNF-03).

- Los embeddings se generan localmente, de modo que la información de dominio no se transmite a terceros (RNF-04).

- Las credenciales residen en variables de entorno excluidas del control de versiones y no se copian a las imágenes, que se construyen en la máquina donde corren y no se publican en ningún registro.

- Los prompts, con la conversación, los fragmentos recuperados y los artefactos de cada sesión, se procesan en Azure OpenAI, dentro de su límite de cumplimiento; con datos reales se prefieren despliegues de zona de datos de EE. UU. sobre los globales.

- La interfaz web no tiene autenticación y solo responde en la máquina donde corre la composición. La aplicación accede al Docker del anfitrión únicamente para crear el sandbox (ADR-0017).

- Durante las pruebas del proyecto se emplean datos sintéticos o anonimizados, conforme al acuerdo de confidencialidad.

**10. TRAZABILIDAD ARQUITECTURA – REQUERIMIENTOS**

**Tabla 6. Correspondencia entre decisiones y requerimientos**

| **Decisión arquitectónica**                               | **Requerimientos que satisface**   |
|-----------------------------------------------------------|------------------------------------|
| Ciclo conversacional N3–N4 con control de suficiencia     | RF-01, RF-02, RF-03, RNF-08        |
| Nodos N5 y N6 con verificación y aprobación humana        | RF-05, RF-06, RF-07, RF-08, RNF-09 |
| Plan de pruebas de aceptación del tester (N16)            | RF-08, RF-21                       |
| Validación y aprobación humana final (N17)                | RF-38, RF-39, RNF-09               |
| Enmiendas de los requerimientos desde N17 (N5, N6, N16)   | RF-05, RF-07, RF-21, RF-39, RNF-09 |
| Agente arquitecto con catálogo de referencia (N7, N8, N9) | RF-09 a RF-14, RNF-09              |
| Especificación de diseño estructurada validable contra esquema | RF-11, RF-12, RF-22                |
| Generación sin recuperación en el nodo N10                | RF-15, RF-29                       |
| Configuración de estilo verificada en N12                 | RF-16, RF-23, RF-36                |
| Verificación de conformidad arquitectónica en N12         | RF-17, RF-22                       |
| Recuperación de criterios de calidad en N13               | RF-23, RF-29                       |
| Colecciones con filtro obligatorio por agente             | RF-29, RF-30, RNF-04               |
| Segmentación diferenciada por naturaleza de contenido     | RF-30, RF-31                       |
| Capa de modelos agnóstica al proveedor                    | RNF-05, RNF-06, RF-37              |
| Composición en contenedores con Azure OpenAI y embeddings locales | RF-37, RNF-04, RNF-07     |
| Estado tipado con puntos de control                       | RF-26, RF-28, RF-33, RNF-02        |
| Traza por nodo con tokens y costo                         | RF-34, RNF-10                      |
| Presupuesto por módulo con pausa antes de los nodos con modelo | RNF-10                       |

*Fuente: Elaboración propia.*

**11. RIESGOS TÉCNICOS Y MITIGACIONES**

**Tabla 7. Riesgos de la arquitectura**

| **Riesgo**                                                                                         | **Mitigación**                                                                                                                                                                         |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| El ciclo conversacional no converge y el cliente queda atrapado en preguntas.                      | Límite configurable de turnos en el control de suficiencia, con escalamiento al analista humano al alcanzarlo.                                                                         |
| El agente arquitecto produce diseños inconsistentes entre ejecuciones.                             | El espacio de decisión se restringe a un catálogo curado; el agente selecciona y parametriza, no crea. La validación contra esquema y la verificación de cobertura acotan la varianza. |
| Sin recuperación de contexto, el desarrollador produce código con formato de salida inconsistente. | El formato de salida se fija mediante ejemplos dentro del prompt de sistema y se valida estructuralmente antes de la ejecución en sandbox.                                             |
| El incremento de agentes eleva la latencia y el costo por unidad procesada.                        | Cinco de diecisiete nodos consumen tokens; el interruptor de presupuesto y los límites de tokens de salida contienen el gasto.                                                             |
| El alcance de cuatro agentes excede el tiempo disponible del proyecto.                             | El catálogo cerrado de arquitecturas constituye el producto mínimo viable; el diseño arquitectónico libre se difiere a trabajos futuros.                                               |
| El sistema depende de un único proveedor de modelos de lenguaje, Azure OpenAI: de su cuota, su disponibilidad, el retiro de versiones, su costo y la región donde procesa los datos. | La capa de modelos es agnóstica al proveedor, y los identificadores, versiones y tarifas residen en configuración (RNF-06); el presupuesto por módulo contiene el gasto (RNF-10); con datos reales se prefieren despliegues de zona de datos de EE. UU. |

*Fuente: Elaboración propia.*

**12. CRITERIO DE APROBACIÓN**

El presente documento se considera aprobado cuando el equipo técnico de Realtix verifique que la topología del grafo cubre la totalidad de los requerimientos funcionales, que las bases de conocimiento reflejan la información que cada agente necesita para cumplir su tarea, que el modelo de datos soporta la trazabilidad exigida y que la vista de despliegue garantiza la operación con los modelos de lenguaje de Azure OpenAI, con la información de dominio bajo control de la empresa. La aprobación se registra mediante acta firmada y habilita el inicio del tercer objetivo específico.

**HISTORIAL DE CAMBIOS**

| **Versión** | **Fecha** | **Cambio** |
|---|---|---|
| 1.0 | 14 de septiembre de 2026 | Versión aprobada por el equipo técnico. |
| 1.1 | 8 de octubre de 2026 | Alineación con el documento de tesis (ADR-0004): especificación de diseño en lugar de contrato; nodo N16 (plan de pruebas de aceptación del tester) y nodo N17 (validación y aprobación humana final); retornos con observaciones desde los tres puntos de control; entidad `aprobaciones_humanas`. |
| 1.2 | 9 de octubre de 2026 | Flujo sin bloqueos (ADR-0014): N10 pasa a N15 si no logra una versión válida; agotado el ciclo de corrección, N15 escala la sesión a N17, donde no puede aprobarse; N17 devuelve el módulo al desarrollador (N10) o al arquitecto (N8), y cada devolución abre un ciclo nuevo; toda sesión en pausa o detenida puede cerrarse en la fase `cerrada`, con su registro. |
| 1.3 | 4 de noviembre de 2026 | Calidad de la primera salida (ADR-0015): N12 detecta las pruebas que simulan el efecto del módulo (CAL-FS-006), y el juez de N14 ve las interfaces y el modelo de datos de la especificación y confirma cada rechazo con una segunda opinión. N8 declara el recorrido de cada escenario con interfaces públicas, fuera del Anexo B, y N9 lo verifica; el registro de decisión gana una sección de revisiones. Los métodos se declaran como interfaces `Clase.metodo`, que N9, N10 y N12 verifican. Tras un rediseño, N10 recibe la versión anterior como referencia, con la retroalimentación de N17 y la revisión del diseño, y antes de entregar aplica el estilo que rechazaría el tester. N3 pregunta por casos límite antes del resumen y una vez por algo más, con un límite de 18 turnos; el registro guarda los casos especiales, los ejemplos con cifras y quién más usa lo pedido, aparte del rol, y con el resumen confirmado N5 toma las preguntas abiertas del registro. N6 corrige los defectos que N5 puede resolver aunque haya preguntas abiertas, y escala estas al analista. N17 gana un tercer destino: una enmienda de los requerimientos por el elicitador, que recorre N5, N6 y N16 hasta N10 sin pasar por el diseño, con una arista nueva de N16 a N10. Al cierre, N9 rechaza `self` y `cls` en las funciones de módulo, el resumen muestra la obligatoriedad de un dato solo si el cliente la dijo y N3 reconoce «no aplica» como no saber. |
| 1.4 | 4 de noviembre de 2026 | Control de costo y traza por nodo (ADR-0016): los nodos con modelo suman su costo al de la sesión y, si alcanzó su presupuesto (1,50 USD por defecto), pausan hasta que una persona lo amplía o la cierra; la traza por nodo pasa a PostgreSQL (`ejecuciones` y `llamadas_modelo`), consultable desde la consola y la web, y Langfuse sale de la vista de despliegue. |
| 1.5 | 4 de noviembre de 2026 | Entrega con Azure OpenAI (ADR-0017): los modelos de lenguaje son los desplegados en Azure OpenAI, sin modelos de lenguaje locales; salen de la vista de despliegue el servicio de inferencia local y los modos de operación, y el modelo de embeddings sigue local por el RNF-04. La composición levanta con un solo comando la aplicación, la base de datos, los embeddings y el sandbox, que la aplicación crea mediante el Docker del anfitrión; la web solo responde en esa máquina. El riesgo de los modelos locales pasa a ser la dependencia de un único proveedor. |

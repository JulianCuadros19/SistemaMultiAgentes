**UNIVERSIDAD CATÓLICA DE COLOMBIA**

FACULTAD DE INGENIERÍA · PROGRAMA DE INGENIERÍA DE SISTEMAS Y COMPUTACIÓN

**DOCUMENTO DE REQUERIMIENTOS FUNCIONALES Y NO FUNCIONALES**

Sistema multiagente de IA para definición de requerimientos, diseño de arquitectura, generación y validación de código en Python para la empresa Realtix

| **Campo** | **Contenido**                                               |
|-----------|-------------------------------------------------------------|
| Producto  | Entregable del Objetivo Específico 1                        |
| Versión   | 1.1                                                         |
| Fecha     | 14 de septiembre de 2026                                    |
| Autores   | Cuadros Muñoz Julián Andrés / Riveros Flórez Laura Catalina |
| Director  | MsC. Juan Carlos Barrero Calixto                            |
| Empresa   | Realidad 5.0 S.A.S. — marca comercial Realtix               |
| Estado    | Para revisión y aprobación del equipo técnico               |

**1. INTRODUCCIÓN Y PROPÓSITO**

Este documento especifica los requerimientos funcionales y no funcionales del sistema multiagente de IA que se desarrolla para la empresa Realtix. Constituye el entregable del primer objetivo específico del trabajo de grado y la base contractual sobre la cual se diseña la arquitectura, se implementan los agentes y se evalúa el desempeño del sistema.

El sistema automatiza la cadena que va desde la necesidad expresada por el cliente hasta el código validado. Cuatro agentes especializados se reparten esa cadena: un elicitador que conversa con el cliente y produce requerimientos formales, un arquitecto que selecciona y parametriza el diseño, un desarrollador que materializa ese diseño en código Python y un tester que valida el resultado. Esta división de roles reproduce el modelo de trabajo de una fábrica de software y se apoya en la evidencia recogida en el estado del arte del anteproyecto, donde los sistemas multiagente que asignan roles diferenciados superan de forma consistente a los modelos de lenguaje individuales en tareas complejas de ingeniería de software.

**2. ALCANCE DEL SISTEMA**

**Unidad de trabajo.** El sistema procesa como unidad un conjunto de requerimientos funcionales que conforman un módulo de software. Esta granularidad es la que otorga sentido al diseño de arquitectura: un requerimiento aislado no admite decisiones estructurales, mientras que un módulo exige definir separación de responsabilidades, interfaces y modelo de datos.

El sistema entrega un producto mínimo viable compuesto por cuatro agentes y un orquestador, capaz de: (i) conversar con el cliente y producir historias de usuario y requerimientos funcionales formales; (ii) seleccionar y parametrizar una arquitectura de referencia para el conjunto de requerimientos aprobado; (iii) generar el código Python del módulo con su documentación y pruebas; y (iv) validar el resultado contra los requerimientos, la especificación de diseño y los criterios de calidad.

**2.1 Limitaciones y exclusiones**

- El lenguaje de generación es exclusivamente Python. El agente arquitecto selecciona frameworks y librerías dentro de un catálogo tecnológico autorizado, pero no decide sobre el lenguaje.

- El agente arquitecto selecciona y parametriza arquitecturas de un catálogo de referencia curado; no diseña arquitecturas originales fuera de dicho catálogo.

- El sistema no despliega el código generado en ambientes productivos ni gestiona su integración continua.

- Durante las pruebas del proyecto se emplean datos sintéticos o anonimizados, conforme al acuerdo de confidencialidad con Realtix.

**3. AGENTES DEL SISTEMA**

**Tabla 1. Agentes, responsabilidades y fuentes de información**

| **Agente**    | **Rol**                          | **Fuente de información**                                                    | **Salidas**                                                |
|---------------|----------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------|
| Elicitador    | Analista de requerimientos       | Conversación con el cliente y bases de conocimiento de elicitación y dominio | Historias de usuario y requerimientos funcionales formales |
| Arquitecto    | Diseñador de software            | Requerimientos aprobados y catálogo de arquitecturas de referencia           | Registro de decisión arquitectónica y especificación de diseño |
| Desarrollador | Programador Python               | Requerimientos y especificación de diseño. No consulta bases de conocimiento       | Código Python, documentación y pruebas                     |
| Tester        | Verificador y auditor de calidad | Código, requerimientos, especificación de diseño y criterios de calidad            | Veredicto por criterio y reporte de defectos               |

*Fuente: Elaboración propia.*

**Criterio de asignación de bases de conocimiento.** Un agente recibe base de conocimiento cuando necesita información que no está contenida en su entrada. El elicitador y el arquitecto la requieren porque deben aportar terminología de dominio y alternativas de diseño que el cliente no expresa. El tester la requiere para determinar qué criterios de calidad aplican. El desarrollador, en cambio, no enfrenta un problema de conocimiento sino de ejecución precisa: sus entradas —requerimientos formales y especificación de diseño— constituyen ya una definición completa. Incorporarle recuperación de contexto añadiría latencia, costo y riesgo de contradicción sin aportar información que no tenga.

**Tratamiento del estilo de código.** Las convenciones de estilo no se entregan al desarrollador como contexto recuperable sino como configuración declarada del sistema, verificable por herramienta durante la validación. Esta decisión convierte el estilo en una restricción objetiva en lugar de una sugerencia probabilística, y no consume tokens.

Los actores humanos son el cliente o usuario de negocio, que sostiene la conversación de elicitación; el analista, que aprueba los requerimientos; el arquitecto de Realtix, que aprueba la especificación de diseño; y el equipo de desarrollo, que opera el sistema.

**4. REQUERIMIENTOS FUNCIONALES**

Se especifican 38 requerimientos funcionales organizados en siete componentes. Cada requerimiento incluye un criterio de aceptación verificable redactado en formato Gherkin.

**4.1 Agente elicitador**

Responsable del diálogo con el cliente y de la producción de historias de usuario y requerimientos formales.

**Tabla 2. Requerimientos de agente elicitador**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                                                                                                                | **Prior.** | **Criterio de aceptación**                                                                                                                                                                          |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-01** | El sistema debe sostener una conversación en lenguaje natural con el cliente para capturar la necesidad de software, gestionando el estado del diálogo a lo largo de múltiples turnos dentro de una sesión identificada.                                                                                                                                         | Alta       | *DADA una sesión iniciada, CUANDO el cliente describe una necesidad, ENTONCES el sistema registra la sesión con identificador único y conserva el historial completo de turnos.*                    |
| **RF-02** | El agente elicitador debe formular preguntas estratégicas dirigidas a completar los atributos mínimos de la historia de usuario (rol, funcionalidad y beneficio) y las reglas de negocio asociadas, siguiendo la guía de elicitación de su base de conocimiento.                                                                                                 | Alta       | *DADA una necesidad expresada de forma incompleta, CUANDO el elicitador responde, ENTONCES formula una pregunta dirigida a un atributo faltante identificado y no repite preguntas ya respondidas.* |
| **RF-03** | El agente elicitador debe mantener un registro estructurado de la información capturada y evaluar en cada turno si es suficiente para cerrar la elicitación, declarando explícitamente los atributos pendientes.                                                                                                                                                 | Alta       | *DADO un registro parcialmente diligenciado, CUANDO el elicitador evalúa la suficiencia, ENTONCES enumera los atributos faltantes o marca la elicitación como completa.*                            |
| **RF-04** | El agente elicitador debe recuperar contexto del dominio de negocio mediante RAG, tanto antes de formular preguntas como antes de redactar los artefactos.                                                                                                                                                                                                       | Alta       | *DADA una sesión de elicitación, CUANDO se generan los artefactos, ENTONCES estos referencian los fragmentos de contexto recuperados.*                                                              |
| **RF-05** | El agente elicitador debe sintetizar las historias de usuario a partir de la conversación, en el formato «Como \[rol\] quiero \[funcionalidad\] para \[beneficio\]», conforme a la plantilla de su base de conocimiento.                                                                                                                                         | Alta       | *DADA una elicitación cerrada, CUANDO el elicitador sintetiza, ENTONCES produce al menos una historia con los tres atributos diligenciados y un identificador único.*                               |
| **RF-06** | El agente elicitador debe transformar cada historia de usuario en un requerimiento funcional formal conforme al formato del Anexo A: identificador, versión, proyecto, tipo de solicitud, impacto, módulo, riesgo, autor, área funcional, funcional responsable, título en forma de historia de usuario, precondición, regla de negocio, datos de entrada, datos de salida, criterios de aceptación en formato Gherkin, prioridad y requerimientos relacionados. | Alta       | *DADA una historia validada, CUANDO finaliza el elicitador, ENTONCES existe un requerimiento con el 100 % de los campos obligatorios diligenciados.*                                                |
| **RF-07** | El sistema debe verificar automáticamente que cada requerimiento cumpla los atributos de calidad (completo, consistente, verificable, trazable y no ambiguo); los que no cumplan deben regresar al elicitador para corrección.                                                                                                                                   | Alta       | *DADO un requerimiento con campos vacíos o contradicciones, CUANDO pasa la verificación, ENTONCES es rechazado con la lista de defectos y reprocesado.*                                             |
| **RF-08** | El sistema debe permitir la revisión y aprobación humana de las historias de usuario y de los requerimientos formales antes de habilitar el diseño de la arquitectura y la preparación de las pruebas de aceptación.                                                                                                                                                                                           | Alta       | *DADO un conjunto de requerimientos formalizado, CUANDO el analista lo aprueba, ENTONCES queda disponible para el agente arquitecto y para el agente tester; si lo rechaza, regresa al elicitador con observaciones.*       |

*Fuente: Elaboración propia.*

**4.2 Agente arquitecto**

Responsable de seleccionar, justificar y parametrizar la arquitectura del módulo a partir de los requerimientos aprobados.

**Tabla 3. Requerimientos de agente arquitecto**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                    | **Prior.** | **Criterio de aceptación**                                                                                                                                                                         |
|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-09** | El agente arquitecto debe recuperar del catálogo de arquitecturas de referencia las alternativas aplicables al conjunto de requerimientos aprobado, junto con sus criterios de aplicabilidad y restricciones.                                                        | Alta       | *DADO un conjunto de requerimientos aprobado, CUANDO el arquitecto consulta el catálogo, ENTONCES recupera al menos dos alternativas candidatas con sus criterios de aplicabilidad.*               |
| **RF-10** | El agente arquitecto debe seleccionar una arquitectura de referencia y registrar la decisión: opción elegida, alternativas descartadas y justificación referida a los requerimientos que la motivan.                                                                 | Alta       | *DADA una selección, CUANDO el arquitecto finaliza, ENTONCES existe un registro de decisión con la opción elegida, al menos una descartada y la justificación trazada a requerimientos concretos.* |
| **RF-11** | El agente arquitecto debe parametrizar la arquitectura seleccionada produciendo una especificación de diseño estructurada y validable contra esquema, que declare módulos, responsabilidades, interfaces públicas, dependencias permitidas entre módulos y modelo de datos. | Alta       | *DADA una especificación de diseño, CUANDO se valida contra el esquema, ENTONCES cumple el 100 % de los campos obligatorios y no declara dependencias circulares.*                                        |
| **RF-12** | El agente arquitecto debe verificar la cobertura del diseño: todo requerimiento funcional aprobado debe quedar asignado al menos a un módulo de la especificación.                                                                                                           | Alta       | *DADO un requerimiento sin módulo asignado, CUANDO se verifica la cobertura, ENTONCES la especificación es rechazada indicando los requerimientos huérfanos.*                                            |
| **RF-13** | El agente arquitecto debe seleccionar los frameworks y librerías dentro del catálogo tecnológico autorizado, sin introducir dependencias fuera de dicho catálogo.                                                                                                    | Alta       | *DADA una especificación de diseño, CUANDO se revisan sus dependencias, ENTONCES todas pertenecen al catálogo tecnológico registrado en la base de conocimiento.*                                         |
| **RF-14** | El sistema debe permitir la revisión y aprobación humana de la especificación de diseño antes de habilitar la generación de código.                                                                                                                                          | Alta       | *DADA una especificación de diseño, CUANDO el arquitecto humano la aprueba, ENTONCES queda disponible para el agente desarrollador; si la rechaza, regresa con observaciones.*                            |

*Fuente: Elaboración propia.*

**4.3 Agente desarrollador**

Responsable de materializar la especificación de diseño en código Python documentado y probado, siguiendo la especificación recibida sin recuperación de contexto.

**Tabla 4. Requerimientos de agente desarrollador**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                               | **Prior.** | **Criterio de aceptación**                                                                                                                                                                                          |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-15** | El agente desarrollador debe producir el código Python del módulo tomando como única fuente los requerimientos aprobados y la especificación de diseño, sin recuperación de contexto externo.                                                                                 | Alta       | *DADA una especificación de diseño aprobada, CUANDO el desarrollador finaliza, ENTONCES existe un archivo Python sintácticamente válido por cada módulo declarado, exponiendo las interfaces públicas de la especificación.*       |
| **RF-16** | El código generado debe ajustarse a la configuración de estilo declarada del sistema —longitud de línea, convenciones de nombres, orden de importaciones y obligatoriedad de documentación—, definida como archivo de configuración versionado y no como contenido recuperable. | Alta       | *DADO el código generado, CUANDO se ejecuta la verificación de estilo con la configuración del sistema, ENTONCES no se reportan infracciones de severidad alta.*                                                    |
| **RF-17** | El agente desarrollador debe respetar las fronteras de dependencia declaradas en la especificación, sin importar módulos no autorizados.                                                                                                                                              | Alta       | *DADO un módulo que importa una dependencia no declarada en la especificación, CUANDO se revisa el código, ENTONCES se registra una violación arquitectónica.*                                                            |
| **RF-18** | El agente desarrollador debe producir la documentación técnica del código y las pruebas unitarias derivadas de los criterios de aceptación Gherkin de los requerimientos asignados a cada módulo.                                                                               | Alta       | *DADO un módulo con N criterios de aceptación, CUANDO el desarrollador finaliza, ENTONCES el 100 % de las funciones públicas contiene documentación y existe al menos un caso de prueba automatizado por criterio.* |
| **RF-19** | El agente desarrollador debe incorporar la retroalimentación estructurada del agente tester en los ciclos de corrección, modificando únicamente lo necesario para resolver los defectos reportados.                                                                             | Alta       | *DADO un reporte de defectos, CUANDO el desarrollador itera, ENTONCES la nueva versión referencia los defectos atendidos y conserva el historial de versiones.*                                                     |

*Fuente: Elaboración propia.*

**4.4 Agente tester y validación**

Responsable de ejecutar, analizar y dictaminar sobre el código producido. No modifica código.

**Tabla 5. Requerimientos de agente tester y validación**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                                                                                              | **Prior.** | **Criterio de aceptación**                                                                                                                                                                   |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-20** | El sistema debe ejecutar el código generado y sus pruebas en un entorno aislado sin acceso a la red ni al sistema de archivos del anfitrión, capturando salida estándar, errores y resultados de las pruebas.                                                                                                                                  | Alta       | *DADO un módulo generado, CUANDO se ejecuta, ENTONCES la ejecución ocurre en el entorno aislado y el sistema captura el resultado completo sin afectar el anfitrión.*                        |
| **RF-21** | El agente tester debe validar el cumplimiento funcional del código contra los criterios de aceptación de los requerimientos aprobados por el humano, marcando cada criterio como cumplido o no cumplido con su evidencia.                                                                                                                                   | Alta       | *DADO el resultado de las pruebas, CUANDO el tester evalúa, ENTONCES emite un veredicto por criterio de aceptación con la prueba asociada como evidencia.*                                   |
| **RF-22** | El agente tester debe verificar la conformidad arquitectónica del código contra la especificación de diseño: existencia de los módulos declarados, correspondencia de las interfaces públicas y respeto de las dependencias permitidas.                                                                                                              | Alta       | *DADA una especificación de diseño y su código, CUANDO el tester verifica la conformidad, ENTONCES reporta por módulo si existe, si su interfaz coincide y si respeta las dependencias declaradas.* |
| **RF-23** | El agente tester debe recuperar de su base de conocimiento los criterios de calidad aplicables al módulo y ejecutar la verificación estática —conformidad de estilo, detección de vulnerabilidades básicas y ausencia de errores de sintaxis— conforme a los criterios derivados de ISO/IEC 25010 e ISO/IEC 27001 (controles A.8.25 y A.8.28). | Alta       | *DADO el código generado, CUANDO el tester lo analiza, ENTONCES el reporte incluye los hallazgos clasificados por severidad y referenciados al criterio de calidad que los origina.*         |
| **RF-24** | El agente tester debe emitir retroalimentación estructurada (defecto, ubicación, severidad, criterio o módulo afectado y sugerencia de corrección) dirigida al agente desarrollador cuando la validación no sea satisfactoria.                                                                                                                 | Alta       | *DADO un veredicto negativo, CUANDO el tester finaliza, ENTONCES existe un reporte estructurado legible por el desarrollador y por el revisor humano.*                                       |
| **RF-25** | El sistema debe registrar la matriz de confusión de las decisiones del tester frente a una evaluación humana de referencia y calcular exactitud, precisión, recall y F1-score.                                                                                                                                                                 | Media      | *DADO un conjunto de casos con evaluación humana de referencia, CUANDO se ejecuta el sistema, ENTONCES se calculan y almacenan las cuatro métricas.*                                         |

*Fuente: Elaboración propia.*

**4.5 Orquestador y flujo iterativo**

Responsable de coordinar el grafo de estado, los ciclos y los puntos de control humano.

**Tabla 6. Requerimientos de orquestador y flujo iterativo**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                                            | **Prior.** | **Criterio de aceptación**                                                                                                                                                                        |
|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-26** | El orquestador debe coordinar el flujo completo —elicitación, aprobación de requerimientos, diseño de arquitectura, aprobación del diseño, desarrollo, validación y decisión— mediante un grafo de estado con soporte de ciclos y transiciones condicionales.                                | Alta       | *DADA una sesión, CUANDO se ejecuta el flujo, ENTONCES cada transición del grafo queda registrada con su estado y marca de tiempo.*                                                               |
| **RF-27** | El nodo de decisión debe cerrar el ciclo desarrollador–tester cuando el código apruebe todos los criterios, o devolverlo al desarrollador con la retroalimentación; el número máximo de iteraciones debe ser configurable (valor por defecto: 3), escalando al humano al alcanzar el límite. | Alta       | *DADO un módulo que falla tras el número máximo de iteraciones, CUANDO se alcanza el límite, ENTONCES el caso se marca «requiere intervención humana» y el flujo se detiene de forma controlada.* |
| **RF-28** | El orquestador debe persistir el estado del flujo mediante puntos de control, permitiendo reanudar una ejecución interrumpida sin pérdida de información, incluido el estado de una conversación de elicitación en curso.                                                                    | Alta       | *DADA una ejecución interrumpida durante la elicitación, CUANDO se reinicia el sistema, ENTONCES el diálogo se reanuda desde el último turno registrado.*                                         |
| **RF-38** | El sistema debe permitir la validación y aprobación humana final del módulo que el agente tester aprobó: la persona revisa el reporte de validación y el código, puede ejecutar pruebas propias en el entorno aislado y aprueba o rechaza el módulo. Si lo rechaza, el módulo regresa al agente desarrollador con sus observaciones. | Alta | *DADO un módulo con veredicto aprobado del tester, CUANDO la persona lo revisa, ENTONCES puede ejecutar pruebas adicionales en el entorno aislado y registrar su aprobación, que cierra el flujo con el módulo validado, o su rechazo, que devuelve el módulo al desarrollador con observaciones.* |

*Fuente: Elaboración propia.*

**4.6 Bases de conocimiento y recuperación**

Responsable de la ingesta y recuperación de contexto, con colecciones independientes por agente.

**Tabla 7. Requerimientos de bases de conocimiento y recuperación**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                                                                                                | **Prior.** | **Criterio de aceptación**                                                                                                                                               |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-29** | El sistema debe mantener bases de conocimiento independientes por agente, de modo que cada agente consulte exclusivamente las colecciones asociadas a sus tareas. El agente desarrollador opera sin recuperación de contexto, tomando su especificación de los artefactos producidos por los agentes anteriores. | Alta       | *DADA una consulta de un agente, CUANDO se recupera contexto, ENTONCES los fragmentos devueltos pertenecen únicamente a las colecciones autorizadas para ese agente.*    |
| **RF-30** | El sistema debe permitir la carga, segmentación, vectorización e indexación de los documentos de cada colección, aplicando la estrategia de segmentación correspondiente a su naturaleza (prosa, catálogo o regla atómica).                                                                                      | Alta       | *DADO un documento nuevo, CUANDO se ingesta, ENTONCES sus fragmentos quedan consultables por búsqueda semántica e identificados por colección, fuente y versión.*        |
| **RF-31** | La recuperación de contexto debe combinar búsqueda semántica y búsqueda léxica con fusión de resultados, dado que el dominio incluye terminología técnica y nombres propios.                                                                                                                                     | Alta       | *DADA una consulta con términos técnicos exactos, CUANDO se recupera contexto, ENTONCES los fragmentos que contienen el término aparecen en los primeros resultados.*    |
| **RF-32** | El sistema debe evaluar la relevancia del contexto recuperado antes de usarlo; si la calidad es insuficiente debe refinar la consulta o declarar la ausencia de contexto, nunca inventarlo.                                                                                                                      | Media      | *DADA una consulta sin cobertura en la base de conocimiento, CUANDO se recupera contexto irrelevante, ENTONCES el sistema lo descarta y lo deja registrado en la traza.* |

*Fuente: Elaboración propia.*

**4.7 Operación, trazabilidad y entregables**

Requerimientos transversales de auditoría, exportación y empaquetado.

**Tabla 8. Requerimientos de operación, trazabilidad y entregables**

| **ID**    | **Requerimiento**                                                                                                                                                                                                                    | **Prior.** | **Criterio de aceptación**                                                                                                                                          |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RF-33** | El sistema debe mantener trazabilidad completa: conversación, historia de usuario, requerimiento formal, decisión arquitectónica, especificación de diseño, versiones de código y resultados de validación, consultable por identificador. | Alta       | *DADO un identificador de sesión, CUANDO se consulta, ENTONCES se obtiene la cadena completa de artefactos asociados.*                                              |
| **RF-34** | El sistema debe registrar la observabilidad de cada ejecución: trazas por agente, prompts y versiones utilizadas, tokens consumidos, costo estimado, latencia y errores.                                                             | Alta       | *DADA una ejecución finalizada, CUANDO se consulta su traza, ENTONCES están disponibles los prompts, tokens, costos y tiempos por nodo del grafo.*                  |
| **RF-35** | El sistema debe exportar los entregables por módulo: requerimientos formales, registro de decisión arquitectónica, especificación de diseño, código fuente, documentación y reporte de validación, en formatos estándar.                   | Media      | *DADO un módulo validado, CUANDO se solicita la exportación, ENTONCES se genera el paquete completo de artefactos.*                                                 |
| **RF-36** | Los prompts especializados de cada agente y la configuración de estilo del sistema deben estar versionados como activos, con posibilidad de auditar qué versión produjo cada artefacto.                                              | Alta       | *DADO un artefacto generado, CUANDO se audita, ENTONCES se identifica la versión exacta del prompt y de la configuración que lo produjeron.*                        |
| **RF-37** | El sistema debe entregarse empaquetado en contenedores, capaz de operar de extremo a extremo sin dependencia de ningún proveedor de nube, utilizando modelos de lenguaje y de embeddings ejecutables localmente.                     | Alta       | *DADO el paquete entregado, CUANDO se despliega en una máquina sin credenciales de nube, ENTONCES el sistema completa el flujo de extremo a extremo en modo local.* |

*Fuente: Elaboración propia.*

**5. REQUERIMIENTOS NO FUNCIONALES**

Los requerimientos no funcionales se clasifican según las características de calidad del producto de software definidas en la norma ISO/IEC 25010:2023.

**Tabla 9. Requerimientos no funcionales**

| **ID**     | **Característica ISO/IEC 25010:2023** | **Requerimiento**                                                                                                                                                                  | **Prior.** |
|------------|----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| **RNF-01** | Eficiencia de desempeño          | Cada turno de la conversación de elicitación debe responder en menos de 15 segundos; el ciclo completo de un módulo no debe exceder los 20 minutos en configuración de referencia. | Alta       |
| **RNF-02** | Fiabilidad                       | El sistema debe reanudar cualquier ejecución interrumpida desde el último punto de control, incluida una conversación en curso, sin pérdida de información.                        | Alta       |
| **RNF-03** | Seguridad                        | Todo código generado debe ejecutarse en un entorno aislado sin acceso a red ni al sistema de archivos del anfitrión.                                                               | Alta       |
| **RNF-04** | Seguridad, confidencialidad      | La información de dominio incorporada a las bases de conocimiento debe permanecer bajo control de la empresa; los embeddings se generan localmente y no se transmiten a terceros.  | Alta       |
| **RNF-05** | Mantenibilidad                   | El sistema debe permitir modificar el prompt, el modelo o la base de conocimiento de un agente sin alterar el código de los demás.                                                 | Alta       |
| **RNF-06** | Flexibilidad                     | La capa de acceso a modelos debe ser agnóstica al proveedor, permitiendo sustituir el modelo de cada agente por configuración y operar íntegramente con modelos locales.           | Alta       |
| **RNF-07** | Compatibilidad                   | El sistema debe ejecutarse sobre Python 3.11 o superior y PostgreSQL 16 o superior, desplegable mediante contenedores en Linux, Windows y macOS.                                   | Alta       |
| **RNF-08** | Capacidad de interacción         | La conversación de elicitación debe ser comprensible para un cliente sin formación técnica: una pregunta por turno, lenguaje de negocio y confirmación explícita antes de cerrar.  | Alta       |
| **RNF-09** | Capacidad de interacción, control humano | El sistema debe detenerse obligatoriamente en tres puntos de control humano: aprobación de requerimientos, aprobación de la especificación de diseño y validación final del módulo. Ante un rechazo, el flujo regresa al agente anterior con las observaciones.                                      | Alta       |
| **RNF-10** | Adecuación funcional             | El costo operativo por módulo procesado debe ser monitoreado y limitado por un presupuesto configurable que detenga la ejecución al superarse.                                     | Alta       |

*Fuente: Elaboración propia.*

**6. REQUERIMIENTOS DE DOMINIO Y DE INTERFAZ**

- **Dominio.** El sistema opera sobre el dominio de gestión tributaria y catastral en el que Realtix presta servicios, por lo que las historias y requerimientos producidos deben emplear la terminología del sector registrada en la base de conocimiento del elicitador.

- **Interfaz de entrada.** Interfaz conversacional para el cliente e interfaz de operación para el equipo técnico, ambas capaces de mostrar el estado del flujo y de gestionar los tres puntos de aprobación.

- **Interfaz de salida.** Artefactos en formatos estándar: requerimientos y especificación de diseño en formato estructurado validado contra esquema y en documento legible; código en archivos .py; reportes en Markdown o PDF.

**7. RESTRICCIONES Y SUPUESTOS**

- El sistema se ejecuta en la infraestructura de Realtix y debe poder operar sin conexión a proveedores de nube.

- El catálogo de arquitecturas de referencia y el catálogo tecnológico autorizado son insumos que se validan antes del desarrollo del agente arquitecto.

- Se supone disponibilidad del equipo técnico de Realtix para los tres puntos de aprobación humana durante las pruebas.

- El número máximo de iteraciones del ciclo de corrección se fija en tres por defecto, configurable.

**8. TRAZABILIDAD CON LOS OBJETIVOS ESPECÍFICOS**

**Tabla 10. Trazabilidad requerimientos – objetivos**

| **Objetivo específico**              | **Requerimientos asociados**   | **KPI**                                    |
|--------------------------------------|--------------------------------|--------------------------------------------|
| OE1 · Definir metas y requerimientos | Documento completo             | 100 % del documento aprobado               |
| OE2 · Diseñar la arquitectura        | RF-26 a RF-32, RF-38, RNF-05 a RNF-07 | 100 % del documento aprobado               |
| OE3 · Desarrollar los agentes        | RF-01 a RF-25, RF-33 a RF-37   | 100 % del producto mínimo viable funcional |
| OE4 · Evaluar el desempeño           | RF-25, RF-34                   | 90 % de aplicación de las pruebas          |

*Fuente: Elaboración propia.*

**9. CRITERIO DE APROBACIÓN DEL DOCUMENTO**

El presente documento se considera aprobado cuando el equipo técnico de Realtix verifique que la totalidad de los requerimientos refleja las necesidades acordadas, que cada uno cuenta con un criterio de aceptación verificable y que el alcance y las exclusiones son correctos. La aprobación se registra mediante acta firmada y habilita el inicio del segundo objetivo específico.

**HISTORIAL DE CAMBIOS**

| **Versión** | **Fecha** | **Cambio** |
|---|---|---|
| 1.0 | 14 de septiembre de 2026 | Versión aprobada por el equipo técnico. |
| 1.1 | 8 de octubre de 2026 | Alineación con el documento de tesis (ADR-0004): el requerimiento formal sigue el formato del Anexo A; el artefacto del arquitecto pasa a llamarse especificación de diseño; los RNF adoptan los nombres de ISO/IEC 25010:2023; se agrega el RF-38 (aprobación humana final), el RNF-09 pasa a tres puntos de control y los requerimientos aprobados se entregan también al agente tester. |

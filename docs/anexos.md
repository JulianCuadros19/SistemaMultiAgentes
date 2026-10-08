# Anexos A y B del documento de tesis

Transcripción de los Anexos A y B y de la Tabla 24 del documento de tesis
(`Confirmar_informacion_y_anexos.pdf`, versión del 2026-10-08). El PDF se conserva solo en
local, en `docs/anexos/`, y no se versiona. Esta transcripción es la referencia de los esquemas
de datos del sistema (`src/multiagente/core/esquemas/`).

El Anexo B se titula aquí «especificación de diseño», término adoptado por el equipo en el
ADR-0004. El PDF todavía lo nombra «contrato de diseño».

## Anexo A · Formato para definición de requerimientos del agente

El formato en el que el agente elicitador (llamado «recopilador» en el anexo) entrega su
salida para revisión. Se compone de dos tablas complementarias: el backlog de historias de
usuario y la ficha de detalle de cada requerimiento funcional. Ambas plantillas se
construyeron a partir del formato real del proyecto de referencia de la plataforma Eduka+IA.

### Tabla 27 · Formato de backlog de historias de usuario

| No. | COMO (rol) | QUIERO (verbo en infinitivo) | PARA (objetivo buscado) |
|---|---|---|---|
| 1 | Profesor | Cargar un PDF con los mapas conceptuales de mi clase e indicar el nombre del grupo y la franja horaria. | Iniciar el proceso de evaluación de forma sencilla. |
| 2 | Profesor | Ver el estado actual del proceso de evaluación mientras ocurre. | Saber en qué etapa se encuentra sin necesidad de recargar la página. |
| 3 | Profesor | Que el sistema identifique automáticamente a cada estudiante a partir de su mapa conceptual. | No tener que ingresarlos manualmente. |
| 4 | Profesor | Que el sistema analice cada mapa conceptual y detecte sus conceptos y palabras de enlace. | Que la evaluación se base en la estructura real del mapa. |
| 5 | Profesor | Ver los resultados de la evaluación de cada estudiante con su puntaje por criterio y la retroalimentación generada. | Tomar decisiones informadas sobre el desempeño de mi clase. |
| 6 | Profesor | Visualizar estadísticas generales de mis grupos en un dashboard. | Tener una visión rápida del desempeño y estado de mis evaluaciones. |
| 7 | Profesor | Visualizar los resultados generales de la evaluación de un grupo. | Analizar el desempeño global de mis estudiantes. |
| 8 | Profesor | Visualizar el detalle de la calificación por criterio de cada estudiante. | Entender el desempeño individual en la rúbrica. |
| 9 | Profesor | Cambiar mi contraseña mediante verificación OTP. | Garantizar la seguridad de mi cuenta. |
| 10 | Profesor | Visualizar y gestionar mis grupos de estudiantes dentro de la plataforma. | Organizar las evaluaciones y consultar los resultados por grupo de manera eficiente. |
| 11 | Profesor | Contar con una guía inicial paso a paso dentro de la aplicación. | Entender cómo usar el sistema correctamente desde mi primer ingreso. |

*Fuente: proyecto de referencia de la plataforma Eduka+IA.*

Las historias 3 y 4 no inician el QUIERO con verbo en infinitivo. La regla de redacción se
verifica como atributo de calidad (RF-07), no como restricción del formato.

### Tabla 28 · Formato de detalle de requerimiento funcional

| Sección | Campo | Valores o contenido |
|---|---|---|
| Identificación | ID requerimiento | `RF-` y numeración, p. ej. RF-01 |
| | Versión | Inicia en 0.1 |
| | Proyecto | |
| | Tipo de solicitud | Corrección, ajuste, adicional o nuevo |
| | Impacto de la solicitud | Alto, medio o bajo |
| | Módulo | |
| | Riesgo | |
| | Autor | |
| | Área funcional | |
| | Funcional responsable | |
| Título | COMO / QUIERO / PARA | Historia de usuario del requerimiento |
| Descripción | Precondición | |
| | Regla de negocio | |
| | Datos de entrada | |
| | Datos de salida | |
| Criterios de aceptación | ID escenario | ESC-01, ESC-02, ESC-03… |
| | Descripción | DADO QUE / CUANDO / ENTONCES |
| Cierre | Prioridad | |
| | Requerimiento relacionado | |

### Tabla 24 · Ejemplo del RF-27 diligenciado en el formato del Anexo A

Ejemplo presentado en el capítulo 2 del documento de tesis.

| Campo | Contenido |
|---|---|
| ID requerimiento | RF-27 |
| Versión | 1.0 |
| Proyecto | Sistema multiagente de IA para la empresa Realtix |
| Tipo de solicitud | Nuevo |
| Impacto de la solicitud | Alto |
| Módulo | Orquestador y flujo iterativo |
| Riesgo | Medio |
| Autor | Equipo del proyecto |
| Área funcional | Orquestación del flujo de trabajo |
| Funcional responsable | Equipo técnico de Realtix |
| Título | Como analista del equipo técnico, quiero que el ciclo entre el agente desarrollador y el agente tester se cierre cuando el código apruebe todos los criterios o se detenga tras un número máximo de intentos, para evitar ciclos de corrección indefinidos y escalar a una persona los casos que el sistema no logre resolver. |
| Precondición | Existe un veredicto del agente tester para la versión vigente del módulo. |
| Regla de negocio | El número máximo de iteraciones es configurable, con un valor por defecto de tres. Al alcanzarlo, el caso se marca como «requiere intervención humana». |
| Datos de entrada | Veredicto por criterio, número de la iteración actual y límite configurado. |
| Datos de salida | Decisión de enrutamiento, que cierra el flujo o devuelve el control al desarrollador con la retroalimentación, y estado actualizado de la sesión. |
| ESC-01 · Cierre por aprobación | DADO QUE el módulo aprueba todos los criterios, CUANDO el nodo de decisión evalúa el veredicto, ENTONCES cierra el flujo y marca el módulo como validado. |
| ESC-02 · Devolución para corrección | DADO QUE el módulo incumple al menos un criterio y no se ha alcanzado el límite, CUANDO el nodo de decisión evalúa el veredicto, ENTONCES devuelve el control al desarrollador con la retroalimentación estructurada. |
| ESC-03 · Escalamiento por límite de iteraciones | DADO QUE el módulo falla tras el número máximo de iteraciones, CUANDO se alcanza el límite, ENTONCES el caso se marca como «requiere intervención humana» y el flujo se detiene de forma controlada. |
| Prioridad | Alta |
| Requerimiento relacionado | RF-19, RF-21, RF-24 y RF-26 |

*Fuente: elaboración propia con base en el formato del Anexo A.*

## Anexo B · Formato de la especificación de diseño del agente arquitecto

La especificación de diseño es el artefacto que produce el agente arquitecto y la entrada única
del agente desarrollador. Al ser estructurada y validable contra esquema, permite que el agente
tester verifique de forma determinística la conformidad entre el código y el diseño aprobado.

### Tabla 29 · Estructura de la especificación de diseño

| Campo | Obligatorio | Descripción |
|---|---|---|
| Identificador de la especificación | Sí | Código único de la especificación dentro del proyecto. |
| Versión | Sí | Versión de la especificación, que se incrementa en cada revisión. |
| Arquitectura base | Sí | Identificador de la arquitectura seleccionada del catálogo de referencia. |
| Requerimientos cubiertos | Sí | Lista de identificadores de los requerimientos que el módulo implementa. |
| Módulos | Sí | Para cada módulo: nombre, ruta, responsabilidad, capa y requerimientos asignados. |
| Interfaces públicas | Sí | Para cada interfaz: nombre, tipo, firma completa, descripción y excepciones previstas. |
| Dependencias permitidas | Sí | Módulos que cada módulo puede importar. Su omisión implica que no puede importar ninguno. |
| Modelo de datos | Sí | Entidades con sus campos, tipos, obligatoriedad y restricciones de dominio. |
| Dependencias externas | Sí | Librerías del catálogo tecnológico autorizado que se emplearán, con su propósito. |
| Reglas de dependencia | Sí | Enunciado de las restricciones estructurales que el código debe respetar. |

*Fuente: elaboración propia.*

### Validaciones antes de habilitar la generación de código

1. Conformidad con el esquema y ausencia de dependencias circulares.
2. Todo requerimiento aprobado queda asignado al menos a un módulo.
3. Las dependencias externas declaradas pertenecen al catálogo tecnológico autorizado.

El Anexo B no incluye un ejemplo diligenciado. El ejemplo de referencia está en
`knowledge_base/arquitecturas_referencia/02-especificacion-de-diseno.md`.

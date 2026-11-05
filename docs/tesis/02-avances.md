# Avances que el documento todavía no recoge

Corte: 4 de noviembre de 2026, al cierre del paso 14. La versión del documento del 4 de noviembre
cuenta el desarrollo hasta el ADR-0014: las interfaces, la verificación con el equipo y la corrida
de 3 casos tras los ajustes de robustez. Falta lo que vino después. El paso 15 está en
`05-evaluacion-paso-15.md`.

**Contenido de este archivo:**
- **Secciones 2 a 6:** material de redacción, con las cifras exactas. El documento lo redacta con
  su propio estilo.
- **Sección 7:** las entradas nuevas del Anexo D, en el formato de la Tabla 34.
- **Sección 8:** lo pendiente.

Toda cifra está también en `03-cifras.md`, con su fuente.

## 1. Dónde va cada cosa

| Avance | Ubicación sugerida |
|---|---|
| Corrida ampliada de línea base (sección 2) | Capítulo 5, como nivel nuevo del plan de pruebas y punto de partida de la evaluación |
| Calidad de la primera salida y enmiendas (sección 3) | Capítulo 4, sección nueva después de la 4.10; sus resultados, en los capítulos 5 y 6 |
| Control de costo y traza por nodo (sección 4) | Capítulo 4, sección nueva |
| Entrega en contenedores con Azure OpenAI (sección 5) | Capítulo 4, sección nueva, antes de «Producto obtenido» |
| Ajustes de las interfaces (sección 6) | Sección 4.9 |
| ADR-0015, ADR-0016 y ADR-0017 (sección 7) | Tabla 21 de la sección 4.3 y Tabla 34 del Anexo D |
| Paso 15 (sección 8) | `05-evaluacion-paso-15.md` indica dónde va cada parte |

## 2. Corrida ampliada de línea base (ADR-0014, 31 de octubre de 2026)

**Por qué se hizo.** Tres casos no bastaban para saber cómo se comportaba el sistema con
necesidades variadas.

**Método:**
- **Casos:** 20 casos sintéticos nuevos, de 3 a 4 por arquitectura del catálogo. Cubren temas de
  arrendamiento, crédito, recaudo, catastro, inventario, archivos y eventos, sin datos de Realtix.
- **Arquitectura esperada:** cada caso la declara. El cliente simulado no la ve y el arquitecto
  elige por su cuenta.
- **Cliente:** simulado por un modelo de lenguaje.
- **Analista simulado** (ADR-0013):
  - en N6 rechaza una vez con los defectos escalados y luego aprueba;
  - en N9 aprueba una especificación sin errores;
  - en N17 aprueba lo que aprobó el tester.

**Resultados:**
- **Desenlaces:** 18 de 20 módulos validados, 10 en la primera versión y 8 en la segunda. Además, 1
  sesión escaló en N17 (caso 19) y 1 quedó en pausa en N6 (caso 18). Ninguna sesión se detuvo y
  ninguna llamada dio error.
- **Arquitectura:** el arquitecto eligió la esperada en los 19 casos que llegaron al diseño, y se
  usaron las seis arquitecturas. La dirigida por eventos (ARQ-06) se usó por primera vez.
- **Tiempo del sistema:** media de 4,6 min y máximo de 9,0 min.
- **Diálogo:**
  - el turno más largo midió 9,4 s;
  - el cierre de la elicitación, que incluye la síntesis, pasó de 30 s en 5 casos, con un máximo
    de 104 s.
- **Costo:**
  - 0,282 USD de media por módulo validado, de 0,161 a 0,490;
  - del costo del sistema (5,89 USD), N10 llevó el 45,7 %, N8 el 22,1 %, N3 el 17,8 %, N5 el 13,8 %
    y N14 el 0,5 %;
  - la corrida costó 6,51 USD con el cliente simulado, en 745 llamadas.
- **Hallazgos:**
  - el desarrollador falló la verificación estructural en 7 de 29 primeros intentos;
  - la causa principal de los rechazos de la primera versión fue CAL-FS-001, «la prueba pasa, pero
    no verifica el escenario», en 5 casos.

## 3. Calidad de la primera salida y enmiendas (ADR-0015, 3 y 4 de noviembre de 2026)

### 3.1 Problema

La corrida de línea base y tres sesiones del equipo mostraron que la primera salida del sistema
solía necesitar correcciones.

**Sesiones del equipo:**
- **Predial:** el tester aprobó la primera versión, pero los dos ciclos de la revisión final vinieron
  de reglas que el cliente no había dicho. Esas reglas quedaron en el código, no en los
  requerimientos exportados.
- **Pensiones:**
  - tres diseños seguidos pasaron N9 sin que sus escenarios pudieran ejecutarse con interfaces
    públicas;
  - el juez aceptó pruebas que fabricaban el estado que debían verificar;
  - tras cada rediseño, el desarrollador generaba desde cero.

**Causas raíz:**
1. Requerimientos sin casos límite.
2. Diseños cuyos escenarios no eran ejecutables.
3. Pruebas que simulaban el efecto del módulo en lugar de verificarlo.

### 3.2 Decisiones del equipo

1. **Mejoras con evidencia.** Pulir a los agentes reproduciendo cada hallazgo con una prueba o un
   caso antes de corregirlo, y medirlo después.
2. **Casos límite en la elicitación.** El elicitador los explora antes del resumen, sin romper la
   convergencia del diálogo.
3. **Reglas nuevas en N17 como enmienda.** Una regla descubierta en la validación final entra a los
   requerimientos por el elicitador, como una enmienda.
   - Así, solo N5 y N6 escriben requerimientos y solo cinco nodos usan modelo.
   - La arquitectura aprobada cambia: N17 gana un destino y N16 una arista hacia N10.
4. **Criterios fijados antes de medir,** sobre la corrida de 20 casos (sección 3.5).

### 3.3 Cambios por agente

**Tester (fase 2):**
- **N12** detecta de forma determinista las pruebas que simulan el efecto del módulo (regla nueva
  CAL-FS-006). Con ella, la colección de criterios pasó a 52 fragmentos y el corpus, a 187.
- **El juez de N14:**
  - ve las interfaces y el modelo de datos de la especificación;
  - confirma cada rechazo con una segunda opinión;
  - solo hace una llamada más cuando rechaza.
- **Medición** sobre un corpus ampliado a 21 defectos y 3 controles, en 3 corridas: detectó 63 de
  63 defectos y aprobó 9 de 9 controles, por 0,037 USD.
- **Rejuzgamiento:** las 49 versiones reales guardadas, juzgadas otra vez, coincidieron con su
  veredicto original en 40 casos. Además, se atrapó un falso positivo anterior y se corrigieron tres
  rechazos falsos.

**Arquitecto (fases 3 y 4):**
- **N8** declara el recorrido de cada escenario de aceptación: cómo se prepara, se ejecuta y se
  observa con interfaces públicas.
- **N9:**
  - verifica que cada escenario sea ejecutable;
  - rechaza tipos imprecisos como `callable` y `any`;
  - desde la fase 7, rechaza `self` y `cls` en las funciones de módulo.
- **Métodos:** se declaran como interfaces `Clase.metodo`, sin cambiar el Anexo B.
- **Revisiones:** si el revisor deja observaciones, el registro de decisión gana una revisión con la
  respuesta y los cambios.
- **Medición:** con el prompt 1.5, 12 de 12 primeros diseños fueron válidos, sin reintentos, a
  0,0997 USD por diseño.

**Desarrollador (fase 4):**
- escribe una prueba por escenario siguiendo su recorrido;
- antes de entregar, verifica el estilo que rechazaría el tester;
- tras un rediseño, parte de la versión anterior y de la retroalimentación que lo motivó.
- **Rediseño real:** N17 devolvió el módulo al arquitecto para pedir una consulta nueva. La
  versión 2 conservó intacto el archivo de pruebas que no cambiaba, modificó solo los módulos que
  tocaba el rediseño y declaró atendida la observación.

**Elicitador (fase 5):**
- **Casos límite:** antes del resumen, pregunta por los casos límite de las reglas capturadas, hasta
  tres y cada uno de un patrón distinto, y una vez por algo más.
- **Límite de turnos:** pasó de 15 a 18.
- **Registro:** guarda los casos especiales acordados, los ejemplos con cifras y los demás usuarios.
- **Resumen:** muestra el tipo y la obligatoriedad de un dato solo si el cliente los dijo.
- **N6:**
  - corrige lo corregible aunque haya preguntas abiertas;
  - exige al menos tres escenarios por requerimiento.
- **Medición:** en casos con reglas ocultas, el elicitador capturó 1,33 de 3 de media por caso, por
  debajo de la meta de 2. El equipo lo aceptó.

### 3.4 Enmiendas desde la validación final (fase 6, RF-39)

**Cuándo aplica.** Si la persona descubre en N17 una regla que los requerimientos no tienen, pide
una enmienda.

**Recorrido:**
1. **N5:** el elicitador incorpora la regla a los requerimientos vigentes sin agregar, quitar ni
   renumerar requerimientos ni escenarios, y sube de versión los que cambian. Usa el prompt
   `elicitador.enmienda` 1.0.
2. **N6:**
   - verifica los requerimientos enmendados y el analista los aprueba o los rechaza con
     observaciones;
   - los defectos que el analista ya había aceptado no vuelven a N5, porque no los causó la
     enmienda.
3. **N16:** rehace el plan de pruebas.
4. **N10:** el desarrollador corrige el módulo con el mismo diseño, en un ciclo de corrección
   nuevo.

**Registro.** La enmienda queda registrada con quién la pidió, su texto, las observaciones del
analista y la versión de cada requerimiento enmendado.

**Cambios en los requerimientos (versión 1.2):**
- el RF-39;
- el rechazo del RF-38, que admite tres destinos;
- el RNF-09, que lleva la enmienda al elicitador.

**Verificación.** En la prueba con costo, el requerimiento subió a la versión 0.2 con la regla y su
escenario, y el módulo corregido salió aprobado, por 0,20 USD.

### 3.5 Corrida final (fase 7, 4 de noviembre de 2026)

**Condiciones:** los mismos 20 casos y la misma política del analista que la línea base, con los
prompts vigentes.

**Desenlaces:**
- **Validación:** los 20 módulos quedaron validados, 18 en la primera versión y 2 en la segunda,
  ambos por CAL-FS-001. Ninguna sesión escaló ni se detuvo.
- **Arquitectura:** el arquitecto eligió la esperada en 19 de 20 casos. En el caso 01 eligió la de
  línea de comandos (ARQ-05) en lugar de la de capas, y su registro lo justificó: el cliente dijo
  que solo lo usaba una persona al cierre de mes.

**Tiempos:**
- **Por módulo:** media de 5,3 min y máximo de 13,2 min (caso 18), frente al límite de 20.
- **Diálogo:** el turno más largo midió 9,4 s, frente al límite de 15.
- **Cierre de la elicitación:** pasó de 30 s en 3 casos, con un máximo de 51 s.

**Costo:**
- **Por módulo validado:** media de 0,342 USD, de 0,180 a 0,871.
- **Reparto del costo del sistema:** 6,85 USD, de los que N10 llevó el 40,8 %, N8 el 27,5 %, N3 el
  20,5 %, N5 el 10,8 % y N14 el 0,4 %.
- **Total de la corrida:** 7,59 USD con el cliente simulado, en 866 llamadas y 2 h 1 min de reloj.

| Criterio, fijado antes de medir | Meta | Línea base | Final | ¿Cumple? |
|---|---|---|---|---|
| Validados en la primera versión | al menos 15 de 19 | 10 de 19 | 18 de 20 | sí |
| Primeros intentos de N10 rechazados | como máximo 2 de 29 | 7 de 29 | 7 de 23 | no |
| Sesiones escaladas | 0 | 1 | 0 | sí |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,28 | 0,342 | sí, al límite |
| Falsos positivos de «prueba que simula» | 0 | — | 0 | sí |
| Turnos sin exploración, en la primera pausa de N6 | como máximo 211 | 211 | 210 | sí, al límite |
| Resúmenes confirmados | al menos 17 de 20 | 17 | 16 | no |

### 3.6 Criterios sin cumplir y decisiones finales

**Primeros intentos de N10 rechazados: 7 de 23.** El reintento corrigió 6. Las causas fueron:
- **Respuesta incompleta, en 3 casos:** el modelo devolvió un archivo de pruebas de relleno.
- **Funciones con `self` declaradas por el arquitecto, en 2 casos.**
- **Estilo, en 2 casos:** el desarrollador ya lo detecta antes de entregar, y le cuesta un reintento
  en lugar de un ciclo del tester.

**Resúmenes confirmados: 16 de 20.**
- en dos casos el resumen afirmaba una obligatoriedad que el cliente no había dicho;
- en uno, el cliente respondía «no aplica» y el diálogo insistía;
- en otro, lo que el cliente pedía en los resultados quedaba en las reglas.

**Decisión del equipo:** cerrar el paso con los dos criterios sin cumplir y aplicar, sin una corrida
nueva, tres correcciones deterministas:
- **Decisión 37:** N9 rechaza `self` y `cls` en las funciones de módulo.
- **Decisión 38:** el resumen solo muestra la obligatoriedad si el cliente la dijo sin negarla.
- **Decisión 39:** «no aplica» al comienzo de una respuesta cuenta como no saber.

**Estado de esas correcciones:** quedaron sin medir. Las verifican las pruebas sin costo y su
aplicación, sin modelo, a las sesiones guardadas de la corrida.

### 3.7 Pendientes que dejó

- **Respuesta incompleta de N10:** se dio en 3 de 23 primeros intentos.
- **Lo que el cliente pide en los resultados:** la extracción lo deja en las reglas.
- **Necesidades de eventos:** se plantean como «publicar un aviso».
- **Costo por módulo:** quedó al borde de la meta, empujado por los casos de eventos (de 0,33 a 0,87
  USD).

## 4. Control de costo y traza por nodo (ADR-0016, 4 de noviembre de 2026)

**Qué exigían los requerimientos:**
- **RNF-10:** un presupuesto por módulo que detenga la ejecución al superarse.
- **RF-34:** que la traza de cada ejecución muestre los prompts, tokens, costos y tiempos por nodo.

Antes de este paso, el costo de cada llamada quedaba solo en un archivo y nada sumaba el costo
acumulado de la sesión.

**Decisiones del equipo:**
1. **La traza va a tablas propias de PostgreSQL,** y Langfuse sale del stack. Su versión
   autoalojada exigía cinco contenedores más (web, worker, ClickHouse, Redis y MinIO), y las tablas
   cubren el RF-34.
2. **El presupuesto por módulo es de 1,50 USD por defecto.** Cubre con holgura el máximo de la
   corrida final (0,87 USD) y la sesión del equipo con más devoluciones (0,97 USD).
3. **Pausa por presupuesto.** Al alcanzarlo, la sesión pausa. Una persona lo amplía, y queda
   registrado quién, cuánto, cuándo y por qué, o cierra la sesión.

**Implementación:**
- **Costo:** cada nodo corre envuelto y suma a la sesión el costo de sus llamadas al modelo.
- **Comprobación:** antes de cada nodo con modelo (N3, N5, N8, N10 y N14) se comprueba el
  presupuesto. Por eso el exceso queda acotado a un nodo: el más caro de la corrida final, N10,
  costó hasta 0,20 USD.
- **Traza:** queda en dos tablas nuevas:
  - `ejecuciones`, una fila por nodo, con su inicio, duración, costo y error;
  - `llamadas_modelo`, una fila por llamada, con el prompt y su versión, el modelo, los tokens con
    los de razonamiento y caché, el costo exacto y la latencia.

  No guarda el contenido de los mensajes, que ya está en los puntos de control.
- **Consulta:** con `multiagente traza ID` o en la página «Traza por nodo» de la web.

**Verificación:**
- **Presupuesto:** una sesión real con el elicitador y un presupuesto de 0,005 USD. La primera
  ejecución de N3 costó 0,0079 USD, y la sesión se detuvo antes de volver a llamar al modelo.
  Ampliado el presupuesto, siguió.
- **Traza:** trajo por nodo los prompts con su versión, los tokens, el costo y los tiempos.
- **Duración y costo:** 65 s y 0,011 USD.
- **Pruebas sin costo:** 741 unitarias, 34 de integración, 19 de embeddings y 33 del entorno
  aislado.

**Límites:**
- **Exceso acotado a un nodo:** el presupuesto se comprueba antes de cada nodo con modelo, no antes
  de cada llamada.
- **Fallas de infraestructura:** si un nodo falla por esa causa, su costo queda en la traza, pero no
  suma al acumulado.
- **N3:** la ampliación se registra cuando el cliente responde.

## 5. Entrega en contenedores con Azure OpenAI (ADR-0017, 4 de noviembre de 2026)

### 5.1 Decisión del equipo

**De dónde salía el modo local.** Los textos aprobados del paso 14 pedían una entrega capaz de
operar sin proveedores de nube, con modelos de lenguaje locales:
- el RF-37 y el RNF-06;
- la vista de despliegue, con un servicio de inferencia local y dos modos de operación;
- el plan de trabajo.

El código nunca los usó: desde el paso 3, todos los nodos con modelo llaman a Azure OpenAI.

**Lo que decidió el equipo:**
- **Modelos de lenguaje:** Azure OpenAI es el único proveedor. No se usan modelos locales ni de
  pesos abiertos.
- **BGE-M3** sigue local. No es un modelo de lenguaje: convierte el corpus y las consultas en
  vectores. Lo exige el RNF-04.

**Documentos corregidos:**
- **Requerimientos 1.3:** el RF-37 y su criterio, el RNF-06 y la restricción de operar sin nube.
- **Arquitectura 1.5:** embeddings, identificadores de modelo, despliegue, seguridad, Tablas 6 y 7
  y criterio de aprobación.
- **Plan de trabajo:** el paso 14 pasó a «Empaquetado en contenedores». Termina cuando, desde un
  clon limpio, la composición levanta el sistema completo y un módulo sale validado con los modelos
  de Azure OpenAI.

### 5.2 Implementación

**Imagen de la aplicación:**
- **Base:** Python 3.14.4, con versión y digest fijados.
- **Versiones exactas:** las dependencias se instalan con las versiones del entorno donde pasan las
  pruebas.
- **Docker:** trae la CLI de Docker, para crear el entorno aislado.
- **Fuera de la imagen:** no entran secretos, datos locales ni el PDF de la tesis.
- **Sin registro:** se construye en la máquina donde corre y no se publica en ningún registro,
  porque lleva el corpus.

**Composición:** un solo comando, `docker compose up -d --build --wait`, hace todo esto:
1. descarga y verifica el modelo de representaciones vectoriales;
2. construye las imágenes de la aplicación y del entorno aislado, y comprueba la segunda;
3. migra la base e indexa las bases de conocimiento;
4. levanta la web en `http://127.0.0.1:8000/`.

**Uso del sistema:**
- **Consola:** corre en otro contenedor de la misma imagen.
- **Imágenes descargadas:** quedan fijadas por versión y digest.

**Decisiones que habían quedado para este paso:**
- **Acceso a Docker:**
  - la aplicación usa el socket de Docker del anfitrión;
  - el entorno aislado no cambia: contenedor hermano, efímero, sin red, de solo lectura y sin root;
  - se descartó Docker dentro de Docker porque exige un contenedor privilegiado.
- **Web:** sigue sin autenticación y solo responde en la máquina. El acceso remoto con TLS y
  autenticación queda como trabajo futuro.

**Usuario sin root:**
- Al arrancar, la aplicación toma el usuario dueño de la carpeta de datos compartida y el grupo del
  socket de Docker. Así, los archivos quedan a nombre de la persona.
- No hay identificadores que configurar.

### 5.3 Verificación (condición de terminado del paso 14)

**Clon limpio,** con volúmenes nuevos y otro nombre de proyecto:
- se descargó y verificó el modelo y se migró la base;
- se indexaron los 36 documentos en 42,7 s;
- la aplicación quedó sana en unos 5 minutos;
- la web respondió desde Ubuntu y desde Windows.

**Sesión real dentro del contenedor,** con Azure OpenAI y el analista simulado de las corridas
medidas:
- el caso 05 salió validado en la validación final en la primera versión;
- sus 46 pruebas pasaron en el entorno aislado;
- tomó 3,7 min y costó 0,245 USD.

**Interfaces sobre esa sesión:**
- **Web:** mostró la sesión y su traza y exportó el módulo, de 13 archivos.
- **Consola en contenedor:** la listó, la exportó a la carpeta compartida a nombre de la persona y
  mostró su traza: 51 ejecuciones de nodos y 30 llamadas.

**Costo total:** 0,40 USD por las dos sesiones de la verificación, cliente simulado incluido.

**Pruebas sin costo, al cierre de ese paso:** 754 unitarias, 34 de integración, 19 de embeddings y 33 del entorno
aislado, en total 840. Una prueba nueva protege lo que promete la composición:
- puertos solo locales;
- direcciones internas;
- secretos fuera de la imagen;
- imágenes fijadas.

**Resultado inesperado.** La construcción sin caché de la imagen del entorno aislado falló una vez,
a los 998 s, mientras descargaba de PyPI a unos 17 KB/s. Repetida, terminó en 1.958 s: se atribuyó
a la red, y basta repetir el comando.

**Límites:**
- **Docker Desktop:** el sistema se verificó en Windows con Docker Desktop y WSL2; macOS no se
  verificó.
- **Código del sistema:** va dentro de la imagen, así que cada cambio exige reconstruirla.
- **Fuera de la composición:** el sistema no opera sin conexión con Azure OpenAI, y depende de su
  cuota, su disponibilidad y el retiro de versiones.

## 6. Ajustes de las interfaces posteriores a la sección 4.9

**Del ADR-0014, después de la versión que recoge el documento:**
- un solo detector de secretos, con criterio de valor;
- el historial lista solo las versiones dictaminadas;
- la extracción retira lo que el cliente rechaza;
- el rol es quien obtiene el valor, y la funcionalidad es lo que se pide construir;
- lo que el cliente no sabe se pregunta dos veces, no sin fin;
- la prioridad y las condiciones del cliente entran al registro;
- el detalle de una falla sale de las líneas que marca pytest;
- el sistema escribe las secciones de requisitos, instalación y pruebas de `USO.md`;
- `requirements.txt` fija también las dependencias transitivas;
- una sesión en curso no se reanuda ni se cierra a la vez, gracias a un bloqueo por sesión en
  PostgreSQL.

**Del ADR-0015:**
- la revisión final ofrece pedir una enmienda;
- la página de la sesión muestra las enmiendas y los requerimientos enmendados con su versión;
- la trazabilidad suma una sección de enmiendas.

**Del ADR-0016:**
- la pausa por presupuesto, en la consola y en la web, con su formulario de ampliación y el cierre;
- el gasto y el presupuesto en el panel, en la lista de sesiones y en la trazabilidad;
- el comando `multiagente traza ID` y la página «Traza por nodo»;
- el cliente, mientras tanto, ve que el equipo revisará su caso.

**Del ADR-0017:**
- **Web:** `docker compose up -d --build --wait` y luego `http://127.0.0.1:8000/`.
- **Consola:** `docker compose run --rm aplicacion multiagente …`.
- **Archivos:** las exportaciones y las pruebas propias que se indican por ruta van en la carpeta
  compartida `data/local`. La web recibe las pruebas propias como archivo adjunto y exporta el
  módulo como `.zip`.

## 7. Entradas nuevas del Anexo D (formato de la Tabla 34)

### ADR-0015. Calidad de la primera salida y enmiendas de los requerimientos desde N17

**Estado y fecha.** Aceptada el 03/11/2026 y cerrada el 04/11/2026. Modificó los registros
ADR-0006, ADR-0008, ADR-0010, ADR-0011, ADR-0012, ADR-0013 y ADR-0014.

**Contexto y problema:**
- **Línea base:** en la corrida de 20 casos, solo 10 de 19 módulos se validaron en la primera
  versión, y el desarrollador falló la verificación en 7 de 29 primeros intentos.
- **Sesiones del equipo:**
  - reglas que el cliente no dijo aparecían recién en la revisión final y no entraban a los
    requerimientos;
  - los diseños pasaban la aprobación sin escenarios ejecutables;
  - el juez aceptaba pruebas que fabricaban el estado que debían verificar.

**Opciones consideradas** para la regla nueva de la revisión final:
- A. La lleva el elicitador: N17 envía la regla a N5, N6 la aprueba, N16 rehace el plan y N10
  corrige.
- B. La persona la escribe en N17 y el código la agrega al requerimiento sin modelo.
- C. Solo mejorar el elicitador.

**Decisión:**
- **Regla nueva:** se eligió la opción A, porque mantiene que solo N5 y N6 escriban requerimientos
  y que solo cinco nodos usen modelo.
- **Pulido por agente,** reproduciendo cada hallazgo antes de corregirlo:
  - **tester:** detecta las pruebas que simulan el efecto (CAL-FS-006) y confirma cada rechazo con
    una segunda opinión;
  - **arquitecto:** declara el recorrido ejecutable de cada escenario y los métodos como
    `Clase.metodo`, y N9 los verifica;
  - **desarrollador:** sigue los recorridos, se adelanta al estilo del tester y, tras un rediseño,
    parte de la versión anterior;
  - **elicitador:** pregunta por los casos límite antes del resumen, con un límite de 18 turnos.
- **Requerimientos:** se agregó el RF-39 y el rechazo del RF-38 admite tres destinos.

**Consecuencias:**
- **Favorables:**
  - lo que se agrega en la revisión final queda en los requerimientos y se prueba;
  - la primera versión pasa al tester mucho más a menudo;
  - ninguna sesión escala.
- **Desfavorables:**
  - el costo por módulo subió a 0,342 USD, al borde de la meta de 0,35;
  - la elicitación es más larga;
  - dos criterios quedaron sin cumplir: los primeros intentos rechazados del desarrollador y los
    resúmenes confirmados.

**Verificación:**
- **Corrida final de 20 casos:** 20 de 20 módulos validados, 18 en la primera versión, frente a 10
  de 19 en la línea base. Ninguno escaló.
- **Tiempo:** 5,3 min de media y 13,2 como máximo.
- **Costo:** 0,342 USD de media por módulo; la corrida completa, 7,59 USD.
- **Enmienda:** en la prueba con costo, el requerimiento subió a v0.2 y el módulo corregido salió
  aprobado, por 0,20 USD.
- **Pruebas sin costo:** 731 unitarias, 31 de integración, 19 de embeddings y 33 del entorno
  aislado.

### ADR-0016. Control de costo y traza por nodo

**Estado y fecha.** Aceptada el 04/11/2026. Modificó los registros ADR-0001, ADR-0003, ADR-0006 y
ADR-0014.

**Contexto y problema.** El paso 13 exigía que el presupuesto detuviera una ejecución que lo
superara (RNF-10) y que la traza de cada ejecución mostrara los prompts, tokens, costos y tiempos
por nodo (RF-34). El costo de cada llamada quedaba solo en un archivo, nada sumaba el costo
acumulado de la sesión, y Langfuse figuraba en las dependencias sin usarse.

**Opciones consideradas:**
- **Para la traza:**
  - A. Tablas propias en PostgreSQL.
  - B. Las mismas tablas y Langfuse autoalojado.
  - C. Solo Langfuse.
- **Para la detención:**
  - A. Una pausa por presupuesto.
  - B. Detener la sesión como una falla.

**Decisión.** Se eligió la opción A en ambos casos. Langfuse exigía cinco contenedores más y las
tablas cubren el RF-34.
- **Presupuesto:** 1,50 USD por módulo por defecto. Se comprueba antes de cada nodo con modelo.
- **Ampliación:** al alcanzarlo, la sesión pausa hasta que una persona lo amplía, con registro de
  quién, cuánto, cuándo y por qué, o la cierra.
- **Traza:** queda en las tablas `ejecuciones` y `llamadas_modelo`, consultables desde la consola y
  la web.

**Consecuencias:**
- **Favorables:**
  - ninguna sesión gasta sin límite;
  - el costo, el prompt y el tiempo de cada nodo quedan consultables por sesión, sin servicios
    externos.
- **Desfavorables:**
  - no hay una interfaz de exploración como la de Langfuse;
  - el exceso queda acotado a un nodo y no a una llamada;
  - el costo de un nodo que falla por infraestructura no suma al acumulado.

**Verificación:**
- **Sesión real con un presupuesto de 0,005 USD:** se detuvo antes de que N3 volviera a llamar al
  modelo; ampliado el presupuesto, siguió.
- **Traza:** trajo por nodo los prompts, tokens, costo y tiempos.
- **Duración y costo:** 65 s y 0,011 USD.
- **Pruebas sin costo:** 741 unitarias, 34 de integración, 19 de embeddings y 33 del entorno
  aislado.

### ADR-0017. Entrega en contenedores con Azure OpenAI

**Estado y fecha.** Aceptada el 04/11/2026. Modificó los registros ADR-0001, ADR-0002, ADR-0003,
ADR-0007, ADR-0011, ADR-0014 y ADR-0016.

**Contexto y problema:**
- **Lo que pedían los textos aprobados:** el paso 14 pedía operar sin proveedores de nube, con
  modelos de lenguaje locales (RF-37 y RNF-06). El código nunca los había usado.
- **Lo que quedaba por decidir:**
  - cómo accede a Docker la aplicación en contenedor;
  - si la web se abre a acceso remoto.

**Opciones consideradas:**
- **Para Docker:**
  - A. El socket del anfitrión.
  - B. Docker dentro de Docker, privilegiado.
  - C. La aplicación fuera de contenedores.
- **Para la web:**
  - A. Solo en la máquina, sin autenticación.
  - B. Acceso remoto con TLS y autenticación.

**Decisión:**
- **Modelos:** el equipo fijó Azure OpenAI como único proveedor de modelos de lenguaje. BGE-M3 sigue
  local, por el RNF-04.
- **Documentos:** se corrigieron el RF-37, el RNF-06 y la arquitectura.
- **Docker y web:** se eligió la opción A en ambos casos. La B de Docker exige un contenedor
  privilegiado y la C no cumple el RF-37.
- **Composición:** un solo comando construye las imágenes, descarga el modelo, migra, indexa y
  levanta la web. La aplicación corre sin root, con el dueño de la carpeta de datos y el grupo del
  socket.

**Consecuencias:**
- **Favorables:**
  - el código de los nodos no cambió;
  - el despliegue se simplificó, sin servidor de inferencia ni GPU.
- **Desfavorables:**
  - el sistema depende de la cuota, la disponibilidad, las versiones y el costo de Azure OpenAI;
  - los prompts se procesan en Azure;
  - el contenedor de la aplicación accede al Docker del anfitrión.

**Verificación:**
- **Clon limpio:** con volúmenes nuevos, la composición levantó el sistema completo.
- **Sesión real en contenedores:** un caso salió validado en la primera versión, por 0,245 USD.
- **Interfaces:** la web y la consola mostraron la sesión, su traza y su exportación.
- **Costo total:** 0,40 USD.
- **Pruebas sin costo:** 754 unitarias, 34 de integración, 19 de embeddings y 33 del entorno
  aislado.

### Ajustes a las entradas existentes del Anexo D

En «Estado y fecha», agregar quién modificó cada registro después:

| Registro | Agregar |
|---|---|
| ADR-0001 | Ajustada por el ADR-0016, que retiró Langfuse, y por el ADR-0017, que instala el paquete en la imagen con versiones exactas. |
| ADR-0002 | Ajustada por el ADR-0017: imagen fijada por digest y composición completa. |
| ADR-0003 | Ajustada por el ADR-0016, que suma el costo por nodo y guarda la traza en PostgreSQL, y por el ADR-0017, que dejó a Azure OpenAI como único proveedor. El argumento de los servidores de modelos locales queda sin efecto; la elección de Chat Completions se mantiene. |
| ADR-0006 | Ajustada por el ADR-0015 (enmiendas desde N17 y límite de 18 turnos) y por el ADR-0016 (costo en el estado y pausa por presupuesto). |
| ADR-0007 | Ajustada por el ADR-0015 (regla CAL-FS-006, 187 fragmentos) y por el ADR-0017, que retira el factor de operar sin nube; los embeddings siguen locales por el RNF-04 y por el costo. |
| ADR-0008, ADR-0010, ADR-0012 y ADR-0013 | Ajustadas por el ADR-0015. |
| ADR-0011 | Ajustada por los ADR-0015 y ADR-0017; este da a la aplicación acceso al Docker del anfitrión. |
| ADR-0014 | Ajustada por los ADR-0015, ADR-0016 y ADR-0017; este cierra el acceso remoto: la web sigue solo en la máquina. |

En el texto de las entradas:
- **ADR-0001:** dice que Langfuse entró como dependencia. Conviene una nota: el ADR-0016 lo retiró.
- **ADR-0003:** dice que Chat Completions es «la interfaz que también exponen los servidores de
  modelos locales». Conviene la nota del ADR-0017.

## 8. Paso 15 (fase 4 de la metodología)

**Hecho.** El texto para el documento está en `05-evaluacion-paso-15.md`, y las cifras, en la sección 13 de
`03-cifras.md`:
- la comparación con dos líneas base de un solo modelo de lenguaje, en nueve casos;
- las métricas RAGs, sobre las 20 sesiones de la corrida ampliada;
- la medición de las decisiones 37 a 39 del ADR-0015;
- la matriz del tester frente a las pruebas de referencia;
- el despliegue de demostración en Azure.

**No se hizo, y se presenta como trabajo futuro:**
- la comparación con desarrollo humano;
- el benchmark de modelos en N3 y N5.

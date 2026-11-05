---
estado: aceptada
fecha: 2026-11-05
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0014 (presentación de la web: la sesión por etapas, el panel agrupado, la vista del cliente, los documentos en HTML, la tipografía propia y la huella de los estáticos)
---

# ADR-0018 · Rediseño de la interfaz web por etapas

## Contexto y planteamiento del problema

La web del ADR-0014 cumplía sus funciones, pero cada página era una sola columna plana:
- **Sesión:** mostraba solo la pausa pendiente. En N17 no se veían los requerimientos ni el
  diseño aprobados, y nada indicaba en qué punto del flujo estaba la sesión ni qué faltaba.
- **Panel:** una tabla con todas las sesiones mezcladas, sin separar las que esperan al equipo.
- **Vista del cliente:** el diálogo nombraba al agente, «Elicitador», un término que el cliente
  no tiene por qué conocer.
- **Trazabilidad y traza:** el Markdown se mostraba como texto plano.
- **Tipografía:** la del sistema, que cambia de una máquina a otra.

El equipo pidió un diseño más propio, profesional y limpio, sin excesos y sin cambiar las
funciones. También pidió que los apartados de la sesión no quedaran en una sola página plana.

## Factores de decisión

- Las rutas, los formularios y los textos que validan las pruebas de la web no cambian.
- ADR-0014: la web no carga recursos de terceros, ni de una CDN.
- RNF-08: el cliente lee lenguaje de negocio.
- RNF-09: los tres puntos de control humano deben reconocerse a simple vista.
- WCAG 2.2 AA:
  - contraste de 4,5:1 para el texto;
  - objetivos táctiles (2.5.8);
  - teclado y foco visibles;
  - movimiento reducido.
- Confidencialidad: la interfaz se revisa sin datos de Realtix y sin costo de modelos.

## Opciones consideradas

Para organizar la página de la sesión:
1. Etapas en la misma página, con pestañas que son anclas.
2. Una página por etapa.
3. La página plana, con secciones plegables.

Para la trazabilidad y la traza en HTML:
1. Un conversor propio del Markdown que escriben los generadores.
2. Una biblioteca de Markdown.
3. Plantillas HTML propias, armadas desde el estado.

Para la tipografía:
1. Una familia libre servida por la aplicación.
2. Las fuentes del sistema.

## Resultado de la decisión

### Decisiones del equipo (2026-11-05)

1. **Etapas en la misma página** (opción 1).
   - Una página por etapa multiplica las rutas y pierde el contexto de la sesión.
   - La página plana con secciones plegables sigue siendo larga y no muestra el recorrido.
2. **IBM Plex servida por la aplicación** (opción 1 de la tipografía).
   - Plex Sans 1.1.0, en cuatro pesos, y Plex Mono 2.5.0, en dos, de las publicaciones de IBM.
     Van en `estaticos/fuentes/`, en subconjunto Latin-1 y en WOFF2, y suman unos 120 KB.
   - Su licencia, la SIL Open Font License 1.1, va en `fuentes/OFL.txt`.
   - Las fuentes del sistema cambian según la máquina, y una fuente de terceros cargada desde
     internet contradice el ADR-0014.
3. **«Equipo» en la vista del cliente.** El elicitador se presenta como «Equipo» en la
   conversación del cliente. El equipo lo sigue viendo como «Elicitador» en su página de la sesión
   y en la trazabilidad.

### Decisiones de implementación

4. **La línea del flujo** (`interfaces/web/etapas.py`, `plantillas/sesion.html` y
   `estaticos/etapas.js`).
   - **Etapas:** cinco agrupan los diecisiete nodos:
     - conversación, de N1 a N4;
     - requerimientos, N5 y N6;
     - diseño, de N7 a N9 y N16;
     - desarrollo y pruebas, de N10 a N15;
     - aprobación final, N17.
   - **Marcas:** el círculo marca el trabajo de los agentes y el rombo, los tres puntos de control
     humano.
   - **Estados:** cada etapa queda hecha, actual o pendiente según lo que existe en el estado, no
     según el orden. Tras una enmienda o una devolución desde N17, las etapas siguientes siguen
     hechas.
   - **Tono de la etapa actual:** indica qué espera la sesión: una decisión, al cliente, un
     presupuesto, que la reanuden tras una falla o que termine un proceso.
   - **Pestañas:** se ve una etapa a la vez, y se abre sola la que espera. Siguen el patrón de
     pestañas de WAI-ARIA y se manejan con flechas, Inicio y Fin. Sin JavaScript, cada pestaña es
     un ancla y las etapas se ven en orden.
   - **Pantallas angostas:** la línea se desplaza de lado. El lado que oculta etapas se desvanece,
     y la etapa abierta queda a la vista.
5. **Lo que muestra cada etapa.**
   - **Artefactos:** cada etapa muestra los suyos aunque ya esté hecha, y la que espera a una
     persona termina con su decisión.
   - **Desarrollo y pruebas:** cada versión con su veredicto. La última queda abierta y las
     anteriores, plegadas. Una versión que el tester aún no dictamina también aparece, con su
     código.
   - **Aprobación final:** el resumen del veredicto, las pruebas propias (RF-38) y la decisión. Una
     vez validado el módulo, muestra la versión, quién la validó, cuándo y el veredicto del tester.
   - **Avisos de acción:** la pausa por presupuesto y la falla que hay que reanudar van en una
     tarjeta propia, encima de la línea.
6. **Panel agrupado por quién debe actuar** (`plantillas/panel.html`).
   - **Grupos:**
     - las que esperan al equipo: una decisión, un presupuesto o que las reanuden;
     - las que avanzan o esperan al cliente;
     - las terminadas.
   - **Filas:** cada sesión repite la línea del flujo en miniatura junto a su estado.
   - **Formulario de sesión nueva:** queda al lado de la lista y, si falta un dato, conserva lo
     escrito.
7. **Vista del cliente** (`plantillas/conversacion.html`). Muestra el avance en cuatro pasos de su
   lenguaje, derivados de las etapas: conversación, revisión del equipo, construcción y pruebas, y
   validación final.
8. **Trazabilidad y traza en HTML** (opción 1, `interfaces/web/documento_html.py`).
   - **Fuente:** sigue siendo el Markdown de `interfaces/documentos.py`, el mismo que usan la
     consola y la exportación.
   - **Alcance del conversor:** entiende solo lo que esos generadores escriben: títulos, listas de
     dos niveles, tablas, párrafos, negrita y código.
   - **Seguridad:** escapa todo el texto antes de darle formato, de modo que lo que escribió el
     cliente o devolvió un modelo nunca se interpreta como HTML.
   - **Presentación:** las columnas de cifras se alinean a la derecha, y el Markdown queda plegado al
     final de la página, para copiarlo.
   - **Descartadas:**
     - una biblioteca agrega una dependencia y su descarga para un subconjunto cerrado;
     - plantillas propias duplicarían el contenido de los documentos, con dos fuentes que podrían
       divergir.
9. **Sistema visual** (`estaticos/estilos.css`).
   - **Paleta:** tokens de color para el modo claro y el oscuro, que sigue al sistema. El armazón
     va en petróleo, y el acento marca las acciones principales y lo hecho.
   - **Colores de estado,** solo donde significan algo:
     - ámbar: espera a una persona;
     - azul: procesa;
     - verde: aprobado;
     - rojo: alerta;
     - gris: cerrada.
   - **Contraste medido:** cada par de texto y fondo supera 4,5:1. El mínimo es 4,83:1 en claro y
     6,36:1 en oscuro.
   - **Superficies del navegador con la paleta:** la selección, el cursor, el foco, las barras de
     desplazamiento y las cifras tabulares.
   - **Lectura:** los párrafos largos no pasan de 75 caracteres.
10. **Movimiento.**
    - **Cambio de etapa:** no se anima, porque es frecuente y se hace también con el teclado.
    - **La llegada a una etapa nueva:** es el único movimiento propio.
      - Cuando la sesión cambió de etapa desde la última visita a su página, el tramo que la une con
        la anterior se dibuja una vez, en 260 ms y con salida exponencial.
      - La última etapa vista se guarda en el almacenamiento de la pestaña. Sin él, la línea se
        muestra quieta.
    - **Botones:** al presionarlos ceden, con escala 0,97 en 120 ms.
    - **Movimiento reducido:** no hay desplazamientos ni escalas, y el indicador de proceso late en
      lugar de girar.
11. **Huella de los estáticos** (`huella_de_estaticos` en `aplicacion.py`). La hoja de estilos y los
    guiones se piden con `?v=` y los diez primeros caracteres del SHA-256 de los estáticos. Así, el
    navegador no usa una versión vieja tras una actualización.
12. **Modo de demostración** (`scripts/web_demostracion.py`).
    - **Qué levanta:** la web en `http://127.0.0.1:8010/`, con los servicios simulados del paso 5 y
      todo en memoria.
    - **Sesiones:** nueve sintéticas, una por estado que la interfaz debe mostrar.
    - **Costo y datos:** no llama a Azure OpenAI ni toca PostgreSQL. Solo las pruebas propias de
      N17 usan el entorno aislado de Docker.
    - **Uso:** sirve para revisar y capturar la interfaz sin datos de Realtix.

### Límites

- **Sin pruebas automáticas de la interacción.** El teclado en las pestañas y la llegada a una
  etapa se verificaron leyendo el código y en las capturas. Una herramienta de pruebas en
  navegador agregaría una dependencia y sus navegadores.
- **El panel lee el estado de cada sesión** para dibujar su línea. Con las 118 sesiones guardadas
  en la base de desarrollo, armarlo pasó de unos 0,3 s a 0,46 s.
- **La página de la sesión lee el historial de versiones,** que recorre sus puntos de control. Solo
  lo hace si la sesión tiene versiones. En esas 118 sesiones, tarda 26 ms de media y 224 ms la de
  más puntos, con 93 puntos y 6 versiones.
- **Navegadores:** solo se verificó con Edge, de motor Chromium. No se verificaron Firefox ni
  Safari, ni un lector de pantalla.
- **Imagen de la aplicación:** el código va dentro de la imagen (ADR-0017). Para ver la web nueva
  en el puerto 8000 hay que reconstruirla con `docker compose up -d --build --wait`.

### Consecuencias

- **Favorable:** el recorrido de la sesión, sus tres puntos de control y lo que espera se leen de
  un vistazo, y lo ya aprobado sigue a la mano en cada etapa.
- **Favorable:** el panel separa lo que exige al equipo de lo que avanza solo o espera al cliente.
- **Favorable:** sin dependencias nuevas de Python ni recursos de terceros.
- **Desfavorable:** más código de plantillas y estilos. Si `documentos.py` empieza a escribir otra
  sintaxis de Markdown, el conversor debe aprenderla; sus pruebas usan los documentos reales para
  notarlo.

### Confirmación

- `pytest tests/unitarias/test_web.py tests/unitarias/test_web_etapas.py
  tests/unitarias/test_documento_html.py`.
- Para revisarlo a ojo, `python scripts/web_demostracion.py`, recorriendo cada estado en claro, en
  oscuro y en una pantalla angosta.

## Verificación

- **Sin costo:**
  - 771 pruebas unitarias: 11 de las etapas, 5 del conversor y 1 de la web son nuevas;
  - 34 de integración, 19 de embeddings y 33 del entorno aislado.
- **Pruebas de la web:** las 12 que ya existían pasan, con una sola aserción ajustada al formato
  nuevo del gasto en el encabezado: «0.0500 de 0.0500 USD».
- **Capturas:** con Edge sin ventana, desde WSL.
  - **Anchos:** 1440 y 1024 px, y 390 px dentro de un marco, porque Edge impone un ancho mínimo de
    ventana.
  - **Temas:** claro y oscuro.
  - **Páginas:** las nueve sesiones de la demostración, el panel, la vista del cliente, la
    trazabilidad, la traza y la página de error.
  - **Defectos que destaparon y se corrigieron:**
    - el contorno de foco del panel al llegar por su ancla;
    - el texto de la etapa de desarrollo cuando la sesión se detiene antes del veredicto;
    - un choque de nombres de clase que centraba los turnos del cliente;
    - la barra superior en pantallas angostas.
- **Contraste:** se calculó para cada par de texto y fondo de los dos temas, con la fórmula de
  WCAG.

## Cambios para el documento de tesis

- **Interfaces (paso 12):**
  - la página de la sesión se organiza por etapas, con la línea del flujo y sus tres puntos de
    control;
  - el panel agrupa las sesiones según quién debe actuar;
  - el cliente ve su avance en cuatro pasos.
- **Figuras:** las capturas pueden tomarse de la demostración, con datos sintéticos.
- **Paquete de `docs/tesis/`:** el rediseño se incorpora cuando el paquete se actualice, al cerrar
  el paso 15.

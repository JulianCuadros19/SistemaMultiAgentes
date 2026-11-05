# Paquete de contexto para actualizar el documento de tesis

**Corte:** 4 de noviembre de 2026, al cierre del paso 14 del plan de trabajo.

**Versión contrastada:** «Trabajo de Grado - Sistema Multiagente Realtix», 112 páginas, exportada
el 4 de noviembre de 2026. Se guarda solo en local, en `docs/anexos/`.

Este paquete es un documento derivado. La fuente de verdad son los documentos del repositorio:
- `docs/requerimientos.md`, versión 1.3;
- `docs/arquitectura.md`, versión 1.5;
- los registros de decisión de `docs/decisiones/`;
- las mediciones de `docs/mediciones/`.

## Qué contiene

| Archivo | Para qué sirve |
|---|---|
| `01-correcciones.md` | Lo que el documento dice hoy y ya no es cierto, en su orden y con su página, y lo que debe decir. 45 entradas |
| `02-avances.md` | Lo que el documento todavía no cuenta y dónde va (ver la lista debajo) |
| `03-cifras.md` | Todas las cifras con su fuente. Es la referencia única: ninguna cifra se toma de otro lado |
| `04-arquitectura-final.md` | La arquitectura vigente: nodos, flujo con su diagrama, estado, datos, conocimiento, modelos y despliegue. Sirve para rehacer la Figura 8 y la Tabla 35 |

**Lo que trae `02-avances.md`:**
- la corrida ampliada de 20 casos, con su línea base y su corrida final;
- la calidad de la primera salida y las enmiendas;
- el control de costo y la traza por nodo;
- la entrega en contenedores con Azure OpenAI;
- las tres entradas nuevas del Anexo D;
- lo pendiente.

## Cómo usarlo

1. **Archivos para la conversación de redacción:**
   - **Siempre:** los cuatro archivos de esta carpeta.
   - **Como respaldo, si caben:**
     - `docs/requerimientos.md`;
     - `docs/arquitectura.md`;
     - `docs/decisiones/0015-calidad-de-la-primera-salida.md`;
     - `docs/decisiones/0016-control-de-costo-y-traza-por-nodo.md`;
     - `docs/decisiones/0017-entrega-en-contenedores-con-azure-openai.md`.
   - **Para el Anexo F:** los prompts de `prompts/<agente>/*.md`.
2. **Mensaje:** pegar el mensaje de abajo.
3. **Orden de trabajo:** primero las correcciones, después los avances. Pedir los cambios por
   capítulo y revisarlos contra `03-cifras.md` antes de aceptarlos.
4. **Antes de entregar el documento,** el equipo decide los puntos abiertos:
   - el estado del RNF-04 (`01-correcciones.md`, C-30);
   - el componente del RF-39 (C-07);
   - si se reinsertan la figura del prompt y la tabla de indicadores (C-13 y C-45).

## Mensaje para pegar

```text
Te comparto el paquete de contexto del sistema multiagente al 4 de noviembre de 2026, al cierre
del paso 14 del plan de trabajo. Úsalo para actualizar el documento de tesis en dos tiempos.

1. Correcciones. Aplica 01-correcciones.md en el orden del documento. Cada entrada trae la
   ubicación, con la página de la versión del 4 de noviembre, lo que dice hoy, lo que debe decir y
   por qué. Si un pasaje ya no está igual, ubica el equivalente y aplica el sentido de la
   corrección. Las entradas marcadas como decisión del equipo no las resuelvas: déjalas señaladas.
2. Avances. Redacta lo nuevo con 02-avances.md: las tres secciones nuevas del capítulo 4, la
   actualización de los capítulos 5 y 6, las conclusiones y las recomendaciones, y las tres
   entradas nuevas del Anexo D en el formato de la Tabla 34. Para la Figura 8 y la Tabla 35 del
   Anexo E usa 04-arquitectura-final.md.

Reglas:
- Toma toda cifra de 03-cifras.md tal cual, con su unidad. No la recalcules ni la redondees de
  otra forma. Si necesitas una cifra que no está, pregunta antes de escribirla.
- Conserva la terminología del documento: especificación de diseño (nunca contrato), requerimiento
  formal, punto de control humano, revisión o validación final, entorno aislado, enmienda, traza
  por nodo y presupuesto por módulo.
- Todos los casos de prueba son sintéticos; no hay datos de Realtix.
- Los modelos de lenguaje son solo los desplegados en Azure OpenAI y BGE-M3 corre local. No
  plantees modelos de lenguaje locales ni de pesos abiertos.
- La comparación con la implementación manual, la línea base de un modelo único y el benchmark de
  modelos son el paso 15 y todavía no se hicieron. No escribas resultados de ellos: preséntalos
  como trabajo pendiente de la fase de evaluación.
- Los autores son Julián Andrés Cuadros Muñoz y Laura Catalina Riveros Flórez. No atribuyas
  autoría a herramientas.
- Mantén el estilo del documento: voz impersonal, tiempo pasado, coma decimal y cifras con su
  unidad.
- Al terminar, actualiza la lista de tablas, la de figuras y las referencias cruzadas. Hoy
  arrastran una Tabla 28 y una Figura 9 que ya no existen (C-45).
```

## Cuándo se actualiza

Al cerrar el paso 15 (casos de referencia y líneas base), con:
- los resultados del objetivo 4;
- el benchmark de modelos;
- las métricas RAGs, si se calculan.

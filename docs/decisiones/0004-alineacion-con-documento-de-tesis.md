---
estado: aceptada
fecha: 2026-10-08
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0004 · Alineación con el documento de tesis: formatos, término y flujo con tres aprobaciones

## Contexto y planteamiento del problema

El equipo entregó la versión actualizada del documento de tesis
(`Confirmar_informacion_y_anexos.pdf`, 2026-10-08), con la metodología, los capítulos de
requerimientos y arquitectura, y los Anexos A, B y C. Al contrastarlo con los documentos fuente
del repositorio aparecieron diferencias:

- `requerimientos.md` (RF-06), `arquitectura.md` y la plantilla 03 de la base de conocimiento
  ubicaban el formato del requerimiento en el Anexo B. El documento de tesis lo ubica en el
  **Anexo A**, y el Anexo B es el formato del artefacto del arquitecto.
- Los RNF de `requerimientos.md` conservaban nombres anteriores a ISO/IEC 25010:2023.
- El documento contiene notas del equipo sobre el flujo (página 9), que el equipo confirmó como
  decisiones: revisar el término «contrato», entregar los requerimientos aprobados al tester,
  permitir el retorno al paso anterior en las aprobaciones humanas y añadir una aprobación
  humana final con pruebas independientes.

La decisión afecta a los documentos fuente, a `CLAUDE.md`, a la base de conocimiento y a la
topología que implementará el paso 5.

## Factores de decisión

- Los documentos fuente son la referencia de todo el desarrollo y deben coincidir con el
  documento de tesis aprobado.
- RNF-09 (control humano) y RF-08, RF-14 y RF-21 (aprobaciones y validación).
- Mantener el gasto concentrado en los mismos cinco nodos con modelo de lenguaje.
- No renumerar los nodos existentes, que ya se citan en documentos, requerimientos y código.

## Opciones consideradas

- A. Alinear los documentos del repositorio al documento de tesis e incorporar las notas como
  decisiones.
- B. Mantener los documentos aprobados y registrar las diferencias como pendientes.

## Resultado de la decisión

Opción elegida: «A», por decisión del equipo.

1. **Formatos.** El requerimiento formal sigue el **Anexo A** (backlog de historias y ficha de
   detalle) y el artefacto del arquitecto el **Anexo B**. Ambos se transcriben en
   `docs/anexos.md`; el PDF queda solo en local.
2. **Término.** «Contrato de diseño» pasa a llamarse **«especificación de diseño»**, para no
   confundirlo con un contrato legal. Su identificador usa el prefijo `ED-`, la plantilla de
   la base de conocimiento se renombra a `02-especificacion-de-diseno.md` y la entidad a
   `especificaciones_diseno`. Se conservan los demás sentidos de «contrato»: contratos de
   datos, de interfaz, legal y externo.
3. **Requerimientos al tester: nodo N16.** Al aprobarse los requerimientos en N6, se entregan
   al arquitecto y al tester. El tester deriva en **N16**, de forma determinística, un caso de
   prueba de aceptación por cada escenario Gherkin aprobado, en paralelo con N7. N14 dictamina
   caso por caso contra ese plan, de modo que la validación se ancla en lo acordado con el
   humano y no solo en las pruebas que escribe el desarrollador.
4. **Aprobación humana final: nodo N17 y RF-38.** Con veredicto aprobado, N15 ya no cierra el
   flujo: lo remite a **N17**. Allí la persona revisa el reporte y el código, puede ejecutar
   pruebas propias en el entorno aislado y aprueba el módulo o lo devuelve a N10 con
   observaciones. Se agrega el **RF-38**; el total pasa a 38 RF y el RNF-09 a tres puntos de
   control.
5. **Retornos.** Cada rechazo humano devuelve el flujo al agente anterior con observaciones:
   N6 → N3, N9 → N8 y N17 → N10. Las decisiones quedan en la nueva entidad
   `aprobaciones_humanas`.
6. **Nombres de los RNF** según ISO/IEC 25010:2023: Seguridad y confidencialidad,
   Flexibilidad, Capacidad de interacción, Capacidad de interacción y control humano, y
   Adecuación funcional.

La topología pasa de 15 a **17 nodos**; siguen siendo cinco los que invocan un modelo de
lenguaje (N3, N5, N8, N10 y N14). `requerimientos.md` y `arquitectura.md` pasan a la versión
1.1, con su historial de cambios. Los documentos de la base de conocimiento modificados pasan a
la versión 1.1.

### Consecuencias

- Favorable, porque los documentos del repositorio, `CLAUDE.md` y la base de conocimiento
  coinciden con el documento de tesis.
- Favorable, porque la validación del tester se ancla en los requerimientos que aprobó el humano
  y el módulo no se da por validado sin una revisión humana final.
- Desfavorable, porque cada módulo exige un tercer momento de disponibilidad humana, lo que
  alarga el ciclo y debe considerarse en la medición del RNF-01.
- Desfavorable, porque el documento de tesis debe actualizarse para coincidir: RF-38 en el
  Anexo C, el conteo de requerimientos del orquestador en la Tabla 23, la Figura 7 con N16,
  N17 y los retornos, y el término «especificación de diseño» en el Anexo B.

### Confirmación

- `git grep -i contrato` solo encuentra los sentidos que se conservan.
- `git grep -i "anexo b"` solo se refiere a la especificación de diseño.
- El paso 5 verifica que una sesión recorre los 17 nodos y ejercita los retornos de los tres
  puntos de control.

## Análisis de las opciones

### Opción A · Alinear e incorporar
- Favorable, porque el desarrollo parte de una sola fuente coherente.
- Desfavorable, porque modifica documentos que ya habían sido aprobados.

### Opción B · Registrar como pendiente
- Favorable, porque no toca documentos aprobados.
- Desfavorable, porque el paso 4 y el paso 5 se construirían sobre formatos y un flujo que el
  equipo ya decidió cambiar.

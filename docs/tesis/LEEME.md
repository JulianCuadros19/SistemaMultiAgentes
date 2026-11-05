# Paquete para actualizar el documento de tesis

**Corte:** 5 de noviembre de 2026, al cierre del paso 15 del plan de trabajo.

**Versión contrastada:** «Trabajo de Grado - Sistema Multiagente Realtix», 112 páginas, exportada
el 4 de noviembre de 2026. Se guarda solo en local, en `docs/anexos/`.

Este paquete es un documento derivado. La fuente de verdad son los documentos del repositorio:
- `docs/requerimientos.md`, versión 1.3;
- `docs/arquitectura.md`, versión 1.6;
- los registros de decisión de `docs/decisiones/`;
- las mediciones de `docs/mediciones/` y `docs/evaluacion/informe-objetivo-4.md`.

## Qué contiene

| Archivo | Para qué sirve |
|---|---|
| `01-correcciones.md` | Lo que el documento dice hoy y ya no es cierto, en su orden y con su página, y lo que debe decir. 46 entradas |
| `02-avances.md` | Material para las secciones nuevas del capítulo 4 y las entradas de los ADR-0015 a ADR-0017 del Anexo D |
| `03-cifras.md` | Las cifras con su fuente. Es la referencia: ninguna cifra se toma de otro lado |
| `04-arquitectura-final.md` | La arquitectura vigente: nodos, flujo con su diagrama, estado, datos, conocimiento, modelos y despliegue. Sirve para rehacer la Figura 8 y la Tabla 35 |
| `05-evaluacion-paso-15.md` | El texto de la evaluación, ya redactado: 1.6.4, 3.8, 4.14, capítulo 5, 6.4, 6.5, 7, 8 y las entradas de los ADR-0018 a ADR-0020 del Anexo D |
| `06-prompts-anexo-f.md` | Los ocho prompts vigentes, para el Anexo F |

## Cómo usarlo

1. **Revisa las decisiones del equipo** que trae el mensaje de abajo. Si cambias alguna, edítala en el mensaje antes de pegarlo.
2. **Adjunta los seis archivos numerados** a la conversación donde está el documento. Este LEEME no hace falta.
3. **Pega el mensaje.**
4. **Revisa cada tanda** contra `03-cifras.md` antes de dar el visto bueno a la siguiente.
5. **En Word, al terminar:** `Ctrl+A` y `F9` para actualizar la tabla de contenido, las listas y las referencias.

## Mensaje para pegar

```text
Actualiza mi documento de tesis con los seis archivos adjuntos. Son el paquete definitivo, con corte al 5 de noviembre de 2026, y están contrastados con la versión de 112 páginas del 4 de noviembre. Si un pasaje ya no está igual, ubica el equivalente y aplica el sentido del cambio. Si no lo encuentras, dímelo; no lo inventes.

QUÉ ES CADA ARCHIVO
- 01-correcciones.md: lo que el documento dice hoy y ya no es cierto, y lo que debe decir (entradas C-01 a C-46).
- 02-avances.md: material para las secciones nuevas del capítulo 4 y las entradas de los ADR-0015 a ADR-0017 del Anexo D.
- 03-cifras.md: la referencia de cifras, con su fuente.
- 04-arquitectura-final.md: la arquitectura vigente, para la Figura 8 y la Tabla 35.
- 05-evaluacion-paso-15.md: el texto de la evaluación, ya redactado, y las entradas de los ADR-0018 a ADR-0020 del Anexo D.
- 06-prompts-anexo-f.md: los ocho prompts vigentes, para el Anexo F.

Si dos fuentes no coinciden, manda este mensaje, luego 05, luego 01 y luego 02.

DECISIONES DEL EQUIPO, YA TOMADAS
1. El RNF-04 queda «Cumplido parcialmente». El conteo final es de siete requerimientos no funcionales cumplidos y tres parciales.
2. El RF-39 va en el componente «Orquestador y flujo iterativo», que pasa de 3 a 4. El total es de 39 requerimientos funcionales.
3. La figura del prompt no se reinserta: 3.4 y el Anexo F quedan con el texto de C-13 y C-44.
4. La tabla de indicadores se reinserta al final de 6.4, con el contenido del archivo 05.
5. El Anexo F incluye los ocho prompts completos, en letra monoespaciada de 9 puntos.

ORDEN DE TRABAJO
Trabaja por tandas. Al terminar cada una, dime qué cambiaste y qué no pudiste aplicar, y espera mi visto bueno antes de seguir.
1. Preliminares y capítulos 1 a 3: C-01 a C-18, más 1.6.4 y 3.8 del archivo 05.
2. Capítulo 4: C-19 a C-27. Redacta las secciones nuevas con las secciones 3 a 6 de 02, y la del despliegue con 05.
3. Capítulo 5: todo lo del capítulo 5 en 05, más C-28, C-30 y C-31.
4. Capítulos 6 a 8: C-32 a C-37, más 6.4, 6.5, 7 y 8 del archivo 05.
5. Anexos: C-39 a C-44. Las entradas del Anexo D salen de 02, sección 7, y de 05, cada una con los aspectos de la Tabla 34.
6. Listas: C-45. Actualiza la tabla de contenido, la lista de tablas, la de figuras y las referencias cruzadas.

REGLAS
- Si puedes editar el archivo de Word, hazlo con control de cambios y conserva sus estilos. Si no, dame el texto final de cada sección, listo para pegar, e indica dónde va.
- Lleva tal cual el texto entre comillas « » de las entradas de 01 y el texto de 05. El material de 02 redáctalo con el estilo del documento.
- Toma las cifras de 03 y 05 tal cual, con su unidad. No las recalcules ni las redondees de otra forma. Si necesitas una que no está, pregunta antes de escribirla.
- Los números de tabla y de figura del paquete son los de la versión del 4 de noviembre. [Tabla A] a [Tabla G] son tablas nuevas. Numera todas en orden de aparición, con la leyenda arriba y «Fuente:» abajo, como las demás.
- Conserva la terminología del documento: especificación de diseño (nunca contrato), requerimiento formal, punto de control humano, revisión o validación final, entorno aislado, enmienda, traza por nodo y presupuesto por módulo.
- Todos los casos de prueba son sintéticos; no hay datos de Realtix.
- Los modelos de lenguaje son solo los desplegados en Azure OpenAI y BGE-M3 corre local. No plantees modelos de lenguaje locales ni de pesos abiertos.
- La comparación se hizo con código generado por un solo modelo de lenguaje, porque Realtix no pudo compartir su código. No afirmes ningún ahorro frente al trabajo manual. El benchmark de modelos queda como trabajo futuro, sin resultados.
- No suavices los resultados desfavorables: el sistema no tuvo menos errores que un solo modelo de lenguaje, costó y tardó el doble o más, y la exactitud del tester frente a las pruebas de referencia fue de 0,52.
- Los autores son Julián Andrés Cuadros Muñoz y Laura Catalina Riveros Flórez. No atribuyas autoría a herramientas.
- Mantén el estilo del documento: voz impersonal, tiempo pasado, coma decimal y cifras con su unidad.

COMPROBACIÓN FINAL
Al terminar, busca en el documento y repórtame dónde siguen apareciendo, fuera del Anexo D: «38 requerimientos», «38 functional», «582», «catorce registros», «186 fragmentos», «seis niveles», «six-level», «modelos remotos», «remote models», «desarrollo manual», «desarrollo humano», «¡Error!» y «[Tabla». Confirma también que el documento dice 39 requerimientos funcionales, 909 pruebas, veinte registros de decisión, once niveles de prueba, y siete requerimientos no funcionales cumplidos y tres parciales.
```

## Estado

El benchmark de modelos en N3 y N5 quedó fuera por decisión del equipo (ADR-0019).

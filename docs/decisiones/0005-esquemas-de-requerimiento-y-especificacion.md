---
estado: aceptada
fecha: 2026-10-08
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0005 · Esquemas Pydantic del requerimiento formal y de la especificación de diseño

## Contexto y planteamiento del problema

El paso 4 del plan exige que los esquemas de datos validen los ejemplos de los Anexos A y B
(`docs/anexos.md`). Los anexos definen campos, pero no tipos, cardinalidades ni reglas de
consistencia, y sus ejemplos tienen particularidades: el RF-27 de la Tabla 24 expresa los datos
de entrada y de salida en texto libre, el backlog de la Tabla 27 incumple su propia regla de
«QUIERO en infinitivo» y el Anexo B no trae ningún ejemplo. Hay que fijar cómo se interpretan.
La decisión afecta a `src/multiagente/core/esquemas/` y a las salidas estructuradas de los
nodos N5 y N8.

## Factores de decisión

- RF-06 y RF-11: requerimiento formal y especificación de diseño validables contra esquema.
- RF-22: el tester verifica la conformidad del código contra la especificación de forma
  determinística, lo que exige estructura legible por máquina.
- RF-07: la verificación de calidad del requerimiento es una etapa propia (N6).
- Los ejemplos oficiales de los anexos deben validar.

## Opciones consideradas

- A. Esquemas estructurales y estrictos; las reglas de redacción quedan para la verificación de
  calidad del RF-07.
- B. Esquemas que además impongan las reglas de redacción y de completitud.

## Resultado de la decisión

Opción elegida: «A», porque con la opción B el backlog oficial del Anexo A no validaría y el
elicitador no podría registrar un requerimiento incompleto, como pide la plantilla de la base de
conocimiento, sin que su salida fuera rechazada.

Criterios de interpretación:

1. **Módulos.** `comunes.py` reúne los identificadores (`RF-`, `HU-`, `ESC-`, `ED-`, `ARQ-` y
   la versión `n.n`), las enumeraciones y el enunciado como, quiero y para. Los esquemas están en
   `requerimiento.py` (`BacklogHistorias`, `HistoriaUsuario`, `RequerimientoFormal`) y en
   `especificacion_diseno.py` (`EspecificacionDiseno`). Todos rechazan campos no declarados.
2. **Datos estructurados.** Por decisión del equipo, los datos de entrada son listas de
   {nombre, tipo, obligatorio, restricción} y los de salida de {nombre, tipo, formato}. El RF-27
   se transcribió a esa forma en `tests/datos/anexos/anexo_a_rf27.json`. El `tipo` es texto
   libre, porque los ejemplos usan vocabularios distintos.
3. **Campos opcionales.** En la ficha del Anexo A, `riesgo` y `funcional_responsable` son
   opcionales y de texto libre; el ejemplo oficial usa «Medio» como riesgo.
4. **Valores canónicos.** Las enumeraciones van en minúsculas y sin tilde (`nuevo`,
   `correccion`, `alto`, `alta`). La transcripción de los ejemplos usa esa forma.
5. **«Obligatorio: Sí» en el Anexo B** significa que el campo debe estar presente. Las listas
   que definen el artefacto no pueden ir vacías: requerimientos cubiertos, módulos, interfaces
   de cada módulo y requerimientos de cada módulo. `modelo_datos`, `dependencias_externas` y
   `reglas_de_dependencia` pueden ir vacías, y `dependencias_permitidas` vale lista vacía si se
   omite, como indica el anexo. Las interfaces públicas se anidan en cada módulo.
6. **Validación 1 del Anexo B en el esquema.** Nombres y rutas de módulo únicos, dependencias
   que solo apuntan a módulos declarados, grafo de dependencias acíclico y requerimientos de
   cada módulo incluidos en los cubiertos. Las validaciones 2 (cobertura de los requerimientos
   aprobados) y 3 (catálogo tecnológico) necesitan datos externos y se implementan en N9
   (paso 8).
7. **Reglas de redacción fuera del esquema.** QUIERO en infinitivo, rol distinto de «usuario»,
   ausencia de marcadores como «por definir» y existencia de un escenario de error se verifican
   en el RF-07.

### Consecuencias

- Favorable, porque los ejemplos oficiales y las plantillas de la base de conocimiento validan,
  y una prueba lo comprueba en cada ejecución: si alguien cambia una plantilla sin ajustar el
  esquema, las pruebas fallan.
- Favorable, porque los mismos modelos servirán para las salidas estructuradas de N5 y N8.
- Desfavorable, porque un requerimiento estructuralmente válido aún puede ser de baja calidad;
  depende de que el paso 7 implemente la verificación del RF-07.
- Desfavorable, porque la transcripción estructurada del RF-27 interpreta el texto original y
  debe revisarse si cambia el documento de tesis.

### Confirmación

- `pytest tests/unitarias/test_esquemas_requerimiento.py tests/unitarias/test_esquemas_especificacion.py`
  valida el backlog y el RF-27 del Anexo A, los ejemplos de las plantillas 03 y 02 y 39 casos
  negativos: campos faltantes, valores inválidos, duplicados, autorreferencia, dependencias no
  declaradas y ciclos.

## Análisis de las opciones

### Opción A · Esquemas estructurales
- Favorable, porque separa la estructura (esquema) de la calidad (RF-07), como la arquitectura
  separa N5 y N6.
- Desfavorable, porque deja la calidad en manos de otra etapa.

### Opción B · Esquemas con reglas de redacción
- Favorable, porque detecta antes ciertos defectos.
- Desfavorable, porque rechaza los ejemplos oficiales y los requerimientos incompletos
  legítimos.

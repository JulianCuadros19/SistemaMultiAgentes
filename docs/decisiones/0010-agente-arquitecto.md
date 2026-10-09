---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0006 (punto 5, retorno de N9) y ADR-0003 (tiempo de espera por llamada)
---

# ADR-0010 · Agente arquitecto: catálogo cerrado, decisión trazable y validaciones del Anexo B

## Contexto y planteamiento del problema

El paso 8 exige que la especificación de diseño que genera el arquitecto pase las tres
validaciones del Anexo B antes de habilitar la generación de código:
1. esquema sin ciclos;
2. cobertura de los requerimientos aprobados;
3. catálogo tecnológico autorizado.

Hay que reemplazar la simulación de N7, N8 y N9 por el agente real, que selecciona y parametriza
del catálogo cerrado de seis arquitecturas (decisión 5 de `CLAUDE.md`). La decisión afecta a:
- `src/multiagente/agentes/arquitecto/` y `src/multiagente/agentes/contexto.py`;
- el orquestador y `src/multiagente/llm/`;
- `prompts/arquitecto/` y `evaluacion/casos/`.

## Factores de decisión

- RF-09 a RF-14:
  - recuperar al menos dos alternativas;
  - registro de decisión con alternativa descartada y justificación trazada a requerimientos;
  - especificación validable, con cobertura y catálogo tecnológico;
  - aprobación humana.
- Tabla 3 de la arquitectura: N8 tiene perfil alto. RNF-10: costo acotado.
- El Anexo B condiciona la generación de código a las tres validaciones.
- Lo aprendido en el paso 7: separar tareas en llamadas distintas y verificar en código lo que
  pueda verificarse.

## Opciones consideradas

- A. N8 en una sola llamada que produce el registro y la especificación.
- B. N8 en dos llamadas, selección y parametrización, con el registro armado y las validaciones
  hechas en código.

## Resultado de la decisión

Opción elegida: «B».

### Decisiones del equipo

1. **N8 usa `gpt-5`, del perfil alto.** Despliegue Global Standard, versión 2025-08-07. Tarifa:
   entrada 1,25, caché 0,125 y salida 10 USD por millón de tokens, consultada el 2026-10-09.
2. **Escalamiento de N9 solo con rechazo.**
   - N9 devuelve a N8 hasta `MAX_CORRECCIONES_DISENO` (2).
   - Al agotarlo, pausa con los errores a la vista, pero la aprobación queda bloqueada: el Anexo
     B exige las tres validaciones antes de generar código.
   - La persona rechaza con observaciones, y el contador se reinicia.
3. **N8 en dos llamadas.**
   - **Selección**, con el catálogo, los criterios y la plantilla a la vista. Produce el
     registro de decisión.
   - **Parametrización**, con la arquitectura elegida, el esquema y el catálogo tecnológico.
     Produce la especificación.

### Decisiones de implementación

4. **N7 recupera el catálogo completo.**
   - Cada arquitectura se consulta por su identificador y su título, y se toma el fragmento de
     su propio documento. La consulta solo por identificador devolvía primero los criterios de
     selección, que nombran las seis.
   - Si falta alguna, N7 falla.
   - Se recuperan además completos los criterios de selección (los cinco pasos y las
     prohibiciones), la plantilla de decisión, el esquema y el catálogo tecnológico.
   - Una consulta descriptiva con los requerimientos aprobados trae los patrones.
   - Solo la colección `arquitecturas_referencia` llega a los prompts del arquitecto.
5. **Registro de decisión verificado y armado en código.** Las reglas de arq-001 y arq-003:
   - al menos dos opciones del catálogo, y la elegida entre ellas;
   - una descartada con motivo que cite un RF aprobado;
   - justificación que cite RF aprobados y ninguno inexistente;
   - una consecuencia desfavorable y una confirmación verificable.

   El código arma el registro con la estructura MADR. Las etiquetas `F1…Fn` que cite el modelo
   se reemplazan por la referencia estable del fragmento.
6. **Especificación con campos deterministas.** `ED-01`, versión `0.<diseño>`, arquitectura base
   igual a la elegida y requerimientos cubiertos iguales a los aprobados. La validación 1 la
   hace el esquema, con un reintento.
7. **Corrección acotada en N8.**
   - Ante errores de N9 solo se vuelve a parametrizar, porque la elección sigue en pie.
   - Una observación nueva del revisor reabre también la selección; lo controla
     `Arquitectura.observaciones_atendidas`.
8. **Validaciones de N9, determinísticas** (`agentes/arquitecto/validacion.py`).
   - **1. Esquema:**
     - esquema y ciclos;
     - firmas de Python analizables, con tipo en cada parámetro y retorno en las funciones;
     - nombre de la firma igual al de la interfaz;
     - ruta coherente con el nombre del módulo y con su capa;
     - ningún paquete que tape un módulo de la biblioteca estándar o una dependencia.
   - **2. Cobertura:** todo RF aprobado está en un módulo, y no se declaran RF ajenos.
   - **3. Catálogo:** las dependencias externas pertenecen al catálogo tecnológico, sin
     declarar módulos estándar, y la arquitectura base pertenece al catálogo de referencia.
   - Además, un campo o parámetro monetario con `float` es error (decisión 10).
   - El catálogo tecnológico (arq-004) y los identificadores ARQ-nn se leen de la base de
     conocimiento, que es la fuente única.
9. **Tiempo de espera por nodo.**
   - La parametrización con `gpt-5` superaba los 60 s del cliente, y además el cliente la
     reintentaba.
   - `ParametrosNodo.tiempo_espera_s` permite fijarlo por nodo: N8 usa 300 s
     (`TIEMPO_ESPERA_N8_ARQUITECTURA`) y N3 conserva 60 s, que protegen el RNF-01.
   - Las llamadas que vencen por tiempo no devuelven consumo y no quedan en la traza, aunque el
     proveedor pudo cobrarlas.
10. **Esfuerzo `low` en N8.** Con `medium`, un diseño tardaba 240 s y costaba 0,21 USD; con `low`,
    70 s y 0,08 USD, con la misma calidad.
11. **Respuestas humanas inválidas sin bloqueo.** Este defecto venía del paso 5.
    - Un rechazo sin observaciones, o una respuesta vacía, hacía fallar el nodo después de la
      pausa, y LangGraph repetía esa respuesta en cada reanudación: la sesión quedaba detenida
      para siempre.
    - Ahora N3, N6, N9 y N17 vuelven a pausar con un aviso, y la siguiente respuesta válida se
      lee, también al reanudar en otro proceso con PostgreSQL.
    - La aprobación bloqueada de N9 usa el mismo mecanismo.
12. **Casos de diseño.**
    - `evaluacion/casos/diseno-*.json` trae requerimientos aprobados con las arquitecturas que
      admiten según arq-003.
    - `ElicitadorFijo` los entrega sin elicitación.
    - `scripts/disenar_arquitectura.py` diseña con el arquitecto real y permite aprobar o
      rechazar.

### Mediciones (2026-10-09)

Con `gpt-5` y esfuerzo `low`, la prueba `nube` (tres casos, tres corridas):

| Caso | Candidatas (arq-003) | Elegida en las tres corridas | Módulos | Costo por diseño |
|---|---|---|---|---|
| Cálculo del avalúo | ARQ-01, ARQ-02 | ARQ-01, ARQ-01, ARQ-01 | 2 | 0,047–0,053 USD |
| Liquidación por lotes | ARQ-03 | ARQ-03, ARQ-03, ARQ-03 | 6 a 10 | 0,065–0,084 USD |
| Registro de mutaciones | ARQ-01, ARQ-04 | ARQ-04, ARQ-01, ARQ-01 | 4 | 0,051–0,066 USD |

- **Resultado.** Las nueve corridas llegaron a N9 sin errores en el primer diseño, sin
  correcciones automáticas.
- **Latencia por llamada.** Selección: 22 s de media. Parametrización: 40 s de media, 45 s
  máximo.
- **Camino humano.** Con el script, un rechazo («preferir ARQ-01, más simple») reabrió la
  selección. La versión 0.2 eligió ARQ-01 con una justificación trazada al RF-01, pasó las
  validaciones y se aprobó, por 0,12 USD con las dos versiones.
- **Gasto del paso en mediciones.** Cerca de 1 USD, incluidas las corridas con `medium`.

### Consecuencias

- **Favorable:** la especificación llega a la aprobación humana validada contra el Anexo B, con
  un registro de decisión trazado a requerimientos y a los fragmentos del catálogo.
- **Favorable:** la elección respeta los criterios de selección. En los casos con una sola
  candidata clara se reproduce siempre.
- **Desfavorable: la elección varía en los casos ambiguos.** El registro de mutaciones admite
  ARQ-01 y ARQ-04, y el modelo alternó entre ambas. La revisión humana de N9 decide, como se vio
  en el camino humano.
- **Desfavorable: el tamaño de la especificación varía entre corridas.** La de lotes tuvo de 6
  a 10 módulos. La simplicidad suficiente está en el prompt, pero no se mide.
- **Desfavorable: hay incoherencias que N9 no detecta.** Por ejemplo, un parámetro
  `Optional[Decimal]` frente a un campo obligatorio del modelo de datos. Quedan para el
  arquitecto humano y para N12.

### Confirmación

- `pytest`:
  - validaciones del Anexo B, con una falla inyectada por regla y los catálogos leídos de la
    base;
  - selección y registro;
  - parametrización;
  - N7 con recuperador falso;
  - corrección y reselección;
  - grafo con escalamiento, aprobación bloqueada y respuesta inválida.
- `pytest -m embeddings tests/integracion/test_arquitecto_contexto.py`: N7 con BGE-M3 recupera
  las seis arquitecturas y los criterios completos.
- `pytest -m nube tests/integracion/test_arquitecto_nube.py`: es la condición de terminado.
- `python scripts/disenar_arquitectura.py --requerimientos evaluacion/casos/<caso>.json`.

## Análisis de las opciones

### Opción A · Una llamada
- Favorable, porque es una sola llamada por diseño.
- Desfavorable, porque produce una salida grande y difícil de corregir por partes, y obliga a
  repetir la elección ante un error de formato.

### Opción B · Dos llamadas con verificación en código
- Favorable, porque cada salida se valida y se corrige por separado, y una corrección de la
  especificación no cambia la decisión.
- Desfavorable, porque son dos llamadas al modelo de perfil alto por diseño.

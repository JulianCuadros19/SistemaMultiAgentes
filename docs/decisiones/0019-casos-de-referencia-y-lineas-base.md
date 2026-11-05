---
estado: propuesta
fecha: 2026-11-05
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0001 (subpaquete `evaluacion`)
---

# ADR-0019 · Casos de referencia y líneas base del objetivo 4

> **Borrador de la fase 1.** Fija el diseño, las métricas y las hipótesis antes de medir. Los
> resultados se agregan al cerrar el paso 15, y entonces el estado pasa a «aceptada».

## Contexto y planteamiento del problema

El paso 15 termina cuando hay «métricas calculadas contra la implementación manual y contra un
modelo único».

**El objetivo 4 de la tesis** pide evaluar el sistema con métricas de tiempo, costo y tasa de
errores en corridas de extremo a extremo, contrastadas con los umbrales de los requerimientos no
funcionales.

**Lo que la tesis registra como pendiente** (6.4 y Recomendaciones):
- la comparación con el desarrollo manual, que dejó sin cuantificar el ahorro;
- las métricas RAGs de la Tabla 14, definidas pero no calculadas sobre las trazas;
- la comparación sistemática de los modelos de cada nodo.

**Lo que dejó el ADR-0015:** las decisiones 37 a 39, que se aplicaron sin medir.

Hasta ahora, la tasa de errores se medía con el tester del propio sistema, contra los
requerimientos que el mismo sistema elicitó. Esa medida no sirve para comparar enfoques: cada uno
tendría sus propias pruebas.

## Factores de decisión

- **Un mismo oráculo para los tres enfoques,** independiente de las pruebas que cada uno escriba.
- **Criterios fijados antes de medir,** como en el ADR-0015.
- **Datos:** casos sintéticos, sin material de Realtix.
- **Costo:** un tope de 17 USD para todo el paso, por decisión del equipo.
- **Modelos:** solo los despliegues de Azure OpenAI (ADR-0017).
- **Sin dependencias nuevas de Python.**
- **Reproducibilidad:** las tablas se regeneran desde los resultados guardados.

## Opciones consideradas

**El oráculo de la tasa de errores:**
1. Pruebas de aceptación de referencia escritas desde la ficha de cada caso, que se ejecutan sobre
   cada implementación por medio de un adaptador.
2. El tester del sistema, con los requerimientos de una corrida del sistema como referencia.
3. Un juez de modelo que lea la ficha y el código.

**Lo que recibe el modelo único:**
1. Conversa con el mismo cliente simulado y entrega todo.
2. Recibe la ficha completa, sin conversar.
3. Recibe los requerimientos que aprobó el analista.

**Quién hace la implementación manual:**
1. Los autores, cronometrando cada fase.
2. Desarrolladores de Realtix.
3. Una estimación de la empresa.

## Resultado de la decisión

### Decisiones del equipo (2026-11-05)

1. **Implementación manual:** la hacen los autores, cronometrando cada fase (opción 1). El costo
   es horas × una tarifa por hora que fijan antes de medir, en `evaluacion/manual/LEEME.md`.
2. **Tres casos de referencia sintéticos,** de arquitecturas distintas y con ejemplos con cifras:
   - `caso-ampliada-02`, reajuste anual del canon (ARQ-01);
   - `caso-ampliada-12`, dígito de verificación del NIT (ARQ-04);
   - `caso-ampliada-16`, simulador de amortización (ARQ-05).
3. **Modelo único:** `gpt-6.1-sol` conversa con el mismo cliente simulado y entrega todo (opción 1).
   No usa recuperación, puntos de control ni tester. Las diferencias salen de la arquitectura, no
   de la información.
4. **Alcance adicional:**
   - las métricas RAGs;
   - una corrida ampliada nueva de los 20 casos para medir las decisiones 37 a 39.

   El benchmark de modelos en N3 y N5 queda fuera.
5. **Tope de 17 USD** para todo el paso.

### Ajuste del diseño (2026-11-05, decisión del equipo)

Tomado el día de la entrega, con la corrida ampliada y el modelo único ya medidos. Reemplaza las
decisiones 1, 2 y 3 en lo que aquí se indica. Las pruebas de referencia de 02, 12 y 16 no cambian.

- **Sin implementación manual.**
  - **Por qué:** Realtix no puede compartir sus desarrollos por el acuerdo de confidencialidad, y si
    la hicieran los autores no sería independiente: construyeron el sistema y conocen los casos.
  - **Qué sale:** la implementación manual, la corrida con revisión humana y la tarifa por hora. La
    hipótesis H2 queda retirada, sin evaluar.
  - **Qué sigue:** la comparación con desarrollo humano queda como recomendación, como ya dice la
    tesis.
- **Dos líneas base de un solo modelo de lenguaje,** ambas con el despliegue de N10 y sin intervención
  humana:
  - **con diálogo:** el modelo único de la decisión 9, con la misma información que el sistema;
  - **de un solo prompt:** recibe en un mensaje lo que el cliente sabe (`evaluacion/llm_un_prompt.md`),
    sin diálogo. Es el mejor caso para un modelo solo, porque tiene la información completa.
- **Nueve casos de referencia,** con las seis arquitecturas. A 02, 12 y 16 se suma el primer caso de
  cada arquitectura, por número y sin mirar su resultado: 01, 04, 07, 10, 14 y 17.
  - **Oráculo:** sigue las reglas de la decisión 6. Se escribió solo desde la ficha y se versionó antes
    de abrir las salidas de esos casos y de correr los modelos.
  - **Lo que ya se conocía:** de 10 y 14, los hallazgos del tester en la corrida ampliada, no su código.
  - **Corridas:** el sistema, con la corrida ampliada, más `sistema-2` en 02, 12 y 16; el modelo con
    diálogo, una corrida más por caso nuevo; el de un solo prompt, una por caso.
- **Matriz adicional:** el tester frente al oráculo, en cada versión dictaminada de los casos de
  referencia. Lo positivo es que el oráculo falle; la predicción positiva, que el tester rechace.
- **Código abierto de GitHub:** se descartó como línea base, porque no implementa estas fichas y no
  trae tiempos ni costos.
- **Sistema:** no cambia hasta terminar de medir.
- **Hipótesis nuevas, exploratorias,** porque nacen después de ver datos de 3 casos:
  - **H4:** el sistema cuesta y tarda más que un modelo solo;
  - **H5:** el tester detiene defectos que un modelo solo entrega sin aviso.
- **Lectura:** la tasa de errores es descriptiva. En costo y tiempo se agrega una prueba de signos por
  caso, también exploratoria.

### Decisiones de implementación (fase 1)

6. **Oráculo: pruebas de aceptación de referencia** (opción 1, `evaluacion/referencia/`).
   - **Por caso:**
     - una interfaz neutra (`interfaz.md`);
     - 9 o 10 verificaciones (`test_referencia.py`), 29 en total;
     - una implementación de control y tres mutantes.
   - **Solo lo que la ficha dice sin ambigüedad:** los ejemplos con cifras, las reglas, los rangos y
     los mensajes de error textuales. Lo que admite dos lecturas queda fuera y se registra.
   - **Validado antes de medir:** en el entorno aislado, con Python 3.11, el control pasa todas las
     verificaciones y cada mutante falla al menos una
     (`python scripts/evaluar_referencia.py --oraculo`).
   - **Revisión:** las revisa el autor que no implementa el caso a mano.
   - **Por qué no las otras opciones:**
     - el tester del sistema mide contra los requerimientos del propio sistema y exige sus
       convenciones;
     - un juez de modelo no ejecuta el código.
7. **Adaptadores.** Cada implementación evaluada lleva un `adaptador_referencia.py` que solo traduce
   la interfaz neutra a la suya.
   - **Verificación del árbol sintáctico:** rechaza la aritmética, las funciones y los métodos que
     calculan (`sum`, `round`, `quantize`…) y los módulos de cálculo.
   - **Comportamiento ausente:** si la implementación no lo ofrece, el adaptador lanza `Ausente`.
     La verificación falla y se cuenta aparte.
8. **Métricas, iguales para los tres enfoques.**
   - **Tiempo:**
     - de reloj;
     - horas-persona: las del manual y las de revisión en N6, N9 y N17;
     - la latencia del cliente simulado se informa aparte.
   - **Costo:** la inferencia, más las horas-persona × la tarifa.
   - **Tasa de errores:** las verificaciones de referencia que no pasan entre el total.
   - **Complementarias:**
     - las pruebas propias que pasan;
     - los hallazgos de Ruff por severidad, con `config/estilo_generado/ruff.toml`;
     - los turnos de diálogo.
   - **Desvío frente al plan:** los detectores de dinero y de secretos del tester no entran. Los dos
     dependen de la especificación de diseño, que el modelo único y la implementación manual no
     tienen. El uso correcto del dinero lo verifican las pruebas de referencia, con cifras exactas
     al peso.
9. **Modelo único** (`multiagente.evaluacion.modelo_unico`, `evaluacion/modelo_unico.md` 1.0).
   - **Un prompt, dos momentos:** el diálogo y la entrega.
   - **Configuración del sistema,** sin identificadores en el código:
     - el despliegue de N10;
     - en el diálogo, el esfuerzo bajo y el límite de 4.000 tokens de N3;
     - en la entrega, el esfuerzo medio, los 32.000 tokens y los 600 s de N10.
   - **Condiciones del diálogo:** el límite de 18 intervenciones del cliente y el mismo cliente
     simulado.
   - **Lo que recibe del entorno:** lo mismo que N10, es decir, la configuración de estilo, los
     paquetes del entorno aislado y Python 3.11.
   - **Lo que no recibe:** el catálogo de arquitecturas ni los criterios de calidad, que son el
     conocimiento de la arquitectura.
   - **Reintento:** una entrega inservible se reintenta una vez, como N10. Es inservible si no trae
     código, pruebas o `USO.md`, si tiene rutas inseguras o si no compila en 3.11.
10. **Métricas RAGs** (`multiagente.evaluacion.rag`, `evaluacion/juez_rag.md` 1.0).
    - **Muestras:** una por sesión y por agente. El elicitador produce un solo artefacto con sus
      dos colecciones y se juzga una vez.
    - **Juez:** `gpt-6.1-sol`, que no usa ningún nodo con recuperación, con esfuerzo bajo.
    - **Fidelidad:** las afirmaciones sustentadas entre el total, por agente.
    - **Relevancia de la respuesta:** la similitud con BGE-M3 entre la consulta y tres preguntas que
      propone el juez, por agente.
    - **Relevancia del contexto:** los fragmentos necesarios entre los recuperados, por colección.
    - **Desvío de costo:** las muestras reales traen de 8 a 28 fragmentos y de 44.000 a 58.000
      caracteres de media por agente. Juzgar las 20 sesiones costaría unos 3,3 USD, frente a ~1 USD
      del plan.
      - El guion empieza por los 10 casos impares, que cubren las seis arquitecturas, unos
        1,65 USD.
      - Sigue con los pares solo si el tope lo permite.
11. **Paquete `multiagente.evaluacion`.**
    - **Módulos:** `referencia`, `modelo_unico`, `rag` y `traza`.
    - **Guiones:** `evaluar_referencia.py`, `evaluar_modelo_unico.py` y `evaluar_rag.py`.
    - **Prompts:** en `evaluacion/`, como los del cliente simulado y del juez de reglas ocultas.
    - **Fuera del flujo:** nada del paquete participa en el grafo.
12. **Hipótesis, fijadas antes de medir.**
    - **H1:** el sistema tiene menos errores de referencia que el modelo único.
    - **H2:** el sistema tarda y cuesta menos que la implementación manual, contando la revisión
      humana.
    - **H3:** con la corrida ampliada nueva, la tabla de criterios del ADR-0015, con las mismas
      metas, para las decisiones 37 a 39.
    - **Lectura:** con tres corridas por caso, es descriptiva, sin afirmaciones estadísticas.
13. **Orden de las corridas con costo,** de mayor a menor prioridad, con el costo estimado:
    1. la corrida ampliada: ~7,6 USD;
    2. el modelo único, 3 × 3: ~4,5 USD;
    3. una corrida con revisión humana por caso, después de la manual de ese caso: ~1,2 USD;
    4. una corrida automática más por caso: ~1,2 USD;
    5. las RAGs, con lo que quede del tope.

    Cada guion recibe lo que queda del tope y se detiene antes de pasarlo.

### Límites

- **Muestra:** tres casos sintéticos y tres corridas por enfoque. Ninguna conclusión es
  estadística.
- **La implementación manual la hacen los autores,** no desarrolladores de Realtix.
- **Asimetría a favor del manual:** leen la ficha del cliente sin entrevistarlo. El sistema y el
  modelo único tienen que averiguarla preguntando.
- **Lo que el oráculo no cubre:** la capa HTTP del caso 12, porque el entorno aislado no tiene
  cliente HTTP de pruebas, y el contrato documentado.
- **El juez de RAGs es un modelo:** sus juicios varían entre corridas. Un autor revisa una muestra
  de cinco.

### Consecuencias

- **Favorable:** la tasa de errores se compara con la misma vara en los tres enfoques, y sin
  Docker ni modelo se verifica el oráculo.
- **Favorable:** la corrida ampliada sirve a la vez para las decisiones 37 a 39, para una corrida
  del sistema por caso de referencia y para las RAGs.
- **Desfavorable:** cada implementación necesita su adaptador, escrito a mano y revisado.

### Confirmación

- `python scripts/evaluar_referencia.py --oraculo`.
- `pytest -m "sandbox and not nube" tests/integracion/test_evaluacion_sandbox.py`.
- `pytest tests/unitarias/test_evaluacion_*.py`, sin costo.

## Verificación de la fase 1

- **Oráculo, en el entorno aislado:**
  - los controles pasan 9 de 9, 10 de 10 y 10 de 10;
  - los 9 mutantes fallan de 1 a 7 verificaciones cada uno.
- **Comportamiento ausente:** se clasifica aparte, y no pasa por accidente una verificación que
  espera un rechazo.
- **Pruebas sin costo:**
  - las unitarias del paquete nuevo: referencia, modelo único y RAGs;
  - 5 del entorno aislado.
- **Extracción de las muestras de RAGs:** se comprobó en solo lectura sobre las 20 sesiones de la
  corrida final del ADR-0015.

## Resultados

Se agregan al cerrar el paso 15.

## Cambios para el documento de tesis

- **1.6.4 y capítulo 5:**
  - el diseño de la evaluación con los casos de referencia;
  - el oráculo común;
  - las líneas base del modelo único y de la implementación manual.
- **Tabla 24:** niveles nuevos para las tres comparaciones.
- **5.4:** las métricas RAGs, calculadas.
- **6.4, 6.5 y Recomendaciones:** los resultados y lo que queda pendiente.

---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0008 (modelo de N3 y N5)
---

# ADR-0009 · Modelo de perfil intermedio para el elicitador: gpt-5.4-mini en N3 y N5

## Contexto y planteamiento del problema

La arquitectura asigna un perfil de modelo a cada nodo que invoca un modelo de lenguaje
(Tabla 3):
- intermedio para N3 y N5;
- alto para N8 y N10;
- económico para N14.

Hasta el paso 7 los cinco nodos usaban `gpt-5-nano`, que corresponde al perfil económico. Las
mediciones del paso 7 (ADR-0008) mostraron limitaciones coherentes con esa diferencia:
- extracciones incompletas;
- preguntas compuestas;
- copia de reglas del dominio;
- una síntesis fallida en siete corridas.

Antes del paso 8 hay que decidir el modelo del elicitador. La decisión afecta a `.env`
(`MODELO_N3_DIALOGO` y `MODELO_N5_SINTESIS`) y a `config/tarifas_modelos.toml`.

## Factores de decisión

- Tabla 3 de la arquitectura: perfil intermedio para N3 y N5. La selección definitiva se hace
  por benchmark (paso 15).
- RNF-01: menos de 15 s por turno.
- RNF-10: costo por módulo acotado.
- Decisión 7 de `CLAUDE.md`: cambiar de modelo es editar `.env`, sin tocar el código.

## Opciones consideradas

Precios de la API de precios minoristas de Azure, consultados el 2026-10-09, en USD por millón
de tokens, despliegue Global Standard en southcentralus:

| Opción | Modelo | Entrada | Caché | Salida | Estado |
|---|---|---|---|---|---|
| A | gpt-5-nano | 0,05 | 0,005 | 0,40 | Desplegado |
| B | gpt-5-mini | 0,25 | 0,025 | 2,00 | Sin desplegar |
| C | gpt-5.4-mini (2026-03-17) | 0,75 | 0,075 | 4,50 | Desplegado |

## Resultado de la decisión

Opción elegida: «C», por decisión del equipo. Ya estaba desplegado, es compatible con el código
y mejoró de forma medible la latencia y la estabilidad del elicitador.

1. **Asignación.** N3 y N5 usan `gpt-5.4-mini`. N14 conserva `gpt-5-nano`, que es su perfil. N8 y
   N10 se deciden al empezar los pasos 8 y 9, con una medición de su tarea; hoy siguen con
   `gpt-5-nano`, sin uso.
2. **Compatibilidad verificada.**
   - Acepta los esfuerzos `minimal` y `low`, `max_completion_tokens` y la salida estructurada
     estricta.
   - Reporta los tokens de razonamiento.
   - No requiere cambios en el código.
3. **Tarifas.** `config/tarifas_modelos.toml` registra `gpt-5-mini` y `"gpt-5.4-mini"`. La clave
   con punto va entre comillas: sin ellas TOML la lee como una tabla anidada, y una prueba
   ahora lo detecta.
4. **Comparación justa.** `MODELO_CLIENTE_SIMULADO`, opcional, fija el modelo del cliente simulado.
   Si se omite, usa el de N3. Las mediciones de esta comparación lo dejaron en `gpt-5-nano` con
   esfuerzo `medium`, como en el paso 7.
5. **El esfuerzo no cambia.** `low` en N3 y N5, con los mismos límites de salida.
6. **El benchmark del paso 15 compara las tres opciones.** `gpt-5-mini` es la alternativa más
   económica dentro del perfil intermedio.

### Mediciones (2026-10-09)

Mismo caso sintético de mutación de propietario y el mismo cliente simulado.

| Medida | gpt-5-nano | gpt-5.4-mini |
|---|---|---|
| Corridas `nube` que llegan a N6 sin defectos | 6 de 7 | 4 de 4 |
| Latencia de cada llamada de N3: media y máxima | 4,0 s y 7,0 s | 1,6 s y 3,1 s |
| Razonamiento medio por llamada de N3 | 371 tokens | 52 tokens |
| Latencia de N5: media y máxima | 7,8 s y 10,0 s | 8,0 s y 8,8 s |
| Llamadas a N5 por corrida, sin rechazo humano | 1, 3 y 1 | 1, 1, 1 y 1 |
| Turno más largo del recorrido completo con rechazo | 15,3 s | 11,6 s |
| Costo del sistema por elicitación | 0,002 a 0,005 USD | 0,018 a 0,033 USD |

Revisión del contenido:
- El recorrido completo con rechazo incorporó la observación del analista en la versión 0.2 del
  requerimiento («un radicado que incluye el año de radicación»).
- No hubo contenido inventado.
- Se observó que el modelo repetía las palabras clave Gherkin dentro de las cláusulas. N5 ahora
  las quita de forma determinística.

### Consecuencias

- **Favorable:** el elicitador cumple el RNF-01 con holgura, incluido el turno que cierra con la
  síntesis. Ya no necesita correcciones automáticas en las corridas medidas.
- **Favorable:** el cambio fue solo de configuración, lo que confirma la capa agnóstica al
  proveedor (RNF-06).
- **Desfavorable: el costo por elicitación sube unas ocho veces.** Sigue en centavos. Con datos
  reales de Realtix y despliegue Data Zone, las tarifas suben un 10 %.
- **Desfavorable: un modelo más reciente puede retirarse o cambiar de versión antes.** La
  versión que responde queda en la traza de cada llamada.

### Confirmación

- `pytest tests/unitarias/test_costos.py`: cada modelo resuelve su tarifa del archivo
  versionado.
- Para repetir la comparación:

  ```
  MODELO_N3_DIALOGO=gpt-5.4-mini MODELO_N5_SINTESIS=gpt-5.4-mini MODELO_CLIENTE_SIMULADO=gpt-5-nano \
    pytest -m nube tests/integracion/test_elicitador_nube.py
  ```

## Análisis de las opciones

### Opción A · gpt-5-nano
- Favorable, porque es el más barato.
- Desfavorable, porque está por debajo del perfil asignado y mostró variabilidad que obligó a
  compensar en código.

### Opción B · gpt-5-mini
- Favorable, porque es el perfil intermedio más barato.
- Desfavorable, porque no estaba desplegado y no se midió; queda para el benchmark.

### Opción C · gpt-5.4-mini
- Favorable, porque fue el más rápido y estable en las mediciones, y ya estaba desplegado.
- Desfavorable, porque cuesta el triple que gpt-5-mini.

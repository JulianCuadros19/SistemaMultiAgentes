---
estado: aceptada
fecha: 2026-10-09
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0003 (costo con escritura en caché) y ADR-0006 (entrada de N10 y contenido del código en el estado)
---

# ADR-0011 · Agente desarrollador: gpt-6.1-sol, verificación estructural y entorno aislado

> El ADR-0012 (paso 10) mueve el análisis de conformidad a `core/conformidad.py`, compartido con
> N12, y alinea N10 con el umbral 0: su verificación rechaza las importaciones privadas y el
> prompt de generación pasa a la versión 1.1.
> El ADR-0014 (paso 12) fija las secciones de `USO.md`, que la verificación exige, y pasa el
> prompt a la versión 1.5: no escribe `requirements.txt`, y el reintento es una corrección del
> intento rechazado, que el código combina como en el RF-19. Una generación fallida cuenta como
> iteración rechazada y va de N10 a N15. Si la especificación cambió, N10 genera de cero en lugar
> de corregir.
> El ADR-0017 (paso 14) da a la aplicación en contenedor acceso al Docker del anfitrión por su
> socket, para crear el entorno aislado, que no cambia.

## Contexto y planteamiento del problema

El paso 9 exige que el código generado se importe sin error y cubra las interfaces de la
especificación. Hay que reemplazar la simulación de N10 por el agente real, que implementa la
especificación sin recuperación de contexto (decisión 1 de `CLAUDE.md`).

Hay tres restricciones:
- el RNF-03 prohíbe ejecutar código generado en el anfitrión, así que la importación exige un
  entorno aislado, que el plan ubicaba en el paso 10;
- el estilo es configuración verificable, no conocimiento (decisión 2), pero
  `config/estilo_generado/` estaba vacío;
- la arquitectura asigna a N10 «el perfil más alto disponible» (§5) y pide validar el formato de
  salida antes del sandbox (§11).

La decisión afecta a:
- `src/multiagente/agentes/desarrollador/`, `src/multiagente/sandbox/` y `src/multiagente/core/`;
- el orquestador y `src/multiagente/llm/costos.py`;
- `prompts/desarrollador/`, `config/estilo_generado/` y `docker/sandbox/`;
- `evaluacion/casos/`.

## Factores de decisión

- RF-15 a RF-19:
  - un archivo válido por módulo con sus interfaces;
  - estilo declarado;
  - fronteras de dependencia;
  - documentación y una prueba por criterio;
  - corrección con la retroalimentación del tester.
- RNF-03 (entorno aislado), RNF-07 (Python 3.11) y RNF-10 (costo acotado).
- Decisiones 1, 2, 3, 7, 10 y 11 de `CLAUDE.md`.
- Lo aprendido en los pasos 7 y 8: verificar en código lo que pueda verificarse y reintentar una
  vez con los problemas a la vista.

## Opciones consideradas

Para el modelo de N10, precios de la API de precios minoristas de Azure, consultados el
2026-10-09, en USD por millón de tokens, Global Standard en southcentralus:

| Opción | Modelo | Entrada | Caché | Escritura de caché | Salida | API |
|---|---|---|---|---|---|---|
| A | gpt-5 (2025-08-07) | 1,25 | 0,125 | — | 10,00 | Chat Completions |
| B | gpt-6.1-sol (2026-09-29) | 2,00 | 0,10 | 2,50 | 10,00 | Chat Completions |
| C | gpt-6-astra (2026-09-03) | 10,00 | 1,00 | 12,50 | 50,00 | Chat Completions |
| D | gpt-5.3-codex | — | — | — | — | Solo Responses |

Para verificar la importación:
- E. entorno aislado mínimo ya, que N11 reutiliza en el paso 10;
- F. solo análisis estático en el paso 9, y la importación real en el paso 10.

## Resultado de la decisión

Opciones elegidas: «B» y «E», por decisión del equipo.
- gpt-6.1-sol es el perfil más alto disponible con un costo razonable. Su salida, que domina en la
  generación de código, cuesta lo mismo que la de gpt-5, y Microsoft lo ubica cerca de Astra en
  programación.
- Astra cuesta cinco veces más, y gpt-5.3-codex exigiría una segunda implementación por la API
  Responses (ADR-0003).
- El entorno aislado permite verificar la condición de terminado sin violar el RNF-03.

### Decisiones del equipo

1. **N10 usa `gpt-6.1-sol`**, en despliegue Global Standard, versión 2026-09-29, sin solicitud de
   acceso. N8 sigue con gpt-5; compararlos queda para el benchmark del paso 15.
2. **Entorno aislado mínimo en el paso 9** (`docker/sandbox/`, `multiagente.sandbox`).
   - **Imagen:** `python:3.11.17-slim-trixie`, fijada por digest, con las librerías del catálogo
     arq-004 en versiones publicadas al menos dos semanas antes. numpy queda en 2.4.6, porque 2.5
     exige Python 3.12. Se construye con `docker compose --profile sandbox build sandbox`.
   - **Contenedor:** uno efímero por ejecución:
     - sin red, de solo lectura, con `/tmp` en memoria;
     - sin root ni capacidades;
     - con límites de procesos, memoria, CPU y tiempo.
   - **Entrada:** el código entra como tar por la entrada estándar. No se monta ninguna carpeta
     del anfitrión.
   - **Tiempo:** vencido el límite, se mata el contenedor.
   - **Uso:** en el paso 9 lo usan la prueba de terminado y el script; en el paso 10, N11.

### Decisiones de implementación

3. **Una llamada estructurada por versión.**
   - La salida trae `archivos` (`ruta` y `contenido`) y `documentacion_uso`, que se guarda como
     `USO.md`.
   - La entrada es solo los requerimientos aprobados, la especificación y el contenido de
     `config/estilo_generado/ruff.toml`.
   - Una prueba verifica que el agente no tiene recuperador y que no importa nada de
     `multiagente.rag`.
4. **Verificación estructural determinística en N10** (`agentes/desarrollador/verificacion.py`).
   Verifica, sin ejecutar, lo que se lee del árbol sintáctico en RF-15, RF-17 y RF-18:
   - **Archivos:** exactamente las rutas declaradas, `tests/test_*.py` y `USO.md`, más un
     `tests/conftest.py` opcional. Sin `__init__.py`: son paquetes de espacio de nombres.
   - **Sintaxis:** de Python 3.11 (`feature_version`).
   - **Interfaces:** en el nivel superior del módulo, con los mismos parámetros, tipos y retorno.
     - Las anotaciones equivalentes se normalizan: `Optional[X]` con `X | None`, y
       `decimal.Decimal` con `Decimal`.
     - Al final se admiten parámetros adicionales con valor por defecto: la firma declarada sigue
       funcionando, que es lo compatible según CAL-AR-002. N12 debe aplicar la misma noción.
     - El constructor de una clase admite `__init__` o campos de dataclass y de BaseModel.
   - **Excepciones declaradas:** definidas en el módulo, importadas o integradas.
   - **Importaciones:** absolutas y dentro de la biblioteca estándar, las dependencias externas
     declaradas y las `dependencias_permitidas`.
   - **Docstring:** en todo lo público.
   - **Pruebas:** al menos una prueba `test_rf_NN_esc_NN_…` por escenario de cada RF cubierto.
     Esa convención permitirá que N14 trace cada caso de N16 a su prueba.
   - **Reintento:** una salida con problemas se reintenta una vez con ellos a la vista.
   - **Fuera de N10:** el estilo (RF-16), la ejecución y la severidad los dictamina el tester.
5. **Corrección (RF-19).**
   - N10 recibe la versión vigente (`previa`) y la retroalimentación etiquetada `D1…Dn`.
   - El modelo devuelve solo los archivos que cambian, y el código los combina sobre la versión
     previa.
   - Una corrección que no cambia nada se rechaza.
   - `defectos_atendidos` es la retroalimentación vigente.
6. **Estilo del código generado:** `config/estilo_generado/ruff.toml`.
   - Python 3.11, líneas de 100 y documentación google.
   - Familias E, W, F, I, N, D, ANN, S, BLE, B, UP y C90 (complejidad 10).
   - Se ignora N818, porque las excepciones del dominio van en español.
   - En `tests/` se ignoran D, ANN y S101.
   - `core.estilo` la lee con su huella, que se guarda en la versión (RF-36), y la aplica con
     Ruff. Ruff solo lee el código, así que corre en el anfitrión. En el paso 9 se informa; N12 la
     dictaminará.
7. **Escritura en caché en el costo.**
   - gpt-6.1-sol cobra aparte los tokens que escribe en caché.
   - La API los reporta en `prompt_tokens_details.cache_write_tokens`, incluidos en la entrada. Se
     verificó con dos llamadas: 2.140 de 2.143 escritos y luego leídos.
   - `ConsumoTokens` los desglosa y `Tarifa` admite `escritura_cache`. Sin ese precio, se cobran
     como entrada normal.
8. **Esfuerzo `medium` en N10.**
   - Con `low`, el modelo razonaba unos 50 tokens y degeneraba el archivo de pruebas de mutación
     en cada primer intento: tras `@pytest.fixture` escribía ` def_placeholder = None`, y el
     documento de uso llegaba vacío.
   - Con `medium` razona de 300 a 1.000 tokens, acierta casi siempre al primer intento y cuesta
     lo mismo que `low` con reintento.
   - Configuración: `ESFUERZO_N10_GENERACION=medium`, `MAX_TOKENS_N10_GENERACION=32000` y
     `TIEMPO_ESPERA_N10_GENERACION=600`.
9. **Casos de desarrollo.**
   - `evaluacion/casos/desarrollo-*.json` traen los tres casos de diseño con el diseño que aprobó
     el arquitecto en una corrida real del paso 8. Se exportaron con
     `disenar_arquitectura.py --exportar`, por 0,22 USD los tres.
   - `ArquitectoFijo` los entrega en N8: el desarrollador se prueba siempre contra la misma
     especificación y sin embeddings.
10. **Defecto corregido del paso 5.** `VersionCodigo` heredaba `str_strip_whitespace` y recortaba
    el contenido de los archivos, con lo que quitaba el salto de línea final. Ahora lo conserva
    tal cual.

### Mediciones (2026-10-09)

`gpt-6.1-sol` en South Central US, con los tres casos de desarrollo. Cada corrida recorre los tres
casos con la prueba `nube`:

| Configuración | Corridas | Pasan | Aciertan al primer intento | Latencia por llamada | Costo de N10 por módulo |
|---|---|---|---|---|---|
| `low` | 9 | 8 | 2 | 30–88 s | 0,045–0,164 USD |
| `medium`, firmas idénticas | 6 | 5 | 4 | 80–142 s | 0,071–0,245 USD |
| `medium`, firmas compatibles (final) | 6 | 6 | 5 | 64–131 s | 0,058–0,213 USD |

Configuración final, por caso:

| Caso | Arquitectura | Módulos | Pruebas generadas | Costo de N10 |
|---|---|---|---|---|
| Cálculo del avalúo | ARQ-01 | 3 | 57 y 38 | 0,058–0,065 USD |
| Liquidación por lotes | ARQ-03 | 6 | 42 y 36 | 0,117–0,213 USD |
| Registro de mutaciones | ARQ-01 | 3 | 52 y 103 | 0,074–0,079 USD |

- **Condición de terminado.** En las seis corridas finales:
  - la primera versión pasó la verificación estructural;
  - cada módulo declarado se importó en el entorno aislado, en unos 350 ms;
  - las pruebas generadas pasaron en el entorno aislado, aunque eso solo se informa.
- **Reintentos.**
  - El único reintento final se debió a un defecto real: una excepción declarada que el módulo
    no importaba. El reintento lo corrigió.
  - Antes del ajuste, la verificación rechazaba un campo privado con valor por defecto
    (`_vigencia: int | None = None`), que es compatible.
- **Estilo**, solo para informar: de 0 a 12 hallazgos por módulo, sobre todo líneas largas
  (E501), importaciones sin uso (F401) y orden de importaciones (I001).
- **Corrección (RF-19)** con el script: un rechazo en N17 de mutación pidió validar la
  identificación del nuevo propietario.
  - La versión 2 cambió solo los tres archivos implicados y el documento de uso; la capa de
    presentación no se tocó.
  - Pasó de 38 a 50 pruebas.
  - Costó 0,138 USD por las dos versiones, en 129 s.
- **Caché.** La primera llamada de una sesión escribe en caché unos 4.300 tokens, a 1,25 veces la
  entrada, y la corrección los lee a 0,10.
- **Gasto del paso en mediciones:** cerca de 2,8 USD.
  - 0,22 USD en la exportación de los casos.
  - Unos 1,8 USD en la comparación de `low` y `medium` con su diagnóstico.
  - 0,6 USD en las corridas finales.
  - 0,14 USD en la corrección.

### Consecuencias

- **Favorable:** la condición de terminado se cumple con el modelo real.
  - El código generado se importa en un entorno aislado y cubre las interfaces de la
    especificación, verificadas en código.
  - Sus propias pruebas pasan sin red.
- **Favorable:** N11 hereda un entorno aislado probado, con aislamiento de red, archivos y
  privilegios verificado por pruebas.
- **Favorable:** la verificación estructural detecta defectos reales y los devuelve al modelo con
  instrucciones precisas. El tester recibe código que ya cumple la forma de la especificación.
- **Favorable:** la corrección cambia solo lo necesario y aprovecha la caché.
- **Desfavorable: el costo y la latencia de N10.** Una generación cuesta de 0,06 a 0,21 USD y tarda
  de 1 a 2 minutos. El RNF-01 (20 minutos por módulo) se cumple, pero el ciclo de corrección
  puede triplicar ambos.
- **Desfavorable: quedan hallazgos de estilo.** N12 los reportará en el paso 10 y pueden abrir
  ciclos de corrección; el prompt podría reforzar el estilo si el tester los clasifica como de
  severidad alta.
- **Desfavorable: el código importa funciones privadas (`_validar_…`) de otros módulos.** Respeta
  las dependencias permitidas, pero las acopla. Es un candidato a criterio del tester.
- **Desfavorable: Docker es requisito** de las pruebas de terminado y lo será de N11. Cuando la
  aplicación corra en contenedor (paso 14), hará falta darle acceso a Docker; se decide en ese
  paso.

### Confirmación

- `pytest`:
  - verificación estructural, con una falla inyectada por regla y las variantes equivalentes que
    admite;
  - agente con modelo falso: mensajes sin contexto, reintento, corrección parcial y N10 en el grafo
    hasta N17, con un rechazo final;
  - entorno aislado sin Docker;
  - costo con escritura en caché;
  - casos de desarrollo contra el Anexo B.
- `pytest -m sandbox`:
  - Python 3.11 con el catálogo;
  - importación y errores;
  - sin red, sin root y sin escritura fuera de `/tmp`;
  - el tiempo vencido elimina el contenedor.
- `pytest -m "nube and sandbox" tests/integracion/test_desarrollador_nube.py` es la condición de
  terminado.
- `python scripts/generar_modulo.py --caso evaluacion/casos/<caso>.json [--rechazar "…"] --aprobar`.

## Análisis de las opciones

### Opción A · gpt-5
- Favorable, porque ya estaba desplegado y medido en N8.
- Desfavorable, porque es una generación anterior al perfil más alto disponible.

### Opción B · gpt-6.1-sol
- Favorable, porque es la generación vigente, con salida al precio de gpt-5 y compatible con Chat
  Completions y la salida estructurada.
- Desfavorable, porque cobra la escritura en caché y es un modelo de diez días: puede cambiar de
  versión, que queda en la traza.

### Opción C · gpt-6-astra
- Favorable, porque es el más capaz.
- Desfavorable, porque cuesta cinco veces más, y el ciclo de corrección multiplica ese costo por
  módulo (RNF-10).

### Opción D · gpt-5.3-codex
- Desfavorable, porque solo funciona con la API Responses (ADR-0003).

### Opción E · Entorno aislado ya
- Favorable, porque la condición de terminado se verifica de verdad y N11 hereda un entorno
  probado.
- Desfavorable, porque adelanta trabajo del paso 10 y exige Docker activo para esas pruebas.

### Opción F · Solo análisis estático
- Desfavorable, porque la condición del paso 9 se cumpliría solo en parte.

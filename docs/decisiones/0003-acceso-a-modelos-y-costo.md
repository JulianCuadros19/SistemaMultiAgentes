---
estado: aceptada
fecha: 2026-09-26
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
---

# ADR-0003 · Acceso a modelos por la API OpenAI v1 y registro de costo por llamada

> El ADR-0010 permite fijar el tiempo de espera por nodo. El ADR-0011 agrega al costo la escritura
> en caché, que los modelos GPT-6 cobran aparte y la API reporta en `cache_write_tokens`.

## Contexto y planteamiento del problema

El paso 3 del plan exige que una llamada real a Azure OpenAI responda y que su costo quede
registrado. Los modelos GPT-5 son de razonamiento: generan tokens ocultos que se facturan como
salida, y en una prueba previa en el portal una respuesta corta consumió cerca de 4.700 tokens.
Hay que definir cómo se invoca el modelo, cómo se controla el razonamiento, cómo se calcula el
costo y dónde queda registrado. La decisión afecta a `src/multiagente/llm/`, a la
configuración y a la traza de costo de los nodos N3, N5, N8, N10 y N14.

## Factores de decisión

- RNF-06 y decisión 7 de `CLAUDE.md`: capa de modelos agnóstica al proveedor, con los
  identificadores en configuración.
- RF-37: la entrega debe poder operar con modelos locales (paso 14). Por ahora el equipo usa
  solo Azure, con la suscripción Azure for Students, y no descarga modelos locales.
- RF-34 y RNF-10: tokens, costo y latencia por llamada, con presupuesto controlable.
- Decisión 10 de `CLAUDE.md`: el dinero se representa con `Decimal`.
- RNF-01: cada turno de elicitación debe responder en menos de 15 segundos.

## Opciones consideradas

- A. API OpenAI v1 con Chat Completions.
- B. API OpenAI v1 con Responses.
- C. SDK específico de Azure (`azure-ai-inference`).

## Resultado de la decisión

Opción elegida: «A», porque cubre lo que el sistema necesita de un modelo de razonamiento
(`reasoning_effort`, `max_completion_tokens` y el desglose de tokens de razonamiento) y es la
interfaz que también exponen los servidores de modelos locales, de modo que el paso 14 no
exige una segunda implementación.

Decisiones asociadas:

1. **API v1 sin versión.** El cliente `openai` apunta a `<endpoint>/openai/v1/`. Se eliminó
   `AZURE_OPENAI_API_VERSION` de la plantilla. El recurso está en **southcentralus**, con
   despliegue **Global Standard** de `gpt-5-nano` (versión `2025-08-07`). El endpoint y la
   clave viven solo en `.env`.
2. **Esfuerzo y límite explícitos.** `invocar()` exige `esfuerzo` y `max_tokens_salida` en
   cada llamada, sin valores por defecto. Cada nodo deberá fijar los suyos.
3. **Costo en `Decimal` desde tarifas versionadas.** `config/tarifas_modelos.toml` guarda los
   precios oficiales por millón de tokens, consultados en la API de precios de Azure el
   2026-09-25: entrada 0,05, entrada en caché 0,005 y salida 0,40 USD. La tarifa se busca por
   el prefijo más largo del modelo que responde.
4. **Razonamiento aparte, cobrado una vez.** Los tokens de razonamiento se registran aparte,
   pero ya están incluidos en la salida y no se suman de nuevo.
5. **Registro provisional en JSONL.** Hasta que exista la tabla `ejecuciones` (traza por
   nodo, pasos 5 y 13), las mediciones se registran en
   `docs/mediciones/paso-03-azure-openai.jsonl`, sin la clave ni el endpoint.
6. **Pruebas con costo aisladas.** El marcador `nube` excluye por defecto las pruebas que
   llaman al modelo; se ejecutan con `pytest -m nube`.

### Resultados medidos (2026-09-26)

Mismo mensaje sintético (48 tokens de entrada), procesado en South Central US:

| Esfuerzo | Límite | Fin | Salida | Razonamiento | Visible | Costo USD | Latencia |
|---|---|---|---|---|---|---|---|
| minimal | 8.000 | stop | 80 | 0 | 80 | 0,0000344 | 1,7 s |
| low | 8.000 | stop | 555 | 448 | 107 | 0,0002244 | 4,6 s |
| medium | 8.000 | stop | 1.340 | 1.216 | 124 | 0,0005384 | 8,9 s |
| medium | 64 | length | 64 | 64 | 0 | 0,0000280 | 1,1 s |

- Con esfuerzo medium, el 91 % de la salida es razonamiento; con low, el 81 %.
- La latencia crece con el esfuerzo. En N3, que debe responder en menos de 15 s (RNF-01),
  conviene minimal o low.
- Si el límite es menor que el razonamiento, la respuesta llega **vacía** con motivo de fin
  `length`, y los tokens se cobran igual. Cada nodo debe validar el motivo de fin.

### Consecuencias

- Favorable, porque cada llamada deja tokens, razonamiento, costo exacto y latencia, que
  son la base del recálculo del modelo de costos y del presupuesto del RNF-10.
- Favorable, porque cambiar de modelo o de proveedor compatible es editar `.env` y las tarifas.
- Desfavorable, porque las funciones exclusivas de Responses (por ejemplo, reutilizar el
  razonamiento entre turnos) quedan fuera.
- Desfavorable, porque las tarifas se actualizan a mano; si Azure cambia precios, el costo
  registrado será incorrecto hasta editar el archivo.

### Confirmación

- `pytest` ejecuta las pruebas de costos y del cliente sin red.
- `pytest -m nube` hace una llamada real y verifica respuesta y costo mayor que cero.
- `python scripts/medir_azure.py` repite la medición y agrega líneas al JSONL.

## Análisis de las opciones

### Opción A · Chat Completions
- Favorable, porque la soportan Azure, OpenAI y los servidores locales compatibles.
- Desfavorable, porque recibe las funciones nuevas de OpenAI después que Responses.

### Opción B · Responses
- Favorable, porque es la API más completa para modelos de razonamiento.
- Desfavorable, porque los servidores locales la soportan menos, lo que pondría en riesgo el
  RF-37.

### Opción C · azure-ai-inference
- Desfavorable, porque está retirado, como registra `CLAUDE.md`.

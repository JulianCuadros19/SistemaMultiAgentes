---
estado: aceptada
fecha: 2026-11-04
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0001 (Langfuse sale de las dependencias), ADR-0003 (la traza de las llamadas deja de ser solo un JSONL provisional), ADR-0006 (control de costo en el estado y pausa por presupuesto) y ADR-0014 (interfaces de la pausa y de la traza)
---

# ADR-0016 · Control de costo y traza por nodo

> El ADR-0017 (paso 14) descarta el modo sin nube: Azure OpenAI es el único proveedor de modelos de
> lenguaje. Langfuse sigue fuera, porque su versión autoalojada exigiría cinco contenedores más.

## Contexto y planteamiento del problema

El paso 13 termina cuando **el presupuesto detiene una ejecución que lo supera**. Lo piden dos
requerimientos:
- **RNF-10:** el costo por módulo se monitorea y lo limita un presupuesto configurable que detiene
  la ejecución al superarse.
- **RF-34:** cada ejecución registra su observabilidad. Su criterio: dada una ejecución
  finalizada, al consultar su traza están disponibles los prompts, tokens, costos y tiempos por
  nodo del grafo.

Antes de este paso:
- cada llamada al modelo quedaba en `RegistroLlamada` (prompt y versión, huella, tokens, costo en
  `Decimal`, latencia y error), pero solo en un JSONL, sin los tiempos de los nodos sin modelo ni
  una consulta por sesión;
- `Control.costo_acumulado_usd` existía y nada lo actualizaba;
- `.env.example` reservaba `PRESUPUESTO_MAXIMO_POR_MODULO_USD` y `LANGFUSE_*` sin uso, y el SDK de
  Langfuse estaba en las dependencias sin importarse;
- el ADR-0008 dejó para este paso la tabla `ejecuciones` (Tabla 5 de la arquitectura) y Langfuse.

## Factores de decisión

- RNF-10 y RF-34.
- RNF-04 y RF-37: la traza no sale de la infraestructura, y el sistema debe correr completo sin
  nube (paso 14).
- Decisión 10 de `CLAUDE.md`: el dinero se representa con `Decimal`.
- El flujo sin bloqueos del ADR-0014: cada detención termina en una decisión humana con salida.

## Opciones consideradas

Para la traza:
1. Tablas propias en PostgreSQL, consultadas desde la consola y la web.
2. Las mismas tablas y, además, Langfuse autoalojado.
3. Solo Langfuse autoalojado.

Para la detención:
1. Una pausa por presupuesto, en la que una persona lo amplía o cierra la sesión.
2. Detener la sesión como una falla, que se reanuda después de ampliar el presupuesto.

## Resultado de la decisión

### Decisiones del equipo (2026-11-04)

1. **La traza va a tablas propias, y Langfuse sale del stack** (opción 1).
   - La versión 3 autoalojada de Langfuse exige cinco contenedores más: web, worker, ClickHouse,
     Redis y MinIO.
   - Pesaría en el paso 14, que debe correr sin nube.
   - Las tablas cubren el RF-34.
2. **El presupuesto por módulo es de 1,50 USD por defecto.** Cubre con holgura el máximo de la
   corrida final del ADR-0015 (0,87 USD) y la sesión de pensiones del equipo, que con sus
   devoluciones llegó a 0,97.
3. **Pausa por presupuesto** (opción 1). Al alcanzarlo, la sesión se detiene en la pausa
   «presupuesto». Una persona lo amplía, y queda registrado quién, cuánto, cuándo y por qué, o
   cierra la sesión.

### Decisiones de implementación

4. **Costo de cada nodo** (`llm/traza.py`, `orquestador/grafo.py`).
   - **Captura:** cada nodo corre dentro de `capturar_llamadas()`, un `ContextVar`.
     `InvocadorNodo` anota allí cada `RegistroLlamada` además de entregarla al registrador. Las
     llamadas del cliente simulado ocurren fuera de los nodos y no cuentan.
   - **Envoltura:** `construir_grafo` envuelve los 17 nodos (`_instrumentado`). Al terminar un
     nodo, suma el costo de sus llamadas a `Control.costo_acumulado_usd`. Solo escribe `control`
     si hubo costo o ampliación, así que N7 y N16, que corren en paralelo, no lo escriben a la
     vez.
   - **Simulación:** `ServiciosSimulados.costo_por_llamada` anota un costo en los trabajos de los
     nodos con modelo, para probar el presupuesto sin gastar.
5. **Pausa por presupuesto** (modifica el ADR-0006).
   - **Cuándo:** antes de cada uno de los cinco nodos con modelo (N3, N5, N8, N10 y N14), si lo
     gastado alcanzó el presupuesto, la envoltura pausa con `interrupt` en el punto
     `presupuesto`, con lo gastado, el presupuesto y el nodo.
   - **Respuesta:** la respuesta válida trae el revisor, un presupuesto que supere lo gastado y,
     si se quiere, un motivo. Una inválida vuelve a pausar con un aviso, como en los puntos de
     control.
   - **Registro:** la ampliación queda en `Control.ampliaciones`.
   - **Salida:** cerrar la sesión ya funcionaba desde cualquier pausa.
   - **Estado:** `Control.presupuesto_usd`, que fija N1 con la configuración. Las sesiones
     anteriores, con `None`, no tienen tope.
6. **Traza por nodo en PostgreSQL** (modifica el ADR-0003).
   - **Migración 0002:**
     - `ejecuciones` guarda una fila por nodo, con su inicio, duración, costo y error;
     - `llamadas_modelo` guarda una por llamada, con su prompt y versión, la huella, el modelo,
       los tokens, el costo exacto (`numeric` sin escala) y la latencia;
     - no guarda el contenido de los mensajes, que ya está en los puntos de control.
   - **Observador:** la envoltura informa cada nodo a un observador opcional
     (`orquestador/traza.py`), también si el nodo falla, con su error. Las pausas no se informan:
     un nodo que espera a una persona se informa al terminar, con el tiempo que tardó después de
     la respuesta.
   - **Escritura:** `TrazaEjecuciones` (`persistencia/ejecuciones.py`) guarda cada nodo con sus
     llamadas en una transacción.
   - **Migraciones:** `abrir_operador` migra al arrancar, con un bloqueo consultivo para que dos
     procesos no apliquen la misma migración.
   - **Scripts:** siguen con su JSONL.
7. **Interfaces** (modifica el ADR-0014).
   - La consola y la web ofrecen en la pausa ampliar el presupuesto, con su motivo, o cerrar la
     sesión.
   - Las vistas, el panel, la lista de sesiones y la trazabilidad muestran lo gastado, el
     presupuesto y sus ampliaciones.
   - `multiagente traza ID` y la página «Traza por nodo» muestran la traza en tres partes: el
     resumen por nodo, cada ejecución y cada llamada al modelo.
   - El cliente ve que el equipo revisará su caso.
8. **Configuración.**
   - `PRESUPUESTO_MAXIMO_POR_MODULO_USD` vive en `ConfiguracionOrquestador`.
   - Una variable vacía toma el valor por defecto: la plantilla anterior la dejaba vacía, y un
     `.env` copiado de ella no debía romper la carga.
9. **Montos con cuatro decimales.** Las interfaces muestran los montos con cuatro decimales; el
   estado y los datos de la pausa conservan el valor exacto. La prueba `nube` había mostrado
   «gastó 0.00786000 de 0.005 USD», porque los `Decimal` arrastran su escala.

### Límites

- **El exceso queda acotado a un nodo:** se verifica antes de cada nodo con modelo, no antes de
  cada llamada. El nodo más caro de la corrida final, N10, costó hasta 0,20 USD.
- **Un nodo que falla por infraestructura** deja su costo en la traza, pero no lo suma al
  acumulado, porque su actualización del estado no se escribe. Al reanudarse, vuelve a gastar. No
  ocurrió en la corrida final.
- **En N3, la ampliación se escribe al responder el cliente.** La pausa del diálogo viene en el
  mismo nodo que la del presupuesto, así que la ampliación queda en el estado cuando el cliente
  responde. Si la sesión se cierra antes, no queda registrada.

### Consecuencias

- **Favorable:** ninguna sesión gasta sin límite, y la que lo alcanza espera una decisión humana
  con salida, como las demás detenciones del ADR-0014.
- **Favorable:** el costo de cada nodo, cada prompt con su versión y cada tiempo quedan
  consultables por sesión, sin servicios externos y en la misma base. Es la base de las métricas
  del paso 15.
- **Desfavorable:** no hay una interfaz de exploración como la de Langfuse, como filtros, gráficos
  o comparaciones entre sesiones. Las consultas se hacen en SQL o con la traza en Markdown.
- **Desfavorable:** la traza crece con cada nodo. Basta para cientos de sesiones; su depuración
  queda para cuando haga falta.

### Confirmación

- `pytest tests/unitarias/test_presupuesto.py`: costo, pausa, ampliación, traza en memoria y
  `traza_md`.
- `pytest -m integracion tests/integracion/test_traza_ejecuciones.py`: migración, escritura,
  consulta y operador con el checkpointer de PostgreSQL.
- `pytest -m "nube and embeddings" tests/integracion/test_presupuesto_nube.py`: la condición de
  terminado del paso 13 y el criterio del RF-34.

## Verificación

- **Sin costo:** 741 pruebas unitarias, 34 de integración, 19 de embeddings y 33 del entorno
  aislado.
- **Prueba `nube`**, con el elicitador real, respuestas fijas y un presupuesto de 0,005 USD:
  - la primera ejecución de N3 costó 0,0079 USD y superó el presupuesto, así que la sesión se
    detuvo antes de que N3 volviera a llamar al modelo;
  - ampliado, N3 procesó una respuesta más;
  - la traza en PostgreSQL trae, por nodo, los prompts `elicitador.extraccion@1.7` y
    `elicitador.dialogo@1.10`, los tokens con la caché y el razonamiento, el costo y los tiempos;
  - pasó en 65 s y costó 0,011 USD.

## Cambios para el documento de tesis

- **Stack:** Langfuse sale; la observabilidad es la traza por nodo en PostgreSQL.
- **Tabla 4 (particiones del estado):** `control` guarda además el presupuesto y sus
  ampliaciones. Lo escriben N1, los nodos con modelo, al sumar su costo, y N15.
- **Tabla 5 (entidades):** `ejecuciones` es la traza por nodo y `llamadas_modelo`, una entidad
  nueva con cada llamada al modelo.
- **Vista de despliegue:** la observabilidad deja de ser una plataforma aparte.
- **Flujo:** una sesión que alcanza su presupuesto se detiene antes del siguiente nodo con modelo,
  hasta que una persona lo amplía o la cierra.

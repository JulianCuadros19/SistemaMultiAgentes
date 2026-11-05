# Cifras del sistema y de su evaluación

Corte: 4 de noviembre de 2026, al cierre del paso 14. Es la referencia única de cifras para el
documento de tesis. Cada valor indica su fuente:
- un registro de decisión (ADR) de `docs/decisiones/`;
- un archivo de `docs/mediciones/`;
- un documento fuente.

Las cifras de costo, tokens y llamadas se recalcularon el 4 de noviembre de 2026 desde los
archivos de medición y coinciden con los ADR. Los montos están en dólares (USD) y los tiempos son
del sistema, sin la espera humana ni el cliente simulado, salvo que se diga otra cosa.

## 1. El sistema

| Concepto | Valor | Fuente |
|---|---|---|
| Requerimientos funcionales | 39 (RF-01 a RF-39) | `docs/requerimientos.md` 1.3 |
| Requerimientos no funcionales | 10 (RNF-01 a RNF-10) | `docs/requerimientos.md` 1.3 |
| Nodos del grafo | 17, de ellos 5 con modelo de lenguaje (N3, N5, N8, N10 y N14) | `docs/arquitectura.md` 1.5 |
| Puntos de control humano | 3: N6, N9 y N17 | `docs/arquitectura.md` 1.5 |
| Registros de decisión | 17 (ADR-0001 a ADR-0017) | `docs/decisiones/` |
| Colecciones de conocimiento | 4 | ADR-0007 |
| Documentos del corpus | 36 | ingesta del 2026-11-04 |
| Fragmentos del corpus | 187: elicitación 62, dominio de negocio 40, arquitecturas de referencia 33 y criterios de calidad 52 | base de datos, 2026-11-04 |
| Reglas de calidad verificables | 34 (CAL-…), con CAL-FS-006 agregada en el ADR-0015 | `knowledge_base/criterios_calidad/` |
| Umbral de relevancia de la recuperación | 0,37 | ADR-0007 |
| Arquitecturas del catálogo cerrado | 6: ARQ-01 en capas, ARQ-02 hexagonal, ARQ-03 pipeline por etapas, ARQ-04 servicio API REST, ARQ-05 línea de comandos y ARQ-06 dirigida por eventos | `knowledge_base/arquitecturas_referencia/catalogo/` |
| Límite de turnos del diálogo | 18 (antes 15) | ADR-0015 |
| Iteraciones del ciclo de corrección | 3 por defecto, configurables | ADR-0006 |
| Presupuesto por módulo | 1,50 USD por defecto, configurable | ADR-0016 |
| Modelo de representaciones vectoriales | BGE-M3, local, vector de 1024 dimensiones, descarga de 2,29 GB | ADR-0007 |

**El 4 de noviembre de 2026, en los capítulos de la tesis figuraba:**
- 38 RF;
- 14 ADR;
- 186 fragmentos;
- 582 pruebas.

## 2. Modelos de lenguaje (Azure OpenAI)

**Despliegues:**
- todos son Global Standard, en un recurso de Azure OpenAI de la región South Central US;
- es el único proveedor de modelos de lenguaje del sistema (ADR-0017);
- tarifas en USD por millón de tokens (`config/tarifas_modelos.toml`). Con zona de datos, cada
  tarifa sube un 10 %.

| Nodo | Modelo y versión | Esfuerzo de razonamiento | Límite de salida | Entrada | Caché | Escritura en caché | Salida | Fuente |
|---|---|---|---|---|---|---|---|---|
| N3 diálogo | gpt-5.4-mini 2026-03-17 | low | 4.000 | 0,75 | 0,075 | — | 4,50 | ADR-0009 |
| N5 síntesis y enmienda | gpt-5.4-mini 2026-03-17 | low | 8.000 | 0,75 | 0,075 | — | 4,50 | ADR-0009 |
| N8 diseño | gpt-5 2025-08-07 | low, espera de 300 s | 16.000 | 1,25 | 0,125 | — | 10,00 | ADR-0010 |
| N10 generación | gpt-6.1-sol 2026-09-29 | medium, espera de 600 s | 32.000 | 2,00 | 0,10 | 2,50 | 10,00 | ADR-0011 |
| N14 veredicto | gpt-6-luna 2026-09-22 | low | 6.000 | 0,10 | 0,01 | 0,125 | 0,50 | ADR-0012 |

- **Cliente simulado** de las pruebas: el mismo despliegue de N3 (gpt-5.4-mini).
- **Medido en el ADR-0003,** con gpt-5-nano y el mismo mensaje:

  | Esfuerzo | Tokens de salida | De ellos, razonamiento | Tiempo |
  |---|---|---|---|
  | minimal | 80 | — | 1,7 s |
  | low | 555 | 448 | 4,6 s |
  | medium | 1.340 | 1.216 | 8,9 s |

## 3. Prompts vigentes

| Prompt | Nodo | Versión |
|---|---|---|
| `elicitador.dialogo` | N3 | 1.10 |
| `elicitador.extraccion` | N3 | 1.7 |
| `elicitador.sintesis` | N5 | 1.9 |
| `elicitador.enmienda` | N5 | 1.0 |
| `arquitecto.seleccion` | N8 | 1.2 |
| `arquitecto.parametrizacion` | N8 | 1.6 |
| `desarrollador.generacion` | N10 | 1.9 |
| `tester.veredicto` | N14 | 1.2 |

Fuente: `prompts/<agente>/*.md`. En el documento figuran las versiones 1.2 del arquitecto y del
desarrollador.

## 4. Pruebas automatizadas, sin costo de inferencia

| Momento | Unitarias | Integración | Embeddings | Entorno aislado | Total | Fuente |
|---|---|---|---|---|---|---|
| Verificación del ADR-0014, cifra de la tesis | 507 | 30 | 19 | 26 | 582 | ADR-0014 |
| Cierre del paso 12 | 731 | 31 | 19 | 33 | 814 | ADR-0015 |
| Cierre del paso 13 | 741 | 34 | 19 | 33 | 827 | ADR-0016 |
| **Cierre del paso 14 (vigente)** | **754** | **34** | **19** | **33** | **840** | ADR-0017 |

## 5. Pruebas de cada agente (sin cambios frente a la Tabla 22 del documento)

| Agente | Modelo | Corridas satisfactorias | Costo por corrida | Fuente |
|---|---|---|---|---|
| Elicitador | gpt-5.4-mini | 4 de 4 | 0,018 a 0,033 USD | ADR-0009 |
| Arquitecto | gpt-5 | 9 de 9 | 0,05 a 0,08 USD | ADR-0010 |
| Desarrollador | gpt-6.1-sol | 6 de 6 | 0,06 a 0,21 USD | ADR-0011 |
| Tester | gpt-6-luna | 3 de 3 | 0,003 USD | ADR-0012 |

## 6. Desempeño del agente tester

| Medición | Corpus | Corridas | Defectos detectados | Controles aprobados | Fuente |
|---|---|---|---|---|---|
| Paso 10, figura en la tesis | 16 defectos y 2 controles | 3 | 16 de 16 por corrida | 2 de 2 | ADR-0012 |
| Fase 2 del ADR-0015, juez vigente (prompt 1.2 con segunda opinión) | 21 defectos y 3 controles (24 variantes) | 3 | 63 de 63 (21 por corrida) | 9 de 9 | ADR-0015, `paso-12-tester.jsonl` |

**Detalles de la fase 2:**
- **Marcas sobrantes:** 3 casos quedaron marcados fuera de lo esperado, y las tres eran
  detecciones correctas del defecto D01.
- **Costo:** 0,037 USD.
- **Matriz de confusión:** con la detección de un defecto como caso positivo, no hubo falsos
  positivos ni negativos. Precisión, sensibilidad, F1 y exactitud: 1,00.
- **Rejuzgamiento:** las 49 versiones reales guardadas se juzgaron otra vez con el tester vigente.
  Coincidieron con el veredicto original 40 de 49 con la segunda opinión y 39 de 49 sin ella.
  Costó 0,12 USD.

## 7. Integración de extremo a extremo (paso 11, ya en la tesis)

| Concepto | Valor | Fuente |
|---|---|---|
| Corridas validadas | 9 de 9, sobre 3 casos y 4 arquitecturas | ADR-0013 |
| Tiempo por módulo | 2,7 a 14,3 min, mediana 5,3 min | ADR-0013 |
| Costo por módulo | 0,157 a 0,369 USD, media 0,267 | ADR-0013 |
| Reparto del costo | N10 51 %, N8 31 %, N3 14 %, N5 4 %, N14 0,4 % | ADR-0013 |
| Módulos que llegaron al tester | 14: 11 aprobados en la v1 y 3 en la v2 | ADR-0013 |
| Turnos bajo 15 s | 90 de 91 | ADR-0013 |
| Corrida con persona real | 0,41 USD | ADR-0013 |
| Corrida de 3 casos tras los ajustes de robustez | 3 de 3 validados en la v1, 14,7 min en total, 0,23 a 0,32 USD por módulo | ADR-0014 |

## 8. Corrida ampliada de 20 casos sintéticos

**Método:**
- **Casos:** 20 casos sintéticos, de 3 a 4 por arquitectura del catálogo, en
  `evaluacion/casos/ampliada/`. Cada caso declara la arquitectura que espera, que el cliente
  simulado no ve.
- **Cliente:** simulado por un modelo de lenguaje.
- **Analista simulado** (ADR-0013):
  - en N6 rechaza una vez, con los defectos escalados, y luego aprueba;
  - en N9 aprueba una especificación sin errores;
  - en N17 aprueba lo que aprobó el tester.

| Indicador | Línea base, 2026-10-31 (ADR-0014) | Corrida final, 2026-11-04 (ADR-0015, fase 7) |
|---|---|---|
| Desenlaces | 18 validados, 1 escalado en N17 y 1 en pausa en N6 | **20 validados**, ninguno escalado ni detenido |
| Validados en la primera versión (v1) | 10 de 19 que llegaron a N17 | **18 de 20**; 2 en la v2 por CAL-FS-001 |
| Arquitectura esperada elegida | 19 de 19 que llegaron al diseño | 19 de 20; el caso 01 eligió ARQ-05, justificado |
| Tiempo por módulo | media 4,6 min, máximo 9,0 min | media 5,3 min, máximo 13,2 min (caso 18) |
| Turno de diálogo más largo | 9,4 s | 9,4 s |
| Cierre de la elicitación sobre 30 s | 5 casos, máximo 104 s | 3 casos, máximo 51 s |
| Costo medio por módulo validado | 0,282 USD (0,161 a 0,490) | 0,342 USD (0,180 a 0,871) |
| Costo del sistema | 5,89 USD | 6,85 USD |
| Costo del cliente simulado | 0,62 USD | 0,75 USD |
| Costo total de la corrida | 6,51 USD | 7,59 USD |
| Llamadas a modelos | 745 | 866 |
| Llamadas con error | 0 | 0 |
| Reparto del costo del sistema | N10 45,7 %, N8 22,1 %, N3 17,8 %, N5 13,8 %, N14 0,5 % | N10 40,8 %, N8 27,5 %, N3 20,5 %, N5 10,8 %, N14 0,4 % |
| Primeros intentos de N10 rechazados por la verificación estructural | 7 de 29 | 7 de 23 |
| Resúmenes confirmados por el cliente | 17 de 20, en la medición 2 del ADR-0014 | 16 de 20 |
| Tiempo de reloj | 1 h 46 min | 2 h 1 min |

Fuentes:
- `docs/mediciones/paso-12-corrida-ampliada.jsonl` (línea base) y
  `docs/mediciones/paso-12-corrida-ampliada-2.jsonl` (corrida final);
- los resultados por caso en `evaluacion/resultados/`, que no se versionan.

### Criterios fijados antes de medir (ADR-0015)

| Criterio | Meta | Línea base | Corrida final | ¿Cumple? |
|---|---|---|---|---|
| Validados en la v1 | al menos 15 de 19 | 10 de 19 | 18 de 20 | sí |
| Primeros intentos de N10 rechazados | como máximo 2 de 29 | 7 de 29 | 7 de 23 | no |
| Sesiones escaladas | 0 | 1 | 0 | sí |
| Costo medio por módulo validado | como máximo 0,35 USD | 0,28 | 0,342 | sí, al límite |
| Falsos positivos de «prueba que simula» en el corpus | 0 | — | 0 | sí |
| Turnos sin exploración, en la primera pausa de N6 | como máximo 211 | 211 | 210 | sí, al límite |
| Resúmenes confirmados | al menos 17 de 20 | 17 | 16 | no |
| Reglas ocultas capturadas por caso | al menos 2 de 3 | — | 1,33 de media | aceptado por el equipo |

### Corrida final por caso (ADR-0015, fase 7)

| Caso | Tema | Esperada | Elegida | Desenlace | Bloqueantes de la v1 | Turnos (sin exploración) | Resumen | Min | USD |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Comisiones de corretaje | ARQ-01 | ARQ-05 | validado en la v1 | — | 13 (10) | confirmado | 2,95 | 0,18 |
| 02 | Reajuste del canon | ARQ-01 | ARQ-01 | validado en la v2 | CAL-FS-001 | 13 (9) | confirmado | 4,11 | 0,24 |
| 03 | Mantenimientos preventivos | ARQ-01 | ARQ-01 | validado en la v1 | — | 14 (10) | confirmado | 3,57 | 0,24 |
| 04 | Contratos de arrendamiento | ARQ-02 | ARQ-02 | validado en la v1 | — | 11 (7) | confirmado | 5,74 | 0,36 |
| 05 | Cupo de crédito rotativo | ARQ-02 | ARQ-02 | validado en la v1 | — | 13 (9) | confirmado | 3,08 | 0,19 |
| 06 | Despacho por lotes | ARQ-02 | ARQ-02 | validado en la v1 | — | 10 (7) | confirmado | 3,52 | 0,21 |
| 07 | Conciliación del recaudo | ARQ-03 | ARQ-03 | validado en la v1 | — | 13 (9) | confirmado | 5,69 | 0,36 |
| 08 | Depuración de predios | ARQ-03 | ARQ-03 | validado en la v1 | — | 9 (5) | confirmado | 4,45 | 0,28 |
| 09 | Indicadores desde Excel | ARQ-03 | ARQ-03 | validado en la v1 | — | 11 (8) | confirmado | 4,59 | 0,27 |
| 10 | Tarifa predial por HTTP | ARQ-04 | ARQ-04 | validado en la v1 | — | 18 (17) | sin confirmar | 3,42 | 0,19 |
| 11 | Inmuebles en arriendo | ARQ-04 | ARQ-04 | validado en la v1 | — | 18 (14) | confirmado en el límite | 5,71 | 0,38 |
| 12 | Dígito de verificación del NIT | ARQ-04 | ARQ-04 | validado en la v1 | — | 18 (14) | sin confirmar | 4,02 | 0,29 |
| 13 | Reservas de parqueadero | ARQ-04 | ARQ-04 | validado en la v1 | — | 16 (12) | confirmado | 6,60 | 0,41 |
| 14 | Escaneos de expedientes | ARQ-05 | ARQ-05 | validado en la v1 | — | 13 (9) | confirmado | 4,60 | 0,30 |
| 15 | Rotación de registros | ARQ-05 | ARQ-05 | validado en la v1 | — | 12 (10) | confirmado | 5,66 | 0,37 |
| 16 | Amortización de crédito | ARQ-05 | ARQ-05 | validado en la v1 | — | 12 (9) | confirmado | 4,82 | 0,34 |
| 17 | Trámites catastrales | ARQ-06 | ARQ-06 | validado en la v1 | — | 18 (15) | sin confirmar | 7,80 | 0,54 |
| 18 | Ventas de la caja | ARQ-06 | ARQ-06 | validado en la v2 | CAL-FS-001 | 18 (14) | sin confirmar | 13,16 | 0,87 |
| 19 | Pagos de pensiones | ARQ-06 | ARQ-06 | validado en la v1 | — | 14 (10) | confirmado | 7,15 | 0,50 |
| 20 | Sensores del cuarto frío | ARQ-06 | ARQ-06 | validado en la v1 | — | 16 (12) | confirmado | 5,05 | 0,33 |

### Corrida de línea base por caso (ADR-0014)

| Caso | Desenlace | Bloqueantes de la v1 | Min | USD |
|---|---|---|---|---|
| 01 | validado en la v2 | CAL-FS-002 | 3,24 | 0,21 |
| 02 | validado en la v1 | — | 2,81 | 0,18 |
| 03 | validado en la v1 | — | 2,53 | 0,16 |
| 04 | validado en la v1 | — | 3,84 | 0,26 |
| 05 | validado en la v2 | CAL-FS-001 | 3,05 | 0,20 |
| 06 | validado en la v1 | — | 3,11 | 0,21 |
| 07 | validado en la v1 | — | 4,86 | 0,31 |
| 08 | validado en la v2 | CAL-FS-001 | 4,78 | 0,32 |
| 09 | validado en la v2 | CAL-FS-001 | 4,37 | 0,30 |
| 10 | validado en la v1 | — | 4,14 | 0,27 |
| 11 | validado en la v2 | CAL-FS-001 y CAL-MT-003 | 6,12 | 0,40 |
| 12 | validado en la v2 | CAL-FS-002 | 3,83 | 0,21 |
| 13 | validado en la v2 | CAL-MT-002 | 8,15 | 0,49 |
| 14 | validado en la v1 | — | 4,20 | 0,30 |
| 15 | validado en la v1 | — | 5,05 | 0,33 |
| 16 | validado en la v1 | — | 4,06 | 0,28 |
| 17 | validado en la v2 | CAL-SG-006 | 4,62 | 0,31 |
| 18 | en pausa en N6 | — | 4,03 | 0,20 |
| 19 | escalado en N17 | CAL-FS-001, también en la v2 | 9,01 | 0,61 |
| 20 | validado en la v1 | — | 5,94 | 0,35 |

## 9. Mediciones del pulido (ADR-0015) por fase

| Fase | Qué se midió | Resultado | Costo |
|---|---|---|---|
| 2 · Tester | Corpus de 24 variantes, 3 corridas | 63 de 63 defectos y 9 de 9 controles | 0,037 USD por medición; rejuzgar 49 versiones, 0,12 |
| 3 · Arquitecto | 4 casos de diseño por 3 corridas, prompt 1.4 | 12 de 12 primeros diseños válidos, con recorridos; 0,110 USD por diseño | unos 3 USD |
| 4 · Arquitecto y desarrollador | Prompt 1.5 del arquitecto: 4 casos por 3 corridas | 12 de 12 primeros diseños válidos y ningún reintento; 0,0997 USD por diseño | 2,82 USD en total |
| 4 · Arquitecto y desarrollador | Desarrollador 1.7 con el tester real | 11 corridas: 3 primeros intentos rechazados y 9 v1 aprobadas | incluido en los 2,82 USD |
| 5 · Elicitador | Corridas de 20 elicitaciones y casos con reglas ocultas | reglas ocultas: 1,33 de media por caso | 13,92 USD |
| 6 · Enmienda | Prueba con costo de la enmienda | el requerimiento sube a v0.2 y el módulo corregido sale aprobado | 0,20 USD |
| 7 · Corrida final | 20 casos de extremo a extremo | sección 8 | 7,59 USD |

## 10. Control de costo y traza (ADR-0016)

| Concepto | Valor |
|---|---|
| Presupuesto por defecto | 1,50 USD por módulo (`PRESUPUESTO_MAXIMO_POR_MODULO_USD`) |
| Comprobación | antes de N3, N5, N8, N10 y N14; el exceso queda acotado a un nodo (el más caro de la corrida final, N10, costó hasta 0,20 USD) |
| Prueba con costo | sesión real con presupuesto de 0,005 USD: la primera ejecución de N3 costó 0,0079 USD, la sesión se detuvo antes de volver a llamar al modelo, se amplió y siguió; 65 s y 0,011 USD |
| Traza | tablas `ejecuciones` (una fila por nodo) y `llamadas_modelo` (una por llamada), consultables con `multiagente traza ID` y en la web |

## 11. Entrega en contenedores (ADR-0017)

| Concepto | Valor |
|---|---|
| Servicios de la composición | 6: `db`, `descarga-modelo`, `embeddings`, `sandbox`, `ingesta` y `aplicacion` |
| Arranque con las imágenes construidas | 77 s |
| Ingesta sin cambios | 0,2 s |
| Desde un clon limpio, ingesta del corpus desde cero | 42,7 s, unos 5 min de arranque en total con la descarga del modelo |
| Primera sesión de la verificación | `producir_modulo.py --aprobar`; quedó en pausa en N6, como prevé ese guion con defectos escalados; 0,088 USD |
| Segunda sesión, caso 05 con el analista simulado | validada en N17 en la v1, 46 pruebas generadas aprobadas en el entorno aislado, 3,7 min, 0,245 USD |
| Costo total de la verificación | 0,4044 USD con el cliente simulado: 0,3334 del sistema y 0,0711 del cliente; 79 llamadas (`docs/mediciones/paso-14-contenedores.jsonl`) |
| Construcción sin caché de la imagen del entorno aislado | primer intento: falló a los 998 s por la lentitud de PyPI (unos 17 KB/s); segundo: 1.958 s, sin errores |
| Usuario de la aplicación | UID 1000, grupos 1000 y 1001 (el del socket de Docker); el entorno aislado corre con UID 10001 y sin red |

## 12. Sesión de ejemplo (sección 4.12 del documento, sin cambios)

| Concepto | Valor |
|---|---|
| Turnos de diálogo | 7, media 3,7 s, máximo 4,8 s |
| Tiempo total | 6,6 min |
| Costo | 0,41 USD, 0,28 de ellos en N10 |

## 13. Evaluación del paso 15 (ADR-0019)

Fuente: `docs/evaluacion/informe-objetivo-4.md`. Regenerables con `scripts/tabla_objetivo_4.py` y
`scripts/matriz_tester_oraculo.py`.

### Comparación con las pruebas de referencia

| Métrica | Sistema | Modelo con diálogo | Modelo de un solo prompt |
|---|---|---|---|
| Implementaciones | 12 | 15 | 9 |
| Verificaciones aprobadas | 115 de 119 | 140 de 148 | 90 de 90 |
| Tasa de errores | 3,4 % | 5,4 % | 0,0 % |
| Implementaciones sin errores | 9 de 12 | 13 de 15 | 9 de 9 |
| Costo medio por módulo | 0,358 USD | 0,170 USD | 0,104 USD |
| Tiempo medio de máquina | 5,9 min | 2,9 min | 2,5 min |
| Con pruebas propias que fallan | 1 de 12 | 3 de 15 | 2 de 9 |
| Hallazgos de Ruff por implementación | 0,3 | 1,2 | 1,0 |

- **Casos:** 9, con las seis arquitecturas; 90 verificaciones y 35 mutantes detectados.
- **Prueba de signos:** costo y tiempo, 9 a 0 frente a cada línea base (p = 0,004). Errores frente al modelo con diálogo: 2 a 2,
  con 5 empates (p = 1,000).
- **Modelo con diálogo sin la corrida 3 del caso 16:** 137 de 138, 0,7 %.
- **Modelo con diálogo:** 14,0 turnos del cliente de media y 1 corrida en el límite.

### Corrida ampliada de 20 casos

| Concepto | Valor |
|---|---|
| Desenlace | 16 validados, 11 en la v1; 4 escalados |
| Arquitectura esperada | 20 de 20 |
| Tiempo del sistema | media de 6,6 min, de 3,3 a 10,3 |
| Costo por módulo | media de 0,403 USD, de 0,181 a 0,690 |
| Costo por módulo validado | media de 0,391 USD |
| Costo por nodo | N10 44,8 %, N8 27,1 %, N3 18,2 %, N5 9,3 % y N14 0,7 % |
| Turno más largo | 16,2 s (caso 05); el siguiente, 12,4 s |
| Cierre de la elicitación más largo | 77,3 s (caso 15) |
| Diálogo en la primera pausa de N6 | 272 turnos, 205 sin exploración, 19 resúmenes confirmados y 1 sesión en el límite |
| Primeros intentos de N10 rechazados | 4 de 35 |

**Corrida adicional:** los casos 02, 12 y 16, sin escalar; 2 en la v1 y 1 en la v2.

### Tester

| Medición | Resultado |
|---|---|
| Corpus de 21 defectos y 3 controles, 3 corridas | 63 de 63 y 9 de 9; precisión, sensibilidad, F1 y exactitud de 1,00; 0,04 USD |
| Juez por caso en el corpus | 261 casos, 5 rechazos falsos, sin cambiar veredictos |
| Frente al oráculo, 21 versiones | 4 verdaderos positivos, 8 falsos positivos, 2 falsos negativos y 7 verdaderos negativos |
| Métricas frente al oráculo | exactitud 0,52, precisión 0,33, sensibilidad 0,67 y F1 0,44 |
| Si los 2 rechazos justificados del caso 10 cuentan como aciertos | exactitud 0,62, precisión 0,50, sensibilidad 0,75 y F1 0,60 |
| Rejuicios de una prueba idéntica en la corrida ampliada | 3 cambios de 124 |

### Métricas RAGs, 20 sesiones

| Colección | Agente | Fidelidad | Relevancia de la respuesta | Relevancia del contexto |
|---|---|---|---|---|
| `elicitacion` | Elicitador | 0,81 | 0,56 | 0,57 |
| `dominio_negocio` | Elicitador | 0,81 | 0,56 | 0,10 |
| `arquitecturas_referencia` | Arquitecto | 0,84 | 0,51 | 0,67 |
| `criterios_calidad` | Tester | 0,47 (cerca de 0,68 sin las afirmaciones de ejecución) | 0,37 | 0,42 |

### Despliegue de demostración (ADR-0020)

| Concepto | Valor |
|---|---|
| Máquina | `Standard_D4s_v4`, 4 vCPU y 16 GiB, Central US, Ubuntu 24.04 |
| Arranque desde cero | unos 5 min |
| Módulo de verificación | caso 01, validado en la v1, 3,15 min y 0,198 USD |
| Reinicio | el enlace volvió en 32 s |
| Memoria de los embeddings | 11,17 GiB |

### Pruebas sin costo al cierre

812 unitarias, 34 de integración, 19 de embeddings y 44 del entorno aislado.

### Costo del paso

16,74 USD de inferencia, con el cliente simulado, frente a un tope de 17.

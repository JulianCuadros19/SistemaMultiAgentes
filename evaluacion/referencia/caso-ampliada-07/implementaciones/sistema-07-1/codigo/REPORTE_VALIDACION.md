# Reporte de validación · versión 1

**Veredicto: APROBADO** · 5 de 5 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_recaudo.py::test_rf_01_esc_01_csv_y_resumen_de_los_cuatro_estados'] pasan. La prueba ejecuta el lote mediante `Orquestador().ejecutar`, comprueba en el CSV las seis columnas exactas y valida los registros de los cuatro estados y el resumen `Resumen(1, 1, 1, 1)`, que cuenta cada estado. |
| CP-RF-01-ESC-02 | sí | ['tests/test_recaudo.py::test_rf_01_esc_02_diferencia_firmada'] pasan. La prueba crea un pago distinto al valor facturado, ejecuta `conciliar_lotes` y compara el registro con estado `diferencia` y el valor firmado esperado; cubre tanto pago inferior (`-10`) como superior (`10`). |
| CP-RF-01-ESC-03 | sí | ['tests/test_recaudo.py::test_rf_01_esc_03_columna_faltante'] pasan. La prueba quita una columna requerida de cada tipo de archivo y exige que `leer_archivos` lance `ColumnaFaltante`; verifica además que la excepción identifique el archivo y la columna faltante. |
| CP-RF-01-ESC-04 | sí | ['tests/test_recaudo.py::test_rf_01_esc_04_fila_invalida_no_detiene_lote'] pasan. La prueba procesa una fila con valor no numérico junto con una fila válida y comprueba que la inválida queda como pendiente, sin valor pagado, mientras la válida se concilia; así demuestra el rechazo de la fila sin detener el lote. |
| CP-RF-01-ESC-05 | sí | ['tests/test_recaudo.py::test_rf_01_esc_05_reanudar_conciliacion_sin_repetir_etapas', 'tests/test_recaudo.py::test_rf_01_esc_05_reintentar_escritura_realmente_fallida'] pasan. Una prueba reanuda desde conciliación y comprueba que los contadores de lectura y normalización no aumentan; otra provoca un fallo real de escritura, reintenta desde esa etapa y verifica los contadores para confirmar que el procesamiento continúa sin repetir las etapas previas. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| contratos.esquemas | sí | PagoEntrada, Factura, DatosLeidos, PagoNormalizado, DatosNormalizados, RegistroResultado, Resumen, ResultadoConciliacion | — | — |
| etapas.lectura | sí | leer_archivos, ColumnaFaltante | — | — |
| etapas.normalizacion | sí | normalizar_datos | — | — |
| etapas.conciliacion | sí | conciliar_lotes | — | — |
| etapas.escritura | sí | escribir_resultados, EscrituraError | — | — |
| entrada_salida.archivos | sí | generar_csv_banco_a, generar_csv_banco_b, generar_csv_banco_c, generar_csv_facturas, leer_csv_resultados, escribir_texto | — | — |
| orquestacion.pipeline | sí | Orquestador, Orquestador.ejecutar, Orquestador.ejecutar_hasta, Orquestador.reintentar_desde, Orquestador.obtener_contadores | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 38 ({'paso': 38}), en 1158 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
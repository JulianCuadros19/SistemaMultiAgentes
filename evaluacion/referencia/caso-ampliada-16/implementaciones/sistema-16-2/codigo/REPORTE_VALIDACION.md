# Reporte de validación · versión 1

**Veredicto: APROBADO** · 10 de 10 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_simulador.py::test_rf_01_esc_01_cuota_valida'] pasan. La prueba ejecuta `ejecutar_cuota` con los tres valores del escenario y exige que el resultado sea exactamente `Decimal('1399472')`, la cuota mensual indicada. |
| CP-RF-01-ESC-02 | sí | ['tests/test_simulador.py::test_rf_01_esc_02_limites_inferiores'] pasan. La prueba calcula la cuota con los datos indicados y verifica el valor redondeado exacto `Decimal('837833')`, además de que no tiene decimales. |
| CP-RF-01-ESC-03 | sí | ['tests/test_simulador.py::test_rf_01_esc_03_falta_tasa'] pasan. La prueba llama a `ejecutar_cuota` sin tasa y exige `ErrorCLI` con un mensaje que identifica la tasa, un código de salida distinto de cero y mensaje no vacío. |
| CP-RF-02-ESC-01 | sí | ['tests/test_simulador.py::test_rf_02_esc_01_detalle_mensual'] pasan. La prueba obtiene la tabla mediante `ejecutar_tabla` con los valores del escenario y verifica sus 120 filas, los campos de saldo, interés y abono, y la continuidad entre meses; esto comprueba el detalle mensual solicitado. |
| CP-RF-02-ESC-02 | sí | ['tests/test_simulador.py::test_rf_02_esc_02_exportar_csv'] pasan. La prueba solicita guardar la tabla con `ejecutar_tabla`, comprueba que el CSV exista y compara sus filas y columnas con la tabla producida, verificando que se entrega el detalle en el archivo. |
| CP-RF-02-ESC-03 | sí | ['tests/test_simulador.py::test_rf_02_esc_03_ajuste_final'] pasan. La prueba verifica que la última fila producida por `ejecutar_tabla` tenga saldo final cero, que su abono cubra el saldo inicial y que su cuota se ajuste con el interés; también comprueba que las cuotas anteriores mantengan el valor regular. |
| CP-RF-02-ESC-04 | sí | ['tests/test_simulador.py::test_rf_02_esc_04_falta_monto'] pasan. La prueba llama a `ejecutar_tabla` sin monto y exige `ErrorCLI` con mensaje que menciona el monto y código distinto de cero; además comprueba que no se creó el CSV. |
| CP-RF-03-ESC-01 | sí | ['tests/test_simulador.py::test_rf_03_esc_01_resumen_coherente'] pasan. La prueba solicita el resumen y verifica que el total pagado y los intereses coincidan con las sumas de las cuotas e intereses de la tabla generada para los mismos datos, comprobando ambos valores del resumen. |
| CP-RF-03-ESC-02 | sí | ['tests/test_simulador.py::test_rf_03_esc_02_limites_superiores'] pasan. La prueba solicita el resumen con los valores del escenario y verifica que ambos totales estén redondeados al peso mediante exponente cero; también comprueba que representan pagos e intereses positivos y que guardan la relación con el capital. |
| CP-RF-03-ESC-03 | sí | ['tests/test_simulador.py::test_rf_03_esc_03_plazo_invalido'] pasan. La prueba llama a `ejecutar_resumen` con el plazo de 10 meses y exige `ErrorCLI` con mensaje que menciona el plazo, código distinto de cero y mensaje no vacío. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.credito | sí | AmortizacionFila, Resumen, tasa_mensual, cuota_fija, redondear_peso | — | — |
| servicios.simulador | sí | ValidacionError, calcular_cuota, generar_tabla, calcular_resumen | — | — |
| entrada_salida.csv_salida | sí | TablaCSV, TablaCSV.guardar, TablaCSV.existe | — | — |
| comandos.cli | sí | ErrorCLI, ejecutar_cuota, ejecutar_tabla, ejecutar_resumen | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 73 ({'paso': 73}), en 1283 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
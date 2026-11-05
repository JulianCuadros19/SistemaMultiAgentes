# Reporte de validación · versión 3

**Veredicto: RECHAZADO** · 8 de 9 casos cumplen · hallazgos: 1 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_simulacion.py::test_rf_01_esc_01_calcula_cuota'] pasan. El fixture `parametros` prepara monto 100.000.000, plazo 120 y tasa 12%; la prueba llama a `calcular_cuota` y compara el resultado exactamente con `1399472`, como pide el escenario. |
| CP-RF-01-ESC-02 | sí | ['tests/test_simulacion.py::test_rf_01_esc_02_redondea_al_peso'] pasan. La prueba construye los parámetros concretos del escenario, invoca `calcular_cuota` y verifica tanto que la cuota sea un entero como que sea exactamente `837833` pesos. |
| CP-RF-01-ESC-03 | sí | ['tests/test_simulacion.py::test_rf_01_esc_03_rechaza_tasa'] pasan. Con la tasa del escenario modificada a cero, la prueba exige `DatosInvalidosError` con mensaje sobre la tasa; además ejecuta la operación en un proceso y comprueba código de salida distinto de cero y el mensaje concreto de error. |
| CP-RF-02-ESC-01 | sí | ['tests/test_simulacion.py::test_rf_02_esc_01_guarda_csv'] pasan. El fixture prepara los datos indicados y `generar_tabla` recibe un `EscritorTablaCSV`; la prueba verifica que se crea el archivo, que contiene encabezado y 120 filas de datos, y que la última fila corresponde a la tabla generada. |
| CP-RF-02-ESC-02 | sí | ['tests/test_simulacion.py::test_rf_02_esc_02_no_guarda_csv'] pasan. La prueba solicita `generar_tabla` sin escritor y verifica que devuelve 120 filas de amortización y que no se crea ningún archivo CSV en el directorio de trabajo. |
| CP-RF-02-ESC-03 | sí | ['tests/test_simulacion.py::test_rf_02_esc_03_rechaza_plazo'] pasan. Con plazo de 6 meses, la prueba exige `DatosInvalidosError` con referencia al plazo, verifica que no se crea el CSV y comprueba en un proceso que hay salida no nula y un mensaje explícito de rango inválido. |
| CP-RF-03-ESC-01 | sí | ['tests/test_simulacion.py::test_rf_03_esc_01_muestra_resumen'] pasan. Con los parámetros del fixture, `calcular_resumen` devuelve el resumen y la prueba compara exactamente sus totales pagado e intereses con valores calculados por un oráculo independiente. |
| CP-RF-03-ESC-02 | no | ['tests/test_simulacion.py::test_rf_03_esc_02_resumen_separado'] pasan. La prueba llama a `calcular_resumen` y confirma que no se crea un archivo, pero no verifica que no se entregue la tabla de amortización; comprobar que el resumen es de tipo `ResumenCredito` no demuestra esa ausencia. |
| CP-RF-03-ESC-03 | sí | ['tests/test_simulacion.py::test_rf_03_esc_03_rechaza_monto'] pasan. Con monto de 9.000.000, la prueba exige `DatosInvalidosError` con mención al monto y, en un proceso, verifica código distinto de cero y el mensaje concreto de rango inválido. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.credito | sí | ParametrosCredito, ParametrosCredito.validar, ParametrosCredito.tasa_mensual, AmortizacionFila, ResumenCredito, DatosInvalidosError | — | — |
| servicios.simulacion | sí | calcular_cuota, generar_tabla, calcular_resumen | — | — |
| entrada_salida.tabla_csv | sí | EscritorTablaCSV, EscritorTablaCSV.escribir, EscritorTablaCSV.existe, EscritorTablaCSV.leer | — | — |
| comandos.simulador | sí | main_cuota, main_tabla, main_resumen | — | — |

## Hallazgos

### Severidad alta

- **CAL-FS-001** · `tests/test_simulacion.py::test_rf_03_esc_02_resumen_separado` · La prueba pasa, pero no verifica el escenario (dado que el asesor de crédito ingresa un monto de 100.000.000, un plazo en meses de 120 y una tasa efectiva anual de 12% y no solicita la tabla de amortización, cuando solicita mostrar el resumen, entonces el sistema muestra el resumen sin entregar la tabla de amortización): La prueba llama a `calcular_resumen` y confirma que no se crea un archivo, pero no verifica que no se entregue la tabla de amortización; comprobar que el resumen es de tipo `ResumenCredito` no demuestra esa ausencia. *Sugerencia:* Verificar explícitamente que la operación de resumen no devuelve ni entrega filas de amortización, usando la interfaz pública disponible para observar ese resultado o efecto.


## Ejecución en el entorno aislado

- Pruebas: 45 ({'paso': 45}), en 1445 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
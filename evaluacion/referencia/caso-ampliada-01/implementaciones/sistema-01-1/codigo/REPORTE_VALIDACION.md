# Reporte de validación · versión 1

**Veredicto: APROBADO** · 5 de 5 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_liquidacion.py::test_rf_01_esc_01_venta_con_un_asesor'] pasan. `test_rf_01_esc_01_venta_con_un_asesor` llama a `calcular_comision` con venta, 1 asesor, cerrado y 1000000, y compara ambas comisiones exactamente con 30000 y 300000 pesos. |
| CP-RF-01-ESC-02 | sí | ['tests/test_liquidacion.py::test_rf_01_esc_02_arriendo_con_dos_asesores'] pasan. `test_rf_01_esc_02_arriendo_con_dos_asesores` usa los valores del escenario y verifica exactamente que la comisión de la inmobiliaria sea 1000000 y la de cada asesor 300000 pesos. |
| CP-RF-01-ESC-03 | sí | ['tests/test_liquidacion.py::test_rf_01_esc_03_rechazar_negocio_abierto'] pasan. `test_rf_01_esc_03_rechazar_negocio_abierto` intenta liquidar el negocio abierto con los datos indicados y exige `NegocioAbiertoError` con el mensaje exacto «El negocio aún no está cerrado». |
| CP-RF-01-ESC-04 | sí | ['tests/test_liquidacion.py::test_rf_01_esc_04_minimo_por_asesor'] pasan. `test_rf_01_esc_04_minimo_por_asesor` calcula con venta cerrada, 2 asesores y 5000000, y verifica que la comisión de cada asesor sea exactamente 300000 pesos, como pide el escenario. |
| CP-RF-01-ESC-05 | sí | ['tests/test_liquidacion.py::test_rf_01_esc_05_rechazar_valor_cero'] pasan. `test_rf_01_esc_05_rechazar_valor_cero` usa arriendo cerrado con valor cero y exige el rechazo mediante `pytest.raises(ValorNoPermitidoError)`, suficiente para el «se rechaza» del escenario. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.comisiones | sí | Negocio, ResultadoComision, calcular_para_negocio, NegocioAbiertoError, ValorNoPermitidoError, ReglaNegocioError | — | — |
| aplicacion.liquidacion | sí | calcular_comision | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 42 ({'paso': 42}), en 1090 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
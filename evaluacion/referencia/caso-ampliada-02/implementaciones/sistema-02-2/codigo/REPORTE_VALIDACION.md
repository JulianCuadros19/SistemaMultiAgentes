# Reporte de validación · versión 1

**Veredicto: APROBADO** · 5 de 5 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_reajuste.py::test_rf_01_esc_01_ipc_dentro_del_pacto'] pasan. La prueba llama a `calcular_reajuste` con los valores del escenario y compara explícitamente porcentaje aplicado (5.20), incremento (52000) y canon reajustado (1052000). |
| CP-RF-01-ESC-02 | sí | ['tests/test_reajuste.py::test_rf_01_esc_02_limite_pactado'] pasan. La prueba ejecuta `calcular_reajuste` con los datos indicados y verifica los tres resultados exactos: porcentaje 5.00, incremento 50000 y canon 1050000. |
| CP-RF-01-ESC-03 | sí | ['tests/test_reajuste.py::test_rf_01_esc_03_ipc_cero'] pasan. La prueba usa el IPC cero indicado y comprueba exactamente porcentaje aplicado 0.00, incremento 0 y canon reajustado 1000000. |
| CP-RF-01-ESC-04 | sí | ['tests/test_reajuste.py::test_rf_01_esc_04_periodo_insuficiente'] pasan. Con las fechas del escenario, la prueba exige que `calcular_reajuste` lance `PeriodoInsuficienteDoceMeses`, lo que verifica el rechazo del reajuste por no cumplir doce meses. |
| CP-RF-01-ESC-05 | sí | ['tests/test_reajuste.py::test_rf_01_esc_05_canon_faltante'] pasan. La prueba llama a `calcular_reajuste` con `canon_actual=None` y exige `DatosObligatoriosFaltantes`, verificando que no se obtiene un resultado con los campos del reajuste. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.reajuste | sí | ResultadoReajuste, DatosObligatoriosFaltantes, PeriodoInsuficienteDoceMeses, ValorInvalido, validar_periodo_doce_meses, calcular_porcentaje_aplicable, redondear_a_centena_mas_cercana | — | — |
| aplicacion.calculo_reajuste | sí | calcular_reajuste | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 29 ({'paso': 29}), en 1160 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
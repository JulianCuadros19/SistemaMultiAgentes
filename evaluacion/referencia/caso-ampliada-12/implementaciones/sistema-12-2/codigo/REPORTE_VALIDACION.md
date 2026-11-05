# Reporte de validación · versión 2

**Veredicto: APROBADO** · 6 de 6 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_nit_validacion.py::test_rf_01_esc_01_calcula_digito_esperado', 'tests/test_rutas_nit.py::test_rf_01_esc_01_http_calcula_digito'] pasan. `test_rf_01_esc_01_calcula_digito_esperado` llama `calcular_digito("900123456")` y compara con el dígito exacto `8`; la prueba HTTP asociada también verifica código 200 y `digito_esperado: 8`. |
| CP-RF-01-ESC-02 | sí | ['tests/test_nit_validacion.py::test_rf_01_esc_02_acepta_separadores', 'tests/test_rutas_nit.py::test_rf_01_esc_02_http_acepta_separadores'] pasan. `test_rf_01_esc_02_acepta_separadores` ejecuta el cálculo con `900123456-7` y compara el resultado exacto con `8`; la prueba HTTP verifica igualmente la respuesta exacta para ese valor. |
| CP-RF-01-ESC-03 | sí | ['tests/test_nit_validacion.py::test_rf_01_esc_03_rechaza_letras', 'tests/test_rutas_nit.py::test_rf_01_esc_03_http_rechaza_letras'] pasan. `test_rf_01_esc_03_rechaza_letras` exige que el cálculo de `90012A456` lance `NITSoloDigitosError` con el mensaje exacto solicitado; la prueba HTTP asociada también comprueba el rechazo y el detalle exacto. |
| CP-RF-02-ESC-01 | sí | ['tests/test_nit_validacion.py::test_rf_02_esc_01_valida_nit_correcto', 'tests/test_rutas_nit.py::test_rf_02_esc_01_http_valida_nit'] pasan. `test_rf_02_esc_01_valida_nit_correcto` compara el resultado de validar `900123456-8` con `(True, 8)`, verificando tanto que sea válido como el dígito esperado. La prueba HTTP comprueba los mismos valores. |
| CP-RF-02-ESC-02 | sí | ['tests/test_nit_validacion.py::test_rf_02_esc_02_informa_digito_incorrecto', 'tests/test_rutas_nit.py::test_rf_02_esc_02_http_informa_digito_incorrecto'] pasan. `test_rf_02_esc_02_informa_digito_incorrecto` compara el resultado de validar `900123456-7` con `(False, 8)`, verificando el rechazo de validez y el dígito esperado; la prueba HTTP confirma ambos campos. |
| CP-RF-02-ESC-03 | sí | ['tests/test_nit_validacion.py::test_rf_02_esc_03_rechaza_mas_de_quince_digitos', 'tests/test_rutas_nit.py::test_rf_02_esc_03_http_rechaza_longitud'] pasan. `test_rf_02_esc_03_rechaza_mas_de_quince_digitos` exige que validar el NIT de 16 dígitos lance `NITMaximoDigitosError` con el mensaje exacto; la prueba HTTP asociada comprueba el código de rechazo y el detalle exacto. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| rutas.nit | sí | crear_app | — | — |
| esquemas.nit | sí | CalculoDigitoRequest, CalculoDigitoResponse, ValidarNitRequest, ValidarNitResponse | — | — |
| servicios.nit_validacion | sí | NITSoloDigitosError, NITMaximoDigitosError, calcular_digito, validar_nit | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 51 ({'paso': 51}), en 1538 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
# Reporte de validación · versión 1

**Veredicto: APROBADO** · 7 de 7 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_nit.py::test_rf_01_esc_01_calcular_numero_valido'] pasan. La prueba construye `NumeroEntrada(numero="900123456")`, invoca la función de ruta `calcular_digito` y comprueba que `respuesta.digito_calculado == 8`, el valor exacto requerido. |
| CP-RF-01-ESC-02 | sí | ['tests/test_nit.py::test_rf_01_esc_02_calcular_con_separadores'] pasan. La prueba usa `NumeroEntrada(numero="900.123.456")`, llama a `calcular_digito` y verifica `respuesta.digito_calculado == 8`, tal como pide el escenario. |
| CP-RF-01-ESC-03 | sí | ['tests/test_nit.py::test_rf_01_esc_03_rechazar_longitud_excesiva'] pasan. Con `NumeroEntrada(numero="1234567890123456")`, la prueba invoca `calcular_digito` y exige que lance `HTTPException` con estado 400 y el mensaje exacto de longitud máxima; verifica el rechazo solicitado. |
| CP-RF-02-ESC-01 | sí | ['tests/test_nit.py::test_rf_02_esc_01_validar_digito_correcto'] pasan. La prueba entrega a `validar_nit` el NIT `900.123.456-8` y comprueba que es válido y que el dígito esperado es 8; además verifica que el calculado también sea 8. |
| CP-RF-02-ESC-02 | sí | ['tests/test_nit.py::test_rf_02_esc_02_validar_digito_incorrecto'] pasan. La prueba valida `900123456-7` y verifica que `validez_del_nit is False` y que `digito_esperado == 8`, los dos resultados requeridos; también comprueba el dígito calculado. |
| CP-RF-02-ESC-03 | sí | ['tests/test_nit.py::test_rf_02_esc_03_rechazar_letras'] pasan. La prueba envía `90012A456` a `validar_nit` y exige una `HTTPException` con estado 400 y detalle exactamente igual a «El NIT solo admite dígitos». |
| CP-RF-02-ESC-04 | sí | ['tests/test_nit.py::test_rf_02_esc_04_rechazar_longitud_excesiva'] pasan. La prueba envía el NIT de 16 dígitos a `validar_nit` y exige una `HTTPException` con estado 400 y el detalle exacto «El NIT admite como máximo 15 dígitos». |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| esquemas.nit | sí | NumeroEntrada, DigitoRespuesta, ValidacionEntrada, ValidacionRespuesta | — | — |
| servicios.nit | sí | calcular_digito, validar_nit, MaxLengthExceededError, InvalidCharactersError | — | — |
| rutas.nit | sí | calcular_digito, validar_nit | — | — |

## Hallazgos

Sin hallazgos.

## Ejecución en el entorno aislado

- Pruebas: 39 ({'paso': 39}), en 1677 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
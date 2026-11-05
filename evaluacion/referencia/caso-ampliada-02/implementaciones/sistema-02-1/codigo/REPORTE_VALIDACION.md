# Reporte de validación · versión 3

**Veredicto: RECHAZADO** · 4 de 5 casos cumplen · hallazgos: 1 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_reajuste.py::test_rf_01_esc_01_ipc_menor_al_pactado'] pasan. La prueba llama a `realizar_reajuste` con canon 1.200.000, porcentaje pactado 10, IPC 5,20 y fechas separadas por doce meses; compara el resultado completo con porcentaje 5,20, nuevo canon 1.262.400 e incremento 62.400. |
| CP-RF-01-ESC-02 | sí | ['tests/test_reajuste.py::test_rf_01_esc_02_porcentaje_pactado_como_tope'] pasan. La prueba ejecuta `realizar_reajuste` con los valores y plazo del escenario y verifica mediante igualdad que el nuevo canon es 978.500 y el porcentaje aplicado es 3; también comprueba el incremento coherente de 28.500. |
| CP-RF-01-ESC-03 | sí | ['tests/test_reajuste.py::test_rf_01_esc_03_ipc_no_positivo'] pasan. La prueba llama a `realizar_reajuste` con los valores del escenario y verifica que el porcentaje aplicado y el incremento son cero y que el canon se conserva en 850.000. La parametrización añade casos de IPC negativo, sin contradecir el escenario. |
| CP-RF-01-ESC-04 | no | Sus pruebas no se ejecutaron o se omitieron: ['tests/test_reajuste.py::test_rf_01_esc_04_redondeo_a_centena'] |
| CP-RF-01-ESC-05 | sí | ['tests/test_reajuste.py::test_rf_01_esc_05_plazo_insuficiente'] pasan. La prueba intenta el reajuste antes de cumplir doce meses, exige `MesesInsuficientesError` con `pytest.raises` y compara su texto exactamente con el mensaje especificado. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.reajuste | sí | ReajusteResultado, MesesInsuficientesError, calcular_reajuste | — | — |
| aplicacion.reajuste | sí | realizar_reajuste | — | — |

## Hallazgos

### Severidad alta

- **CAL-FS-002** · `CP-RF-01-ESC-04` · Las pruebas ['tests/test_reajuste.py::test_rf_01_esc_04_redondeo_a_centena'] no se ejecutaron o se omitieron *Sugerencia:* Corrige el código para que la prueba pase sin debilitar lo que verifica.


## Ejecución en el entorno aislado

- Pruebas: 34 ({'paso': 33, 'omitida': 1}), en 1176 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
# Reporte de validación · versión 3

**Veredicto: APROBADO** · 8 de 8 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 1 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_tarifas.py::test_rf_01_esc_01_consulta_residencial'] pasan. La prueba consulta `obtener_tarifa("residencial", 3)` y compara el resultado completo con `TarifaResultado(8, 3)`, verificando la tarifa y el estrato aplicado exigidos. |
| CP-RF-01-ESC-02 | sí | ['tests/test_tarifas.py::test_rf_01_esc_02_consulta_comercial'] pasan. La prueba consulta `obtener_tarifa("comercial")` y verifica `resultado.tarifa == 11` y `resultado.estrato_aplicado is None`, tal como requiere el escenario. |
| CP-RF-01-ESC-03 | sí | ['tests/test_tarifas.py::test_rf_01_esc_03_destino_desconocido'] pasan. La prueba consulta un destino no reconocido y exige `DestinoNoReconocidoError` con el mensaje exacto mediante `pytest.raises` y `match`. |
| CP-RF-01-ESC-04 | sí | ['tests/test_tarifas.py::test_rf_01_esc_04_estrato_fuera_de_rango'] pasan. La prueba consulta el destino residencial con estrato 7 y exige `EstratoInvalidoError` con el mensaje exacto requerido. |
| CP-RF-02-ESC-01 | sí | ['tests/test_tarifas.py::test_rf_02_esc_01_calculo_residencial'] pasan. La prueba calcula el impuesto para avalúo 120.000.000, destino residencial y estrato 3, y compara el resultado completo con `CalculoImpuestoResultado(960_000, 8, 3)`. |
| CP-RF-02-ESC-02 | sí | ['tests/test_tarifas.py::test_rf_02_esc_02_calculo_comercial'] pasan. La prueba verifica el impuesto exacto `1_100_000`, su tipo `int` (sin decimales), la tarifa 11 y que no se informa estrato aplicado. |
| CP-RF-02-ESC-03 | sí | ['tests/test_tarifas.py::test_rf_02_esc_03_avaluo_cero'] pasan. La prueba calcula con avalúo 0 y exige `AvaluoNoValidoError` con el mensaje exacto indicado en el escenario. |
| CP-RF-02-ESC-04 | sí | ['tests/test_tarifas.py::test_rf_02_esc_04_destino_desconocido'] pasan. La prueba calcula con avalúo 50.000.000 y destino no reconocido, y exige `DestinoNoReconocidoError` con el mensaje exacto requerido. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| rutas.tarifas | sí | construir_router | — | — |
| esquemas.tarifas | sí | ConsultaTarifaRequest, ConsultaTarifaResponse, CalculoImpuestoRequest, CalculoImpuestoResponse | — | — |
| servicios.tarifas | sí | TarifaResultado, CalculoImpuestoResultado, DestinoNoReconocidoError, EstratoInvalidoError, AvaluoNoValidoError, obtener_tarifa, calcular_impuesto | — | — |

## Hallazgos

### Severidad baja

- **CAL-MT-009** · `src/esquemas/tarifas.py:13` · B010: Do not call `setattr` with a constant attribute value. It is not any safer than normal property access. *Sugerencia:* Ajusta el código a la configuración de estilo del sistema.


## Ejecución en el entorno aislado

- Pruebas: 62 ({'paso': 62}), en 1602 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
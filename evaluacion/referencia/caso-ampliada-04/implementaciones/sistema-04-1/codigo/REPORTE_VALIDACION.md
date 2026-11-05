# Reporte de validación · versión 1

**Veredicto: APROBADO** · 12 de 12 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 2 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_contratos.py::test_rf_01_esc_01_activacion_exitosa'] pasan. La prueba prepara C-100 como borrador con documento y canon indicados, llama a `activar_contrato` mediante `_activar` y verifica el estado vigente, el usuario y la fecha devueltos, además de que el contrato almacenado coincide con el resultado. |
| CP-RF-01-ESC-02 | sí | ['tests/test_contratos.py::test_rf_01_esc_02_documento_obligatorio'] pasan. Prepara C-101 como borrador sin documento y exige `DocumentoArrendatarioObligatorio` con un mensaje que indica que el documento es obligatorio; también verifica que el contrato no cambió. |
| CP-RF-01-ESC-03 | sí | ['tests/test_contratos.py::test_rf_01_esc_03_fecha_incorrecta'] pasan. Activa con las fechas indicadas en orden inválido y exige `FechasInvalidas` con el texto `posterior`; además, comprueba que el contrato permanece sin cambios. |
| CP-RF-01-ESC-04 | sí | ['tests/test_contratos.py::test_rf_01_esc_04_cruce_de_contratos'] pasan. Prepara un contrato vigente para INM-100 durante el periodo indicado y exige `CruceDeVigencias` con el mensaje esperado al activar C-103; verifica que ambos contratos conservan sus estados. |
| CP-RF-02-ESC-01 | sí | ['tests/test_contratos.py::test_rf_02_esc_01_terminacion_exitosa'] pasan. Prepara C-200 como vigente, ejecuta `terminar_contrato` con motivo y fecha indicados y verifica que queda terminado y que el resultado incluye la fecha de cambio y el usuario operador. |
| CP-RF-02-ESC-02 | sí | ['tests/test_contratos.py::test_rf_02_esc_02_motivo_obligatorio'] pasan. Prepara C-201 como vigente, intenta terminarlo sin motivo y exige `MotivoObligatorio` con el mensaje correspondiente; también comprueba que el contrato no se modifica. |
| CP-RF-02-ESC-03 | sí | ['tests/test_contratos.py::test_rf_02_esc_03_fecha_fuera_del_periodo'] pasan. Prepara C-202 con periodo hasta el 2026-12-31 e intenta terminarlo el 2027-01-01; exige `FechaTerminacionFueraDePeriodo` con el mensaje esperado y verifica que no cambia su estado. |
| CP-RF-02-ESC-04 | sí | ['tests/test_contratos.py::test_rf_02_esc_04_estado_anulado'] pasan. Prepara C-203 en estado anulado y exige `EstadoNoModificable` indicando ese estado al intentar terminarlo; además, confirma que el contrato permanece igual. |
| CP-RF-03-ESC-01 | sí | ['tests/test_contratos.py::test_rf_03_esc_01_borrador_a_anulado'] pasan. Prepara C-300 en borrador, solicita el cambio a anulado con `cambiar_estado` y verifica el estado final, el usuario y la fecha de cambio en el resultado. |
| CP-RF-03-ESC-02 | sí | ['tests/test_contratos.py::test_rf_03_esc_02_vigente_a_terminado'] pasan. Prepara C-301 en vigente, solicita el cambio a terminado y comprueba el estado resultante, junto con el usuario y la fecha de cambio devueltos. |
| CP-RF-03-ESC-03 | sí | ['tests/test_contratos.py::test_rf_03_esc_03_transicion_no_permitida'] pasan. Prepara C-302 en borrador e intenta cambiarlo a terminado; exige `TransicionNoPermitida` con el estado actual indicado y comprueba que el contrato no cambia. |
| CP-RF-03-ESC-04 | sí | ['tests/test_contratos.py::test_rf_03_esc_04_estado_final'] pasan. Prepara C-303 en terminado e intenta cambiarlo a vigente; exige `EstadoNoModificable` indicando el estado actual y verifica que el contrato permanece sin cambios. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| dominio.contratos | sí | Contrato, CambioEstado, RepositorioContratos, RepositorioContratos.registrar, RepositorioContratos.consultar_por_codigo, RepositorioContratos.existe_vigencia_en_inmueble, RepositorioContratos.actualizar, DocumentoArrendatarioObligatorio, CanonInvalido, FechasInvalidas, CruceDeVigencias, TransicionNoPermitida, EstadoNoModificable, MotivoObligatorio, FechaTerminacionFueraDePeriodo | — | — |
| aplicacion.contratos | sí | activar_contrato, terminar_contrato, cambiar_estado | — | — |
| adaptadores.salida.repositorios_memoria | sí | RepositorioContratosMemoria, RepositorioContratosMemoria.registrar, RepositorioContratosMemoria.consultar_por_codigo, RepositorioContratosMemoria.existe_vigencia_en_inmueble, RepositorioContratosMemoria.actualizar | — | — |

## Hallazgos

### Severidad baja

- **CAL-MT-009** · `src/aplicacion/contratos.py:3` · I001: Import block is un-sorted or un-formatted *Sugerencia:* Ajusta el código a la configuración de estilo del sistema.
- **CAL-MT-009** · `tests/test_contratos.py:3` · I001: Import block is un-sorted or un-formatted *Sugerencia:* Ajusta el código a la configuración de estilo del sistema.


## Ejecución en el entorno aislado

- Pruebas: 54 ({'paso': 54}), en 1180 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
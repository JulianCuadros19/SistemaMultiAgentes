# Reporte de validación · versión 3

**Veredicto: RECHAZADO** · 13 de 14 casos cumplen · hallazgos: 1 de severidad alta, 0 media (umbral 0) y 0 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_escaneos.py::test_rf_01_esc_01_revision_existente'] pasan. La prueba crea la carpeta y el archivo, solicita la revisión mediante el servicio y el comando, y verifica el listado esperado y la salida de terminal con código 0. |
| CP-RF-01-ESC-02 | no | ['tests/test_escaneos.py::test_rf_01_esc_02_revision_programada_parcial'] pasan. La prueba verifica una revisión invocable, pero no demuestra que una tarea programada nocturna la dispare sin intervención manual; el propio comentario reconoce que no verifica ese disparo y la especificación no ofrece una interfaz pública de planificador. |
| CP-RF-01-ESC-03 | sí | ['tests/test_escaneos.py::test_rf_01_esc_03_carpeta_inexistente'] pasan. La prueba solicita la revisión de una carpeta inexistente y comprueba el mensaje de error, el código de salida 1 y que no se imprime salida estándar. |
| CP-RF-02-ESC-01 | sí | ['tests/test_escaneos.py::test_rf_02_esc_01_separadores_incorrectos'] pasan. La prueba crea el archivo con separadores incorrectos, ejecuta la validación y compara el nombre, el motivo exacto y el total reportado; además comprueba que analizarlo lanza FormatoInvalido. |
| CP-RF-02-ESC-02 | sí | ['tests/test_escaneos.py::test_rf_02_esc_02_tipo_desconocido'] pasan. La prueba valida el archivo XYZ_2019_00001.pdf y comprueba que se lista como error, que el motivo indica «Tipo desconocido» y que el total coincide. |
| CP-RF-02-ESC-03 | sí | ['tests/test_escaneos.py::test_rf_02_esc_03_anio_fuera_de_rango'] pasan. La prueba valida el archivo con año 1949 y comprueba que aparece listado con un motivo que indica «Año fuera de rango». |
| CP-RF-02-ESC-04 | sí | ['tests/test_escaneos.py::test_rf_02_esc_04_extension_distinta'] pasan. La prueba valida el archivo con extensión .doc y comprueba que aparece listado con un motivo que indica «Extensión distinta de pdf». |
| CP-RF-03-ESC-01 | sí | ['tests/test_escaneos.py::test_rf_03_esc_01_renombrado_efectivo'] pasan. La prueba ejecuta el renombrado efectivo y verifica el cambio exacto a ESC_2019_00042.pdf, que no hay conflictos ni errores y que el archivo quedó renombrado. |
| CP-RF-03-ESC-02 | sí | ['tests/test_escaneos.py::test_rf_03_esc_02_simulacion'] pasan. La prueba ejecuta el renombrado en modo de simulación, comprueba el cambio propuesto exacto a ESC_2019_00042.pdf y verifica que el archivo conserva su nombre original. |
| CP-RF-03-ESC-03 | sí | ['tests/test_escaneos.py::test_rf_03_esc_03_conflicto'] pasan. La prueba prepara el archivo de origen y el destino existente, y verifica que no hay cambios, que se reporta el conflicto y que ambos archivos mantienen sus nombres. |
| CP-RF-03-ESC-04 | sí | ['tests/test_escaneos.py::test_rf_03_esc_04_tipo_no_corregible'] pasan. La prueba ejecuta el renombrado con tipo desconocido y comprueba que no hay cambios ni conflictos, que se reporta un error para el archivo y que su nombre permanece intacto. |
| CP-RF-04-ESC-01 | sí | ['tests/test_escaneos.py::test_rf_04_esc_01_reporte_valido'] pasan. La prueba genera el reporte con los dos archivos indicados y verifica los conteos exactos por año y tipo, el total de dos y la presencia de ambos nombres en las líneas del reporte. |
| CP-RF-04-ESC-02 | sí | ['tests/test_escaneos.py::test_rf_04_esc_02_mezcla_de_anios_y_tipos'] pasan. La prueba genera el reporte con los tres archivos y compara los conteos exactos separados por año y tipo, además de comprobar el total y la cantidad de líneas. |
| CP-RF-04-ESC-03 | sí | ['tests/test_escaneos.py::test_rf_04_esc_03_carpeta_inexistente'] pasan. La prueba solicita el reporte para una carpeta inexistente y verifica el mensaje de error, el código de salida 1 y que la salida estándar está vacía. |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| comandos.revisar | sí | ejecutar_revisar | — | — |
| comandos.validar | sí | ejecutar_validar | — | — |
| comandos.renombrar | sí | ejecutar_renombrar | — | — |
| comandos.reporte | sí | ejecutar_reporte | — | — |
| servicios.revision | sí | revisar_carpeta | — | — |
| servicios.validacion | sí | validar_nombres | — | — |
| servicios.renombrado | sí | renombrar_archivos | — | — |
| servicios.reporte | sí | generar_reporte | — | — |
| dominio.convencion | sí | EstructuraNombre, ResultadoValidacion, CambioNombre, ConflictoRenombrado, ErrorRenombrado, Reporte, analizar_nombre, normalizar_nombre, FormatoInvalido, TipoDesconocido, AnioFueraDeRango, ExtensionInvalida, CarpetaNoExiste | — | — |
| entrada_salida.archivos | sí | GestorArchivos, GestorArchivos.crear_carpeta, GestorArchivos.crear_archivo, GestorArchivos.existe_carpeta, GestorArchivos.listar_archivos, GestorArchivos.renombrar | — | — |

## Hallazgos

### Severidad alta

- **CAL-FS-001** · `tests/test_escaneos.py::test_rf_01_esc_02_revision_programada_parcial` · La prueba pasa, pero no verifica el escenario (dado que existe la carpeta /archivos/escaneos/expedientes y la tarea programada de la noche se ejecuta, cuando la tarea dispara la revisión, entonces la herramienta revisa la carpeta de escaneos de expedientes sin intervención manual): La prueba verifica una revisión invocable, pero no demuestra que una tarea programada nocturna la dispare sin intervención manual; el propio comentario reconoce que no verifica ese disparo y la especificación no ofrece una interfaz pública de planificador. *Sugerencia:* Añadir o exponer una interfaz de planificación que permita preparar y disparar la ejecución programada y observar que revisa la carpeta sin intervención manual.


## Ejecución en el entorno aislado

- Pruebas: 35 ({'paso': 35}), en 1078 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
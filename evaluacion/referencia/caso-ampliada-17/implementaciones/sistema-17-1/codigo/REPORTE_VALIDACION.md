# Reporte de validación · versión 1

**Veredicto: APROBADO** · 13 de 13 casos cumplen · hallazgos: 0 de severidad alta, 0 media (umbral 0) y 1 baja.

## Casos de aceptación

| Caso | Cumple | Evidencia |
|---|---|---|
| CP-RF-01-ESC-01 | sí | ['tests/test_seguimiento.py::test_rf_01_esc_01_publicacion_completa'] pasan. La prueba publica mediante `_publicar` y compara en el aviso el número, tipo, estados, fecha y funcionario concretos del escenario; también comprueba que queda pendiente en el canal. |
| CP-RF-01-ESC-02 | sí | ['tests/test_seguimiento.py::test_rf_01_esc_02_reaccion_separada'] pasan. Comprueba que el aviso queda pendiente y que la bitácora no reacciona antes del despacho, y luego verifica que al despacharlo registra el trámite; esto demuestra la separación entre publicación y reacción del otro proceso. |
| CP-RF-01-ESC-03 | sí | ['tests/test_seguimiento.py::test_rf_01_esc_03_transicion_invalida'] pasan. Publica la transición indicada y despacha el aviso; verifica que se marca inválida y queda en la bitácora, además de comprobar que los consumidores de mensajes e indicadores no la procesan. |
| CP-RF-02-ESC-01 | sí | ['tests/test_seguimiento.py::test_rf_02_esc_01_asiento_completo'] pasan. Tras despachar el aviso, consulta el asiento de la bitácora y compara cada dato solicitado con el aviso publicado, incluida la validez de la transición. |
| CP-RF-02-ESC-02 | sí | ['tests/test_seguimiento.py::test_rf_02_esc_02_fallo_aislado'] pasan. Registra el consumidor que falla junto con bitácora, indicador y mensajes; tras despachar comprueba que los tres procesos restantes reaccionaron y que se informa el fallo en el log. |
| CP-RF-02-ESC-03 | sí | ['tests/test_seguimiento.py::test_rf_02_esc_03_marca_invalida'] pasan. La prueba despacha a la bitácora el aviso de la transición indicada y verifica que el asiento resultante tiene `transicion_valida is False`. |
| CP-RF-03-ESC-01 | sí | ['tests/test_seguimiento.py::test_rf_03_esc_01_cuatro_dias_habiles'] pasan. Prepara la radicación en la fecha indicada, procesa el aviso con fecha final 2026-11-06 y comprueba que los días calculados son exactamente `4`. |
| CP-RF-03-ESC-02 | sí | ['tests/test_seguimiento.py::test_rf_03_esc_02_promedio_aprobados'] pasan. Procesa avisos de aprobación para dos trámites del tipo mutación y comprueba los promedios exactos tras cada actualización (`4` y `3`), además de que otro tipo conserva promedio `0`. |
| CP-RF-03-ESC-03 | sí | ['tests/test_seguimiento.py::test_rf_03_esc_03_promedio_rechazados'] pasan. Prepara la fecha de radicación, procesa un aviso cuyo estado nuevo es `rechazado` y verifica que el promedio de mutación se actualiza a `4`. |
| CP-RF-03-ESC-04 | sí | ['tests/test_seguimiento.py::test_rf_03_esc_04_estado_no_final'] pasan. Procesa el cambio de radicado a en revisión y comprueba que no se registran días ni se actualiza el promedio, que permanece en `Decimal(0)`. |
| CP-RF-04-ESC-01 | sí | ['tests/test_seguimiento.py::test_rf_04_esc_01_mensaje_aprobado'] pasan. La prueba prepara el aviso de aprobado, lo procesa mediante el consumidor de mensajes y compara el texto generado con la frase exacta del escenario. |
| CP-RF-04-ESC-02 | sí | ['tests/test_seguimiento.py::test_rf_04_esc_02_mensaje_rechazado'] pasan. La prueba procesa el cambio a rechazado y compara el texto del mensaje con la frase exacta solicitada para T-0002. |
| CP-RF-04-ESC-03 | sí | ['tests/test_seguimiento.py::test_rf_04_esc_03_mensaje_revision'] pasan. La prueba procesa el cambio a en revisión y verifica que el mensaje contiene exactamente «Su trámite T-0003 está en revisión». |

## Conformidad arquitectónica

| Módulo | Existe | Interfaces conformes | Interfaces divergentes | Dependencias no autorizadas |
|---|---|---|---|---|
| eventos.aviso | sí | AvisoCambioEstado, AsientoBitacora, MensajeCiudadano, CanalEventos, CanalEventos.suscribir, CanalEventos.publicar, CanalEventos.obtener_pendientes, CanalEventos.despachar_pendientes, RegistroBitacora, RegistroBitacora.registrar, RegistroBitacora.consultar_por_tramite, RegistroIndicadores, RegistroIndicadores.registrar_dias, RegistroIndicadores.consultar_dias_calculados, RegistroIndicadores.promedio_por_tipo, RegistroFechasTramite, RegistroFechasTramite.registrar_radicado, RegistroFechasTramite.obtener_fecha_radicado, RegistroMensajes, RegistroMensajes.registrar, RegistroMensajes.consultar_por_tramite | — | — |
| productores.cambios_estado | sí | publicar_cambio_estado | — | — |
| consumidores.bitacora | sí | BitacoraConsumidor, BitacoraConsumidor.manejar | — | — |
| consumidores.indicador | sí | IndicadorConsumidor, IndicadorConsumidor.manejar | — | — |
| consumidores.mensajes | sí | MensajesConsumidor, MensajesConsumidor.manejar | — | — |
| consumidores.falla | sí | ConsumidorFalla, ConsumidorFalla.manejar | — | — |
| infraestructura.canal_memoria | sí | CanalEventosMemoria, CanalEventosMemoria.suscribir, CanalEventosMemoria.publicar, CanalEventosMemoria.obtener_pendientes, CanalEventosMemoria.despachar_pendientes | — | — |
| infraestructura.bitacora_memoria | sí | RegistroBitacoraMemoria, RegistroBitacoraMemoria.registrar, RegistroBitacoraMemoria.consultar_por_tramite | — | — |
| infraestructura.indicadores_memoria | sí | RegistroIndicadoresMemoria, RegistroIndicadoresMemoria.registrar_dias, RegistroIndicadoresMemoria.consultar_dias_calculados, RegistroIndicadoresMemoria.promedio_por_tipo | — | — |
| infraestructura.calendario_tramite_memoria | sí | RegistroFechasTramiteMemoria, RegistroFechasTramiteMemoria.registrar_radicado, RegistroFechasTramiteMemoria.obtener_fecha_radicado | — | — |
| infraestructura.mensajes_memoria | sí | RegistroMensajesMemoria, RegistroMensajesMemoria.registrar, RegistroMensajesMemoria.consultar_por_tramite | — | — |

## Hallazgos

### Severidad baja

- **CAL-MT-009** · `src/consumidores/mensajes.py:28` · E501: Line too long (102 > 100) *Sugerencia:* Ajusta el código a la configuración de estilo del sistema.


## Ejecución en el entorno aislado

- Pruebas: 51 ({'paso': 51}), en 1095 ms.
- Módulos que no se importan: ninguno.
- Archivos de prueba sin recolectar: 0.
- Tiempo vencido: no.

## Reglas no evaluadas

Sin comprobación automática; quedan para la revisión humana: CAL-FB-001, CAL-FB-003, CAL-FB-004, CAL-FB-005, CAL-FS-004, CAL-SG-005, CAL-SG-007.
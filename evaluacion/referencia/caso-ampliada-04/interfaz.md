# Interfaz de referencia · caso 04, ciclo de vida de contratos de arrendamiento

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, esta clase. La traduce a
la implementación evaluada sin decidir nada por su cuenta (ver `../LEEME.md`). Cada instancia empieza
sin contratos, con almacenamiento en memoria.

```python
class Contratos:
    def crear(
        self,
        codigo: str,
        inmueble: str,
        arrendatario: str | None,
        canon: int,
        inicio: date,
        fin: date,
        usuario: str,
    ) -> None:
        """Registra un contrato en borrador."""

    def activar(self, codigo: str, usuario: str) -> str:
        """Pasa el contrato a vigente y devuelve su estado."""

    def terminar(self, codigo: str, motivo: str, fecha: date, usuario: str) -> str:
        """Pasa el contrato a terminado y devuelve su estado."""

    def anular(self, codigo: str, usuario: str) -> str:
        """Pasa el contrato a anulado y devuelve su estado."""

    def usuarios_de_los_cambios(self, codigo: str) -> list[str]:
        """El usuario de cada cambio de estado registrado, en orden."""
```

- **Estados devueltos:** `"vigente"`, `"terminado"` y `"anulado"`, tal como los nombra la ficha.
- **Errores:** los métodos lanzan una excepción con el mensaje de la implementación. Si la
  implementación devuelve el rechazo como valor, el adaptador lo convierte en excepción.
- **Crear:** si la implementación no tiene una operación aparte, el adaptador guarda los datos y los usa
  al activar.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_activa_un_contrato_valido` | «de borrador a vigente» |
| `test_rechaza_periodos_que_se_cruzan` | «El inmueble ya tiene un contrato vigente en ese periodo», con las fechas del ejemplo |
| `test_activa_si_los_periodos_no_se_cruzan` | El contrato del 2027-01-01 al 2027-12-31 sí se activa |
| `test_rechaza_activar_sin_arrendatario` | «debe tener arrendatario» |
| `test_rechaza_activar_con_canon_cero` | «canon mayor que cero» |
| `test_rechaza_activar_con_menos_de_seis_meses` | «una duración mínima de seis meses» |
| `test_termina_un_contrato_vigente` | «de vigente a terminado» |
| `test_terminar_exige_motivo` | «se exige un motivo» |
| `test_terminar_exige_fecha_dentro_del_periodo` | «una fecha de terminación dentro del periodo» |
| `test_anula_un_borrador` | «de borrador a anulado» |
| `test_una_transicion_no_permitida_indica_el_estado` | «se rechaza indicando el estado actual» |
| `test_un_contrato_terminado_no_cambia` | «Un contrato terminado o anulado ya no cambia» |
| `test_registra_el_usuario_de_cada_cambio` | «queda registrado con la fecha y el usuario» |

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad

- **Una duración de exactamente seis meses,** ni si el día final cuenta en el cruce de periodos.
- **Los mensajes de los demás rechazos:** la ficha no los da.
- **La fecha de cada cambio:** se registra con el reloj de la implementación o con un dato de entrada.
- **La independencia de las reglas frente al almacenamiento:** no es ejecutable por esta interfaz.

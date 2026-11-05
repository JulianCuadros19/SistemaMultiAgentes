# Interfaz de referencia · caso 16, simulador de amortización de créditos de vivienda

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, estas funciones.
Las traduce a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def cuota(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> int:
    """Cuota mensual fija, en pesos."""


def tabla(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> list[tuple[int, int, int, int]]:
    """Cada mes, en orden: cuota pagada, interés, abono a capital y saldo, en pesos."""


def resumen(monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal) -> tuple[int, int]:
    """Total pagado y total de intereses, en pesos."""


def guardar_tabla_csv(
    monto: int, plazo_meses: int, tasa_efectiva_anual: Decimal, ruta: str
) -> None:
    """Guarda la tabla de amortización en un archivo CSV en la ruta indicada."""


def codigo_de_salida(operacion: str, monto: str, plazo_meses: str, tasa_efectiva_anual: str) -> int:
    """Ejecuta la herramienta de terminal con esa operación y esos datos y devuelve su código de salida."""
```

- **Tasa:** en porcentaje, como `Decimal`: `Decimal("12")` es 12 % efectivo anual.
- **Operaciones de `codigo_de_salida`:** `cuota`, `tabla` y `resumen`. El adaptador arma los
  argumentos que espera la herramienta y la ejecuta dentro del mismo proceso.
- **Errores:** las funciones lanzan una excepción con el mensaje de la implementación.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_cuota_del_ejemplo` | 100.000.000 a 120 meses al 12 %: cuota de 1.399.472 |
| `test_primer_mes_del_ejemplo` | Interés 948.879, abono 450.593 y saldo 99.549.407 |
| `test_la_tabla_termina_en_cero_con_la_ultima_cuota_ajustada` | «la última cuota se ajusta para que el saldo quede exactamente en cero» |
| `test_el_resumen_cuadra_con_la_tabla` | El total pagado y el total de intereses |
| `test_cuota_con_tasa_de_dos_decimales` | La fórmula de la cuota, con 25.000.000 a 36 meses al 9,75 %: 798.951 |
| `test_rechaza_un_monto_fuera_de_rango` | Monto entre 10.000.000 y 500.000.000 |
| `test_rechaza_un_plazo_fuera_de_rango` | Plazo entre 12 y 240 meses |
| `test_rechaza_una_tasa_fuera_de_rango` | Tasa entre 1 y 30 |
| `test_guarda_la_tabla_en_un_csv` | «si el asesor lo pide, la guarda en un archivo CSV» |
| `test_la_herramienta_termina_con_error_ante_datos_invalidos` | «código de salida distinto de cero» |

La cuota de 798.951 se calculó con las reglas de la ficha.

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad

- **Los valores exactos de los meses siguientes al primero y de la última cuota:** dependen de en
  qué paso se redondea al peso. Se verifica que la tabla tenga 120 meses, que las cuotas sean
  iguales salvo la última y que el saldo termine en cero.
- **Si los límites de los rangos se aceptan:** se rechazan valores claramente por fuera.
- **El formato del CSV:** se verifica que tenga una fila por mes y las cifras del primer mes.

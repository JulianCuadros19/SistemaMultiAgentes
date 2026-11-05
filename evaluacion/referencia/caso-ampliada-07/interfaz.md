# Interfaz de referencia · caso 07, conciliación diaria del recaudo

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, esta función. La traduce
a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def conciliar(
    banco_a: str, banco_b: str, banco_c: str, facturas: str, carpeta_salida: str
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Corre el proceso con esos archivos y devuelve las filas del CSV y el total de cada estado."""
```

- **Entradas:** rutas de los cuatro archivos, con los formatos de la ficha, y la carpeta de salida.
- **Filas:** cada una con `referencia`, `valor_facturado`, `valor_pagado`, `banco`, `estado` y
  `diferencia`, como texto. El adaptador lee el CSV de la implementación y traduce los nombres de sus
  columnas a estos.
- **Estados:** `conciliado`, `diferencia`, `pago sin factura` y `pendiente`. El adaptador traduce los de
  la implementación a estos, en la fila y en el total.
- **Errores:** la función lanza una excepción con el mensaje de la implementación.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_pago_igual_al_facturado_queda_conciliado` | F-001 por 85.000, pagada en el banco A con 85.000 |
| `test_pago_distinto_queda_con_diferencia` | F-002 por 120.000, pagada en el banco B con 100.000: diferencia de 20.000 |
| `test_pago_sin_factura` | F-999 en el banco C |
| `test_factura_sin_pago_queda_pendiente` | F-003 sin pago |
| `test_cada_pago_indica_su_banco` | «banco» en el CSV, y los tres formatos de archivo |
| `test_la_fila_trae_lo_facturado_y_lo_pagado` | «valor facturado, valor pagado» |
| `test_el_resumen_cuenta_cada_estado` | «un resumen con el total de cada estado» |
| `test_rechaza_un_archivo_sin_una_columna` | «se rechaza indicando el archivo y la columna» |
| `test_una_fila_con_valor_no_numerico_no_detiene_el_lote` | «sin detener el lote» |

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad o no es ejecutable

- **El signo de la diferencia:** se compara su magnitud.
- **El nombre exacto del archivo en el mensaje de la columna faltante:** se verifica la columna.
- **Dónde se reporta una fila rechazada:** se verifica que el lote siga.
- **Reintentar solo una etapa:** depende del diseño de cada implementación.

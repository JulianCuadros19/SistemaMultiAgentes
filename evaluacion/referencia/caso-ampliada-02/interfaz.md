# Interfaz de referencia · caso 02, reajuste anual del canon

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, esta función. La
traduce a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def reajustar(
    canon_actual: int,
    porcentaje_pactado: Decimal,
    ipc_anterior: Decimal,
    fecha_ultimo_reajuste: date,
    fecha_reajuste: date,
) -> tuple[int, Decimal, int]:
    """Nuevo canon, porcentaje aplicado e incremento, en pesos y en porcentaje."""
```

- **Datos:** el canon en pesos; el porcentaje pactado y el IPC en porcentaje, como `Decimal`
  (`Decimal("5.20")` es 5,20 %); las dos fechas como `date`.
- **Resultado:** el nuevo canon y el incremento como enteros en pesos; el porcentaje aplicado como
  `Decimal`.
- **Errores:** la función lanza una excepción con el mensaje de la implementación.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_ejemplo_con_ipc_menor_que_lo_pactado` | 1.200.000, pactado 10 %, IPC 5,20 %: 5,20 %, 1.262.400 y 62.400 |
| `test_ejemplo_con_pactado_menor_que_el_ipc` | 950.000, pactado 3 %, IPC 5,20 %: 3 % y 978.500 |
| `test_redondea_a_la_centena_mas_cercana` | «El resultado se redondea a la centena de peso más cercana» |
| `test_ipc_cero_no_cambia_el_canon` | «Si el IPC del año anterior es cero o negativo, el canon no cambia» |
| `test_ipc_negativo_no_cambia_el_canon` | La misma regla |
| `test_rechaza_antes_de_doce_meses` | «El contrato aún no cumple doce meses desde el último reajuste» |
| `test_reajusta_al_cumplir_doce_meses` | Al menos doce meses desde el último reajuste |
| `test_rechaza_un_canon_no_positivo` | Canon obligatorio y mayor que cero |
| `test_rechaza_un_porcentaje_pactado_fuera_de_rango` | Porcentaje pactado entre 0 y 100 |

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad

- **El incremento cuando el redondeo lo cambia:** puede leerse como el nuevo canon menos el actual
  o como el porcentaje sobre el canon. Se verifica solo en los ejemplos, donde coinciden.
- **El porcentaje aplicado con IPC cero o negativo.**
- **El redondeo de una centena exacta a la mitad, y el de un canon con 0 % pactado.**
- **Los decimales de más en un porcentaje:** la ficha no dice si se rechazan o se redondean.

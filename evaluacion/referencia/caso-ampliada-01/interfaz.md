# Interfaz de referencia · caso 01, liquidación de comisiones de corretaje

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, esta función. La
traduce a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def liquidar(tipo_negocio: str, valor: int, numero_asesores: int, estado: str) -> tuple[int, int]:
    """Comisión de la inmobiliaria y comisión de cada asesor, en pesos."""
```

- **Datos:** `tipo_negocio` es `"venta"` o `"arriendo"`; `valor`, el valor de venta o el canon mensual,
  en pesos; `estado`, `"cerrado"` o `"abierto"`.
- **Resultado:** las dos comisiones, en pesos sin decimales.
- **Errores:** la función lanza una excepción con el mensaje de la implementación.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_ejemplo_de_venta_con_un_asesor` | Venta de 300.000.000 con un asesor: 9.000.000 y 3.600.000 |
| `test_ejemplo_de_arriendo_con_dos_asesores` | Canon de 1.000.000 y dos asesores: 1.000.000 y el mínimo de 300.000 a cada uno |
| `test_dos_asesores_reparten_el_cuarenta_por_ciento` | «ese 40 % se reparte en partes iguales» |
| `test_arriendo_con_un_asesor` | «el 100 % del primer canon mensual» y «el 40 % de la comisión» |
| `test_el_minimo_aplica_a_un_asesor` | «como mínimo 300.000 pesos por negocio cerrado» |
| `test_redondea_al_peso_mas_cercano` | «redondeados al peso más cercano» |
| `test_rechaza_un_negocio_no_cerrado` | «El negocio aún no está cerrado» |
| `test_rechaza_un_valor_no_positivo` | «un valor de cero o negativo se rechaza» |
| `test_rechaza_mas_de_dos_asesores` | «más de dos asesores se rechaza» |

Las cifras que no trae la ficha se calcularon con sus reglas: 3 % de 100.000.020 es 3.000.000,6, y su
40 % es 1.200.000,24.

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad

- **El redondeo de una mitad exacta de peso.**
- **Si el 40 % se calcula sobre la comisión redondeada o sin redondear:** el valor de la prueba da lo
  mismo en ambos casos.
- **Cero asesores:** la ficha dice «1 o 2», pero solo da como error más de dos.

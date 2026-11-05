# Interfaz de referencia · caso 10, tarifa del impuesto predial

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, estas funciones. Las
traduce a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def consultar_tarifa(destino: str, estrato: int | None) -> int:
    """Tarifa en pesos por cada mil pesos de avalúo."""


def calcular_impuesto(avaluo: int, destino: str, estrato: int | None) -> int:
    """Impuesto en pesos."""
```

- **Destinos:** `"residencial"`, `"comercial"`, `"industrial"` y `"lote"`, el lote urbanizable no
  edificado. El adaptador los traduce a los nombres de la implementación. Un destino que no conoce,
  como `"minero"`, lo pasa tal cual.
- **Errores:** las funciones lanzan una excepción con el mensaje de la implementación.
- **Servicio HTTP:** el adaptador puede llamar a las funciones del dominio o a las de las rutas. El
  entorno aislado no tiene cliente HTTP de pruebas, así que la capa HTTP no se ejercita.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_tarifa_del_ejemplo` | Residencial, estrato 3: 8 por mil |
| `test_impuesto_del_ejemplo` | Residencial, estrato 3, avalúo de 120.000.000: 960.000 |
| `test_tarifas_residenciales_por_estrato` | Estratos 1 a 6: 5, 6, 8, 10, 12 y 14 |
| `test_tarifas_de_los_demas_destinos` | Comercial, 11; industrial, 12; lote, 33 |
| `test_impuesto_de_un_destino_sin_estrato` | «el avalúo por la tarifa dividido entre mil» |
| `test_la_mitad_se_redondea_hacia_arriba` | «redondeado al peso, con las mitades hacia arriba» |
| `test_menos_de_la_mitad_se_redondea_hacia_abajo` | «redondeado al peso» |
| `test_rechaza_un_estrato_invalido` | «Estrato inválido» |
| `test_rechaza_un_destino_desconocido` | «Destino económico no reconocido» |
| `test_rechaza_un_avaluo_no_positivo` | «El avalúo debe ser mayor que cero» |

Las cifras que no trae la ficha se calcularon con sus reglas: 100.100 × 5 ÷ 1.000 = 500,5 y
100.050 × 8 ÷ 1.000 = 800,4.

## Lo que no se verifica

- **El contrato documentado** para los otros sistemas: no es ejecutable.
- **La capa HTTP:** el entorno aislado no tiene cliente HTTP de pruebas.
- **Un estrato en un destino que no es residencial:** la ficha no dice si se ignora o se rechaza.

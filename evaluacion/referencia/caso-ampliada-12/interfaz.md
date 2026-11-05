# Interfaz de referencia · caso 12, dígito de verificación del NIT

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, estas funciones.
Las traduce a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def calcular_digito(numero: str) -> int:
    """Dígito de verificación del número, tal como llega: con o sin puntos y guiones."""


def validar_nit(nit: str) -> tuple[bool, int]:
    """Si el NIT completo, «número-dígito», es válido, y el dígito esperado."""
```

- **Entradas:** los textos llegan tal como los enviaría el portal o el sistema de facturación; quitar
  los puntos y los guiones del número le toca a la implementación.
- **Errores:** la función lanza una excepción con el mensaje de la implementación.
- **Servicio HTTP:** el adaptador puede llamar a las funciones del dominio o a las de las rutas. El
  entorno aislado no tiene cliente HTTP de pruebas, así que la capa HTTP no se ejercita.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_digito_del_primer_ejemplo` | 900123456 tiene dígito 8 |
| `test_digito_del_segundo_ejemplo` | 123456789 tiene dígito 6 |
| `test_valida_un_nit_correcto_con_puntos_y_guion` | «900.123.456-8» es válido |
| `test_informa_el_digito_esperado_de_un_nit_incorrecto` | «900123456-7» no es válido; el esperado es 8 |
| `test_quita_puntos_y_guiones_antes_de_calcular` | «si llega con puntos o guiones, se quitan antes de calcular» |
| `test_residuo_cero_o_uno_es_el_digito` | «si el residuo es 0 o 1, el dígito es el residuo» |
| `test_numeros_de_uno_y_de_quince_digitos` | El número tiene de 1 a 15 dígitos |
| `test_muestra_de_numeros` | Los pesos 3, 7, 13… 71 de derecha a izquierda y el residuo entre 11 |
| `test_rechaza_letras` | «El NIT solo admite dígitos», al calcular y al validar |
| `test_rechaza_mas_de_quince_digitos` | «El NIT admite como máximo 15 dígitos» |

Los dígitos esperados que no trae la ficha se calcularon con su algoritmo
(`100000001` → 0, `100000005` → 1, `7` → 1, `123456789012345` → 2, `860001022` → 7,
`830114921` → 1, `999999999999999` → 2 y `800197268` → 4).

## Lo que no se verifica

- **El contrato documentado** para los equipos de los dos sistemas: no es ejecutable. Se revisa a
  mano en `USO.md` o en la documentación del servicio.
- **La capa HTTP:** el entorno aislado no tiene cliente HTTP de pruebas.
- **El mensaje de un dígito de verificación inválido:** la ficha no lo da.

# Reajuste anual de cánones

Calcula el nuevo canon, el porcentaje aplicado y el incremento efectivo, comprobando el plazo mínimo de doce meses.

## Requisitos

- Python 3.11 o superior; el módulo se probó con Python 3.11.
- Sin dependencias externas: `requirements.txt` fija la versión de pytest.

## Instalación

Desde la carpeta del código, cree un entorno e instale las dependencias:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, el entorno se activa con `.venv\Scripts\activate`. `requirements.txt` acompaña al código: fija las versiones con que se probó e incluye pytest.

## Configuración

No requiere archivos ni variables de entorno. Prepare los importes y porcentajes como `Decimal` creados desde cadenas o enteros, y las fechas como `datetime.date`.

## Ejecución

No hay un punto de entrada de terminal. Con `src` en la ruta de importación, invoque el caso de uso:

```python
from datetime import date
from decimal import Decimal
from aplicacion.reajuste import realizar_reajuste

resultado = realizar_reajuste(
    Decimal("1200000"),
    Decimal("10"),
    Decimal("5.20"),
    date(2023, 6, 15),
    date(2024, 6, 15),
)
print(resultado.nuevo_canon)  # Equivale a 1262400 pesos.
```

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

- `aplicacion.reajuste.realizar_reajuste(canon_actual, porcentaje_pactado, ipc_del_ano_anterior, fecha_de_inicio_o_del_ultimo_reajuste, fecha_del_reajuste)`: caso de uso mostrado arriba; devuelve `ReajusteResultado`.
- `dominio.reajuste.calcular_reajuste`: recibe los mismos parámetros y devuelve el mismo tipo. Ejemplo: `calcular_reajuste(Decimal("1000"), Decimal("3"), Decimal("5.20"), date(2023, 1, 1), date(2024, 1, 1))`.
- `dominio.reajuste.ReajusteResultado(nuevo_canon, porcentaje_aplicado, valor_del_incremento)`: resultado inmutable. Ejemplo: `ReajusteResultado(Decimal("978500"), Decimal("3"), Decimal("28500"))`.
- `dominio.reajuste.MesesInsuficientesError(mensaje)`: excepción de validación. Ejemplo: `MesesInsuficientesError("El contrato aún no cumple doce meses desde el último reajuste")`. Por plazo insuficiente, ese es el mensaje exacto.

Las interfaces del dominio se importan desde `dominio.reajuste`; la excepción también está disponible desde `aplicacion.reajuste`.

## Supuestos

- **La aceptación de ESC-04 permanece bloqueada por una contradicción entre el escenario y la fórmula aprobada.** Para sus entradas, el porcentaje aplicable es `min(10, 5.20) = 5.20`. El cálculo es `1234567 × 1.052 = 1298764.484`, cuyo redondeo a centenas es **1298800**, no **1234600**. El valor exigido por el escenario corresponde a redondear el canon original sin aplicar el incremento. No es posible hacer pasar esa comprobación y conservar simultáneamente la fórmula declarada. No se ha modificado el código ni la prueba: esta continúa marcada como fallo esperado estricto y el escenario no queda acreditado. Se necesita aprobar cuál de las dos instrucciones debe cambiar; no se introduce una excepción de negocio para esos datos.
- Doce meses significa alcanzar el aniversario calendario, inclusive. Para un inicio el 29 de febrero, el aniversario en un año no bisiesto es el 28 de febrero.
- Los empates de redondeo a centenas se resuelven hacia arriba mediante `ROUND_HALF_UP`. El incremento es la diferencia exacta entre el canon redondeado y el canon actual.
- Si el IPC es cero o negativo, se conserva exactamente el canon actual, incluso si no es múltiplo de cien, para cumplir la regla de que el canon no cambia.
- Los ceros decimales finales no cuentan como precisión adicional: `5.200` representa un porcentaje válido de dos decimales.
- Como no se declara una excepción distinta para entradas inválidas, estas también se rechazan mediante `MesesInsuficientesError`, con mensajes específicos. Se exige `Decimal` finito para datos numéricos y `date` sin componente horario para fechas.

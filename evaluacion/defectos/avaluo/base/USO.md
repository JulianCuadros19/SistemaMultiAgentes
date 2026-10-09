# Cálculo de avalúos

Implementa RF-01 con Python 3.11 y biblioteca estándar. Todas las cantidades monetarias y áreas se manejan con `Decimal`.

## Interfaces públicas

```python
from decimal import Decimal
from dominio.avaluo import Predio, ValoresUnitarios, ResultadoAvaluo

predio = Predio("1" * 30, Decimal("200"), Decimal("100"))
valores = ValoresUnitarios(Decimal("500000"), Decimal("1200000"))
resultado = ResultadoAvaluo(
    Decimal("100000000"), Decimal("120000000"), Decimal("220000000")
)
```

`Predio` valida el identificador y ambas áreas. `ValoresUnitarios` valida valores finitos y sus rangos. `ResultadoAvaluo` valida importes finitos, enteros y no negativos.

```python
from aplicacion.calculo_avaluo import calcular_avaluo
from infraestructura.valores_unitarios_repositorio import obtener_valores_unitarios

# Requiere valores registrados previamente en la fuente en memoria.
valores = obtener_valores_unitarios("1" * 30, 2026)
resultado = calcular_avaluo("1" * 30, 2026, Decimal("200"), Decimal("100"))
```

Sin un registro aplicable, ambas consultas lanzan `ValoresUnitariosNoEncontrados`. Las excepciones de entradas inválidas se exponen también desde el módulo de aplicación.

## Supuestos

- La especificación no proporciona registros, mecanismo de carga ni resolución de zona y tipología. El repositorio utiliza un diccionario privado inicialmente vacío, indexado por predio y vigencia. No se inventan valores ni se agrega una interfaz pública de registro. Las pruebas sustituyen ese almacenamiento con `monkeypatch`.
- La vigencia actual es el año de `date.today()`; los límites inclusivos son 1000 y el año actual más uno, sin exceder 9999.
- Se aceptan dígitos decimales Unicode en el identificador, sin convertirlo ni normalizarlo.
- Al no estar especificado el modo de redondeo, se usa `ROUND_HALF_UP` por componente; el total es la suma de los componentes redondeados.
- Para invariantes inválidas de `ValoresUnitarios` y `ResultadoAvaluo`, que no tienen excepción específica declarada, se usa `ValueError`.
- No se valida existencia ni ficha catastral mediante fuentes externas: son precondiciones del requerimiento.

## Pruebas

Con `src` en la ruta de importación, ejecutar `python -m pytest tests`. Se incluyen los tres escenarios aprobados, entradas inválidas, límites y redondeo.

# Reajuste de arriendos

Módulo Python 3.11 para que el analista de cartera calcule el reajuste con el IPC del año calendario anterior que él suministre. No consulta fuentes externas ni necesita red. Solo usa la biblioteca estándar; las pruebas requieren pytest.

## Uso

Con `src/` en la ruta de importación:

```python
from reajuste_arriendo import ErrorReajuste, calcular_reajuste

try:
    resultado = calcular_reajuste(
        canon_actual="1200000",
        porcentaje_pactado="10",
        ipc_anterior="5.20",
        fecha_base="2023-06-15",
        fecha_reajuste="2024-06-15",
    )
except ErrorReajuste as error:
    print(str(error))
else:
    print(resultado.nuevo_canon)          # Decimal equivalente a 1262400
    print(resultado.incremento)           # Decimal equivalente a 62400
    print(resultado.porcentaje_aplicado)  # Decimal equivalente a 5.20
```

Pruebas, desde la raíz del proyecto:

```sh
PYTHONPATH=src python -m pytest tests
```

## Entradas

Los cinco argumentos se pasan por nombre y son obligatorios. Omitir uno o pasar `None` produce un error.

| Argumento | Contenido y límites |
| --- | --- |
| `canon_actual` | Canon en pesos, estrictamente mayor que cero. No se impone una cantidad máxima de decimales. |
| `porcentaje_pactado` | Porcentaje entre 0 y 100 inclusive, con hasta dos decimales significativos después del punto. |
| `ipc_anterior` | IPC del año calendario anterior, con hasta dos decimales; sin límite adicional de valor. Puede ser negativo o cero. |
| `fecha_base` | Fecha de inicio o del último reajuste. |
| `fecha_reajuste` | Fecha para la que se solicita el reajuste. |

**Formato elegido, no confirmado como requisito de negocio:** números como `Decimal`, enteros o cadenas decimales sin separadores de miles, con punto decimal. `5.20` significa 5,20 %, no 0,052. La notación científica que admite `Decimal` también es válida. No se admiten `float`, booleanos, infinitos ni NaN. Los ceros finales no añaden precisión: `5.2000` es válido, `5.201` no. Las fechas son objetos `datetime.date` o cadenas estrictas `AAAA-MM-DD`; no se aceptan objetos `datetime.datetime`.

## Reglas y salidas

1. Se validan todos los datos y el plazo, incluso si el IPC no es positivo.
2. Deben haber transcurrido doce meses desde `fecha_base`.
3. Si el IPC es cero o negativo, se devuelve el canon original sin redondearlo, incremento cero y porcentaje aplicado cero.
4. Si el IPC es positivo, el porcentaje aplicado es el menor entre IPC y porcentaje pactado.
5. Se calcula `canon_actual × (1 + porcentaje_aplicado / 100)` y después se redondea a la centena de peso más cercana.
6. El incremento es el nuevo canon redondeado menos el canon original.

La salida es un `ResultadoReajuste` inmutable con tres atributos `Decimal`: `nuevo_canon`, `incremento` y `porcentaje_aplicado`. Este último es el porcentaje seleccionado antes del redondeo, no el porcentaje efectivo calculado sobre el incremento redondeado. Los valores son numéricos, sin formato de presentación; un canon puede imprimirse con notación científica.

## Decisiones mínimas sobre asuntos pendientes

Estas decisiones son de implementación y **no representan opciones aprobadas por el cliente**:

- Doce meses se interpretan como el aniversario del año siguiente, incluido ese día. Para el 29 de febrero se usa el 28 de febrero del siguiente año. Una fecha anterior a la base se rechaza con el mismo mensaje de plazo insuficiente. Si la fecha base está en el año 9999, ninguna fecha representable permite cumplir el plazo.
- En un empate de redondeo se sube: `1234550` pasa a `1234600`. El ejemplo `1234567` pasa a `1234600`.
- Se sigue la secuencia acordada: seleccionar porcentaje y luego redondear. No se agrega un tope monetario posterior, aunque el redondeo pueda superar el límite porcentual efectivo. Por ejemplo, `1000040` con 5 % pasa a `1050100`.
- Con IPC positivo y porcentaje pactado cero también se ejecuta el redondeo. Este puede subir o bajar el canon. No se impone un piso monetario ni se impide un incremento negativo producido exclusivamente por el redondeo: tales reglas no se acordaron. Con IPC no positivo sí se conserva siempre el valor original.
- Se proporciona una función reutilizable que calcula un reajuste por llamada; no se da por definido el flujo de trabajo individual o por listas. Puede llamarse desde un flujo externo, pero no se incorpora una interfaz de lotes, archivos, pantalla o línea de comandos.
- Un intervalo mayor de doce meses permite un solo cálculo; no se acumulan reajustes ni se generan períodos intermedios.
- Los mensajes distintos del rechazo por plazo se eligieron para identificar el campo inválido. Se reporta el primer error encontrado, no una lista de errores.

## Errores

Todos los errores previstos se comunican mediante `ErrorReajuste`, subclase de `ValueError`.

| Situación | Mensaje |
| --- | --- |
| Dato omitido o `None` | `Falta el dato obligatorio: {campo}` |
| Número de formato o tipo inválido, o no finito | `{campo} debe ser un número decimal válido` |
| Canon cero o negativo | `canon_actual debe ser mayor que cero` |
| Porcentaje pactado fuera de rango | `porcentaje_pactado debe estar entre 0 y 100` |
| Porcentaje pactado o IPC con precisión excesiva | `{campo} debe tener hasta dos decimales` |
| Fecha inválida | `{campo} debe ser una fecha válida en formato AAAA-MM-DD` |
| Plazo insuficiente | `El contrato aún no cumple doce meses desde el último reajuste` |

Los nombres de campo son los argumentos de la función. Se comprueban primero formatos numéricos, luego formatos de fechas, límites y precisión, y finalmente el plazo. El cálculo emplea aritmética decimal con precisión local ajustada al canon, sin usar coma flotante.

## Fuera de alcance

Obtención o certificación del IPC, identificación del contrato, verificación del año de procedencia del IPC, almacenamiento, actualización automática de la fecha del último reajuste, acumulación de reajustes, importación/exportación de hojas de cálculo, interfaz de usuario y reglas legales o contractuales adicionales. El llamador debe proporcionar el IPC correcto y guardar los resultados si lo necesita.

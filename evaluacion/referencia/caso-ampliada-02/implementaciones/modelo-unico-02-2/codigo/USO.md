# Reajuste anual de arriendos

Módulo Python 3.11 para que el analista de cartera calcule **un contrato a la vez**. No necesita red ni paquetes externos. Las pruebas requieren pytest.

## Uso

Con `src/` en la ruta de importación:

```python
from reajuste_arriendo import ErrorReajuste, calcular_reajuste

try:
    resultado = calcular_reajuste(
        canon_actual="1200000",
        ipc_anterior="5,20",
        porcentaje_pactado="10",
        fecha_base="2025-03-15",
        fecha_reajuste="2026-03-15",
    )
    print(format(resultado.porcentaje_aplicado, "f"))  # 5.20
    print(format(resultado.nuevo_canon, "f"))         # 1262400
    print(format(resultado.incremento, "f"))          # 62400
except ErrorReajuste as error:
    print(str(error))
```

Para ejecutar las pruebas desde la raíz, en una consola POSIX:

```sh
PYTHONPATH=src python -m pytest tests
```

No se incluye interfaz gráfica, consola interactiva ni servicio web: la interfaz entregada es la función Python.

## Entradas obligatorias

| Argumento | Significado y validación |
| --- | --- |
| `canon_actual` | Canon vigente en pesos, estrictamente mayor que cero. |
| `ipc_anterior` | IPC del año calendario anterior, ingresado por el analista, como porcentaje con hasta dos decimales. Puede ser cero o negativo; no se estableció un límite superior. |
| `porcentaje_pactado` | Porcentaje contractual entre 0 y 100, inclusive, con hasta dos decimales. |
| `fecha_base` | Fecha de inicio **o** del último reajuste, según corresponda al contrato. |
| `fecha_reajuste` | Fecha en la que se solicita el reajuste. |

Los argumentos omitidos, `None` y los textos vacíos o compuestos solo por espacios se consideran ausentes. Se recomienda llamar con argumentos nombrados.

### Formatos elegidos para esta implementación

Estos detalles **no fueron reglas acordadas con el cliente**; se eligieron para completar una interfaz sencilla:

- Números: `int`, `Decimal` o texto con signo opcional, dígitos y una parte decimal opcional. El texto admite coma o punto decimal y espacios exteriores: `"5,20"`, `"5.20"`, `"1200000,50"`.
- No se admiten separadores de miles, símbolos monetarios, `%`, exponentes en texto, `float` ni booleanos. Para el importe escrito habitualmente como «1.200.000», se debe pasar `1200000` o `"1200000"`. Un único punto se interpreta como decimal, nunca como separador de miles.
- Se permiten fracciones de peso en el canon, sin imponer una cantidad de decimales ni un máximo monetario de negocio. Los límites de representación y recursos son los propios de Python y `Decimal`.
- Los porcentajes se expresan en unidades porcentuales: `5,20` significa **5,20 %**, no una fracción 0,052.
- El límite de dos decimales cuenta también los ceros finales: `"5.200"` y `Decimal("5.200")` se rechazan. Se aceptan `"5"`, `"5,2"` y `"5,20"`.
- No se admiten números no finitos, como NaN o infinito.
- Fechas: objetos `datetime.date` o texto `AAAA-MM-DD`, con espacios exteriores opcionales. No se admiten objetos `datetime.datetime`, horas ni otros formatos.

El analista es responsable de seleccionar el IPC del año calendario correcto y la fecha base correcta. El módulo no puede verificar esa procedencia porque no recibe series de IPC ni el historial del contrato.

## Reglas implementadas

1. Se validan los cinco datos obligatorios.
2. Deben haber transcurrido al menos doce meses desde la fecha base. El control se hace incluso si el cálculo produciría un incremento cero.
3. Con IPC positivo, se aplica el menor entre el IPC y el porcentaje pactado. Con IPC cero o negativo, se aplica 0 %.
4. Si el porcentaje aplicado es cero, se devuelve el canon actual exacto, sin redondear, e incremento cero.
5. En los demás casos:
   - incremento exacto = canon actual × porcentaje aplicado / 100;
   - nuevo canon exacto = canon actual + incremento exacto;
   - ambos importes se redondean a la centena de peso más cercana.

### Decisiones para aspectos pendientes

Estas decisiones completan lo no definido; **no se presentan como acuerdos del cliente**:

- **Doce meses:** se usa el aniversario calendario, inclusive, no una cantidad fija de días. Del 15 de marzo de 2025 se habilita el reajuste el 15 de marzo de 2026. Para el 29 de febrero se usa el 28 de febrero del año siguiente. Una fecha solicitada anterior a la base tampoco cumple el plazo. Si la base pertenece al año 9999, ninguna fecha representable puede alcanzar su siguiente aniversario y se rechaza por plazo insuficiente.
- **Mitades:** se redondean hacia arriba mediante `ROUND_HALF_UP`; 1.234.550 pasa a 1.234.600.
- **Relación entre resultados:** incremento y nuevo canon se redondean **por separado a partir de sus valores exactos**. Por tanto, el incremento mostrado no siempre coincide con la diferencia entre los cánones. Con canon 1.234.567 y 5 %, el incremento mostrado es 61.700 y el nuevo canon 1.296.300.
- **Límite tras redondear:** se limita el porcentaje antes del cálculo, pero no se añade una corrección monetaria posterior. Por ejemplo, canon 1.000 y porcentaje aplicado 5 % dan 1.050 exactos, redondeados a 1.100; el incremento mostrado es 100. **El redondeo puede superar el aumento pactado en pesos.** Para porcentajes pequeños también puede mostrar incremento cero o un nuevo canon inferior al actual si este no es una centena exacta. No se añadió una regla para impedirlo porque no fue definida.
- Los textos de los errores generales y su orden de validación son decisiones de implementación.

## Salida

`ResultadoReajuste` es una instancia inmutable con tres atributos `Decimal`:

- `porcentaje_aplicado`: porcentaje usado, sin redondeo monetario.
- `nuevo_canon`: canon en pesos.
- `incremento`: incremento mostrado en pesos.

Se usa aritmética decimal, sin convertir los importes a `float`. El contexto del cálculo se establece localmente para no depender de la precisión decimal configurada por quien llama. Los importes redondeados pueden tener representación científica interna; `format(valor, "f")` los muestra en notación ordinaria. No se generan archivos ni se actualiza un contrato automáticamente.

## Errores

Todos los errores de validación se comunican con `ErrorReajuste`, una subclase de `ValueError`. No se devuelve resultado parcial. Si hay varios datos inválidos, se informa el primero encontrado, en este orden: canon y rango; IPC y precisión; pacto, precisión y rango; fecha base; fecha solicitada; plazo.

| Situación | Mensaje |
| --- | --- |
| Falta un dato | `Falta el dato obligatorio: <campo>` |
| Número inválido o tipo no admitido | `<campo>: debe ser un número decimal válido` |
| Canon cero o negativo | `canon_actual: debe ser mayor que cero` |
| Más de dos decimales en un porcentaje | `<campo>: debe tener como máximo dos decimales` |
| Pacto fuera de rango | `porcentaje_pactado: debe estar entre 0 y 100` |
| Fecha inválida | `<campo>: debe ser una fecha válida en formato AAAA-MM-DD` |
| Plazo insuficiente | `El contrato aún no cumple doce meses desde el último reajuste` |

El mensaje de plazo insuficiente es el texto exacto indicado por el cliente; los demás no estaban definidos.

## Alcance y pruebas

Se incluyen pruebas del ejemplo confirmado, del menor porcentaje, de los rangos y datos obligatorios, de ambos porcentajes con hasta dos decimales, del IPC no positivo, del pacto cero, del canon conservado sin redondear y del rechazo por plazo insuficiente con su mensaje exacto. También se prueban las decisiones documentadas sobre formatos, aniversario y febrero, mitades, redondeo independiente y ausencia de corrección posterior al límite.

Quedan fuera: búsqueda automática del IPC, procesamiento por lotes, almacenamiento, gestión e historial de contratos, determinación automática de cuándo corresponde el reajuste y reglas legales adicionales no indicadas por el cliente.

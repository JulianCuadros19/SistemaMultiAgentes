# Pruebas de aceptación de referencia (paso 15, ADR-0019)

Este es el oráculo común de la comparación del objetivo 4. Las mismas pruebas evalúan:
- al sistema;
- a la línea base del modelo de lenguaje con diálogo;
- a la línea base del modelo de lenguaje de un solo prompt.

Así, la tasa de errores no depende de las pruebas que cada enfoque escribió para sí mismo.

## Casos

| Caso | Arquitectura esperada | Verificaciones | Mutantes |
|---|---|---|---|
| `caso-ampliada-01`, comisiones de corretaje | ARQ-01 | 9 | 4 |
| `caso-ampliada-02`, reajuste anual del canon | ARQ-01 | 9 | 3 |
| `caso-ampliada-04`, contratos de arrendamiento | ARQ-02 | 13 | 5 |
| `caso-ampliada-07`, conciliación del recaudo | ARQ-03 | 9 | 4 |
| `caso-ampliada-10`, tarifa del impuesto predial | ARQ-04 | 10 | 4 |
| `caso-ampliada-12`, dígito de verificación del NIT | ARQ-04 | 10 | 3 |
| `caso-ampliada-14`, escaneos de expedientes | ARQ-05 | 11 | 5 |
| `caso-ampliada-16`, simulador de amortización | ARQ-05 | 10 | 3 |
| `caso-ampliada-17`, trámites catastrales | ARQ-06 | 9 | 4 |

**Selección:** 02, 12 y 16 se eligieron antes de medir. Los otros seis son el primer caso de cada
arquitectura, por número y sin mirar su resultado (ADR-0019, ajuste del diseño).

Cada carpeta trae:
- **`interfaz.md`:** la interfaz neutra, qué verifica cada prueba y qué queda sin verificar;
- **`test_referencia.py`:** las pruebas;
- **`control.py`:** una implementación de control que sigue la ficha y expone la interfaz;
- **`mutantes.json`:** variantes del control con un defecto cada una.

## Reglas del oráculo

1. **Solo lo que la ficha dice sin ambigüedad.**
   - Se verifican los ejemplos con cifras, las reglas, los rangos y los mensajes de error que la ficha
     da textualmente.
   - Lo que admite dos lecturas queda fuera, y `interfaz.md` lo registra.
2. **Fijado antes de medir.**
   - Las de 02, 12 y 16 se escribieron y se validaron antes de las corridas.
   - Las de los otros seis se escribieron solo desde la ficha y se versionaron antes de abrir sus
     salidas y de correr las líneas base. La corrida ampliada del sistema ya estaba hecha.
   - Las revisa un autor, frente a la ficha.
   - Un cambio posterior solo cabe si una prueba contradice la ficha. Se registra en el ADR-0019.
3. **Validado con mutantes.** `python scripts/evaluar_referencia.py --oraculo` exige dos cosas:
   - que el control pase todas las verificaciones;
   - que cada mutante falle al menos una.

   Corre en el entorno aislado, con Python 3.11.
4. **Los valores que la ficha no trae** se calcularon con sus reglas, con `Decimal`, y están escritos
   en las pruebas: no se recalculan al ejecutarlas.

## Adaptadores

Cada implementación evaluada lleva un adaptador, `src/adaptador_referencia.py`, que ofrece la
interfaz neutra llamando a la implementación.

- **Solo traduce:** convierte tipos, arma argumentos y convierte un error devuelto como valor en
  una excepción. No calcula nada por su cuenta.
- **Verificación automática:** rechaza las operaciones aritméticas, las funciones y los métodos que
  calculan (`sum`, `round`, `quantize`…) y los módulos de cálculo (`math`…). Para armar textos se
  usan f-strings.
- **Comportamiento ausente:** si la implementación no lo ofrece, el adaptador lanza `Ausente`
  (`referencia_comun.py`). Esas verificaciones fallan y se cuentan aparte.
- **Ubicación:** los adaptadores quedan en `adaptadores/` de cada caso, versionados con la
  evaluación.

## Ejecución

- **Ruta de importación:** el entorno aislado pone en `src/` la implementación, el adaptador y
  `referencia_comun.py`, y corre `tests/test_referencia.py` aparte de las pruebas propias de la
  implementación.
- **Comando:**

  ```bash
  python scripts/evaluar_referencia.py --manifiesto evaluacion/referencia/implementaciones.json
  ```

- **Fuera de la suite:** esta carpeta no está en `testpaths` ni la revisa Ruff, como los demás
  insumos de `evaluacion/`.

# Interfaz de referencia · caso 14, validación y renombrado de escaneos

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, estas funciones. Las
traduce a la implementación evaluada sin decidir nada por su cuenta (ver `../LEEME.md`).

```python
def validar(carpeta: str) -> dict[str, str]:
    """Cada archivo que no cumple la convención, con su motivo."""


def renombrar(carpeta: str, simulacion: bool) -> dict[str, str]:
    """Por cada archivo tratado, el nombre corregido o el texto del problema que se reporta."""


def reporte(carpeta: str) -> tuple[dict[str, int], dict[str, int]]:
    """Cantidad de archivos por año y por tipo."""


def codigo_de_salida(operacion: str, carpeta: str) -> int:
    """Ejecuta esa operación de la herramienta de terminal y devuelve su código de salida."""
```

- **Operaciones de `codigo_de_salida`:** `validar`, `renombrar` y `reporte`. El adaptador arma los
  argumentos que espera la herramienta y la ejecuta dentro del mismo proceso.
- **Errores:** las funciones lanzan una excepción con el mensaje de la implementación.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_validar_lista_el_tipo_desconocido` | «XYZ_2019_00001.pdf» no se corrige: tipo desconocido |
| `test_validar_lista_el_anio_fuera_de_rango` | «AAAA es el año, entre 1950 y el año actual» |
| `test_validar_lista_la_extension_distinta` | «extensión distinta de pdf» |
| `test_validar_no_lista_un_nombre_correcto` | La convención `TIPO_AAAA_NNNNN.pdf` |
| `test_renombrar_corrige_el_ejemplo` | «esc-2019-42.PDF» pasa a «ESC_2019_00042.pdf» |
| `test_renombrar_corrige_los_espacios` | «guiones o espacios como separadores, que pasan a guion bajo» |
| `test_la_simulacion_no_cambia_nada` | «muestra los cambios sin hacerlos» |
| `test_renombrar_no_toca_un_tipo_desconocido` | «Lo que no se corrige y se reporta» |
| `test_renombrar_reporta_el_conflicto` | «no se renombra y se reporta «Conflicto»» |
| `test_reporte_cuenta_por_anio_y_por_tipo` | «cuenta los archivos por año y por tipo» |
| `test_carpeta_inexistente_termina_con_error` | «un código de salida distinto de cero» |

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad

- **El texto exacto de los motivos:** se verifica que mencionen el tipo, el año o la extensión.
- **La línea por archivo y el resumen que se muestran:** el formato es libre.
- **La tarea programada:** es externa a la herramienta.

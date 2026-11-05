# Interfaz de referencia · caso 17, reacciones a los cambios de estado de trámites

El adaptador de cada implementación ofrece, en `src/adaptador_referencia.py`, esta función. La traduce
a la implementación evaluada sin calcular nada por su cuenta (ver `../LEEME.md`).

```python
def procesar(
    avisos: list[dict[str, object]],
) -> tuple[list[tuple[str, bool]], list[str], dict[str, float]]:
    """Publica los avisos en orden, por el canal en memoria, y devuelve lo que dejan los procesos."""
```

- **Cada aviso:** `numero`, `tipo` (`"mutación"`, `"rectificación"` o `"certificado"`),
  `estado_anterior`, `estado_nuevo` (`"radicado"`, `"en revisión"`, `"aprobado"` o `"rechazado"`), `fecha`
  (`datetime`) y `funcionario`.
- **Fecha de radicación:** la del primer aviso de cada trámite, que sale de `radicado`. Si la
  implementación la pide como dato o espera un aviso de radicación, el adaptador se la entrega.
- **Lo que devuelve:**
  - la bitácora: por cada aviso de la lista, su número de trámite y si quedó válido;
  - los mensajes preparados para el ciudadano, en orden;
  - el promedio de días hábiles por tipo de trámite.
- **El canal:** el adaptador arma el canal en memoria y los tres procesos, como lo pide la ficha para las
  pruebas.

## Lo que verifican las pruebas

| Verificación | De la ficha |
|---|---|
| `test_la_bitacora_registra_cada_aviso` | «bitácora: registra cada aviso» |
| `test_mensaje_de_aprobado` | «Su trámite T-0001 fue aprobado» |
| `test_mensaje_de_rechazado` | «Su trámite N fue rechazado; puede consultar el motivo en la oficina» |
| `test_mensaje_en_revision` | «Su trámite N está en revisión» |
| `test_dias_habiles_del_ejemplo` | Radicado el lunes 2026-11-02 y aprobado el viernes 2026-11-06: 4 días hábiles |
| `test_el_fin_de_semana_no_cuenta` | «días hábiles (lunes a viernes)» |
| `test_promedio_por_tipo_de_tramite` | «lleva el promedio por tipo de trámite» |
| `test_una_transicion_invalida_queda_marcada` | «queda en la bitácora marcado como inválido» |
| `test_una_transicion_invalida_no_se_procesa` | «no se procesa» |

## Lo que no se verifica, porque la ficha no lo dice sin ambigüedad o no es ejecutable

- **La independencia ante una falla:** provocar la falla de un proceso depende de cada implementación.
- **Si el día de radicación cuenta:** el ejemplo de la ficha fija que no.
- **Que el publicador no espere:** no es ejecutable con el canal en memoria.

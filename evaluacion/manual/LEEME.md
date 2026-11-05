# Implementación manual de los casos de referencia (paso 15, ADR-0019)

Es la línea base humana de la comparación del objetivo 4. Los casos los implementa a mano uno de los
autores, cronometrando cada fase. Después, las mismas pruebas de aceptación de referencia que evalúan
al sistema y al modelo único evalúan su implementación.

**Alcance reducido el 2026-11-05 por la fecha de entrega** (ADR-0019, ajuste del alcance): un solo
autor, dos casos como máximo, con un tope de 1 h 30 por caso.

## Antes de empezar

1. **Asignación.** Quien implementa un caso no revisa sus pruebas de referencia, y quien las revisa
   no lo implementa. Así, nadie programa para pasar unas pruebas que conoce.

   | Caso | Implementa | Revisa las pruebas de referencia |
   |---|---|---|
   | `caso-ampliada-02`, reajuste anual del canon | Julián | Laura, si puede; si no, queda sin revisión independiente |
   | `caso-ampliada-12`, dígito de verificación del NIT | Julián, solo si a las 15:15 terminó el 02 | Laura, si puede; si no, queda sin revisión independiente |
   | `caso-ampliada-16`, simulador de amortización | Nadie: es el caso de la revisión humana | Julián |

2. **Tarifa por hora, fijada antes de medir.** Convierte las horas en dinero, para comparar el costo
   de la implementación manual y de la revisión humana con el de la inferencia.

   | Tarifa por hora (USD) | Fuente | Fijada el |
   |---|---|---|
   | 9 | 3,5 M COP de salario de un desarrollador junior × 1,5 de carga laboral ÷ 180 h al mes ÷ 3.300 COP por dólar. Salario: entre los 2,8 M COP de Indeed y los 3 a 4,5 M COP de Colombia Move, consultados el 2026-11-05. La carga laboral, las horas y el cambio son supuestos | 2026-11-05 |

   El informe muestra también el costo con 5 y con 20 USD por hora.

## Qué pueden ver y qué no

- **Entrada:** solo la ficha del caso, en `evaluacion/casos/ampliada/elicitacion-*.md`, como si
  ya hubieran conversado con el cliente. Las secciones «Lo que sabes» y «Lo que no sabes» son todo
  lo que el cliente diría.
- **Recursos habituales del equipo:**
  - la documentación de Python y de los paquetes;
  - el editor;
  - el catálogo de arquitecturas y los criterios de calidad de `knowledge_base/`.
- **Sin asistentes de IA ni modelos de lenguaje:** es la línea base manual.
- **Sin mirar, hasta terminar el caso:**
  - `evaluacion/referencia/<caso>/`: la interfaz, las pruebas, el control y los mutantes;
  - las salidas del sistema y del modelo único para ese caso, en `evaluacion/resultados/`;
  - las sesiones de ese caso en la web o en la base.

## Entregables

En `evaluacion/manual/<caso>/`, con el `tiempos.csv` de `plantilla/`. Por la fecha de entrega, no se
escriben los requerimientos ni la especificación de diseño. El sistema sí los produce, así que este
recorte favorece a la implementación manual, y el informe lo dice.

| Archivo | Contenido |
|---|---|
| `src/<paquete>/` | El código, con `__init__.py` |
| `tests/` | Pruebas con pytest de cada regla, ejemplo y caso de error |
| `USO.md` | Qué hace el módulo, cómo se usa, sus entradas, salidas y errores |
| `tiempos.csv` | El tiempo de cada fase |

**Condiciones del código:** las mismas que tienen el sistema y el modelo único.
- **Entorno:** Python 3.11, con la biblioteca estándar y los paquetes del entorno aislado
  (`docker/sandbox/requisitos.txt`), sin red.
- **Estilo:** el del código generado.

  ```bash
  ruff check --config config/estilo_generado/ruff.toml evaluacion/manual/<caso>
  ```

- **Pruebas:** corren con `src/` en la ruta de importación.

## Cómo cronometrar

En `tiempos.csv`, una fila por tramo de trabajo, con la hora de inicio y de fin en formato
`AAAA-MM-DD HH:MM`.

- **Fases:**
  - `analisis`: leer la ficha y decidir cómo hacerlo;
  - `codigo`;
  - `pruebas`;
  - `documentacion`.
- **Interrupciones:** si paran, cierren la fila y abran otra al volver. Las pausas no cuentan.
- **Minutos:** si se deja vacía, la columna `minutos` se calcula del inicio y el fin.
- **Tope:** al llegar a 1 h 30 del caso, se detiene el trabajo y se evalúa lo que haya. Lo que falte
  cuenta como error.

```csv
fase,inicio,fin,minutos,notas
analisis,2026-11-05 13:55,2026-11-05 14:05,,
codigo,2026-11-05 14:05,2026-11-05 14:40,,
```

Al terminar un caso, avisen: se evalúa con `python scripts/evaluar_referencia.py`.

# Implementación manual de los casos de referencia (paso 15, ADR-0019)

Es la línea base humana de la comparación del objetivo 4. Cada caso de referencia lo implementa
a mano uno de los autores, cronometrando cada fase. Después, las mismas pruebas de aceptación de
referencia que evalúan al sistema y al modelo único evalúan su implementación.

## Antes de empezar

1. **Asignen los casos.** Quien implementa un caso no revisa sus pruebas de referencia, y quien las
   revisa no lo implementa.

   | Caso | Implementa | Revisa las pruebas de referencia |
   |---|---|---|
   | `caso-ampliada-02`, reajuste anual del canon | | |
   | `caso-ampliada-12`, dígito de verificación del NIT | | |
   | `caso-ampliada-16`, simulador de amortización | | |

2. **Fijen la tarifa por hora antes de medir.** Con ella se calcula el costo de la implementación
   manual y el de la revisión humana del sistema.

   | Tarifa por hora (USD) | Fuente | Fijada el |
   |---|---|---|
   | | | |

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

En `evaluacion/manual/<caso>/`, partiendo de `plantilla/`:

| Archivo | Contenido |
|---|---|
| `requerimientos.md` | Historias de usuario y requerimientos formales con el formato del Anexo A |
| `diseno.md` | Especificación de diseño con el formato del Anexo B |
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
  - `analisis`: leer la ficha y decidir qué falta;
  - `requerimientos`;
  - `diseno`;
  - `codigo`;
  - `pruebas`;
  - `documentacion`.
- **Interrupciones:** si paran, cierren la fila y abran otra al volver. Las pausas no cuentan.
- **Minutos:** si se deja vacía, la columna `minutos` se calcula del inicio y el fin.

```csv
fase,inicio,fin,minutos,notas
analisis,2026-11-06 09:00,2026-11-06 09:20,,
requerimientos,2026-11-06 09:20,2026-11-06 10:05,,dos historias y un RF
```

Al terminar un caso, avisen: se evalúa con `python scripts/evaluar_referencia.py`.

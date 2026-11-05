# Estado del paso 15 · casos de referencia y líneas base

Actualizado el 2026-11-05. El paso está cerrado. El diseño y sus cambios están en el ADR-0019, y los resultados, en
`docs/evaluacion/informe-objetivo-4.md`.

## Decisiones del equipo

1. **Sin implementación manual.** Realtix no puede compartir sus desarrollos y los autores no son independientes.
2. **Comparación contra un LLM independiente,** con `gpt-6.1-sol`: con diálogo, ante el mismo cliente simulado, y de un solo
   prompt, con lo que sabe el cliente.
3. **Nueve casos de referencia sintéticos:** 01, 02, 04, 07, 10, 12, 14, 16 y 17, con las seis arquitecturas.
4. **El sistema no cambió durante la medición.** Las correcciones recomendadas están en la sección 10 del informe.
5. **Tope de 17 USD.** Se gastaron 16,74.

## Lo que falta, a cargo del equipo

- [ ] Revisar los oráculos frente a las fichas: cada `evaluacion/referencia/<caso>/interfaz.md` lista qué verifica.
- [ ] Revisar 5 juicios de RAGs: `evaluacion/resultados/paso-15/rag/revision.md`.
- [ ] Aplicar `docs/tesis/` al documento y resolver las marcas `[CONFIRMAR]` de `05-evaluacion-paso-15.md`.
- [ ] Decidir los puntos abiertos de `docs/tesis/LEEME.md`.
- [ ] Rotar la clave de Azure OpenAI y borrar la máquina de demostración cuando no se necesite.

## Comandos, sin costo

Desde `~/proyectos/SistemaMultiAgentes`, con `source .venv/bin/activate` y la infraestructura arriba.

**Validar los oráculos:**

```bash
python scripts/evaluar_referencia.py --oraculo
```

**Evaluar las implementaciones:**

```bash
python scripts/evaluar_referencia.py --manifiesto evaluacion/referencia/implementaciones.json --rehacer
```

**Tabla comparativa:**

```bash
python scripts/tabla_objetivo_4.py
```

**Matriz del tester frente al oráculo.** Requiere los resultados de las corridas, en `evaluacion/resultados/`, que solo están en
esta máquina:

```bash
python scripts/matriz_tester_oraculo.py
```

**Métricas RAGs:**

```bash
python scripts/evaluar_rag.py --resumen
```

**Lo gastado:**

```bash
python -c "from pathlib import Path; from multiagente.evaluacion.traza import gastado_en_traza as g; t = sorted(Path('docs/mediciones').glob('paso-15-*.jsonl')); [print(p.name, g(p)) for p in t]; print('total', sum(g(p) for p in t))"
```

## Máquina de demostración

- **Enlace:** `https://multiagente-demo.centralus.cloudapp.azure.com/`. La contraseña no se versiona.
- **Encender y apagar:** en el portal de Azure, **Iniciar** y **Detener**. Tiene apagado automático si se corrió su comando.
- **Publicar una versión nueva:**

  ```bash
  scripts/desplegar_azure.sh multiagente-demo.centralus.cloudapp.azure.com
  ```

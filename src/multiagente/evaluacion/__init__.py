"""Evaluación del objetivo 4: casos de referencia y líneas base (paso 15, ADR-0019).

- `referencia`: el oráculo común. Las pruebas de aceptación de referencia de cada caso, que
  evalúan igual al sistema, al modelo único y a la implementación manual.
- `modelo_unico`: la línea base de un solo despliegue de Azure OpenAI, con un solo prompt.
- `matriz`: la matriz de confusión del tester frente al oráculo, en módulos reales.
- `rag`: las métricas de la generación aumentada por recuperación sobre las sesiones guardadas.

Nada de este paquete participa en el flujo del sistema: lo usan los guiones de evaluación.
"""

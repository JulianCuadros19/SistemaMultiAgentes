---
id: arq-arq-03
titulo: Pipeline de procesamiento por etapas
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, pipeline_de_datos]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-03 · Pipeline de procesamiento por etapas

        ## Descripción

        Descompone el procesamiento en etapas independientes conectadas en secuencia, donde la salida de cada etapa es la entrada de la siguiente.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - El módulo transforma datos en lotes: extracción, validación, transformación, carga
- Cada etapa puede fallar de forma independiente y reintentarse
- Se requiere trazabilidad del dato a lo largo de su transformación

        ## Estructura de módulos sugerida

        - `etapas/ · una función o clase por etapa, con contrato de entrada y salida`
- `contratos/ · esquemas de los datos que circulan entre etapas`
- `orquestacion/ · encadenamiento, manejo de errores y reintentos`
- `io/ · lectura de origen y escritura de destino`

        ## Regla de dependencia

        Cada etapa importa solo de contratos. La orquestación importa de etapas; las etapas no se importan entre sí.

        ## Consecuencias favorables

        - Cada etapa se prueba y se reintenta de forma aislada
- Facilita la instrumentación y el registro por etapa
- Permite paralelizar etapas independientes

        ## Consecuencias desfavorables

        - El estado intermedio entre etapas debe gestionarse explícitamente
- Los errores parciales exigen una política de compensación clara
- Puede ser excesiva para transformaciones de un solo paso

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |

---
id: arq-arq-05
titulo: Aplicación de línea de comandos por subcomandos
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, aplicacion_de_linea_de_comandos]
version: 1.1
fecha: 2026-11-03
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-05 · Aplicación de línea de comandos por subcomandos

        ## Descripción

        Organiza la funcionalidad como subcomandos independientes que comparten una capa de servicios común.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - El módulo es una herramienta operativa ejecutada por técnicos o por tareas programadas
- No requiere ser consumido por otros sistemas en red
- Las operaciones son discretas y se invocan por separado

        ## Estructura de módulos sugerida

        - `comandos/ · un módulo por subcomando, solo análisis de argumentos y presentación`
- `servicios/ · lógica de negocio invocada por los comandos`
- `dominio/ · entidades y reglas`
- `entrada_salida/ · lectura y escritura de archivos` (no se llama io, que es un módulo de la biblioteca estándar)

        ## Regla de dependencia

        Los comandos importan de servicios. Los servicios no importan de comandos ni conocen la consola.

        ## Consecuencias favorables

        - Muy bajo costo de despliegue y de operación
- Fácil de encadenar con otras herramientas y de programar
- Los subcomandos son unidades naturales de prueba

        ## Consecuencias desfavorables

        - No apta si se requiere acceso concurrente de múltiples usuarios
- La interacción es limitada frente a una interfaz gráfica
- El manejo de errores debe traducirse cuidadosamente a códigos de salida

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |

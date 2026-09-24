---
id: arq-arq-01
titulo: Arquitectura en capas
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, arquitectura_en_capas]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-01 · Arquitectura en capas

        ## Descripción

        Organiza el sistema en capas horizontales con dependencia unidireccional descendente: presentación, aplicación, dominio e infraestructura.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - El módulo tiene lógica de negocio moderada y flujo de datos predecible
- El equipo que mantendrá el código es mixto o rota con frecuencia
- No se prevé sustituir la tecnología de persistencia a corto plazo

        ## Estructura de módulos sugerida

        - `presentacion/ · adaptadores de entrada: CLI, API o interfaz`
- `aplicacion/ · casos de uso y orquestación de servicios`
- `dominio/ · entidades, objetos de valor y reglas de negocio`
- `infraestructura/ · persistencia, sistema de archivos, servicios externos`

        ## Regla de dependencia

        Cada capa importa únicamente de la capa inmediatamente inferior. La capa de dominio no importa de ninguna.

        ## Consecuencias favorables

        - Estructura familiar y de baja curva de aprendizaje
- Separación clara de responsabilidades por capa
- Fácil de verificar automáticamente por reglas de importación

        ## Consecuencias desfavorables

        - Puede degenerar en capas anémicas donde el dominio solo transporta datos
- Los cambios transversales obligan a tocar todas las capas
- Acopla el dominio a la dirección de dependencia hacia infraestructura

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |

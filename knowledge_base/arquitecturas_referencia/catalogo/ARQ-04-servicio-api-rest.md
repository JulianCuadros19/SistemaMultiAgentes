---
id: arq-arq-04
titulo: Servicio de API REST por recursos
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, servicio_api_rest]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-04 · Servicio de API REST por recursos

        ## Descripción

        Expone la funcionalidad como recursos identificados por rutas, con operaciones sobre ellos y separación entre enrutamiento, servicios y persistencia.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - El módulo debe ser consumido por otros sistemas o por una interfaz web
- Las operaciones se modelan naturalmente como recursos
- Se requieren contratos de interfaz explícitos y documentados

        ## Estructura de módulos sugerida

        - `rutas/ · definición de endpoints y validación de entrada`
- `esquemas/ · modelos de petición y respuesta`
- `servicios/ · lógica de negocio independiente del transporte`
- `repositorios/ · acceso a datos`

        ## Regla de dependencia

        Las rutas importan de esquemas y servicios. Los servicios no importan de rutas ni conocen el protocolo.

        ## Consecuencias favorables

        - Contrato de interfaz explícito y verificable
- Separación natural entre transporte y lógica
- Documentación generable automáticamente desde los esquemas

        ## Consecuencias desfavorables

        - Añade una capa de transporte que puede ser innecesaria en procesos internos
- Exige gestionar versionado de la interfaz
- Introduce preocupaciones de autenticación y manejo de errores HTTP

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |

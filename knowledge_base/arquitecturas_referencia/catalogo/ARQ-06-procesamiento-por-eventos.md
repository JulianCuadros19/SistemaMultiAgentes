---
id: arq-arq-06
titulo: Procesamiento dirigido por eventos
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, procesamiento_por_eventos]
version: 1.1
fecha: 2026-11-03
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-06 · Procesamiento dirigido por eventos

        ## Descripción

        Los componentes reaccionan a eventos publicados en un canal, sin conocerse entre sí, lo que desacopla emisor y receptor.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - El módulo debe reaccionar a cambios producidos por otros procesos
- Se requiere desacoplar productores y consumidores en el tiempo
- Existen múltiples consumidores interesados en el mismo hecho

        ## Estructura de módulos sugerida

        - `eventos/ · definición y esquema de los eventos del dominio`
- `productores/ · componentes que publican eventos`
- `consumidores/ · manejadores, uno por tipo de evento`
- `infraestructura/ · adaptador del canal de mensajería y almacén del estado que registran y actualizan los consumidores, con operaciones de registro y de consulta`

        ## Regla de dependencia

        Productores y consumidores importan solo de eventos. Nunca se importan entre sí.

        ## Consecuencias favorables

        - Desacoplamiento fuerte entre componentes
- Permite añadir consumidores sin modificar el productor
- Absorbe picos de carga mediante la cola

        ## Consecuencias desfavorables

        - La depuración es más difícil por la ausencia de flujo lineal
- Exige garantizar idempotencia en los consumidores
- Introduce consistencia eventual y complejidad operativa

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |
        | Estado del dominio | Dónde vive lo que los consumidores registran o actualizan, y con qué interfaces se registra y se consulta |

---
id: arq-arq-02
titulo: Arquitectura hexagonal o de puertos y adaptadores
fuente: Catálogo de arquitecturas de referencia, elaboración propia sobre patrones consolidados
tipo_fuente: practica_industria
tags: [arquitectura, catalogo, arquitectura_hexagonal]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# ARQ-02 · Arquitectura hexagonal o de puertos y adaptadores

        ## Descripción

        Sitúa el dominio en el centro y define puertos como interfaces abstractas; los adaptadores implementan esos puertos hacia tecnologías concretas.

        ## Criterios de aplicabilidad

        Esta arquitectura es candidata cuando se cumple al menos uno de estos criterios:

        - La lógica de negocio es el activo principal y debe poder probarse aislada
- Se prevé sustituir o añadir tecnologías de persistencia o entrada
- El módulo debe ser ejercitable sin infraestructura real en las pruebas

        ## Estructura de módulos sugerida

        - `dominio/ · entidades y reglas, sin dependencias externas`
- `puertos/ · interfaces abstractas que el dominio requiere`
- `adaptadores/entrada/ · CLI, API, consumidores de eventos`
- `adaptadores/salida/ · repositorios, clientes de servicios externos`

        ## Regla de dependencia

        El dominio define los puertos. Los adaptadores importan del dominio; el dominio nunca importa de los adaptadores.

        ## Consecuencias favorables

        - El dominio queda libre de dependencias tecnológicas
- Las pruebas del dominio no requieren base de datos ni red
- Sustituir una tecnología solo implica escribir otro adaptador

        ## Consecuencias desfavorables

        - Introduce indirección y más archivos para el mismo comportamiento
- Desproporcionada para módulos con lógica de negocio trivial
- Exige disciplina para no filtrar tipos de infraestructura al dominio

        ## Parámetros que el arquitecto debe definir

        | Parámetro | Descripción |
        |---|---|
        | Nombre de los módulos | Adaptado al dominio del requerimiento, no genérico |
        | Asignación de requerimientos | Qué requerimiento implementa cada módulo |
        | Interfaces públicas | Firma completa de lo que cada módulo expone |
        | Dependencias externas | Librerías del catálogo tecnológico que se emplearán |

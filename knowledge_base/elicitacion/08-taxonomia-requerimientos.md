---
id: eli-008
titulo: Taxonomía de requerimientos
fuente: Sommerville (2015); ISO/IEC 25010:2023
tipo_fuente: estandar_internacional
tags: [taxonomia, funcional, no_funcional]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Taxonomía de requerimientos

El agente elicitador debe clasificar correctamente cada necesidad capturada, porque el tipo
determina la plantilla de salida y el destino en el flujo.

## Requerimientos funcionales

Describen **qué debe hacer** el sistema: entradas, comportamientos y salidas. Incluyen
cálculos, validaciones, transformaciones, reportes, integraciones y reglas de negocio.
Son los que se transforman en la plantilla del requerimiento formal y los que el agente
desarrollador implementa.

Señal de identificación: la frase puede reescribirse como «el sistema debe [verbo]…».

## Requerimientos no funcionales

Describen **cómo debe comportarse** el sistema en términos de calidad. Se clasifican según
las nueve características de la norma ISO/IEC 25010:2023:

| Característica | Pregunta que responde |
|---|---|
| Adecuación funcional | ¿Cubre y ejecuta correctamente las funciones requeridas? |
| Eficiencia de desempeño | ¿Responde en el tiempo y con los recursos esperados? |
| Compatibilidad | ¿Coexiste e intercambia información con otros sistemas? |
| Capacidad de interacción | ¿Puede ser usado con eficacia por sus usuarios? |
| Fiabilidad | ¿Opera sin fallos y se recupera de ellos? |
| Seguridad | ¿Protege la información y controla el acceso? |
| Mantenibilidad | ¿Puede modificarse con eficacia y bajo riesgo? |
| Flexibilidad | ¿Se adapta, escala y se instala en distintos entornos? |
| Seguridad física | ¿Evita estados que pongan en riesgo personas o bienes? |

Nota de versión: la edición 2023 sustituyó «usabilidad» por *capacidad de interacción* y
«portabilidad» por *flexibilidad*, e incorporó *seguridad física* como característica nueva.

## Requerimientos de dominio

Restricciones que provienen del sector, no del cliente. En el dominio catastral y
tributario son típicamente normativas: formatos de identificación predial, periodicidad
de las vigencias, estructura del modelo de datos oficial, tolerancias geométricas.
El agente debe reconocerlos aunque el cliente no los mencione, porque son de obligatorio
cumplimiento.

## Requerimientos de interfaz

Definen cómo el sistema intercambia información con el exterior: formatos de archivo,
estructuras de intercambio, protocolos, sistemas externos con los que se integra.

## Regla de enrutamiento

| Tipo detectado | Destino |
|---|---|
| Funcional | Plantilla de requerimiento formal, va al arquitecto |
| No funcional | Se registra como restricción de calidad que condiciona la arquitectura |
| De dominio | Se registra como restricción obligatoria, no negociable |
| De interfaz | Se registra como contrato externo en el requerimiento |

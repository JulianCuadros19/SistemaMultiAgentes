---
id: dom-004
titulo: Modelo de datos catastral y estándares geoespaciales
fuente: Modelo LADM-COL basado en ISO 19152; marco de referencia MAGNA-SIRGAS
tipo_fuente: estandar_internacional
tags: [ladm, iso19152, geoespacial, modelo_datos]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Modelo de datos catastral y estándares geoespaciales

El dominio catastral colombiano se estructura sobre un modelo de datos normalizado derivado
del estándar internacional de administración del territorio. El agente elicitador debe
reconocer estos elementos porque condicionan la estructura de datos de cualquier
requerimiento del dominio.

## Modelo de dominio de administración del territorio

El modelo nacional se basa en el estándar ISO 19152, *Land Administration Domain Model*,
que define un vocabulario común para describir la relación entre personas, derechos y
unidades territoriales. Su adopción nacional especifica las clases, atributos y relaciones
obligatorias para la información catastral.

## Entidades conceptuales principales

| Entidad | Descripción |
|---|---|
| Interesado | Persona natural o jurídica que ostenta un derecho sobre el predio |
| Unidad espacial | Representación geométrica del predio: terreno, construcción, unidad |
| Derecho | Vínculo jurídico entre el interesado y la unidad espacial |
| Restricción | Limitación al ejercicio del derecho, como servidumbres o afectaciones |
| Responsabilidad | Obligación asociada a la tenencia del predio |
| Fuente administrativa | Documento que soporta el derecho, la restricción o la responsabilidad |
| Fuente espacial | Insumo que soporta la geometría, como el levantamiento topográfico |

## Marco de referencia geodésico

La información geoespacial catastral se georreferencia en el marco de referencia oficial
nacional. El sistema de proyección plano-cartesiano de referencia para el territorio
continental se identifica con el código EPSG 9377. Todo requerimiento que manipule
geometrías debe declarar explícitamente el sistema de coordenadas de entrada y de salida.

## Reglas de calidad geométrica

Los procesos catastrales imponen validaciones topológicas y geométricas que suelen
traducirse en reglas de negocio:

1. Las geometrías de terreno deben ser polígonos cerrados y válidos, sin autointersecciones.
2. No deben existir superposiciones entre terrenos de predios distintos más allá de la
   tolerancia definida.
3. No deben existir vacíos entre predios colindantes más allá de la tolerancia definida.
4. El área calculada a partir de la geometría debe ser consistente con el área declarada
   dentro del margen de tolerancia.
5. Toda unidad espacial debe estar asociada al menos a un interesado mediante un derecho.

## Implicaciones para los requerimientos

Cuando un requerimiento manipula información predial, el agente debe indagar:

- ¿El proceso trabaja con la geometría del predio o solo con sus atributos alfanuméricos?
- ¿Qué sistema de coordenadas usan los datos de entrada?
- ¿Qué tolerancia se acepta en las validaciones de área y topología?
- ¿El resultado debe cumplir la estructura del modelo de datos oficial para su entrega?

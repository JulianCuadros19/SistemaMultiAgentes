---
id: dom-005
titulo: Marco normativo del servicio catastral
fuente: Normativa colombiana de catastro multipropósito
tipo_fuente: normativa_nacional
tags: [normativa, catastro, regulacion]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Marco normativo del servicio catastral

Los requerimientos del dominio están condicionados por normativa de obligatorio
cumplimiento. El agente elicitador debe registrarlos como requerimientos de dominio,
no negociables, incluso si el cliente no los menciona.

## Instrumentos de política

El catastro multipropósito fue elevado a política de Estado mediante el Plan Nacional de
Desarrollo, que habilitó la figura de gestores catastrales distintos al instituto
geográfico nacional y ordenó la implementación progresiva del modelo en el territorio.
Los documentos de política económica y social que le dieron origen definieron la hoja de
ruta, el esquema institucional y las fuentes de financiación.

## Regulación técnica

La regulación del servicio público de gestión catastral define de manera integral los
procedimientos de formación, actualización, conservación y difusión; las funciones de
gestores y operadores; la interrelación con el registro de instrumentos públicos; y las
especificaciones técnicas de la base de datos catastral.

La norma técnica del modelo de datos establece las clases, atributos y relaciones
obligatorias, las tolerancias geométricas y topológicas, los procedimientos de mutación y
los criterios de control de calidad de la información.

## Obligaciones que impactan los requerimientos

| Obligación | Efecto en el software |
|---|---|
| Estructura de datos oficial | El modelo de datos de salida debe ser conforme |
| Interrelación con registro | Debe existir mecanismo de conciliación con el folio de matrícula |
| Trazabilidad de actos | Toda modificación debe quedar asociada al acto administrativo que la soporta |
| Conservación de históricos | No se sobrescribe información; se versiona por vigencia |
| Protección de datos personales | La información de interesados es dato personal y su tratamiento está regulado |
| Publicidad y notificación | Los actos que afectan al propietario requieren notificación formal |

## Preguntas que el agente debe formular ante un requerimiento del dominio

- ¿Este proceso produce un acto administrativo que deba quedar registrado?
- ¿La información resultante debe entregarse en el formato del modelo de datos oficial?
- ¿Hay un plazo normativo asociado a este trámite?
- ¿La información que se manipula incluye datos personales de los propietarios?
- ¿Debe conservarse el histórico de la información anterior al cambio?

## Nota de vigencia

La normativa catastral colombiana ha tenido cambios frecuentes. Todo requerimiento que
dependa de un umbral, un plazo o un porcentaje normativo debe registrar la fuente y la
fecha de consulta, y marcarse para revisión periódica.

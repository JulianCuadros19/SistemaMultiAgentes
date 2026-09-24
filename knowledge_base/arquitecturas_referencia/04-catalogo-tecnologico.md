---
id: arq-004
titulo: Catálogo tecnológico autorizado
fuente: Elaboración propia
tipo_fuente: elaboracion_propia
tags: [stack, librerias, dependencias]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Catálogo tecnológico autorizado

Conjunto cerrado de dependencias que el agente arquitecto puede declarar en el contrato de
diseño. Cualquier dependencia fuera de este catálogo constituye una violación verificable
del contrato.

## Lenguaje y versión

| Elemento | Valor |
|---|---|
| Lenguaje | Python |
| Versión mínima | 3.11 |
| Gestión de dependencias | Declaración explícita en archivo de proyecto |

## Librerías por propósito

| Propósito | Librería autorizada | Cuándo usarla |
|---|---|---|
| Validación de datos y esquemas | `pydantic` | Modelado de entradas, salidas y contratos |
| Interfaz de línea de comandos | `typer` | Arquitectura ARQ-05 |
| Servicio HTTP | `fastapi` | Arquitectura ARQ-04 |
| Servidor de aplicación | `uvicorn` | Acompaña a `fastapi` |
| Acceso a base de datos relacional | `sqlalchemy` | Persistencia con mapeo de objetos |
| Controlador PostgreSQL | `psycopg` | Acceso directo cuando no se requiere mapeo |
| Manipulación tabular | `pandas` | Procesamiento de lotes en ARQ-03 |
| Cómputo numérico | `numpy` | Operaciones vectorizadas |
| Fechas y zonas horarias | Biblioteca estándar `datetime`, `zoneinfo` | Siempre |
| Decimales financieros | Biblioteca estándar `decimal` | Obligatoria en cálculos monetarios |
| Registro de eventos | Biblioteca estándar `logging` | Siempre |
| Pruebas | `pytest` | Siempre |
| Datos de prueba | `pytest` con parametrización | Casos derivados de criterios Gherkin |

## Reglas de uso

1. **Decimales en dinero.** Todo cálculo monetario o de avalúo debe usar el tipo decimal de
   la biblioteca estándar. El uso de punto flotante en cálculos de dinero es una violación
   de severidad alta.
2. **Biblioteca estándar primero.** Si la biblioteca estándar resuelve la necesidad, no se
   declara una dependencia externa.
3. **Sin dependencias transitivas implícitas.** Solo se declara lo que se importa
   directamente.
4. **Sin librerías de propósito no listado.** Si un requerimiento exige una capacidad no
   cubierta, el arquitecto lo registra como pregunta abierta y no inventa la dependencia.

## Prohibiciones explícitas

| Práctica prohibida | Razón |
|---|---|
| Ejecución dinámica de código (`eval`, `exec`) | Riesgo de seguridad |
| Invocación de comandos del sistema con entrada no validada | Riesgo de inyección |
| Credenciales embebidas en el código | Riesgo de seguridad |
| Punto flotante en cálculos monetarios | Error de precisión acumulado |
| Dependencias sin versión declarada | Irreproducibilidad de la construcción |

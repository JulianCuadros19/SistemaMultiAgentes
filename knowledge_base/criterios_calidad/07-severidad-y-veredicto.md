---
id: cal-sv
titulo: Escala de severidad y regla de veredicto
fuente: Elaboración propia con base en ISO/IEC 25010:2023 e ISO/IEC/IEEE 29119
tipo_fuente: elaboracion_propia
tags: [severidad, veredicto, decision]
version: 1.1
fecha: 2026-10-08
agente_consumidor: tester
segmentacion: una_regla_por_fragmento
coleccion: criterios_calidad
---

# Escala de severidad y regla de veredicto

Define cómo el agente tester traduce el conjunto de hallazgos en un veredicto único.

## Escala de severidad

| Severidad | Definición | Efecto |
|---|---|---|
| Alta | El hallazgo impide que el código cumpla su propósito, compromete la seguridad o viola la especificación de diseño | Bloquea la aprobación |
| Media | El hallazgo degrada la calidad de forma apreciable pero el código cumple funcionalmente | No bloquea; se reporta para corrección |
| Baja | El hallazgo es de estilo o consistencia sin impacto funcional | Se reporta como observación |

## Regla de veredicto

```
SI existe al menos un hallazgo de severidad Alta
   ENTONCES veredicto = RECHAZADO
SI NO, SI algún criterio de aceptación quedó sin cumplir
   ENTONCES veredicto = RECHAZADO
SI NO, SI el número de hallazgos de severidad Media supera el umbral configurado
   ENTONCES veredicto = RECHAZADO
SI NO
   ENTONCES veredicto = APROBADO
```

## Estructura obligatoria del veredicto

```json
{
  "veredicto": "APROBADO | RECHAZADO",
  "criterios": [
    {"id": "ESC-01", "requerimiento": "RF-021", "cumplido": true,
     "evidencia": "test_mutacion_valida"}
  ],
  "conformidad_arquitectonica": {
    "modulos_declarados": 4, "modulos_encontrados": 4,
    "interfaces_conformes": 7, "interfaces_divergentes": 0,
    "dependencias_no_autorizadas": []
  },
  "hallazgos": [
    {"regla": "CAL-MT-001", "severidad": "Alta",
     "ubicacion": "src/dominio/predio.py:42",
     "descripcion": "La función publica no expone documentacion",
     "sugerencia": "Agregar documentacion con parametros, retorno y excepciones"}
  ],
  "resumen": {"alta": 1, "media": 0, "baja": 3}
}
```

## Reglas de conducta del agente tester

1. **No corregir.** El tester dictamina; la corrección corresponde al desarrollador.
2. **Toda afirmación con evidencia.** Un criterio marcado como cumplido debe nombrar la
   prueba que lo demuestra.
3. **Reportar todo, no solo el primero.** El reporte incluye la totalidad de los hallazgos
   para que el desarrollador corrija en un solo ciclo.
4. **Referenciar la regla.** Cada hallazgo cita el identificador de la regla de calidad que
   lo origina, lo que hace el veredicto trazable y auditable.
5. **No inventar hallazgos.** Si una comprobación no pudo ejecutarse, se reporta como no
   evaluada, nunca como aprobada.

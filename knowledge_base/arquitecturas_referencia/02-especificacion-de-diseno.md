---
id: arq-002
titulo: Esquema de la especificación de diseño
fuente: Formato del Anexo B del documento de tesis
tipo_fuente: elaboracion_propia
tags: [especificacion, esquema, diseño, modulos, anexo_b]
version: 1.2
fecha: 2026-11-03
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Esquema de la especificación de diseño

La especificación de diseño es la salida principal del agente arquitecto y la entrada única del
agente desarrollador. Es un artefacto estructurado, validable contra esquema, no un
documento en prosa. Su precisión determina la calidad del código generado, porque el
desarrollador no dispone de ninguna otra fuente de información.

## Estructura

```json
{
  "id_especificacion": "ED-003",
  "version": "0.1",
  "arquitectura_base": "ARQ-02",
  "requerimientos_cubiertos": ["RF-021", "RF-022", "RF-023"],
  "modulos": [
    {
      "nombre": "dominio.predio",
      "ruta": "src/dominio/predio.py",
      "responsabilidad": "Entidad de predio y sus invariantes de negocio",
      "capa": "dominio",
      "interfaces_publicas": [
        {
          "nombre": "Predio",
          "tipo": "clase",
          "firma": "Predio(numero_predial: str, area_terreno: Decimal, area_construida: Decimal)",
          "descripcion": "Representa un predio con sus atributos físicos",
          "excepciones": ["NumeroPredialInvalido"]
        }
      ],
      "dependencias_permitidas": [],
      "requerimientos": ["RF-021"]
    }
  ],
  "modelo_datos": [
    {
      "nombre": "Predio",
      "campos": [
        {"nombre": "numero_predial", "tipo": "str", "obligatorio": true,
         "restriccion": "exactamente 30 dígitos numéricos"}
      ]
    }
  ],
  "dependencias_externas": [
    {"paquete": "pydantic", "proposito": "validación de esquemas de datos"}
  ],
  "reglas_de_dependencia": [
    "La capa de dominio no importa de ninguna otra capa",
    "La capa de aplicación importa de dominio pero no de infraestructura"
  ]
}
```

## Reglas de validación de la especificación

| Regla | Verificación |
|---|---|
| Cobertura completa | Todo requerimiento aprobado aparece en `requerimientos` de al menos un módulo |
| Sin dependencias circulares | El grafo de `dependencias_permitidas` es acíclico |
| Interfaces declaradas | Todo módulo expone al menos una interfaz pública |
| Firmas completas | Toda interfaz declara tipos de parámetros y de retorno |
| Stack autorizado | Toda dependencia externa pertenece al catálogo tecnológico |
| Rutas coherentes | La ruta del archivo corresponde a la capa declarada |
| Escenarios ejecutables | Todo escenario aprobado tiene un recorrido que lo prepara, lo ejecuta y lo observa con interfaces declaradas. El recorrido acompaña a la especificación, fuera del Anexo B |

## Por qué la especificación debe ser estructurada y no prosa

El agente tester verifica la conformidad arquitectónica del código de forma determinística:
comprueba que cada módulo declarado exista, que sus interfaces públicas coincidan con las
firmas de la especificación y que ningún módulo importe algo fuera de `dependencias_permitidas`.
Esa verificación solo es posible si la especificación es legible por máquina. Un documento en
prosa obligaría a una evaluación subjetiva y haría el veredicto no reproducible.

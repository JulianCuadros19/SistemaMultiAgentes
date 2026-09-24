---
id: arq-002
titulo: Esquema del contrato de diseño
fuente: Elaboración propia
tipo_fuente: elaboracion_propia
tags: [contrato, esquema, diseño, modulos]
version: 1.0
fecha: 2026-09-14
agente_consumidor: arquitecto
segmentacion: por_unidad_conceptual
coleccion: arquitecturas_referencia
---

# Esquema del contrato de diseño

El contrato de diseño es la salida principal del agente arquitecto y la entrada única del
agente desarrollador. Es un artefacto estructurado, validable contra esquema, no un
documento en prosa. Su precisión determina la calidad del código generado, porque el
desarrollador no dispone de ninguna otra fuente de información.

## Estructura

```json
{
  "id_contrato": "CD-003",
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

## Reglas de validación del contrato

| Regla | Verificación |
|---|---|
| Cobertura completa | Todo requerimiento aprobado aparece en `requerimientos` de al menos un módulo |
| Sin dependencias circulares | El grafo de `dependencias_permitidas` es acíclico |
| Interfaces declaradas | Todo módulo expone al menos una interfaz pública |
| Firmas completas | Toda interfaz declara tipos de parámetros y de retorno |
| Stack autorizado | Toda dependencia externa pertenece al catálogo tecnológico |
| Rutas coherentes | La ruta del archivo corresponde a la capa declarada |

## Por qué el contrato debe ser estructurado y no prosa

El agente tester verifica la conformidad arquitectónica del código de forma determinística:
comprueba que cada módulo declarado exista, que sus interfaces públicas coincidan con las
firmas del contrato y que ningún módulo importe algo fuera de `dependencias_permitidas`.
Esa verificación solo es posible si el contrato es legible por máquina. Un documento en
prosa obligaría a una evaluación subjetiva y haría el veredicto no reproducible.

---
id: eli-001
titulo: Formato de la historia de usuario
fuente: Cohn, User Stories Applied (2004); práctica ágil consolidada
tipo_fuente: practica_industria
tags: [historia_usuario, formato, plantilla]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Formato de la historia de usuario

## Estructura obligatoria

Toda historia de usuario producida por el agente elicitador debe seguir la plantilla de tres
partes. Ninguna de las tres es opcional.

```
Como [ROL]
quiero [FUNCIONALIDAD]
para [BENEFICIO]
```

## Reglas de redacción de cada parte

**ROL.** Identifica quién obtiene el valor. Debe ser un rol concreto del negocio, nunca
«usuario» ni «el sistema». Ejemplos válidos en el dominio: *liquidador catastral*,
*analista de conservación*, *funcionario de la secretaría de hacienda*, *gestor catastral*.
Si el cliente dice «el usuario», el elicitador debe preguntar cuál rol específico.

**FUNCIONALIDAD.** Describe la capacidad deseada, no la solución técnica. Inicia con verbo en
infinitivo. Es incorrecto escribir «quiero un botón azul»; es correcto «quiero exportar el
listado de predios actualizados».

**BENEFICIO.** Responde por qué la funcionalidad importa. Es la parte que más se omite y la
que más valor aporta: sin beneficio explícito no puede evaluarse la prioridad ni descartarse
una funcionalidad innecesaria. Si el cliente no lo expresa, el elicitador debe preguntarlo
de forma directa.

## Atributos complementarios

Además del enunciado, cada historia registra:

| Atributo | Descripción |
|---|---|
| `id` | Identificador único con prefijo `HU-` y numeración correlativa |
| `epica` | Agrupación funcional a la que pertenece |
| `prioridad` | Alta, media o baja, acordada con el cliente |
| `supuestos` | Condiciones que el elicitador asumió y el cliente debe confirmar |
| `preguntas_abiertas` | Puntos que quedaron sin resolver en la conversación |

## Antipatrones que el elicitador debe evitar

- **Historia técnica disfrazada.** «Como desarrollador quiero refactorizar el módulo» no
  aporta valor de negocio observable.
- **Historia compuesta.** Si el enunciado contiene «y» entre dos capacidades distintas,
  deben separarse en dos historias.
- **Beneficio tautológico.** «para poder exportar» como beneficio de «quiero exportar» no
  aporta información; hay que preguntar qué hace el rol con ese archivo.
- **Solución prescrita.** El cliente propone la implementación en lugar de la necesidad.
  El elicitador debe reconducir preguntando qué problema resuelve esa implementación.

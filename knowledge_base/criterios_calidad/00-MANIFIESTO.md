# Manifiesto de la colección `criterios_calidad`

- **Agente consumidor:** tester
- **Documentos:** 8
- **Segmentación:** una_regla_por_fragmento
- **Fecha de construcción:** 2026-09-14

## Inventario

| id | Archivo | Título | Tipo de fuente |
|---|---|---|---|
| `cal-fs` | `iso25010/01-adecuacion-funcional.md` | Adecuación funcional | estandar_internacional |
| `cal-mt` | `iso25010/02-mantenibilidad.md` | Mantenibilidad | estandar_internacional |
| `cal-sg` | `iso25010/03-seguridad.md` | Seguridad | estandar_internacional |
| `cal-fb` | `iso25010/04-fiabilidad-y-desempeno.md` | Fiabilidad y eficiencia de desempeño | estandar_internacional |
| `cal-ar` | `iso25010/05-conformidad-arquitectonica.md` | Conformidad arquitectónica y compatibilidad | estandar_internacional |
| `cal-tp` | `ieee29119/06-tecnicas-de-prueba.md` | Técnicas de diseño de casos de prueba | estandar_internacional |
| `cal-sv` | `07-severidad-y-veredicto.md` | Escala de severidad y regla de veredicto | elaboracion_propia |
| `cal-pg` | `iso9001/08-principios-gestion-calidad.md` | Principios de gestión de la calidad aplicados al proceso | estandar_internacional |

## Nota sobre el formato de las reglas

Cada documento contiene reglas atómicas delimitadas por encabezado de tercer nivel
con el prefijo `### REGLA`. El proceso de ingesta debe segmentar por ese delimitador,
de modo que cada fragmento recuperable corresponda exactamente a una regla verificable.

## Nota sobre derechos de autor

Las reglas son de elaboración propia. No reproducen el texto de las normas ISO, que
es material protegido. Cada regla cita la norma de referencia para trazabilidad, pero
su redacción y sus criterios de verificación fueron construidos para este proyecto.

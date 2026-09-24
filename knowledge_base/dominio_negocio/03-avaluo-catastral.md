---
id: dom-003
titulo: Avalúo catastral y componentes
fuente: IGAC, normativa de avalúos catastrales
tipo_fuente: normativa_nacional
tags: [avaluo, valoracion, reglas_negocio]
coleccion: dominio_negocio
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Avalúo catastral y componentes

El avalúo catastral es la determinación del valor de los predios, obtenida mediante
investigación y análisis estadístico del mercado inmobiliario. Constituye la base gravable
del impuesto predial y aparece en casi todo requerimiento de liquidación.

## Composición

El avalúo catastral de un predio resulta de la suma de dos componentes:

```
avalúo_catastral = avalúo_terreno + avalúo_construcción
```

**Avalúo del terreno.** Producto del área del terreno por el valor unitario del terreno
correspondiente a su zona homogénea física y geoeconómica.

**Avalúo de la construcción.** Producto del área construida por el valor unitario de
construcción, determinado según la tipología, el uso y el estado de conservación.

## Conceptos asociados

**Zona homogénea física.** Área geográfica con características similares en vías,
servicios públicos, uso del suelo, tipología de construcción y norma urbanística.

**Zona homogénea geoeconómica.** Área dentro de una zona homogénea física a la que se
asigna un valor unitario de terreno homogéneo.

**Valor unitario de terreno.** Valor por metro cuadrado asignado a una zona homogénea
geoeconómica para una vigencia determinada.

**Tipología constructiva.** Clasificación de la construcción según materiales, acabados y
sistema estructural, que determina el valor unitario de construcción aplicable.

**Uso del predio.** Destinación económica: residencial, comercial, industrial,
institucional, agropecuario, entre otros. Incide en la tarifa del impuesto.

**Vigencia.** Periodo anual al que corresponde la información catastral y su avalúo.

## Reglas de negocio típicas

1. El avalúo se determina por vigencia; cada vigencia tiene sus propios valores unitarios.
2. Un predio sin construcción registrada tiene avalúo igual al del terreno.
3. Los avalúos se reajustan anualmente conforme al índice que fije la autoridad competente.
4. Toda mutación que modifique área, construcción o uso obliga a recalcular el avalúo.
5. El propietario puede solicitar revisión del avalúo cuando considere que no corresponde
   a las características del predio.
6. El avalúo catastral no puede ser inferior al porcentaje del avalúo comercial que fije
   la normativa vigente.

## Validaciones habituales en requerimientos

| Validación | Regla |
|---|---|
| Área de terreno | Mayor que cero; unidad según localización urbana o rural |
| Área construida | Mayor o igual a cero; cero implica predio sin construcción |
| Vigencia | Año de cuatro dígitos; no superior a la vigencia actual más uno |
| Valor unitario | Mayor que cero y correspondiente a la zona y vigencia del predio |
| Avalúo resultante | Mayor que cero; expresado en pesos colombianos sin decimales |

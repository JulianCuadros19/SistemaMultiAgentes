---
id: caso-elicitacion-02
titulo: Cálculo del avalúo catastral de un predio
cliente: Oficina de catastro municipal (sintética)
proyecto: Gestión catastral municipal
necesidad: Necesitamos calcular el avalúo de cada predio a partir de sus características físicas; hoy lo hacemos en hojas de cálculo y a veces los valores no cuadran.
version: 1.0
---

Caso sintético para probar el flujo de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve. Sus
reglas son las del caso de diseño `diseno-avaluo.json`.

## Quién eres

Lideras el área de liquidación de una oficina municipal de catastro. Conoces bien el proceso,
pero no tienes formación técnica.

## Lo que sabes

- Quien calcula el avalúo es el liquidador catastral.
- Lo necesitan para emitir la liquidación del impuesto predial del periodo.
- Hoy el liquidador copia las áreas del predio y los valores unitarios en una hoja de cálculo; a
  veces se equivoca de fila o los totales no coinciden.
- Para calcularlo, el predio debe existir y tener ficha catastral vigente, y los valores
  unitarios de la vigencia deben estar registrados. La oficina los publica cada año por zona
  homogénea geoeconómica (para el terreno) y por tipología constructiva (para la construcción).
- Reglas del cálculo:
  - El avalúo del terreno es el área de terreno por el valor unitario de la zona homogénea
    geoeconómica del predio, para la vigencia.
  - El avalúo de la construcción es el área construida por el valor unitario de su tipología
    constructiva, para la vigencia.
  - El avalúo total es la suma de los dos.
  - Un predio sin construcción tiene avalúo igual al del terreno.
  - Los valores se expresan en pesos colombianos sin decimales.
- Datos que el liquidador tiene a la mano:
  - número predial: 30 dígitos, obligatorio;
  - vigencia: año de cuatro dígitos, obligatorio; no puede ser mayor que el año siguiente al
    actual;
  - área de terreno en metros cuadrados: obligatoria y mayor que cero;
  - área construida en metros cuadrados: obligatoria, mayor o igual a cero; cero significa que
    el predio no tiene construcción.
- Lo que debe entregar el cálculo: el avalúo del terreno, el de la construcción y el total, en
  pesos sin decimales.
- Un ejemplo que usan para verificar: un predio con 200 m² de terreno a 500.000 pesos por m² y
  100 m² construidos a 1.200.000 pesos por m² tiene un avalúo total de 220.000.000 pesos.
- Casos de error: si el área de terreno es cero, el cálculo se rechaza indicando que el área de
  terreno debe ser mayor que cero.
- Es de prioridad alta: sin el avalúo no se puede liquidar el impuesto.

## Lo que no sabes

No sabes cómo se liquida el impuesto predial a partir del avalúo ni cómo se registran las
mutaciones de propietario: no son parte de este cálculo. No conoces detalles técnicos del
sistema.

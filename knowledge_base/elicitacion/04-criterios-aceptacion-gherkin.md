---
id: eli-004
titulo: Redacción de criterios de aceptación en Gherkin
fuente: Behaviour-Driven Development; práctica industrial consolidada
tipo_fuente: practica_industria
tags: [gherkin, criterios_aceptacion, pruebas]
coleccion: elicitacion
version: 1.0
fecha: 2026-09-14
agente_consumidor: elicitador
segmentacion: por_seccion
---

# Redacción de criterios de aceptación en formato Gherkin

Los criterios de aceptación son el puente entre el requerimiento y la prueba automatizada.
El agente desarrollador deriva de ellos las pruebas unitarias, y el agente tester los usa
para emitir el veredicto. Por tanto, su calidad determina la verificabilidad del sistema.

## Estructura

```
DADO QUE  [contexto o estado previo]
CUANDO    [acción o evento que dispara el comportamiento]
ENTONCES  [resultado observable y verificable]
```

## Reglas de redacción

1. **Un solo comportamiento por escenario.** Si aparece «y entonces» con dos resultados
   independientes, hay que dividir el escenario.
2. **Resultado observable.** El `ENTONCES` debe describir algo que una prueba pueda
   comprobar: un valor devuelto, un estado persistido, una excepción lanzada, un mensaje.
   Nunca un estado interno no observable ni una apreciación subjetiva.
3. **Sin detalles de implementación.** El escenario describe comportamiento, no la función
   que lo implementa.
4. **Datos concretos.** Cuando el comportamiento depende de valores, deben usarse valores
   reales. «DADO QUE el predio tiene un avalúo de 85.000.000 COP» es verificable;
   «DADO QUE el predio tiene un avalúo alto» no lo es.

## Cobertura mínima obligatoria

Todo requerimiento funcional debe tener al menos tres escenarios:

| Escenario | Propósito |
|---|---|
| Camino feliz | El comportamiento esperado con entradas válidas |
| Camino alterno | Una variación legítima de la regla de negocio |
| Camino de error | Entrada inválida, precondición no cumplida o excepción |

Un requerimiento con un solo escenario feliz se considera incompleto y debe devolverse.

## Ejemplo correcto

```
ESC-01 · Liquidación de predio urbano con construcción
DADO QUE existe un predio urbano con número predial válido y área construida registrada
CUANDO se solicita el cálculo del avalúo para la vigencia actual
ENTONCES el sistema devuelve el avalúo total como la suma del valor del terreno
         y el valor de la construcción, expresado en pesos colombianos

ESC-02 · Predio sin construcción registrada
DADO QUE existe un predio urbano sin área construida
CUANDO se solicita el cálculo del avalúo
ENTONCES el sistema devuelve únicamente el valor del terreno

ESC-03 · Número predial con formato inválido
DADO QUE se recibe un número predial de longitud distinta a 30 dígitos
CUANDO se solicita el cálculo del avalúo
ENTONCES el sistema rechaza la solicitud e informa el formato esperado
```

## Ejemplo incorrecto y su corrección

| Incorrecto | Problema | Corrección |
|---|---|---|
| ENTONCES el sistema funciona correctamente | No observable | Especificar qué devuelve |
| ENTONCES se llama al método calcular() | Implementación | Describir el resultado |
| ENTONCES el proceso es rápido | Subjetivo | Fijar un umbral medible |

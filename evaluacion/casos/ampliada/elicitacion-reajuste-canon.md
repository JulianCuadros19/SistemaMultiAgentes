---
id: caso-ampliada-02
titulo: Reajuste anual del canon de arrendamiento
cliente: Administradora de Arriendos del Valle (sintética)
proyecto: Reajuste anual de cánones
necesidad: Cada año debemos reajustar el canon de los contratos de arriendo según el IPC sin pasarnos de lo pactado; hoy lo hacemos en hojas de cálculo y cometemos errores.
version: 1.0
arquitecturas_esperadas: [ARQ-01]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la jefa de cartera de una administradora de inmuebles en arriendo. Conoces los contratos y
sus reglas, pero no tienes formación técnica.

## Lo que sabes

- Quien calcula el reajuste es el analista de cartera, cuando un contrato cumple su aniversario.
- Lo necesitan para notificar al arrendatario el nuevo canon con anticipación.
- Para reajustar, el contrato debe haber cumplido al menos doce meses desde su inicio o desde el
  último reajuste.
- Reglas del cálculo:
  - El porcentaje que se aplica es el menor entre el porcentaje pactado en el contrato y el IPC
    del año calendario anterior.
  - El nuevo canon es el canon actual incrementado en ese porcentaje.
  - El resultado se redondea a la centena de peso más cercana: 1.234.567 queda en 1.234.600.
  - Si el IPC del año anterior es cero o negativo, el canon no cambia.
- Datos que tiene el analista:
  - canon actual en pesos, obligatorio y mayor que cero;
  - porcentaje pactado, con hasta dos decimales, entre 0 y 100, obligatorio;
  - IPC del año anterior en porcentaje, con hasta dos decimales, obligatorio;
  - fecha de inicio o del último reajuste, obligatoria;
  - fecha del reajuste, obligatoria.
- Lo que debe entregar: el nuevo canon, el porcentaje aplicado y el valor del incremento.
- Ejemplos que usan para verificar:
  - canon de 1.200.000, pactado 10 % e IPC 5,20 %: se aplica 5,20 % y el nuevo canon es
    1.262.400, con un incremento de 62.400;
  - canon de 950.000, pactado 3 % e IPC 5,20 %: se aplica 3 % y el nuevo canon es 978.500.
- Caso de error: si no han pasado doce meses, se rechaza con «El contrato aún no cumple doce
  meses desde el último reajuste».
- Cómo se usa: lo usa el analista dentro del proceso de cartera. Ningún otro sistema lo consulta.
  Las reglas son pocas.
- Es de prioridad alta: hay plazos para notificar.

## Lo que no sabes

No sabes cómo se cobra el canon ni cómo se notifica al arrendatario: no son parte de este
cálculo. No conoces detalles técnicos del sistema.

# Manual de uso del sistema multiagente

Este manual es para quien opera el sistema sin tocar código: el analista, el arquitecto, el revisor y el
cliente. La instalación y el detalle técnico están en `README.md`.

## Qué hace

A partir de una conversación con el cliente, el sistema produce un módulo en Python con sus pruebas y su
documentación. Cuatro agentes hacen el trabajo y una persona aprueba en tres puntos de control:

| Etapa | Quién la hace | Lo que produce | Punto de control |
|---|---|---|---|
| Conversación y requerimientos | Agente elicitador | Historias de usuario y requerimientos formales | N6: la persona aprueba los requerimientos |
| Diseño | Agente arquitecto | Registro de decisión y especificación de diseño | N9: la persona aprueba el diseño |
| Código | Agente desarrollador | Código, pruebas y `USO.md` | |
| Validación | Agente tester | Reporte de validación con su veredicto | N17: la persona valida el módulo final |

Si una persona rechaza, el trabajo vuelve con sus observaciones al agente anterior.

## Cómo entrar

Hay dos formas de usarlo:

| Forma | Dirección | Cuándo |
|---|---|---|
| En su propia máquina | `http://127.0.0.1:8000/` | La entrega normal, también con datos reales de Realtix |
| En la máquina de demostración de Azure | `https://multiagente-demo.centralus.cloudapp.azure.com/` | Para mostrarlo, **solo con datos sintéticos** |

Para usarlo en su propia máquina:

```bash
docker compose up -d --build --wait
```

### La máquina de demostración

- **Encenderla:** en [portal.azure.com](https://portal.azure.com), abra la máquina `multiagente-demo` y haga
  clic en **Iniciar**. El enlace responde poco después, y el sistema arranca solo.
- **Entrar:** el navegador pide usuario y contraseña. El equipo los comparte aparte; no van en este
  documento.
- **Apagarla:** haga clic en **Detener** en el portal. Apagarla desde adentro no detiene el cobro. Además,
  se apaga sola a las 23:30, hora de Bogotá.
- **Costo:** sale de los créditos de estudiante, unos 0,23 USD por hora encendida. Cada sesión gasta además
  hasta 1 USD en modelos: la contraseña no se comparte con cualquiera.

## Operar una sesión

1. **Abrir la sesión.** En el panel, cree una sesión con el cliente, el proyecto y la necesidad.
2. **Conversar.** El cliente responde en su vista, `/conversacion/ID`, una pregunta a la vez, hasta
   confirmar un resumen de lo entendido.
3. **Aprobar los requerimientos (N6).** Revise las historias y los requerimientos. Si rechaza, escriba qué
   falta: vuelve al diálogo con el cliente.
4. **Aprobar el diseño (N9).** Revise el registro de decisión y la especificación. Si rechaza, el arquitecto
   la rehace con sus observaciones.
5. **Esperar el código y la validación.** El desarrollador y el tester trabajan solos. Si el tester rechaza
   una versión, el desarrollador la corrige, hasta completar tres versiones.
6. **Validar el módulo (N17).** Revise el reporte y el código. Puede correr pruebas propias en el entorno
   aislado. Entonces:
   - **apruébelo**, si está conforme;
   - **devuélvalo** al desarrollador o al arquitecto, con observaciones;
   - **pida una enmienda** de los requerimientos, si descubrió una regla nueva.
7. **Exportar.** La web entrega el módulo en un `.zip`, con el código, `USO.md` y los pasos para ponerlo en
   marcha.

## Cómo leer lo que muestra

- **Panel:** agrupa las sesiones según quién debe actuar: las que esperan al equipo, las que avanzan o
  esperan al cliente y las terminadas.
- **Línea del flujo:** muestra las cinco etapas de la sesión y los tres puntos de control.
- **Traza por nodo:** muestra el tiempo, los prompts, los tokens y el costo de cada paso.

## Situaciones comunes

| Lo que ve | Qué significa | Qué hacer |
|---|---|---|
| La sesión escaló a N17 y no se puede aprobar | El tester no aprobó ninguna de las tres versiones | Lea el reporte. Si un escenario es imposible, pida una enmienda; si no, devuélvala o ciérrela |
| Pausa por presupuesto | La sesión alcanzó su límite de costo | Amplíelo, dejando el motivo, o cierre la sesión |
| El agente no logró producir algo | Falló el modelo o su respuesta | Reintente o cierre la sesión: ninguna falla bloquea el flujo |

**Revise con atención en N6 y en N17.** La evaluación mostró que el elicitador puede dejar un escenario de
aceptación que contradice sus propias reglas, y que el desarrollador puede ajustarse a él. Compare las cifras
de los escenarios con las reglas, y lea en `USO.md` lo que el desarrollador declara como contradicción.

## Lo que no debe hacer

- No use datos reales de Realtix en la máquina de demostración.
- No comparta la contraseña sin necesidad.
- No deje la máquina encendida sin usarla.

---
estado: aceptada
fecha: 2026-11-04
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0003 (sin modelos de lenguaje locales), ADR-0007 (los embeddings siguen locales sin el factor del RF-37), ADR-0011 (acceso de la aplicación a Docker), ADR-0014 (acceso a la web) y ADR-0016 (factor del paso 14)
---

# ADR-0017 · Entrega en contenedores con Azure OpenAI

## Contexto y planteamiento del problema

El paso 14 del plan se llamaba «Empaquetado y modo local» y terminaba cuando «el sistema corre
completo sin credenciales de nube». Lo pedían textos aprobados:
- **RF-37:** entregar el sistema en contenedores, «capaz de operar de extremo a extremo sin
  dependencia de ningún proveedor de nube, utilizando modelos de lenguaje y de embeddings
  ejecutables localmente». Su criterio lo verificaba «en una máquina sin credenciales de nube».
- **RNF-06:** la capa de modelos debía permitir «operar íntegramente con modelos locales».
- **Vista de despliegue de la arquitectura:** un «servicio de inferencia local» con modelos
  open-weights y dos «modos de operación», remoto y local.
- **Restricciones de los requerimientos (§7):** operar «sin conexión a proveedores de nube».

El código nunca usó modelos de lenguaje locales. Desde el paso 3, los cinco nodos con modelo y el
cliente simulado llaman a los despliegues de Azure OpenAI. Al planear el paso 14, el equipo
decidió no usar modelos locales en la entrega.

Además, dos decisiones quedaron para este paso:
- **ADR-0011:** cómo accede a Docker la aplicación cuando corre en contenedor, para crear el
  entorno aislado.
- **ADR-0014:** el acceso remoto a la web y su autenticación.

Antes de este paso:
- la composición levantaba la base de datos, la descarga del modelo de embeddings y el servicio
  `embeddings`;
- la aplicación corría en el `.venv` del anfitrión;
- la imagen del entorno aislado se construía aparte y el corpus se ingería con un script.

## Factores de decisión

- La decisión del equipo sobre los modelos de lenguaje.
- RF-37 y RNF-07: entrega en contenedores, desplegable en Linux, Windows y macOS.
- RNF-03: el código generado se ejecuta aislado, sin red ni acceso al anfitrión.
- RNF-04: los embeddings se generan localmente y no se transmiten a terceros.
- El acuerdo de confidencialidad con Realtix: el corpus y los secretos no salen de la máquina.
- Decisión 7 de `CLAUDE.md`: los identificadores de modelo viven en la configuración.

## Opciones consideradas

Para el acceso a Docker desde la aplicación:
1. Montar el socket de Docker del anfitrión en el contenedor de la aplicación.
2. Docker dentro de Docker, en un contenedor privilegiado.
3. Dejar la aplicación fuera de los contenedores.

Para la web:
1. Solo en la máquina donde corre y sin autenticación, como hasta ahora.
2. Acceso remoto con TLS y autenticación.

## Resultado de la decisión

### Decisiones del equipo (2026-11-04)

1. **Azure OpenAI es el único proveedor de modelos de lenguaje.**
   - Ningún nodo usa modelos locales ni de pesos abiertos, y la composición no incluye un servidor
     de inferencia.
   - Los modelos son los despliegues del recurso de Azure OpenAI:
     - `gpt-5.4-mini` en N3 y N5;
     - `gpt-5` en N8;
     - `gpt-6.1-sol` en N10;
     - `gpt-6-luna` en N14.
2. **BGE-M3 sigue local.**
   - No es un modelo de lenguaje: convierte el corpus y las consultas en vectores para la
     recuperación de N2, N7 y N13.
   - Lo exige el RNF-04.
   - Llevarlo a Azure obligaría a reindexar el corpus, recalibrar el umbral de relevancia y
     reformular el RNF-04.
3. **Documentos corregidos.**
   - **Requerimientos 1.3:** el RF-37 y su criterio, el RNF-06 y la restricción de operar sin
     conexión a proveedores de nube.
   - **Arquitectura 1.5:**
     - §3.2: la justificación de los embeddings locales;
     - §5: los identificadores de modelo;
     - §8: la vista de despliegue, sin el servicio de inferencia local ni los modos de operación;
     - §9: los datos que procesa Azure, la web y el acceso a Docker;
     - Tablas 6 y 7;
     - §12: el criterio de aprobación.
   - **Plan de trabajo:** el paso 14 pasa a «Empaquetado en contenedores». Termina cuando, desde un
     clon limpio, la composición levanta el sistema completo y un módulo sale validado con los
     modelos de Azure OpenAI.
   - **`CLAUDE.md`:** el stack, la decisión 12 y el paso actual.
   - **`.env.example`:** sale `OLLAMA_BASE_URL`, que nada usaba.
4. **Acceso a Docker por el socket del anfitrión** (opción 1). Cierra lo que el ADR-0011 dejó para
   este paso.
   - La aplicación crea el entorno aislado con la CLI de Docker, que habla con el Docker del
     anfitrión por su socket.
   - El entorno aislado no cambia: es un contenedor hermano, efímero, sin red, de solo lectura y
     sin root, que recibe el código por la entrada estándar.
   - **Riesgo:** quien controle el contenedor de la aplicación controla el Docker del anfitrión.
     Lo acotan dos cosas: el código generado nunca corre en la aplicación, solo en el entorno
     aislado, y la web solo responde en la máquina.
   - **Opciones descartadas:**
     - Docker dentro de Docker exige un contenedor privilegiado, con más alcance sobre el
       anfitrión;
     - dejar la aplicación fuera de los contenedores no cumple el RF-37.
5. **La web, solo en la máquina donde corre y sin autenticación** (opción 1). Cierra lo que el
   ADR-0014 dejó para este paso.
   - En la composición, la web escucha en todas las interfaces del contenedor, pero se publica
     solo en `127.0.0.1` del anfitrión.
   - El acceso remoto exigiría TLS, autenticación del equipo y un enlace por sesión para el
     cliente. Queda como trabajo futuro.

### Consecuencias

- **Favorable:** el código de los nodos no cambia. La capa agnóstica ya permitía cambiar de modelo
  editando la configuración, y lo sigue permitiendo.
- **Favorable:** la vista de despliegue se simplifica: sin servidor de inferencia, sin GPU y sin
  descargar modelos de lenguaje.
- **Desfavorable:** el sistema no opera sin conexión con Azure OpenAI. Depende de su cuota, su
  disponibilidad, el retiro de versiones y su costo; es el riesgo nuevo de la Tabla 7.
- **Desfavorable:** los prompts se procesan en Azure, con la conversación, los fragmentos
  recuperados y los artefactos. Con datos reales de Realtix se prefieren los despliegues de zona
  de datos de EE. UU. sobre los globales.
- **Desfavorable:** el contenedor de la aplicación tiene acceso al Docker del anfitrión.

## Cambios para el documento de tesis

- **Requerimientos:** el RF-37 y su criterio, el RNF-06 y la restricción de operar sin conexión a
  proveedores de nube.
- **Stack:** Azure OpenAI es el único proveedor de modelos de lenguaje y BGE-M3 corre local.
- **Vista de despliegue:**
  - salen el servicio de inferencia local y los modos de operación;
  - la aplicación usa Azure OpenAI y el Docker del anfitrión;
  - la web responde solo en la máquina.
- **Tablas 6 y 7:** la fila de la composición y el riesgo de depender de un único proveedor.
- **Plan de trabajo:** el paso 14 es «Empaquetado en contenedores».
- **Arquitectura, §12:** el criterio de aprobación de la vista de despliegue.

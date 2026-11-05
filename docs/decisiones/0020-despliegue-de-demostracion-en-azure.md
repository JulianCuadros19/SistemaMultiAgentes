---
estado: aceptada
fecha: 2026-11-05
decisores: [Julián Andrés Cuadros Muñoz, Laura Catalina Riveros Flórez]
modifica: ADR-0017 (decisión 5, solo en la máquina de demostración)
---

# ADR-0020 · Despliegue de demostración en una máquina de Azure

## Contexto y planteamiento del problema

El ADR-0017 entregó el sistema en contenedores, con la web solo en la máquina donde corre, y dejó el
acceso remoto como trabajo futuro. La tesis lo presenta como un producto en local.

El equipo necesita un enlace público para compartir el sistema, pagado con los créditos de Azure for
Students y con la máquina apagada mientras no se use.

## Factores de decisión

- **Entorno aislado (RNF-03):** la aplicación lo crea con el Docker del anfitrión. Debe seguir sin red,
  de solo lectura y sin root.
- **Seguridad:** quien controla la aplicación controla ese Docker, y cada sesión gasta crédito. El enlace
  no puede quedar abierto.
- **Sin compras:** todo sale del crédito de estudiante.
- **Cuotas de la suscripción:** solo tiene familias de máquinas anteriores, con 4 vCPU por familia y 6
  por región.
- **Memoria:** el servicio de embeddings llega a unos 11 GB, así que hacen falta 16 GB.
- **Decisiones que no cambian:** BGE-M3 sigue dentro de la composición, y los modelos de lenguaje siguen
  siendo los de Azure OpenAI.

## Opciones consideradas

1. **Una máquina virtual con la composición,** y un proxy con TLS y contraseña.
2. **Azure Container Apps o Container Instances.** No ofrecen un Docker del anfitrión, y el entorno
   aislado habría que reescribirlo.
3. **Solo un túnel SSH,** sin enlace público. No cumple lo que se pide.

## Resultado de la decisión

Se elige la opción 1.

1. **Máquina:** `Standard_D4s_v4`, con 4 vCPU y 16 GiB, Ubuntu 24.04 y 30 GB de disco, en Central US. Fue el
   primer tamaño de 16 GB con cuota y disponibilidad entre las regiones permitidas.
2. **Composición:** `docker-compose.azure.yml` se suma a la base, que no cambia:
   - agrega el servicio `proxy`, con Caddy, que es lo único publicado hacia afuera (80 y 443);
   - baja el presupuesto de cada sesión a 1 USD.
3. **Acceso:**
   - TLS automático con Let's Encrypt, en `multiagente-demo.centralus.cloudapp.azure.com`;
   - una sola contraseña, con su hash en `.env.azure`, que no se versiona;
   - el puerto 22 solo desde la IP del equipo.
4. **Publicación:** `scripts/desplegar_azure.sh` instala Docker si falta, copia `HEAD` con `git archive`,
   sin credenciales de GitHub en la máquina, copia `.env` por `scp` y levanta la composición.
5. **Costo:** se apaga con «Detener» en el portal, porque apagarla desde adentro sigue cobrando. Tiene
   apagado automático a las 23:30 de Bogotá.

### Consecuencias

- **Favorable:** el enlace funciona sin cambiar el sistema ni la composición de la entrega.
- **Desfavorable:** una sola contraseña para todos y sin enlace por sesión para el cliente, como pedía el
  ADR-0017 para un acceso remoto completo.
- **Desfavorable:** la clave de Azure OpenAI queda también en esa máquina. Conviene rotarla al terminar.
- **Desfavorable:** no hay un tope global de gasto: cada sesión tiene el suyo, pero quien tenga la
  contraseña puede abrir varias.
- **Solo datos sintéticos.** La máquina está en la suscripción de los autores, no bajo control de Realtix
  (RNF-04), así que no reemplaza el despliegue local con datos reales.

### Confirmación

`pytest tests/unitarias/test_despliegue_azure.py` comprueba que solo el proxy publique puertos hacia
afuera, que no alcance el Docker del anfitrión, que exija contraseña y que sus secretos no se versionen ni
entren en la imagen.

## Verificación

En la máquina, el 2026-11-05:
- **Arranque desde cero:** `scripts/desplegar_azure.sh` instaló Docker 29.9.3 y levantó la composición en
  unos 5 min, con la construcción de las imágenes, la descarga del modelo y la indexación.
- **Memoria:** el servicio de embeddings usa 11,17 GiB; la máquina tiene 15,6 GiB.
- **Desde afuera:**
  - HTTPS con certificado de Let's Encrypt;
  - sin contraseña o con una incorrecta, 401; con la contraseña, 200;
  - HTTP redirige a HTTPS;
  - los puertos 5432, 8000 y 8081 no responden.
- **Un módulo real:** el caso 01, con el analista simulado de las corridas medidas, salió validado en N17
  en la v1, en 3,15 min y por 0,198 USD, más 0,040 del cliente simulado
  (`docs/mediciones/paso-15-despliegue-azure.jsonl`).
- **Reinicio:** tras `sudo reboot`, el enlace volvió en 32 s y conservó la sesión.

Sin verificar: el ciclo completo de detener e iniciar desde el portal, que lo hace el equipo.

## Cambios para el documento de tesis

- **3.8 (Vista de despliegue):** hoy dice que la nube no fue destino de despliegue. Debe decir que el
  producto se entrega en local y que, además, hay un despliegue de demostración en Azure.
- **Recomendaciones:** la autenticación remota queda parcialmente atendida; falta el enlace por sesión.

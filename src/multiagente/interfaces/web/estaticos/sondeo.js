// Mientras una sesión procesa, consulta su estado cada 2 s y recarga la página al terminar.
// Sin dependencias externas: la interfaz funciona sin conexión.
(function () {
  const caja = document.querySelector(".procesando[data-sesion]");
  if (!caja) {
    return;
  }
  const sesion = caja.dataset.sesion;
  const segundos = caja.querySelector("[data-segundos]");
  const nodo = caja.querySelector("[data-nodo]");

  async function consultar() {
    try {
      const respuesta = await fetch(`/sesiones/${encodeURIComponent(sesion)}/estado.json`, {
        cache: "no-store",
      });
      const estado = await respuesta.json();
      if (!estado.procesando) {
        window.location.reload();
        return;
      }
      if (segundos && estado.segundos !== null) {
        segundos.textContent = `${estado.segundos} s`;
      }
      if (nodo) {
        nodo.textContent = estado.nodo ? `· ${estado.nodo}` : "";
      }
    } catch (error) {
      // Un fallo de red momentáneo no detiene el sondeo.
    }
    window.setTimeout(consultar, 2000);
  }

  window.setTimeout(consultar, 2000);
})();

// Pestañas de la línea del flujo (ADR-0018): muestra una etapa a la vez y se maneja con el
// teclado (flechas, Inicio y Fin). Sin JavaScript, las etapas se ven en orden y cada pestaña es un
// ancla a su sección. Cambiar de etapa no se anima: es frecuente y se hace también con el teclado.
// El único movimiento es la llegada a una etapa nueva, una vez por avance de la sesión.
(function () {
  const lista = document.querySelector("[data-etapas]");
  if (!lista) {
    return;
  }
  const pestanas = Array.from(lista.querySelectorAll('[role="tab"]'));
  const paneles = pestanas.map((p) => document.getElementById(p.getAttribute("aria-controls")));
  if (paneles.some((panel) => !panel)) {
    return;
  }
  const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");

  // En pantallas angostas la línea se desplaza de lado: marca qué lado oculta etapas y deja la
  // etapa abierta a la vista.
  function medir() {
    const desborda = lista.scrollWidth > lista.clientWidth + 1;
    const fin = lista.scrollWidth - lista.clientWidth - 1;
    lista.classList.toggle("corta-inicio", desborda && lista.scrollLeft > 1);
    lista.classList.toggle("corta-final", desborda && lista.scrollLeft < fin);
  }
  lista.addEventListener("scroll", medir, { passive: true });
  if ("ResizeObserver" in window) {
    new ResizeObserver(medir).observe(lista);
  }

  function centrar(indice) {
    if (lista.scrollWidth <= lista.clientWidth) {
      return;
    }
    const etapa = pestanas[indice].parentElement;
    lista.scrollLeft = etapa.offsetLeft - (lista.clientWidth - etapa.offsetWidth) / 2;
    medir();
  }

  function mostrar(indice, opciones) {
    const { foco = false, ancla = true } = opciones || {};
    pestanas.forEach((pestana, i) => {
      const activa = i === indice;
      pestana.setAttribute("aria-selected", activa ? "true" : "false");
      pestana.tabIndex = activa ? 0 : -1;
      paneles[i].hidden = !activa;
    });
    centrar(indice);
    if (foco) {
      pestanas[indice].focus();
    }
    if (ancla) {
      history.replaceState(null, "", "#" + paneles[indice].id);
    }
  }

  // La llegada: si la etapa a la que llegó la sesión cambió desde la última visita a esta página,
  // se dibuja el tramo que la une. Sin almacenamiento disponible, la línea se muestra quieta.
  function marcarLlegada() {
    const frente =
      lista.querySelector(".flujo-etapa.actual") ||
      Array.from(lista.querySelectorAll(".flujo-etapa.hecha")).pop();
    if (!frente) {
      return;
    }
    const llave = "multiagente-etapa:" + window.location.pathname;
    const situacion = frente.classList.contains("actual") ? "actual" : "hecha";
    const ahora = frente.dataset.etapa + ":" + situacion;
    let antes = null;
    try {
      antes = window.sessionStorage.getItem(llave);
      window.sessionStorage.setItem(llave, ahora);
    } catch (error) {
      return;
    }
    if (antes && antes !== ahora && !sinMovimiento.matches) {
      frente.classList.add("llega");
    }
  }
  marcarLlegada();

  // Al entrar: la etapa del ancla de la dirección o, si no hay, la que marcó el servidor.
  const porAncla = paneles.findIndex((panel) => "#" + panel.id === window.location.hash);
  const marcada = pestanas.findIndex((p) => p.getAttribute("aria-selected") === "true");
  mostrar(porAncla >= 0 ? porAncla : Math.max(marcada, 0), { ancla: false });

  pestanas.forEach((pestana, i) => {
    pestana.addEventListener("click", (evento) => {
      evento.preventDefault();
      mostrar(i);
    });
    pestana.addEventListener("keydown", (evento) => {
      const destinos = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: pestanas.length - 1 };
      if (!(evento.key in destinos)) {
        return;
      }
      evento.preventDefault();
      mostrar((destinos[evento.key] + pestanas.length) % pestanas.length, { foco: true });
    });
  });

  // Enlaces dentro de una etapa que llevan a otra, como «Ver la validación y el código».
  document.addEventListener("click", (evento) => {
    const enlace = evento.target.closest('a[href^="#etapa-"]:not([role="tab"])');
    if (!enlace) {
      return;
    }
    const indice = paneles.findIndex((panel) => "#" + panel.id === enlace.getAttribute("href"));
    if (indice < 0) {
      return;
    }
    evento.preventDefault();
    mostrar(indice);
    lista.scrollIntoView({ block: "nearest", behavior: sinMovimiento.matches ? "auto" : "smooth" });
  });
})();

/**
 * OGKKE Core UI — Gestión de esquema de color (Sistema / Oscuro / Claro) y utilidades globales.
 */
(() => {
  const STORAGE_KEY = "color-scheme";
  const mediaDark = window.matchMedia("(prefers-color-scheme: dark)");

  function getMetaScheme() {
    return document.querySelector('meta[name="color-scheme"]');
  }

  function getStoredScheme() {
    try {
      const val = localStorage.getItem(STORAGE_KEY);
      return val === "light" || val === "dark" ? val : null;
    } catch {
      return null;
    }
  }

  function applyScheme(storedValue) {
    const meta = getMetaScheme();
    if (meta) {
      meta.content = storedValue ?? "light dark";
    }

    const isDark = storedValue ? storedValue === "dark" : mediaDark.matches;
    document.documentElement.dataset.bsTheme = isDark ? "dark" : "light";

    // Actualizar estado activo y accesibilidad en los controles del menú de usuario
    document.querySelectorAll("[data-theme-value]").forEach((btn) => {
      const target = btn.getAttribute("data-theme-value");
      const active = (storedValue ?? "system") === target;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    // Notificar a componentes dependientes del tema (ej. Chart.js en Fase 2)
    window.dispatchEvent(
      new CustomEvent("ogkke:themechange", {
        detail: { scheme: storedValue ?? "system", resolved: isDark ? "dark" : "light" },
      })
    );
  }

  function setSchemePreference(choice) {
    try {
      if (choice === "light" || choice === "dark") {
        localStorage.setItem(STORAGE_KEY, choice);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Si el almacenamiento está bloqueado, igualmente aplicamos el tema en memoria
    }
    applyScheme(choice === "light" || choice === "dark" ? choice : null);
  }

  // Sincronizar si cambia la preferencia del sistema operativo (sin borrar nunca el valor fijado en localStorage)
  mediaDark.addEventListener("change", () => {
    applyScheme(getStoredScheme());
  });

  // Sincronizar cambios realizados en otra pestaña del navegador
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY) {
      applyScheme(getStoredScheme());
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    applyScheme(getStoredScheme());

    document.addEventListener("click", (event) => {
      const themeBtn = event.target.closest("[data-theme-value]");
      if (themeBtn) {
        event.preventDefault();
        setSchemePreference(themeBtn.getAttribute("data-theme-value"));
      }
    });
  });
})();

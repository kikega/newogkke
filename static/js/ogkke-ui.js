/**
 * OGKKE Core UI — Gestión de esquema de color (Sistema / Oscuro / Claro),
 * fallbacks progresivos de <dialog> / Invoker Commands, validación accesible (:user-invalid)
 * y listas táctiles de selección múltiple con buscador en vivo.
 */
(() => {
  const STORAGE_KEY = "color-scheme";
  const mediaDark = window.matchMedia("(prefers-color-scheme: dark)");

  function normalizeText(str) {
    return (str || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  /* ==========================================================================
     1. GESTIÓN DE ESQUEMA DE COLOR (SISTEMA / CLARO / OSCURO)
     ========================================================================== */
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

    document.querySelectorAll("[data-theme-value]").forEach((btn) => {
      const target = btn.getAttribute("data-theme-value");
      const active = (storedValue ?? "system") === target;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

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
      // Si localStorage está bloqueado, mantenemos el tema en memoria
    }
    applyScheme(choice === "light" || choice === "dark" ? choice : null);
  }

  mediaDark.addEventListener("change", () => {
    applyScheme(getStoredScheme());
  });

  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY) {
      applyScheme(getStoredScheme());
    }
  });

  /* ==========================================================================
     2. DIÁLOGOS NATIVOS (<dialog>): INVOKER COMMANDS + LIGHT DISMISS FALLBACKS
     ========================================================================== */
  function initDialogEnhancements() {
    const hasNativeInvokers = "commandForElement" in HTMLButtonElement.prototype;

    document.addEventListener("click", (event) => {
      const themeBtn = event.target.closest("[data-theme-value]");
      if (themeBtn) {
        event.preventDefault();
        setSchemePreference(themeBtn.getAttribute("data-theme-value"));
        return;
      }

      const cmdBtn = event.target.closest("button[commandfor][command]");
      if (!cmdBtn) return;

      // Si el disparador vive dentro de un dropdown de navegación, cerrarlo limpiamente
      const parentDropdown = cmdBtn.closest(".dropdown");
      if (parentDropdown && cmdBtn.getAttribute("command") === "show-modal" && window.bootstrap?.Dropdown) {
        const toggleEl = parentDropdown.querySelector('[data-bs-toggle="dropdown"]');
        if (toggleEl) {
          window.bootstrap.Dropdown.getInstance(toggleEl)?.hide();
        }
      }

      // Fallback delegado solo si el navegador aún no soporta Invoker Commands nativamente
      if (!hasNativeInvokers) {
        const target = document.getElementById(cmdBtn.getAttribute("commandfor"));
        if (!(target instanceof HTMLDialogElement)) return;
        const command = cmdBtn.getAttribute("command");
        if (command === "show-modal" && !target.open) {
          target.showModal();
        } else if ((command === "close" || command === "request-close") && target.open) {
          if (typeof target.requestClose === "function" && command === "request-close") {
            target.requestClose();
          } else {
            target.close();
          }
        }
      }
    });

    // Fallback de light-dismiss (closedby="any") exigiendo pulsación y liberación fuera del rectángulo
    if (typeof HTMLDialogElement !== "undefined" && !("closedBy" in HTMLDialogElement.prototype)) {
      const isOutside = (e, dialog) => {
        const r = dialog.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      };

      document.querySelectorAll('dialog[closedby="any"]').forEach((dialog) => {
        let pressedOutside = false;
        dialog.addEventListener("pointerdown", (e) => {
          pressedOutside = e.target === dialog && isOutside(e, dialog);
        });
        dialog.addEventListener("pointerup", (e) => {
          if (pressedOutside && e.target === dialog && isOutside(e, dialog)) {
            dialog.close();
          }
          pressedOutside = false;
        });
      });
    }
  }

  /* ==========================================================================
     3. VALIDACIÓN POST-INTERACCIÓN (:user-invalid + sincronización ARIA)
     ========================================================================== */
  function initFormValidation() {
    const isTrackableField = (el) =>
      (el instanceof HTMLInputElement ||
        el instanceof HTMLTextAreaElement ||
        el instanceof HTMLSelectElement) &&
      el.type !== "search" &&
      el.type !== "hidden" &&
      el.type !== "checkbox" &&
      el.type !== "radio";

    if (typeof CSS !== "undefined" && CSS.supports("selector(:user-invalid)")) {
      const syncAria = (el) => {
        if (!isTrackableField(el)) return;
        el.setAttribute("aria-invalid", el.matches(":user-invalid") ? "true" : "false");
      };

      document.addEventListener("blur", (e) => syncAria(e.target), true);
      document.addEventListener("input", (e) => {
        if (isTrackableField(e.target) && e.target.hasAttribute("aria-invalid")) {
          syncAria(e.target);
        }
      });
      document.addEventListener("change", (e) => {
        if (isTrackableField(e.target) && e.target.hasAttribute("aria-invalid")) {
          syncAria(e.target);
        }
      });
      return;
    }

    // Fallback con WeakMap para navegadores sin soporte de selector(:user-invalid)
    const dirtyState = new WeakMap();
    const updateFallbackState = (input) => {
      const isValid = input.checkValidity();
      input.classList.toggle("user-invalid-fallback", !isValid);
      input.classList.toggle("user-valid-fallback", isValid);
      if (!isValid) {
        input.setAttribute("aria-invalid", "true");
      } else {
        input.removeAttribute("aria-invalid");
      }
    };

    const handleFallbackEvent = (event) => {
      const target = event.target;
      if (event.type === "reset" && target instanceof HTMLFormElement) {
        Array.from(target.elements).forEach((ctrl) => {
          dirtyState.delete(ctrl);
          ctrl.classList?.remove("user-invalid-fallback", "user-valid-fallback");
          ctrl.removeAttribute?.("aria-invalid");
        });
        return;
      }
      if (!isTrackableField(target) || !target.checkValidity) return;

      const state = dirtyState.get(target) || { hasInteracted: false, hasBlurred: false };
      if (event.type === "input" || event.type === "change") {
        state.hasInteracted = true;
        dirtyState.set(target, state);
        if (state.hasBlurred) updateFallbackState(target);
      } else if (event.type === "blur") {
        state.hasBlurred = true;
        dirtyState.set(target, state);
        if (state.hasInteracted) updateFallbackState(target);
      }
    };

    document.addEventListener("blur", handleFallbackEvent, true);
    document.addEventListener("input", handleFallbackEvent);
    document.addEventListener("change", handleFallbackEvent);
    document.addEventListener("reset", handleFallbackEvent, true);
  }

  /* ==========================================================================
     4. LISTAS TÁCTILES DE SELECCIÓN MÚLTIPLE CON BUSCADOR ([data-ogkke-checklist])
     ========================================================================== */
  function initSearchableChecklists(root = document) {
    root.querySelectorAll("[data-ogkke-checklist]").forEach((panel) => {
      if (panel.dataset.checklistReady === "true") return;
      panel.dataset.checklistReady = "true";

      const searchInput = panel.querySelector("[data-checklist-search]");
      const countBadge = panel.querySelector("[data-checklist-count]");
      const emptyNotice = panel.querySelector("[data-checklist-empty]");
      const onlySelectedBtn = panel.querySelector('[data-checklist-action="toggle-selected"]');
      const items = Array.from(panel.querySelectorAll(".ogkke-checklist-item")).map((itemEl) => {
        const checkbox = itemEl.querySelector('input[type="checkbox"]');
        return {
          itemEl,
          checkbox,
          text: normalizeText(itemEl.textContent),
        };
      });

      if (items.length === 0) return;

      let query = "";
      let onlySelected = false;

      function updateView() {
        let visibleCount = 0;
        let checkedCount = 0;

        items.forEach(({ itemEl, checkbox, text }) => {
          if (checkbox?.checked) checkedCount++;
          const matchesQuery = !query || text.includes(query);
          const matchesSelected = !onlySelected || Boolean(checkbox?.checked);
          const visible = matchesQuery && matchesSelected;
          itemEl.hidden = !visible;
          if (visible) visibleCount++;
        });

        if (countBadge) {
          countBadge.textContent = `${checkedCount} seleccionados de ${items.length}`;
        }
        if (emptyNotice) {
          emptyNotice.hidden = visibleCount > 0;
        }
        if (onlySelectedBtn) {
          onlySelectedBtn.setAttribute("aria-pressed", onlySelected ? "true" : "false");
          onlySelectedBtn.classList.toggle("active", onlySelected);
        }
      }

      searchInput?.addEventListener("input", () => {
        query = normalizeText(searchInput.value);
        updateView();
      });

      panel.addEventListener("change", (event) => {
        if (event.target.matches('input[type="checkbox"]')) {
          updateView();
        }
      });

      panel.addEventListener("click", (event) => {
        const actionBtn = event.target.closest("[data-checklist-action]");
        if (!actionBtn) return;
        const action = actionBtn.getAttribute("data-checklist-action");

        if (action === "select-visible") {
          items.forEach(({ itemEl, checkbox }) => {
            if (!itemEl.hidden && checkbox) checkbox.checked = true;
          });
          updateView();
        } else if (action === "clear-all") {
          items.forEach(({ checkbox }) => {
            if (checkbox) checkbox.checked = false;
          });
          if (onlySelected) onlySelected = false;
          updateView();
        } else if (action === "toggle-selected") {
          onlySelected = !onlySelected;
          updateView();
        }
      });

      updateView();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyScheme(getStoredScheme());
    initDialogEnhancements();
    initFormValidation();
    initSearchableChecklists();
  });
})();

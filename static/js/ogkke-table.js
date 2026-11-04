/**
 * OGKKE Responsive Data Tables — Búsqueda instantánea (insensible a tildes),
 * ordenación natural accesible (aria-sort) y paginación ligera sin jQuery.
 */
(() => {
  const collator = new Intl.Collator("es", { numeric: true, sensitivity: "base" });

  function normalizeText(str) {
    return (str || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function enhanceTable(table) {
    if (table.dataset.ogkkeTableReady === "true") return;
    const tbody = table.tBodies[0];
    const thead = table.tHead;
    if (!tbody || !thead) return;

    table.dataset.ogkkeTableReady = "true";

    // 1. Sincronizar etiquetas de columnas hacia variables CSS --label-N para vista apilada móvil
    const headerCells = Array.from(thead.rows[0]?.cells || []);
    headerCells.forEach((th, idx) => {
      const propName = `--label-${idx + 1}`;
      if (!table.style.getPropertyValue(propName)) {
        const cleanLabel = th.textContent.trim().replace(/"/g, "'");
        table.style.setProperty(propName, `"${cleanLabel}"`);
      }
    });

    const allRows = Array.from(tbody.rows).map((tr, originalIndex) => ({
      tr,
      originalIndex,
      searchText: normalizeText(tr.textContent),
    }));

    // Si no hay filas de datos reales, no inyectar controles innecesarios
    if (allRows.length === 0) return;

    let searchQuery = "";
    let pageSize = parseInt(table.dataset.pageSize || "25", 10);
    let currentPage = 1;
    let sortCol = null;
    let sortDir = "asc";

    // Orden inicial opcional: data-default-sort="1:desc"
    if (table.dataset.defaultSort) {
      const [colStr, dirStr] = table.dataset.defaultSort.split(":");
      const parsedCol = parseInt(colStr, 10);
      if (!Number.isNaN(parsedCol) && parsedCol >= 0 && parsedCol < headerCells.length) {
        sortCol = parsedCol;
        sortDir = dirStr === "desc" ? "desc" : "asc";
      }
    }

    const wrapper = table.closest(".table-wrapper") || table.parentElement;
    const container = document.createElement("div");
    container.className = "ogkke-table-shell";
    wrapper.parentNode.insertBefore(container, wrapper);

    // 2. Barra superior: buscador + selector de tamaño de página
    const toolbar = document.createElement("div");
    toolbar.className = "ogkke-table-toolbar";
    const searchId = `table-search-${Math.random().toString(36).slice(2, 8)}`;
    const lengthId = `table-length-${Math.random().toString(36).slice(2, 8)}`;

    toolbar.innerHTML = `
      <div class="ogkke-table-search">
        <label for="${searchId}" class="visually-hidden">Buscar en la tabla</label>
        <i class="bi bi-search ogkke-table-search-icon" aria-hidden="true"></i>
        <input
          type="search"
          id="${searchId}"
          class="form-control form-control-sm"
          placeholder="Buscar en la tabla..."
          enterkeyhint="search"
          autocomplete="off"
        >
      </div>
      <div class="ogkke-table-length">
        <label for="${lengthId}" class="small text-body-secondary">Mostrar</label>
        <select id="${lengthId}" class="form-select form-select-sm" style="inline-size: auto;">
          <option value="10" ${pageSize === 10 ? "selected" : ""}>10</option>
          <option value="25" ${pageSize === 25 ? "selected" : ""}>25</option>
          <option value="50" ${pageSize === 50 ? "selected" : ""}>50</option>
          <option value="0">Todos</option>
        </select>
      </div>
    `;

    // 3. Pie de tabla: contador accesible + paginación
    const footer = document.createElement("div");
    footer.className = "ogkke-table-footer";
    footer.innerHTML = `
      <div class="ogkke-table-info small text-body-secondary" aria-live="polite"></div>
      <nav aria-label="Paginación de tabla">
        <ul class="pagination pagination-sm mb-0 ogkke-table-pagination"></ul>
      </nav>
    `;

    // Fila de "Sin coincidencias" al filtrar
    const emptyRow = document.createElement("tr");
    emptyRow.className = "ogkke-table-empty-row";
    emptyRow.hidden = true;
    const emptyCell = document.createElement("td");
    emptyCell.colSpan = Math.max(1, headerCells.length);
    emptyCell.className = "text-center py-4 text-body-secondary";
    emptyCell.textContent = "No se encontraron registros coincidentes.";
    emptyRow.appendChild(emptyCell);
    tbody.appendChild(emptyRow);

    container.appendChild(toolbar);
    container.appendChild(wrapper);
    container.appendChild(footer);

    const searchInput = toolbar.querySelector("input");
    const lengthSelect = toolbar.querySelector("select");
    const infoBox = footer.querySelector(".ogkke-table-info");
    const paginationList = footer.querySelector(".ogkke-table-pagination");

    // 4. Cabeceras ordenables con soporte de teclado y aria-sort
    headerCells.forEach((th, colIdx) => {
      if (th.dataset.sortable === "false") return;

      const labelText = th.textContent.trim();
      th.textContent = "";
      th.setAttribute("aria-sort", "none");

      const sortBtn = document.createElement("button");
      sortBtn.type = "button";
      sortBtn.className = "ogkke-sort-btn";
      sortBtn.innerHTML = `
        <span>${labelText}</span>
        <i class="bi bi-arrow-down-up ogkke-sort-icon" aria-hidden="true"></i>
      `;

      sortBtn.addEventListener("click", () => {
        if (sortCol === colIdx) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortCol = colIdx;
          sortDir = "asc";
        }
        currentPage = 1;
        render();
      });

      th.appendChild(sortBtn);
    });

    function getCellSortValue(tr, colIdx) {
      const cell = tr.cells[colIdx];
      if (!cell) return "";
      if (cell.dataset.order !== undefined) return cell.dataset.order;
      // Si la celda solo tiene un icono (ej. check de Activo/Internacional), ordenar por presencia
      const text = cell.textContent.trim();
      if (!text && cell.querySelector("i, svg")) return "1";
      return text;
    }

    function updateSortHeaders() {
      headerCells.forEach((th, idx) => {
        const icon = th.querySelector(".ogkke-sort-icon");
        if (!icon) return;
        if (idx === sortCol) {
          th.setAttribute("aria-sort", sortDir === "asc" ? "ascending" : "descending");
          icon.className = `bi ${sortDir === "asc" ? "bi-sort-down-alt" : "bi-sort-down"} ogkke-sort-icon is-active`;
        } else {
          th.setAttribute("aria-sort", "none");
          icon.className = "bi bi-arrow-down-up ogkke-sort-icon";
        }
      });
    }

    function renderPagination(totalPages) {
      paginationList.innerHTML = "";
      if (totalPages <= 1) return;

      const addPageItem = (label, targetPage, disabled = false, active = false, ariaLabel = "") => {
        const li = document.createElement("li");
        li.className = `page-item ${disabled ? "disabled" : ""} ${active ? "active" : ""}`;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "page-link";
        btn.textContent = label;
        if (ariaLabel) btn.setAttribute("aria-label", ariaLabel);
        if (active) btn.setAttribute("aria-current", "page");
        if (!disabled && !active) {
          btn.addEventListener("click", () => {
            currentPage = targetPage;
            render();
          });
        }
        li.appendChild(btn);
        paginationList.appendChild(li);
      };

      addPageItem("‹", currentPage - 1, currentPage === 1, false, "Página anterior");

      const pages = new Set([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
      const validPages = Array.from(pages)
        .filter((p) => p >= 1 && p <= totalPages)
        .sort((a, b) => a - b);

      let prev = 0;
      validPages.forEach((p) => {
        if (p - prev > 1) {
          addPageItem("…", p, true, false);
        }
        addPageItem(String(p), p, false, p === currentPage);
        prev = p;
      });

      addPageItem("›", currentPage + 1, currentPage === totalPages, false, "Página siguiente");
    }

    function render() {
      const filtered = searchQuery
        ? allRows.filter((item) => item.searchText.includes(searchQuery))
        : allRows.slice();

      if (sortCol !== null) {
        const factor = sortDir === "asc" ? 1 : -1;
        filtered.sort((a, b) => {
          const valA = getCellSortValue(a.tr, sortCol);
          const valB = getCellSortValue(b.tr, sortCol);
          const cmp = collator.compare(valA, valB);
          return cmp !== 0 ? cmp * factor : a.originalIndex - b.originalIndex;
        });
      }

      updateSortHeaders();

      const totalFiltered = filtered.length;
      const effectiveSize = pageSize > 0 ? pageSize : Math.max(1, totalFiltered);
      const totalPages = Math.max(1, Math.ceil(totalFiltered / effectiveSize));
      if (currentPage > totalPages) currentPage = totalPages;

      const startIdx = (currentPage - 1) * effectiveSize;
      const endIdx = Math.min(startIdx + effectiveSize, totalFiltered);
      const visibleItems = new Set(filtered.slice(startIdx, endIdx).map((i) => i.tr));

      // Reordenar filas visibles en el DOM respetando el orden actual
      filtered.forEach((item) => {
        const show = visibleItems.has(item.tr);
        item.tr.hidden = !show;
        if (show) {
          tbody.insertBefore(item.tr, emptyRow);
        }
      });

      emptyRow.hidden = totalFiltered > 0;

      const suffix = searchQuery ? ` (filtrado de ${allRows.length} totales)` : "";
      if (totalFiltered === 0) {
        infoBox.textContent = `0 registros${suffix}`;
      } else {
        infoBox.textContent = `Mostrando ${startIdx + 1}–${endIdx} de ${totalFiltered} registros${suffix}`;
      }

      renderPagination(totalPages);
    }

    let debounceTimer = null;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchQuery = normalizeText(searchInput.value);
        currentPage = 1;
        render();
      }, 100);
    });

    lengthSelect.addEventListener("change", () => {
      pageSize = parseInt(lengthSelect.value, 10);
      currentPage = 1;
      render();
    });

    render();
  }

  function initAllTables(root = document) {
    root.querySelectorAll("table[data-ogkke-table]").forEach(enhanceTable);
  }

  document.addEventListener("DOMContentLoaded", () => initAllTables());
  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail && event.detail.target) {
      initAllTables(event.detail.target);
    }
  });
})();

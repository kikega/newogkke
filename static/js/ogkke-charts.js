/**
 * OGKKE Charts — Envoltorio reactivo al tema (claro/oscuro) sobre Chart.js
 * alineado con los tokens visuales de OGKKE.
 */
(() => {
  const activeCharts = new Map();

  function readThemeTokens() {
    const styles = getComputedStyle(document.documentElement);
    const accent = styles.getPropertyValue("--brand-accent").trim() || "#f0b429";
    const textMain = styles.getPropertyValue("--text-main").trim() || "#f1f3f5";
    const textMuted = styles.getPropertyValue("--text-secondary-ink").trim() || "#9ca3af";
    const borderSubtle = styles.getPropertyValue("--border-subtle").trim() || "rgba(255,255,255,0.1)";
    const isDark = document.documentElement.dataset.bsTheme === "dark";

    return {
      accent,
      accentFill: isDark ? "rgba(240, 180, 41, 0.32)" : "rgba(158, 116, 8, 0.24)",
      accentHighlightFill: isDark ? "rgba(240, 180, 41, 0.72)" : "rgba(158, 116, 8, 0.68)",
      textMain,
      textMuted,
      gridColor: borderSubtle,
    };
  }

  function buildColorsForDataset(count, highlightIndex, tokens) {
    if (highlightIndex === null || highlightIndex === undefined) {
      return {
        backgroundColor: tokens.accentFill,
        borderColor: tokens.accent,
      };
    }
    const bg = [];
    const border = [];
    for (let i = 0; i < count; i++) {
      bg.push(i === highlightIndex ? tokens.accentHighlightFill : tokens.accentFill);
      border.push(tokens.accent);
    }
    return { backgroundColor: bg, borderColor: border };
  }

  function renderBarChart(canvasId, { labels, values, title = "", horizontal = false, highlightIndex = null, label = "Registros" }) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return null;

    if (activeCharts.has(canvasId)) {
      activeCharts.get(canvasId).chart.destroy();
      activeCharts.delete(canvasId);
    }

    const tokens = readThemeTokens();
    const palette = buildColorsForDataset(values.length, highlightIndex, tokens);
    const valueAxis = horizontal ? "x" : "y";
    const categoryAxis = horizontal ? "y" : "x";

    const chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label,
            data: values,
            backgroundColor: palette.backgroundColor,
            borderColor: palette.borderColor,
            borderWidth: 2,
            borderRadius: 8,
            maxBarThickness: 48,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: canvas.parentElement?.classList.contains("chart-container") ? false : true,
        indexAxis: horizontal ? "y" : "x",
        plugins: {
          legend: { display: false },
          title: {
            display: Boolean(title),
            text: title,
            color: tokens.textMain,
            font: { size: 16, weight: "600" },
            padding: { bottom: 14 },
          },
        },
        scales: {
          [valueAxis]: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
              precision: 0,
              color: tokens.textMuted,
            },
            grid: { color: tokens.gridColor },
          },
          [categoryAxis]: {
            ticks: { color: tokens.textMain },
            grid: { display: false },
          },
        },
      },
    });

    activeCharts.set(canvasId, { chart, highlightIndex, valuesCount: values.length, horizontal });
    return chart;
  }

  function setHighlightIndex(canvasId, newHighlightIndex) {
    const entry = activeCharts.get(canvasId);
    if (!entry) return;
    entry.highlightIndex = newHighlightIndex;
    const tokens = readThemeTokens();
    const palette = buildColorsForDataset(entry.valuesCount, newHighlightIndex, tokens);
    entry.chart.data.datasets[0].backgroundColor = palette.backgroundColor;
    entry.chart.data.datasets[0].borderColor = palette.borderColor;
    entry.chart.update();
  }

  // Re-tematizar automáticamente los gráficos activos al cambiar entre modo Claro y Oscuro
  window.addEventListener("ogkke:themechange", () => {
    const tokens = readThemeTokens();
    activeCharts.forEach((entry) => {
      const { chart, highlightIndex, valuesCount, horizontal } = entry;
      const palette = buildColorsForDataset(valuesCount, highlightIndex, tokens);
      const valueAxis = horizontal ? "x" : "y";
      const categoryAxis = horizontal ? "y" : "x";

      chart.data.datasets[0].backgroundColor = palette.backgroundColor;
      chart.data.datasets[0].borderColor = palette.borderColor;
      if (chart.options.plugins.title) {
        chart.options.plugins.title.color = tokens.textMain;
      }
      chart.options.scales[valueAxis].ticks.color = tokens.textMuted;
      chart.options.scales[valueAxis].grid.color = tokens.gridColor;
      chart.options.scales[categoryAxis].ticks.color = tokens.textMain;
      chart.update("none");
    });
  });

  window.OGKKECharts = { renderBarChart, setHighlightIndex };
})();

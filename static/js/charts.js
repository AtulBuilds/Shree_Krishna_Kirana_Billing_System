// Shared Chart.js styling so every chart matches the theme (light or dark).
// Pages call KCharts.bar(...), KCharts.line(...) or KCharts.doughnut(...).
(function () {
  // ---- Offline fallback: Chart.js comes from the internet. Without it, draw simple HTML bars instead.
  if (!window.Chart) {
    const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const money = (v) => "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
    const box = (id) => { const c = document.getElementById(id); c.style.display = "none"; return c.parentElement; };
    const cols = (id, labels, values) => {
      const max = Math.max.apply(null, values.concat([1])), step = Math.ceil(labels.length / 8), few = labels.length <= 10;
      box(id).innerHTML = '<div class="fb-cols">' + labels.map((l, i) =>
        '<div class="fb-col" title="' + esc(l) + ': ' + money(values[i]) + '">' +
        '<span class="fb-val">' + (few ? money(values[i]) : "") + '</span>' +
        '<i style="height:' + Math.max(values[i] / max * 100, values[i] ? 2 : 0) + '%"></i>' +
        '<span class="fb-lab">' + (i % step === 0 ? esc(l.slice(-5)) : "") + '</span></div>').join("") + "</div>";
    };
    window.KCharts = {
      bar: cols, line: cols,
      doughnut(id, labels, values) {
        const total = values.reduce((a, b) => a + b, 0) || 1;
        box(id).innerHTML = '<div class="fb-list">' + labels.map((l, i) =>
          '<div><div class="row-between"><span>' + esc(l) + '</span><b>' + money(values[i]) + ' · ' + Math.round(values[i] / total * 100) + '%</b></div>' +
          '<div class="bar"><i style="width:' + (values[i] / total * 100) + '%"></i></div></div>').join("") + "</div>";
      },
    };
    return;
  }

  const root = getComputedStyle(document.documentElement);
  const css = (name) => root.getPropertyValue(name).trim();
  const brand = css("--brand") || "#059669";
  const muted = css("--muted") || "#64748b";
  const grid = css("--border") || "#e6e9ee";
  const surface = css("--surface") || "#fff";
  const text = css("--text") || "#0f172a";

  Chart.defaults.font.family = css("--font") || "system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = muted;
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.plugins.tooltip.backgroundColor = surface;
  Chart.defaults.plugins.tooltip.titleColor = text;
  Chart.defaults.plugins.tooltip.bodyColor = text;
  Chart.defaults.plugins.tooltip.borderColor = grid;
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.displayColors = false;

  const rupee = (v) => "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });
  const scales = () => ({
    x: { grid: { display: false }, border: { display: false } },
    y: {
      beginAtZero: true, border: { display: false }, grid: { color: grid },
      ticks: { callback: (v) => "₹" + Number(v).toLocaleString("en-IN"), maxTicksLimit: 6 },
    },
  });
  const tooltip = { callbacks: { label: (c) => " " + rupee(c.parsed.y) } };

  // categorical palette (readable in light and dark)
  const palette = ["#059669", "#0ea5e9", "#f59e0b", "#8b5cf6", "#f43f5e", "#14b8a6", "#64748b", "#eab308"];

  window.KCharts = {
    bar(id, labels, values) {
      new Chart(document.getElementById(id), {
        type: "bar",
        data: { labels, datasets: [{ data: values, backgroundColor: brand, hoverBackgroundColor: css("--primary-hover") || brand, borderRadius: 8, borderSkipped: false, maxBarThickness: 38 }] },
        options: { scales: scales(), plugins: { tooltip } },
      });
    },
    line(id, labels, values) {
      const el = document.getElementById(id);
      const ctx = el.getContext("2d");
      const g = ctx.createLinearGradient(0, 0, 0, el.parentElement.clientHeight || 260);
      g.addColorStop(0, "rgba(16,185,129,.28)");
      g.addColorStop(1, "rgba(16,185,129,0)");
      new Chart(el, {
        type: "line",
        data: { labels, datasets: [{ data: values, borderColor: brand, backgroundColor: g, fill: true, tension: .35, borderWidth: 2.5, pointRadius: values.length > 20 ? 0 : 3, pointHoverRadius: 5, pointBackgroundColor: surface, pointBorderColor: brand, pointBorderWidth: 2 }] },
        options: { scales: scales(), plugins: { tooltip }, interaction: { intersect: false, mode: "index" } },
      });
    },
    doughnut(id, labels, values) {
      new Chart(document.getElementById(id), {
        type: "doughnut",
        data: { labels, datasets: [{ data: values, backgroundColor: palette, borderColor: surface, borderWidth: 3, hoverOffset: 6 }] },
        options: {
          cutout: "66%",
          plugins: {
            legend: { display: true, position: "bottom", labels: { usePointStyle: true, pointStyle: "circle", boxWidth: 8, padding: 14 } },
            tooltip: { callbacks: { label: (c) => " " + c.label + ": " + rupee(c.parsed) } },
          },
        },
      });
    },
  };
})();

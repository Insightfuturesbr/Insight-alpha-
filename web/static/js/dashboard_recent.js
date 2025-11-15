// static/js/dashboard_recent.js
(function () {
  const app = document.getElementById("app");
  if (!app || app.dataset.page !== "dashboard") return;

  const grid = document.getElementById("recent-strategies");
  const empty = document.getElementById("recent-empty");

  function fmtDate(d) {
    if (!d) return "";
    try { return new Date(d).toLocaleDateString(); } catch { return d; }
  }

  // Tiny sparkline renderer (inline SVG)
  function renderSparkline(el, series, opts={}) {
    if (!el || !series || !series.length) return;
    const width = opts.width || el.clientWidth || 260;
    const height = opts.height || el.clientHeight || 80;
    const padding = 6;
    const w = Math.max(40, width);
    const h = Math.max(30, height);
    const min = Math.min(...series);
    const max = Math.max(...series);
    const span = Math.max(1e-9, max - min);
    const stepX = (w - padding*2) / Math.max(1, (series.length - 1));
    const pts = series.map((v, i) => {
      const x = padding + i * stepX;
      const y = padding + (1 - (v - min)/span) * (h - padding*2);
      return [x, y];
    });
    const path = pts.map((p,i)=> (i? 'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
    const last = pts[pts.length-1];
    el.innerHTML = `
      <svg viewBox="0 0 ${w} ${h}" width="100%" height="100%" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sg-dash" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="#4fd1c5" stop-opacity="0.6"/>
            <stop offset="100%" stop-color="#4fd1c5" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="${path}"
              fill="none" stroke="#4fd1c5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="${pts.map(p=>p.join(',')).join(' ')} ${w-padding},${h-padding} ${padding},${h-padding}"
                  fill="url(#sg-dash)" opacity="0.25"/>
        <circle cx="${last[0]}" cy="${last[1]}" r="2.8" fill="#34d399"/>
      </svg>`;
  }

  function randomWalk(n=30, start=100, vol=2) {
    const out = []; let v = start;
    for (let i=0;i<n;i++) { v += (Math.random()-0.5)*vol; out.push(Math.max(1, v)); }
    return out;
  }

  const demoItems = [
    { id: 'rd1', title: 'SMA Crossover WIN', ativo: 'WIN', status: 'ativo' },
    { id: 'rd2', title: 'Breakout Diário WDO', ativo: 'WDO', status: 'teste' },
    { id: 'rd3', title: 'Reversão Intraday', ativo: 'WIN', status: 'pausado' },
    { id: 'rd4', title: 'Volatility Squeeze', ativo: 'WDO', status: 'ativo' },
    { id: 'rd5', title: 'Momentum Rider', ativo: 'WIN', status: 'ativo' },
    { id: 'rd6', title: 'Mean Reversion Lite', ativo: 'WDO', status: 'teste' },
  ].map((it, idx) => ({
    ...it,
    created_at: new Date(Date.now() - (idx*43200000)).toISOString(),
    spark: randomWalk(30, 100 + idx*3, 2.5)
  }));

function cardTemplate(s) {
  const title = s.title || s.nome || 'Estratégia';
  const ativo = s.ativo || '—';
  const status = s.status || 'draft';
  const created = s.created_at ? fmtDate(s.created_at) : '';
  const chartId = `dspark_${s.id || Math.random().toString(36).slice(2)}`;

  const controlsHTML = `
    <div class="if-cta-wrap">
      <button type="button" class="if-btn" data-action="ativar" aria-label="Ativar automação">
        <svg class="if-ic" viewBox="0 0 24 24" fill="none">
          <path d="M8 5v14l11-7L8 5z" stroke="currentColor" stroke-width="1.5" fill="currentColor"/>
        </svg>
        <span>Ativar</span>
      </button>
      <button type="button" class="if-btn if-btn--pause" data-action="pausar" aria-label="Pausar automação">
        <svg class="if-ic" viewBox="0 0 24 24" fill="none">
          <path d="M8 5h3v14H8zM13 5h3v14h-3z" fill="currentColor"/>
        </svg>
        <span>Pausar</span>
      </button>
      <button type="button" class="if-btn if-btn--rev" data-action="reverse" aria-label="Ativar Reverse Mode">
        <svg class="if-ic" viewBox="0 0 24 24" fill="none">
          <path d="M7 7h9.5l-2.5-2.5M17 17H7.5L10 19.5"
                stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>Reverse Mode</span><span class="if-badge-mini">beta</span>
      </button>
    </div>`;

  return `
    <div class="if-card">
      <div class="flex items-center justify-between mb-1">
        <h3 title="${title}">${title}</h3>
        <span class="if-badge">${status}</span>
      </div>
      <div class="if-meta">Ativo: <strong>${ativo}</strong>${created ? ` · ${created}` : ''}</div>
      <div id="${chartId}" class="if-chart"></div>

      <!-- barra de links -->
      <div class="if-actions">
        <a class="btn" href="${(s.actions && (s.actions.analise_pre)) || '#'}">Resultados</a>
        <a class="btn" href="${(s.actions && (s.actions.analise_padronizada || s.actions.analise_pad)) || '#'}">Fluxo Financeiro</a>
        <a class="btn" href="${(s.actions && s.actions.drawdown) || '#'}">Drawdowns e Lucros</a>
        <a class="btn" href="${(s.actions && s.actions.backtest) || '#'}">Backtest</a>
        <a class="btn" href="${(s.actions && s.actions.insights) || '#'}">Insights</a>
      </div>

      <!-- CTAs principais -->
      ${controlsHTML}
    </div>`;
}

  async function loadRecent() {
    try {
      const resp = await fetch("/api/strategies/recent?limit=6", { cache: 'no-store' });
      if (!resp.ok) throw new Error("Falha ao carregar estratégias");
      const data = await resp.json();
      let items = (data.items || []).map((s, idx) => ({
        ...s,
        id: s.id || `d${idx}`,
        spark: randomWalk(30, 98 + (idx%5)*2, 2.3)
      }));

      if (!items.length) {
        empty.classList.add("hidden");
        items = demoItems;
      } else {
        empty.classList.add("hidden");
      }

      grid.innerHTML = items.map(cardTemplate).join("");
      // Render sparklines
      items.forEach(s => {
        const el = document.getElementById(`dspark_${s.id}`);
        const series = (s.spark && s.spark.length) ? s.spark : randomWalk(30, 100, 2.5);
        if (el) renderSparkline(el, series);
      });
    } catch (err) {
      console.error(err);
      // graceful fallback
      empty.classList.add("hidden");
      grid.innerHTML = demoItems.map(cardTemplate).join("");
      demoItems.forEach(s => {
        const el = document.getElementById(`dspark_${s.id}`);
        if (el) renderSparkline(el, s.spark);
      });
    }
  }

  loadRecent();
})();

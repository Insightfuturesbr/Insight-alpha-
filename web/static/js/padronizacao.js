// /static/js/padronizacao.js
(function () {
  // ---------- helpers ----------
  const $ = (sel) => document.querySelector(sel);
  const setText = (sel, v) => { const el = $(sel); if (el) el.textContent = v; };
  const money = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return "—";
    if (typeof window.formatarParaReais === "function") return window.formatarParaReais(n);
    return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  function setPercent(selText, selBar, value, baseAbs) {
    const pct = baseAbs > 0 ? Math.max(0, value) / baseAbs * 100 : 0;
    if ($(selText)) $(selText).textContent = `${pct.toFixed(0)}%`;
    if ($(selBar))  $(selBar).style.width = `${Math.min(100, pct)}%`;
  }

  function drawPlotly(targetId, payload, fallbackLayout) {
    if (!window.Plotly || !payload) return;
    const el = document.getElementById(targetId);
    if (!el) return;
    const layout = payload.layout || fallbackLayout || { margin: { t: 20, r: 10, b: 30, l: 40 } };
    window.Plotly.newPlot(el, payload.data, layout, { displayModeBar: false });
  }

  // ---------- main ----------
  async function carregarPadronizacao() {
    try {
      // 1) Números da padronização
      const p = await fetch(`/api/padronizacao?t=${Date.now()}`, { cache: "no-store" });
      if (!p.ok) throw new Error(`HTTP ${p.status}`);
      const pj = await p.json();
      const pad = pj.padronizacao || {};

      const bruto   = Number(pad.resultado_bruto_padronizado)   || 0;
      const liquido = Number(pad.resultado_liquido_padronizado) || 0;
      const taxas   = Number(pad.taxas_totais_padronizadas ?? (bruto - liquido));
      const baseAbs = Math.abs(bruto);

      // textos
      setText("#pad_resultado_bruto",   money(bruto));
      setText("#pad_resultado_liquido", money(liquido));
      setText("#pad_taxas_totais",      money(taxas));

      // barras %
      setPercent("#pad_percentual_liquido", "#barraLiquido", liquido, baseAbs);
      setPercent("#pad_percentual_taxas",   "#barraTaxas",   taxas,   baseAbs);

      // 2) Gráficos via API de gráficos
      const g = await fetch(`/api/graficos/padronizacao?t=${Date.now()}`, { cache: "no-store" });
      const gj = await g.json();
      const op  = gj.barras_operacoes ? JSON.parse(gj.barras_operacoes) : null;
      const pv  = gj.pizza_valores     ? JSON.parse(gj.pizza_valores)     : null;
      const pqt = gj.pizza_qtde        ? JSON.parse(gj.pizza_qtde)        : null;
      drawPlotly("grafico-operacoes",    op,  { margin: { t: 20, r: 10, b: 30, l: 40 } });
      drawPlotly("grafico-pizza-valores", pv,  { margin: { t: 20, b: 20 } });
      drawPlotly("grafico-pizza-qtde",    pqt, { margin: { t: 20, b: 20 } });

      console.log("✅ padronizacao.js atualizado");
    } catch (e) {
      console.error("[padronizacao] falha:", e);
      // coloca traço para não ficar “carregando”
      ["#pad_resultado_bruto","#pad_resultado_liquido","#pad_taxas_totais",
       "#pad_percentual_liquido","#pad_percentual_taxas"].forEach(sel => setText(sel, "—"));
    }
  }

  // expõe para debug manual
  window.carregarPadronizacao = carregarPadronizacao;

  // dispara quando o app estiver pronto (SPA) ou na primeira carga
  document.addEventListener("app:ready", carregarPadronizacao, { once: true });
  document.addEventListener("DOMContentLoaded", () => {
    // se sua app não emitir 'app:ready', ainda assim atualiza
    carregarPadronizacao();
  });

  // se a SPA re-renderizar a seção depois, tente novamente quando a página voltar
  window.addEventListener("pageshow", () => {
    // só recarrega se ainda estiver vazio
    const el = document.querySelector("#pad_resultado_bruto");
    if (el && (el.textContent === "" || el.textContent === "Carregando...")) carregarPadronizacao();
  });
})();

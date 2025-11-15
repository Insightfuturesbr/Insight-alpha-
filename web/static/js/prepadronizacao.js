function carregarPrePadronizacao() {
  // Helpers: simple spinner overlay inside target elements
  const spinnerHTML = (
    '<div class="w-full h-full flex items-center justify-center text-slate-300">\n' +
    '  <div class="flex items-center gap-3">\n' +
    '    <div class="animate-spin rounded-full h-6 w-6 border-2 border-slate-400 border-t-transparent"></div>\n' +
    '    <span class="text-sm">Carregando…</span>\n' +
    '  </div>\n' +
    '</div>'
  );

  const elOps = document.getElementById("grafico-pre-operacoes");
  const elPie = document.getElementById("grafico-pre-composicao");
  if (elOps) elOps.innerHTML = spinnerHTML;
  if (elPie) elPie.innerHTML = spinnerHTML;
  const periodoEl = document.getElementById("periodo");
  if (periodoEl && (!periodoEl.textContent || periodoEl.textContent === '—')) periodoEl.textContent = 'Carregando…';
  // Carrega variáveis e estatísticas pré-padronização
  fetch("/api/prepadronizacao?t=" + Date.now(), { cache: "no-store" })
    .then(res => res.json())
    .then(dados => {
      const pre = dados.variaveis_pre || {};
      const stats = dados.estatisticas_positivas_negativas || {};

      // 🗓️ Período
      if (periodoEl) periodoEl.innerText = pre.periodo || "—";

      // 📊 Gráfico Operações (Pré) — barras horizontais: Positivas/Negativas/Neutras
      try {
        if (elOps && window.Plotly) {
          const valores = [stats.qtd_positivas || 0, stats.qtd_negativas || 0, stats.qtd_neutras || 0];
          const labels = ['Positivas', 'Negativas', 'Neutras'];
          const cores = ['rgb(132, 255, 160)', 'rgb(255, 99, 99)', '#B0BEC5'];
          const percentuais = (function(){
            const total = valores.reduce((a,b)=>a+b,0) || 1;
            return valores.map(v => `${((v/total)*100).toFixed(1)}%`);
          })();
          const trace = {
            type: 'bar',
            x: valores,
            y: labels,
            orientation: 'h',
            marker: { color: cores },
            text: percentuais,
            textposition: 'inside',
            insidetextanchor: 'middle',
            textfont: { color: 'black', size: 14 },
          };
          const layout = {
            margin: { t: 20, b: 20, l: 80, r: 20 },
            height: 260,
            xaxis: { showgrid: false, visible: false },
            yaxis: { showgrid: true, visible: true },
            plot_bgcolor: 'rgba(0,0,0,0.15)',
            paper_bgcolor: 'rgba(0,0,0,0.15)',
            font: { color: 'white' },
          };
          window.Plotly.newPlot(elOps, [trace], layout, { displayModeBar: false });
        }
      } catch (e) { console.warn('[pre] falha grafico operacoes', e); }

      // 🥧 Composição (Pré) — pizza de valores: Líquido / Taxas / Restante
      try {
        if (elPie && window.Plotly) {
          const liquido = Number(pre.resultado_liquido_acumulado) || 0;
          const taxas   = Number(pre.taxas) || 0;
          const restante = Math.max(0, Number(pre.resultado_bruto || 0) - (liquido + taxas));
          const labels = ['Líquido', 'Taxas', 'Restante'];
          const valores = [liquido, taxas, restante];
          const cores = ['rgb(132, 255, 160)','rgb(255, 99, 99)','rgb(56, 189, 248)'];
          const trace = { type: 'pie', labels, values: valores, hole: 0.57, marker: { colors: cores }, textinfo: 'percent' };
          const layout = { margin: { t: 20, b: 20 }, plot_bgcolor: 'rgba(0,0,0,0.15)', paper_bgcolor: 'rgba(0,0,0,0.15)', height: 260 };
          window.Plotly.newPlot(elPie, [trace], layout, { displayModeBar: false });
        }
      } catch (e) { console.warn('[pre] falha grafico composicao', e); }
    })
    .catch(err => {
      console.error("Erro ao carregar dados da pré-padronização:", err);
      if (elOps) elOps.innerHTML = '<div class="text-center text-red-300 text-sm">Falha ao carregar</div>';
      if (elPie) elPie.innerHTML = '<div class="text-center text-red-300 text-sm">Falha ao carregar</div>';
    });
}

// Torna global para roteador
window.carregarPrePadronizacao = window.carregarPrePadronizacao || carregarPrePadronizacao;

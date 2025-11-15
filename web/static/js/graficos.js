// --- helpers globais de moeda/numero (idempotentes) ---
window.formatarParaReais = window.formatarParaReais || function (v) {
  const n = Number(v);
  if (!isFinite(n)) return "—";
  try { return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
  catch { return `R$ ${n.toFixed(2)}`; }
};
window.brInt = window.brInt || function (v) {
  const n = Number(v);
  return isFinite(n) ? Math.round(n).toLocaleString("pt-BR") : "—";
};
window.pct = window.pct || function (num, den) {
  const a = Number(num), b = Number(den);
  if (!isFinite(a) || !isFinite(b) || b === 0) return "—";
  return `${((a / b) * 100).toFixed(1)}%`;
};



// =================== 📊 Gráficos via API ===================
function atualizarGraficosInsight() {
  fetch('/api/graficos')
    .then(response => response.json())
    .then(data => {
      const g = data.graficos;

      Plotly.react('grafico-operacoes', g.operacoes.data, g.operacoes.layout);
      Plotly.react('grafico-pizza-valores', g.pizza_valores.data, g.pizza_valores.layout);
      Plotly.react('grafico-pizza-qtde', g.pizza_qtde.data, g.pizza_qtde.layout);
      Plotly.react('grafico-ciclos-drawdown', g.ciclos_drawdown_lucro.data, g.ciclos_drawdown_lucro.layout);
      Plotly.react('grafico-divida-acumulada', g.divida.data, g.divida.layout);
    })
    .catch(err => console.error('Erro ao carregar gráficos da API:', err));
}


function carregarGraficosPadronizacao() {
  fetch("/api/graficos/padronizacao")
    .then(res => res.json())
    .then(data => {
      if (data.status !== "ok") {
        console.warn("⚠️ Não foi possível carregar os gráficos da padronização.");
        return;
      }

      // 🔹 Gráfico de barras: distribuição das operações
      const graficoOperacoes = document.getElementById("grafico-operacoes");
      if (graficoOperacoes && data.barras_operacoes) {
        const obj = JSON.parse(data.barras_operacoes);
        Plotly.newPlot(graficoOperacoes, obj.data, obj.layout);
      }

      // 🔹 Gráfico pizza: distribuição de valores
      const graficoValores = document.getElementById("grafico-pizza-valores");
      if (graficoValores && data.pizza_valores) {
        const obj = JSON.parse(data.pizza_valores);
        Plotly.newPlot(graficoValores, obj.data, obj.layout);
      }

      // 🔹 Gráfico pizza: distribuição de quantidades
      const graficoQtde = document.getElementById("grafico-pizza-qtde");
      if (graficoQtde && data.pizza_qtde) {
        const obj = JSON.parse(data.pizza_qtde);
        Plotly.newPlot(graficoQtde, obj.data, obj.layout);
      }
    })
    .catch(err => {
      console.error("❌ Erro ao carregar gráficos da padronização:", err);
    });
}



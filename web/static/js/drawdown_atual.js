function carregarGraficoDividaAcumulada() {
  fetch("/api/graficos/divida")
    .then(res => res.json())
    .then(dados => {
      if (dados.status === "ok" && dados.grafico_divida) {
        const grafico = JSON.parse(dados.grafico_divida);  // <-- Converte string JSON para objeto JS
        Plotly.newPlot("grafico-divida-real-time", grafico.data, grafico.layout);
      } else {
        console.warn("⚠️ Dados não carregados para gráfico de dívida acumulada.");
      }
    })
    .catch(err => {
      console.error("Erro ao carregar gráfico de dívida acumulada:", err);
    });
}


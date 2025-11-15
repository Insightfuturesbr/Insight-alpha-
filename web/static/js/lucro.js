function carregarGraficoCiclosLucro() {
  fetch("/api/graficos/lucro")
    .then(res => res.json())
    .then(data => {
      if (data.status !== "ok") {
        console.warn("⚠️ Erro ao carregar gráfico de lucro.");
        return;
      }

      const grafico = document.getElementById("grafico-ciclos-lucro");
      if (grafico && data.grafico_lucro) {
        const obj = JSON.parse(data.grafico_lucro);
        Plotly.newPlot(grafico, obj.data, obj.layout);
      }
    })
    .catch(err => {
      console.error("❌ Erro no gráfico de lucro:", err);
    });
}
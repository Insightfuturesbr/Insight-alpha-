function carregarGraficoCiclosDrawdown() {
  fetch("/api/graficos/drawdown")
    .then(res => res.json())
    .then(data => {
      if (data.status !== "ok") {
        console.warn("⚠️ Erro ao carregar gráfico de drawdown.");
        return;
      }

      const grafico = document.getElementById("grafico-ciclos-drawdown");
      if (grafico && data.grafico_ciclos) {
        const obj = JSON.parse(data.grafico_ciclos);
        Plotly.newPlot(grafico, obj.data, obj.layout, {displaylogo: false});
      }
    })
    .catch(err => {
      console.error("❌ Erro no gráfico de drawdown:", err);
    });
}



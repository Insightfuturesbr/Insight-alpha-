function atualizarFluxo() {
  fetch('/api/fluxo')
    .then(response => response.json())
    .then(data => {
      const f = data.variaveis_fluxo;

      const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
      };

      // Painel superior (drawdown em tempo real + estatísticas)
      set('drawdownAtual', formatarParaReais((f && f.divida_acumulada) || 0));
      set('destaqueFluxo', (f && f.destaque) || 'N/A');
      set('perc25Dividas', formatarParaReais((f && f.perc25_das_maximas_dividas) || 0));
      set('mediaDividas', formatarParaReais((f && f.media_das_maximas_dividas) || 0));

      // Painel inferior: Fluxo Financeiro Atual
      set('dividaAtual', formatarParaReais((f && f.divida_acumulada) || 0));
      set('valorEmprestado', formatarParaReais((f && f.valor_emprestado) || 0));
      set('amortizacao', formatarParaReais((f && f.amortizacao) || 0));
      set('lucroGerado', formatarParaReais((f && f.lucro_gerado) || 0));

      // Carrega a máxima dívida do ciclo (complementar)
      fetch('/api/ciclos')
        .then(res => res.json())
        .then(cicloData => {
          const maximo = cicloData.ultimo_ciclo["Máxima Dívida do Ciclo"];
          set('maximoCiclo', formatarParaReais(maximo || 0));
        });
    })
    .catch(err => console.error('Erro no fluxo:', err));
}

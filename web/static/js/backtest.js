// =================== 🚀 Rodar Backtest ===================
function showBacktestSpinner(show = true) {
  const btn = document.getElementById('rodarBacktest');
  const spn = document.getElementById('backtestSpinner');
  if (btn) btn.disabled = !!show;
  if (spn) spn.classList.toggle('hidden', !show);
}

function rodarBacktest() {
  console.log("rodarBacktest function called");
  const dados = {
    ativacao_percentual: parseFloat(document.querySelector('[name="ativacao_percentual"]').value),
    ativacao_base: document.querySelector('[name="ativacao_base"]').value,
    comparador_ativacao: document.querySelector('[name="comparador_ativacao"]').value,
    pausa_percentual: parseFloat(document.querySelector('[name="pausa_percentual"]').value),
    pausa_base: document.querySelector('[name="pausa_base"]').value,
    comparador_pausa: document.querySelector('[name="comparador_pausa"]').value,
    desativacao_percentual: parseFloat(document.querySelector('[name="desativacao_percentual"]').value),
    desativacao_base: document.querySelector('[name="desativacao_base"]').value,
    comparador_desativacao: document.querySelector('[name="comparador_desativacao"]').value,
    encerrar_ao_fim_do_ciclo: document.getElementById('encerrar_ciclo').checked
  };

  // Novo endpoint unificado (API)
  showBacktestSpinner(true);

  fetch('/api/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dados)
  })
    .then(res => res.json())
    .then(data => {
      showBacktestSpinner(false);
      if (data.status === 'ok') {
        const m = data.metricas_backtest || data.metricasback || {};
        const o = data.metricas_original || data.metricasoriginal || {};

        const setText = (id, txt) => { const el = document.getElementById(id); if (el) el.innerText = txt; };

        setText('total_operacoes', o.n_operacoes_automacao_ativada ?? '—');
        setText('operacoes_negativas', o.n_operacoes_negativas ?? '—');
        setText('operacoes_amortizacao', o.n_operacoes_amortizacao ?? '—');
        setText('operacoes_lucro', o.n_operacoes_positivas ?? '—');
        setText('lucro_final', typeof o.resultado_liquido_final === 'number' ? formatarParaReais(o.resultado_liquido_final) : '—');

        setText('total_operacoes_backtest', m.n_operacoes_automacao_ativada ?? '—');
        setText('operacoes_negativas_backtest', m.n_operacoes_negativas ?? '—');
        setText('operacoes_amortizacao_backtest', m.n_operacoes_amortizacao ?? '—');
        setText('operacoes_lucro_backtest', m.n_operacoes_positivas ?? '—');
        setText('lucro_final_backtest', typeof m.resultado_liquido_final === 'number' ? formatarParaReais(m.resultado_liquido_final) : '—');

        setText('drawdown_maximo_backtest', typeof m.drawdown_maximo === 'number' ? formatarParaReais(m.drawdown_maximo) : '—');
        setText('maior_lucro_acumulado_backtest', typeof m.maior_lucro_acumulado === 'number' ? formatarParaReais(m.maior_lucro_acumulado) : '—');

        setText('resumo_ciclo', data.resumo_ciclo || '');

        if (data.frase_dr_drawdown) {
          const p = document.getElementById('textoInsightBacktest');
          const box = document.getElementById('blocoInsightBacktest');
          if (p) p.innerHTML = data.frase_dr_drawdown;
          if (box) box.classList.remove('hidden');
        }

        // Store results in localStorage for the comparison page
        localStorage.setItem('metricas_backtest', JSON.stringify(m));
        localStorage.setItem('metricas_original', JSON.stringify(o));

      } else {
        console.error('Erro no backtest:', data.mensagem || 'Erro desconhecido');
      }
    })
    .catch(error => {
      showBacktestSpinner(false);
      console.error('❌ Erro ao rodar o backtest:', error)
    });
}

// Inicializa o botão e coleta de parâmetros na página
function initBacktest() {
  console.log("initBacktest function called");
  const btn = document.getElementById('rodarBacktest');
  if (btn) btn.addEventListener('click', rodarBacktest);
}

// Compatibilidade global (se não estiver usando módulos)
window.rodarBacktest = window.rodarBacktest || rodarBacktest;
window.initBacktest = window.initBacktest || initBacktest;

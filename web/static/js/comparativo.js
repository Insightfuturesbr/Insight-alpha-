// static/js/comparativo.js
(function () {
  const $ = (id) => document.getElementById(id);

  const brMoney = v => (v==null || isNaN(v)) ? "—" : Number(v).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
  const brInt   = v => (v==null || isNaN(v)) ? "—" : Math.round(Number(v)).toLocaleString("pt-BR");

  function fillFields(data, suffix="") {
    if (!data) return;
    const map = {
      total_operacoes: "total_operacoes"+suffix,
      operacoes_negativas: "operacoes_negativas"+suffix,
      operacoes_amortizacao: "operacoes_amortizacao"+suffix,
      operacoes_lucro: "operacoes_lucro"+suffix,
      lucro_final: "lucro_final"+suffix,
      drawdown_maximo: "drawdown_maximo"+suffix,
      maior_lucro_acumulado: "maior_lucro_acumulado"+suffix
    };
    $(map.total_operacoes) && ($(map.total_operacoes).textContent = brInt(data.total_operacoes));
    $(map.operacoes_negativas) && ($(map.operacoes_negativas).textContent = brInt(data.operacoes_negativas));
    $(map.operacoes_amortizacao) && ($(map.operacoes_amortizacao).textContent = brInt(data.operacoes_amortizacao));
    $(map.operacoes_lucro) && ($(map.operacoes_lucro).textContent = brInt(data.operacoes_lucro));

    $(map.lucro_final) && ($(map.lucro_final).textContent = brMoney(data.lucro_final));
    $(map.drawdown_maximo) && ($(map.drawdown_maximo).textContent = brMoney(data.drawdown_maximo));
    $(map.maior_lucro_acumulado) && ($(map.maior_lucro_acumulado).textContent = brMoney(data.maior_lucro_acumulado));
  }

  function computeHeadline(base, insight) {
    if (!base || !insight) return "Comparando execução sempre ligada vs automação inteligente.";
    const lucroBase    = Number(base.lucro_final);
    const lucroInsight = Number(insight.lucro_final);
    const ddBase       = Math.abs(Number(base.drawdown_maximo));
    const ddInsight    = Math.abs(Number(insight.drawdown_maximo));

    let lucroTxt = "—", riscoTxt = "—";
    if (!isNaN(lucroBase) && Math.abs(lucroBase) > 1e-9) {
      const ganho = ((lucroInsight - lucroBase) / Math.abs(lucroBase)) * 100;
      lucroTxt = `${ganho >= 0 ? "+" : ""}${ganho.toFixed(0)}% de Lucro`;
    }
    if (!isNaN(ddBase) && ddBase > 1e-9) {
      const redu = ((ddBase - ddInsight) / ddBase) * 100;
      riscoTxt = `${redu >= 0 ? "−" : "+"}${Math.abs(redu).toFixed(0)}% de Prejuízos`;
    }
    return `${lucroTxt} com ${riscoTxt}`;
  }

  async function carregarComparativo() {
    try {
      const storedBacktest = localStorage.getItem('metricas_backtest');
      const storedOriginal = localStorage.getItem('metricas_original');

      if (storedBacktest && storedOriginal) {
        const insight = JSON.parse(storedBacktest);
        const base = JSON.parse(storedOriginal);

        fillFields(base, "");
        fillFields(insight, "_backtest");
        const hl = document.getElementById("headlineComparativo");
        if (hl) hl.textContent = computeHeadline(base, insight);

        // Clean up localStorage
        localStorage.removeItem('metricas_backtest');
        localStorage.removeItem('metricas_original');
      } else {
        const resp = await fetch("/api/comparativo");
        const data = await resp.json();
        const base    = data.sempre_ligada || data.base || data.estrategia || data.original || data.sem_controle || null;
        const insight = data.insight_futures || data.insight || data.automacao || data.backtest || data.com_inteligencia || null;

        fillFields(base, "");
        fillFields(insight, "_backtest");
        const hl = document.getElementById("headlineComparativo");
        if (hl) hl.textContent = computeHeadline(base, insight);
      }
    } catch (e) {
      console.error("[comparativo] Falha ao carregar /api/comparativo:", e);
      const hl = document.getElementById("headlineComparativo");
      if (hl) hl.textContent = "Não foi possível carregar o comparativo agora. Tente novamente após novo processamento.";
    }
  }

  function init() {
    const main = document.querySelector('main[data-page]');
    if (!main || main.dataset.page !== 'comparativo') return;
    carregarComparativo();
  }

  document.addEventListener("app:ready", init, { once: true });
})();

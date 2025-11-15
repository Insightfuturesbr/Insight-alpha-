// =================== 🔄 Atualizar Contratos ===================
function atualizarContratos() {
  const contratos = document.getElementById("contratosInput").value;
  const status = document.getElementById("contratosStatus");

  fetch('/recalcular_fluxo_contratos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contratos: contratos })
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'ok') {
        status.innerText = '✅ Contratos atualizados e fluxo recalculado!';
        setTimeout(() => location.reload(), 800);
      } else {
        status.innerText = '❌ Erro ao recalcular: ' + data.mensagem;
      }
    })
    .catch(err => {
      status.innerText = '❌ Erro de conexão.';
      console.error(err);
    });
}



// =================== 🕒 Data e Hora ===================
function atualizarDataHora() {
  const agora = new Date();
  const options = {
    weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  };
  document.getElementById('dataHora').innerText = agora.toLocaleString('pt-BR', options);
}

setInterval(atualizarDataHora, 1000);
atualizarDataHora();

// =================== 💲 Formatar Valores ===================
function formatarParaReais(valor) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}



// =================== 🎯 Eventos DOM ===================
document.addEventListener('DOMContentLoaded', () => {
  atualizarGraficosInsight();
  atualizarFluxo();
  atualizarCiclos();

  const botaoBacktest = document.getElementById('rodarBacktest');
  if (botaoBacktest) botaoBacktest.addEventListener('click', rodarBacktest);

  const contratosInput = document.getElementById("contratosInput");
  if (contratosInput) contratosInput.addEventListener('change', atualizarContratos);
});



// static/js/insights.js
(function () {
  function $ (sel) { return document.querySelector(sel); }

  function brTime(d = new Date()) {
    try { return d.toLocaleString("pt-BR", { hour12: false }); }
    catch { return new Date().toISOString(); }
  }

  function pickIcon(text = "", severity) {
    const t = (text || "").toLowerCase();
    if (severity === "alto" || t.includes("risco") || t.includes("alerta")) return "⚠️";
    if (t.includes("lucro") || t.includes("aproveitamento")) return "💸";
    if (t.includes("reativa") || t.includes("reativação") || t.includes("ligar")) return "🔁";
    if (t.includes("drawdown")) return "📉";
    if (t.includes("recupera") || t.includes("amortiza")) return "🟡";
    return "💡";
  }

  function renderInsights(items) {
    const ul = $("#listaInsights");
    const empty = $("#insightsEmpty");
    const updated = $("#insightsUpdated");
    if (!ul || !empty || !updated) return;

    ul.innerHTML = "";

    if (!items || (Array.isArray(items) && items.length === 0)) {
      empty.classList.remove("hidden");
      updated.textContent = brTime(new Date());
      return;
    }
    empty.classList.add("hidden");

    (Array.isArray(items) ? items : [items]).forEach((it) => {
      const texto = typeof it === "string" ? it : (it.texto ?? it.text ?? "");
      const sev   = typeof it === "string" ? undefined : (it.severity ?? it.nivel ?? it.tipo);

      const li = document.createElement("li");
      li.className = "space-x-2";
      li.textContent = `${pickIcon(texto, sev)} ${texto}`;
      ul.appendChild(li);
    });

    updated.textContent = brTime(new Date());
  }

  async function carregarInsights() {
    try {
      const resp = await fetch("/api/insights");
      const data = await resp.json();
      const items = Array.isArray(data) ? data : (data.insights ?? data.lista ?? data);
      renderInsights(items);
    } catch (e) {
      console.error("[insights] Erro ao buscar /api/insights:", e);
      renderInsights([]);
    }
  }

  function init() {
    // só inicializa se for a página de insights
    const main = document.querySelector('main[data-page]');
    if (!main || main.dataset.page !== 'insights') return;

    $("#btnRefreshInsights")?.addEventListener("click", carregarInsights);
    carregarInsights();
  }

  // roda quando o main.js sinalizar que a página está pronta
  document.addEventListener("app:ready", init, { once: true });
})();

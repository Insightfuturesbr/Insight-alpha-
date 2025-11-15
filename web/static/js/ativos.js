//function carregarAtivos() {
//  fetch("/api/ativos")
//    .then(res => res.json())
//    .then(dados => {
//      let ativo = dados.ativo;
//      let texto;
//
//      if (Array.isArray(ativo)) {
//        texto = ativo.join(", ");
//      } else {
//        texto = String(ativo);
//      }
//
//      const el = document.getElementById("ativosResumo");
//      if (el) el.innerText = texto || "—";
//    })
//    .catch(err => {
//      console.error("Erro ao carregar ativos:", err);
//      const el = document.getElementById("ativosResumo");
//      if (el) el.innerText = "—";
//    });
//}
//
//window.carregarAtivos = carregarAtivos; // ✅ torna acessível ao roteador
//
//
//// 🧪 Teste automático ao carregar a seção (se quiser)
//document.addEventListener("DOMContentLoaded", () => {
//  console.log("🧪 DOM carregado. Verificando se #ativosResumo existe...");
//  if (document.getElementById("ativosResumo")) {
//    console.log("✅ Elemento #ativosResumo encontrado. Chamando carregarAtivos...");
//    window.carregarAtivos();
//  } else {
//    console.warn("⚠️ Elemento #ativosResumo não encontrado no DOM.");
//  }
//});
//
function limparTicker(t) {
  return String(t).replace("[R] ", "").trim().toUpperCase();
}

async function carregarAtivo() {
  const el = document.getElementById("ativo");
  if (!el) return;

  try {
    const res = await fetch("/api/ativos?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const dados = await res.json();

    // 1) usa direto o campo 'ativo' se vier
    let ticker = dados.ativo ? limparTicker(dados.ativo) : "";

    // 2) fallback: primeiro da lista 'ativos'
    if (!ticker && Array.isArray(dados.ativos) && dados.ativos.length) {
      ticker = limparTicker(dados.ativos[0]);
    }

    el.textContent = ticker || "—";
  } catch (e) {
    console.error("Erro ao carregar ativo:", e);
    el.textContent = "—";
  }
}

document.addEventListener("DOMContentLoaded", carregarAtivo);

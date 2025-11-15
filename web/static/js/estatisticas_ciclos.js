// Helpers
function money(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  // use sua função se já existir; caso não:
  if (typeof formatarParaReais === "function") return formatarParaReais(n);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
}
function plain(v) { return (v ?? "—").toString(); }
function setText(sel, val) {
  const el = document.querySelector(sel);
  if (el) el.innerText = (val ?? "—");
  else console.warn("⚠️ seletor não encontrado:", sel);
}

async function atualizarEstatisticasCiclos() {
  try {
    const res = await fetch("/api/ciclos/estatisticas?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const stats = await res.json();
    console.log("📦 stats keys:", Object.keys(stats));

    // 🟠 Empréstimo
    const emp = stats.estatisticas_ciclo_emprestimo ?? {};
    setText("#estatisticas-emprestimo-valor",   money(emp.valor_atual));
    setText("#estatisticas-emprestimo-destaque", plain(emp.destaque));
    setText("#estatisticas-emprestimo-extrema", money(emp.extrema));
    setText("#estatisticas-emprestimo-media",   money(emp.media));
    setText("#estatisticas-emprestimo-pr",      plain(emp.posicao_relativa));

    // 🔵 Amortização
    const amo = stats.estatisticas_ciclo_amortizacao ?? {};
    setText("#estatisticas-amortizacao-valor",   money(amo.valor_atual));
    setText("#estatisticas-amortizacao-destaque", plain(amo.destaque));
    setText("#estatisticas-amortizacao-extrema", money(amo.extrema));
    setText("#estatisticas-amortizacao-media",   money(amo.media));
    setText("#estatisticas-amortizacao-pr",      plain(amo.posicao_relativa));

    // 🟢 Lucro (ciclo atual / percentil / etc. — bloco singular)
    const luc = stats.estatisticas_ciclo_lucro ?? {};
    setText("#estatisticas-lucro-valor",   money(luc.valor_atual));
    setText("#estatisticas-lucro-destaque", plain(luc.destaque));
    setText("#estatisticas-lucro-extrema", money(luc.extrema));
    setText("#estatisticas-lucro-media",   money(luc.media));
    setText("#estatisticas-lucro-pr",      plain(luc.posicao_relativa));

    // 🔢 Quantidades por ciclo
    const qemp = stats.estats_qtd_emp_ciclo ?? {};
    setText("#qtd-emprestimos-valor", plain(qemp.valor_atual));
    setText("#qtd-emprestimos-extrema", plain(qemp.extrema));
    setText("#qtd-emprestimos-media", plain(qemp.media));
    setText("#qtd-emprestimos-pr", plain(qemp.posicao_relativa));

    const qamo = stats.estats_qtd_amo_ciclo ?? {};
    setText("#qtd-amortizacao-valor", plain(qamo.valor_atual));
    setText("#qtd-amortizacao-extrema", plain(qamo.extrema));
    setText("#qtd-amortizacao-media", plain(qamo.media));
    setText("#qtd-amortizacao-pr", plain(qamo.posicao_relativa));

    const qluc = stats.estats_qtd_luc_ciclo ?? {};
    setText("#qtd-lucros-valor", plain(qluc.valor_atual));
    setText("#qtd-lucros-extrema", plain(qluc.extrema));
    setText("#qtd-lucros-media", plain(qluc.media));
    setText("#qtd-lucros-pr", plain(qluc.posicao_relativa));

    // 📈 Estatísticas agregadas de lucro (plural)
    const lucAgg = stats.estatisticas_ciclos_lucro ?? {};
    setText("#lucro-ciclo-atual", money(lucAgg.lucro_ciclo_atual));
    setText("#p75-lucros",        money(lucAgg.percentil_75_lucros));
    setText("#qtd-ciclos-lucro",  plain(lucAgg.quantidade_ciclos_lucro));

    // ⏱️ Duração dos ciclos (strings já formatadas)
    const dur = stats.estatisticas_duracao_ciclos ?? {};
    setText("#duracao-media",   plain(dur.media_formatada));
    setText("#duracao-maxima",  plain(dur.maxima_formatada));
    setText("#duracao-p75",     plain(dur.percentil_75_formatada));

    // placeholders 'x'
    document.querySelectorAll(".placeholder-x").forEach(el => (el.innerText = "x"));
  } catch (err) {
    console.error("Erro ao carregar estatísticas de ciclos:", err.message);
  }
}

// garanta que está chamando
document.addEventListener("DOMContentLoaded", atualizarEstatisticasCiclos);

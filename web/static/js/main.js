// /static/js/main.js  (substituir tudo)
(function () {
  const app  = document.querySelector('main[data-page]');
  const page = app?.dataset?.page || '';

  // ---------- mapeamento de páginas -> scripts (ordem importa) ----------
  const routes = {
    dashboard: [
      'js/graficos.js',
      'js/painel.js',
      'js/insights.js',

    ],
    upload: [
      'js/upload.js',
    ],
    'analise-prepadronizada': [
      'js/graficos.js',
      'js/prepadronizacao.js',
      'js/estatisticas_ciclos.js',
      'js/fluxo.js',
      'js/ativos.js',
      'js/ciclos.js',
    ],
    'analise-padronizada': [
      'js/graficos.js',
      'js/padronizacao.js',
      'js/lucro.js',
    ],
    'analise-drawdown': [
      'js/graficos.js',
      'js/drawdown_atual.js',
      'js/drawdown.js',
      'js/fluxo.js',
      'js/lucro.js',
      'js/ciclos.js',
      'js/estatisticas_ciclos.js',
    ],
    'parametrizacao-backtest': [
      'js/graficos.js',
      'js/backtest.js',
    ],
    insights: [
      'js/insights.js',
    ],
    comparativo: [
      'js/comparativo.js',
    ],
    exportacoes: [],
  };

  // ---------- inits por página ----------
  const callIf = async (fnName, ...args) => {
    const f = window[fnName];
    if (typeof f === 'function') {
      try { return await f(...args); } catch (e) { console.error(`[init] ${fnName} falhou:`, e); }
    }
  };

  const inits = {
    dashboard: async () => {
      await callIf('carregarFluxo');
    },
    upload: () => {},
    'analise-prepadronizada': async () => {
      await callIf('carregarAtivo');
      await callIf('contratosInput');
      await callIf('carregarPrePadronizacao');
      await callIf('atualizarEstatisticasCiclos');
      await callIf('botaoAtualizarContratos');
      await callIf('carregarGrafico');
    },
    'analise-padronizada': async () => {
      // tenta ambos nomes por compatibilidade
      await (callIf('carregarGraficosPadronizacao') || callIf('carregarPadronizacao'));
      if (document.getElementById('graficoFluxo')) await callIf('carregarFluxo');
    },
    'analise-drawdown': async () => {
      await callIf('carregarGraficoCiclosDrawdown');
      await callIf('carregarGraficoCiclosLucro');
      await callIf('carregarGraficoDividaAcumulada');
      await callIf('atualizarEstatisticasCiclos');
      await callIf('atualizarFluxo');
    },
    'parametrizacao-backtest': async () => {
      await callIf('initBacktest');
    },
    insights: () => {},
    comparativo: () => {},
    exportacoes: () => {},
  };

  // ---------- loader de scripts ----------
  function baseStatic() { return (window.STATIC_BASE || '/static/'); }

  function loadScript(src) {
    return new Promise((resolve) => {
      const s = document.createElement('script');
      s.src = baseStatic() + src;
      s.async = false;                  // mantém ordem
      s.onload = resolve;
      s.onerror = () => { console.warn('[main.js] falha ao carregar', src); resolve(); };
      document.body.appendChild(s);
    });
  }

  async function loadList(list) {
    for (const src of list) {
      console.log('[main.js] carregando', src);
      await loadScript(src);
    }
  }

  // ---------- boot ----------
  function whenDomReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  }

  async function boot() {
    console.log('[main.js] page =', page);

    // 1) scripts mapeados pela página
    const list = routes[page] || [];
    await loadList(list);

    // 2) fallback por URL (se esquecer data-page no <main>)
    if (!list.length) {
      const p = location.pathname;
      const q = async (...arr) => loadList(arr);
      if (p.includes('upload')) await q('js/upload.js');
      if (p.includes('dashboard')) await q('js/graficos.js','js/painel.js');
      if (p.includes('analise-prepadronizada')) await q('js/graficos.js','js/prepadronizacao.js','js/estatisticas_ciclos.js','js/fluxo.js','js/ativos.js','js/ciclos.js');
      if (p.includes('analise-padronizada')) await q('js/graficos.js','js/padronizacao.js','js/lucro.js');
      if (p.includes('analise-drawdown')) await q('js/graficos.js','js/drawdown_atual.js','js/drawdown.js','js/fluxo.js','js/lucro.js','js/ciclos.js','js/estatisticas_ciclos.js');
      if (p.includes('parametrizacao-backtest')) await q('js/graficos.js','js/backtest.js');
    }

    // 3) init específico
    await (inits[page]?.());

    // 4) evento global para módulos que esperam 'app:ready'
    document.dispatchEvent(new Event('app:ready'));
  }

  whenDomReady(boot);
})();

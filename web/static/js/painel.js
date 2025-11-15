// ===== Overlay estilo Canva + roteador de "páginas" =====
(() => {
  const OVERLAY_CLASS = 'if-canvas-open';
  const CLOSE_BTN_CLASS = 'if-canvas-close-btn';
  const BACKDROP_ID = 'if-canvas-backdrop';

  // CSS injetado
  const style = document.createElement('style');
  style.textContent = `
    #${BACKDROP_ID}{position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(3px);z-index:60;opacity:0;transition:opacity .15s}
    #${BACKDROP_ID}.show{opacity:1}
    .${OVERLAY_CLASS}{position:fixed!important;inset:3vh 2.5vw!important;z-index:61!important;background:rgba(10,25,47,.92);
      border:1px solid rgba(255,255,255,.08);border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,.5);padding:24px;overflow:auto}
    .${CLOSE_BTN_CLASS}{position:sticky;top:0;float:right;margin-top:-6px;background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.18);
      color:#fff;padding:6px 10px;border-radius:9999px;cursor:pointer;font-size:12px;backdrop-filter:blur(2px)}
    .${CLOSE_BTN_CLASS}:hover{background:rgba(0,0,0,.65)}
  `;
  document.head.appendChild(style);

  function open(target) {
    close();
    if (!target) return;

    const btn = document.createElement('button');
    btn.textContent = '✕';
    btn.className = CLOSE_BTN_CLASS;
    btn.addEventListener('click', close);

    target.classList.add(OVERLAY_CLASS);
    target.setAttribute('data-if-canvas', 'open');
    target.insertBefore(btn, target.firstChild);

    let b = document.getElementById(BACKDROP_ID);
    if (!b) {
      b = document.createElement('div');
      b.id = BACKDROP_ID;
      b.addEventListener('click', close);
      document.body.appendChild(b);
      requestAnimationFrame(() => b.classList.add('show'));
    }
    document.body.classList.add('overflow-hidden');

    // carregamentos sob demanda (opcional)
    const id = target.id;
    if (id === 'analise-drawdown') {
      window.carregarGraficoCiclosDrawdown?.();
      window.carregarGraficoCiclosLucro?.();
      window.atualizarFluxo?.();
      window.atualizarCiclos?.();
      window.carregarGraficoDividaAcumulada?.();
    }
    if (id === 'pagina-prepadronizacao') {
      window.carregarPrePadronizacao?.();
      window.carregarAtivos?.();
    }
    if (id === 'graficos_resultado' || id === 'pagina-padronizacao') {
      window.carregarPadronizacao?.();
      window.carregarGraficosPadronizacao?.();
    }
  }

  function close() {
    document.body.classList.remove('overflow-hidden');
    const b = document.getElementById(BACKDROP_ID);
    if (b) { b.classList.remove('show'); setTimeout(() => b.remove(), 150); }
    document.querySelectorAll('[data-if-canvas="open"]').forEach(sec => {
      sec.classList.remove(OVERLAY_CLASS);
      sec.removeAttribute('data-if-canvas');
      sec.querySelector(`.${CLOSE_BTN_CLASS}`)?.remove();
    });
  }

  // apelidos chamados pelos botões -> seletor real (sem mudar seus HTMLs)
  const map = {
    'pagina-dashboard': null,
    'pagina-upload': '#pagina-upload',
    'pagina-prepadronizacao': '#pagina-prepadronizacao',  // defina esse id no container da seção se quiser
    'pagina-padronizacao': '#graficos_resultado',
    'pagina-drawdown': '#analise-drawdown',
    'pagina-backtest': '#parametrizacao-backtest',
    'pagina-modelos': '#estrategia',
    'pagina-insights': '#insights',
    'pagina-exportacoes': '#exportacoes'
  };

  window.exibirPagina = (apelido) => {
    if (apelido === 'pagina-dashboard') { close(); return; }
    const sel = map[apelido];
    if (!sel) return;
    const sec = document.querySelector(sel);
    if (sec) open(sec);
  };

  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
})();

function atualizarCiclos() {
  fetch('/api/ciclos')
    .then(res => res.json())
    .then(data => {
      const ultimo = data?.ultimo_ciclo ?? {};
      const dur    = data?.estatisticas_duracao_ciclos ?? {};

      const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = (val ?? '—');
      };

      set('duracaoAtual', ultimo['Duração do Ciclo'] || '—');
      set('maximoCiclo', formatarParaReais(ultimo['Máxima Dívida do Ciclo'] || 0));
      set('maximaDuracao', dur.maxima_formatada || '—');
      set('mediaDuracao', dur.media_formatada || '—');
      set('percentil75Duracao', dur.percentil_75_formatada || '—');
    })
    .catch(err => {
      console.error('Erro nos ciclos:', err);
      ['duracaoAtual','maximoCiclo','maximaDuracao','mediaDuracao','percentil75Duracao']
        .forEach(id => { const el = document.getElementById(id); if (el) el.innerText = '—'; });
    });
}

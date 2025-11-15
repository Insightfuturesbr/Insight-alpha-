function getForm() {
  return document.getElementById('formUpload');
}

function getStatusElement() {
  return document.getElementById('statusUpload');
}

function getFileInput() {
  const form = getForm();
  return form?.querySelector('input[type="file"]') || null;
}

function getSubmitButton() {
  const form = getForm();
  return form?.querySelector('button[type="submit"], input[type="submit"]');
}

function setStatus(msg) {
  const statusEl = getStatusElement();
  if (statusEl) statusEl.textContent = msg;
}

function disableSubmit(disabled) {
  const btn = getSubmitButton();
  if (btn) btn.disabled = !!disabled;
}

async function performUpload() {
  const fileInput = getFileInput();
  if (!fileInput || !fileInput.files || !fileInput.files[0]) {
    throw new Error('Selecione um arquivo .csv ou .xlsx.');
  }

  const nome = fileInput.files[0].name.toLowerCase();
  if (!/\.(csv|xlsx)$/.test(nome)) {
    throw new Error('Formato inválido. Envie .csv ou .xlsx.');
  }

  const fd = new FormData();
  fd.append('file', fileInput.files[0]);

  disableSubmit(true);
  setStatus('Enviando arquivo…');

  const resp = await fetch('/upload_inline', { method: 'POST', body: fd });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || 'Falha no upload.');
  }

  let payload = {};
  try {
    payload = await resp.json();
  } catch {
    throw new Error('Erro ao interpretar resposta do servidor.');
  }

  if (payload.status !== 'ok') {
    throw new Error(payload.mensagem || 'Processamento não confirmado pelo servidor.');
  }

  setStatus('Processando dados… aguarde');
}

function upload() {
  const form = getForm();
  if (!form || form.dataset.bound === '1') return;
  form.dataset.bound = '1';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    try {
      await performUpload();
      setStatus('Pronto! Redirecionando…');
    } catch (err) {
      setStatus(err.message || 'Erro inesperado.');
    } finally {
      disableSubmit(false);
    }
  });
}

upload();

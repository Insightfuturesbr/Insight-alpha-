# painel_routes.py
from flask import Blueprint, render_template, redirect, url_for, session, send_file, abort
from pathlib import Path
import locale

# locale (ok se já estiver configurado globalmente)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except Exception:
    pass


# +++ ADIÇÕES NO TOPO DO ARQUIVO +++
from datetime import datetime
import pandas as pd


try:
    from services.logic.conditions import decidir_estado_a_partir_df
except Exception:
    decidir_estado_a_partir_df = None  # fallback seguro

# Serviços (ajuste se seu service tiver outros nomes/assinaturas)
from services.repository.strategy_service import list_strategy_cards  # , get_strategy_by_id

# Use APENAS um Blueprint
painel_routes = Blueprint("painel_routes", __name__)

RESULTS_ROOT = Path("outputs/resultados")
OUTPUTS_ROOT = Path("outputs")

# +++ HELPERS LOCAIS +++

def _caminhos_candidatos(latest_dir: Path) -> list[Path]:
    # Prioridades de leitura (NÃO inventa nomes novos; usa os que já vi no projeto)
    nomes = [
        "fluxocalculado.csv",
        "estrategiapadronizada.csv",
        "InsightFuturesResults.csv",
    ]
    return [latest_dir / n for n in nomes]

def _load_fluxo_df() -> pd.DataFrame | None:
    """
    Tenta carregar o DataFrame do fluxo a partir da pasta mais recente em outputs/resultados/.
    Não altera dados; só lê.
    """
    try:
        latest = _latest_results_dir()
        if not latest:
            return None
        for p in _caminhos_candidatos(latest):
            if p.exists() and p.is_file():
                # CSV padrão (vírgula). Se o teu for ';', troque delimiter.
                return pd.read_csv(p)
        # Fallback: tentar na raiz outputs/ (se você às vezes grava lá)
        root = OUTPUTS_ROOT if 'OUTPUTS_ROOT' in globals() else Path("outputs")
        for name in ("fluxocalculado.csv", "estrategiapadronizada.csv"):
            p = root / name
            if p.exists():
                return pd.read_csv(p)
        return None
    except Exception:
        return None


def _inferir_fase(df: pd.DataFrame) -> str:
    """
    Deduz a fase a partir da 'Dívida Acumulada':
      - < 0 e caindo -> DECLINIO
      - < 0 e subindo (indo a zero) -> RECUPERACAO
      - >= 0 -> LUCRO
    """
    try:
        if "Dívida Acumulada" not in df.columns or len(df) == 0:
            return "LUCRO"
        div = pd.to_numeric(df["Dívida Acumulada"], errors="coerce").fillna(0.0)
        if len(div) < 2:
            return "RECUPERACAO" if div.iloc[-1] < 0 else "LUCRO"
        atual = div.iloc[-1]
        prev = div.iloc[-2]
        if atual < 0 and atual < prev:
            return "DECLINIO"
        if atual < 0 and atual >= prev:
            return "RECUPERACAO"
        return "LUCRO"
    except Exception:
        return "LUCRO"

# +++ ROTA HTMX DO CARD ESTADO ATUAL +++
@painel_routes.route("/painel/_estado_atual")
def painel_estado_atual():
    """
    Retorna um parcial Jinja com o estado atual da estratégia.
    Não reprocessa dados: apenas lê o CSV mais recente de outputs/resultados/.
    """
    df = _load_fluxo_df()
    if df is None or len(df) == 0:
        # Renderiza card “vazio” amigável
        estado = {
            "fase": "—",
            "divida_atual": None,
            "media_maximas_dividas": None,
            "p25_maximas_dividas": None,
            "posicao_relativa_divida": None,
            "recomendacao": "MANTER",
            "motivo": "Sem dados recentes encontrados.",
            "ts": datetime.now(),
        }
        return render_template("painel/_estado_atual.html", e=estado)

    # última linha
    row = df.iloc[-1]

    # leituras seguras (NÃO inventa colunas — só pega se existirem)
    divida_atual = row.get("Dívida Acumulada", None)
    media_maximas = row.get("Média das Máximas Dívidas", None)
    p25_maximas = row.get("Percentil 25 das Máximas Dívidas", None)
    pos_rel = row.get("Posição Relativa Dívida", None)

    # fase inferida por dinâmica da dívida
    fase = _inferir_fase(df)

    # decisão consolidada (se o helper existir)
    if decidir_estado_a_partir_df:
        try:
            # parâmetros vazios por padrão; passe os teus se já tiverem prontos
            recomendacao, motivo = decidir_estado_a_partir_df(df, parametros={})
        except Exception:
            recomendacao, motivo = ("MANTER", "Sem decisão consolidada.")
    else:
        recomendacao, motivo = ("MANTER", "Decisor não configurado.")

    estado = {
        "fase": fase,
        "divida_atual": divida_atual,
        "media_maximas_dividas": media_maximas,
        "p25_maximas_dividas": p25_maximas,
        "posicao_relativa_divida": pos_rel,
        "recomendacao": recomendacao,
        "motivo": motivo,
        "ts": datetime.now(),
    }

    return render_template("painel/_estado_atual.html", e=estado)


def _latest_results_dir() -> Path | None:
    """Retorna a pasta de resultados mais recente em outputs/resultados/"""
    if not RESULTS_ROOT.exists():
        return None
    dirs = [p for p in RESULTS_ROOT.iterdir() if p.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]


def formatar_moeda(valor):
    try:
        return locale.currency(valor, grouping=True, symbol=True)
    except Exception:
        return valor


# -------------------------
# Navegação principal
# -------------------------

@painel_routes.route("/painel")
def painel():
    if "user" not in session:
        return redirect(url_for("auth_routes.login"))
    return redirect(url_for("painel_routes.dashboard"))


@painel_routes.route("/painel/dashboard")
def dashboard():
    return render_template("painel/dashboard.html")


@painel_routes.route("/painel/upload")
def upload_page():
    # recebe opcionalmente uma estratégia (se vier da lista de estratégias)
    estrategia_id = session.get("estrategia_atual")  # opcional: se quiser manter no estado
    return render_template("painel/upload.html", estrategia_id=estrategia_id)


@painel_routes.route("/painel/analise-prepadronizada")
def analise_pre():
    return render_template("painel/analise_prepadronizada.html")


@painel_routes.route("/painel/analise-padronizada")
def analise_pad():
    return render_template("painel/analise_padronizada.html")


@painel_routes.route("/painel/analise-drawdown")
def analise_drawdown():
    return render_template("painel/analise_drawdown.html")


@painel_routes.route("/painel/parametrizacao-backtest")
def parametrizacao():
    # pode aceitar ?estrategia_id= na querystring, se quiser ler via request.args
    return render_template("painel/parametrizacao_backtest.html")


@painel_routes.route("/painel/comparativo")
def comparativo():
    return render_template("painel/comparativo_insight.html")


@painel_routes.route("/painel/insights")
def insights():
    return render_template("painel/insights.html")


@painel_routes.route("/painel/exportacoes")
def exportacoes():
    return render_template("painel/exportacoes.html")


# -------------------------
# Estratégias (lista/detalhe)
# -------------------------

@painel_routes.route("/painel/estrategias")
def pagina_estrategias():
    # Se tiver usuário na sessão e quiser filtrar por owner:
    owner = session.get("user")
    cards = list_strategy_cards(owner=owner)
    return render_template("painel/estrategias.html", strategies=cards)

# (Opcional) detalhe da estratégia — crie um template "painel/estrategia_detalhe.html" quando quiser
# @painel_routes.route("/painel/estrategias/<int:id>")
# def detalhe_estrategia(id: int):
#     strategy = get_strategy_by_id(id)  # se tiver no seu service
#     if not strategy:
#         return redirect(url_for("painel_routes.pagina_estrategias"))
#     return render_template("painel/estrategia_detalhe.html", strategy=strategy)


# -------------------------
# Downloads/Exportações
# -------------------------
# Observação: use estes endpoints nas âncoras do exportações.html
# url_for('painel_routes.download_export', filename='...')
# url_for('painel_routes.download_export_resultados', subpath='pasta/arquivo.ext')
# -------------------------

@painel_routes.route("/export/download/<path:filename>")
def download_export(filename: str):
    # whitelist simples — só os arquivos que você linka no template
    allowed = {
        "InsightFuturesResults.csv",
        "estrategiapadronizada.csv",
        "fluxocalculado.csv",
        "ciclos_drawdown.csv",
        "posicoesrelativas.csv",
    }
    if filename not in allowed:
        abort(404)

    # 1ª tentativa: pasta mais recente de resultados
    latest = _latest_results_dir()
    candidate = (latest / filename) if latest else None
    if candidate and candidate.exists():
        return send_file(candidate, as_attachment=True)

    # 2ª tentativa: outputs/ raiz (fallback)
    fallback = OUTPUTS_ROOT / filename
    if fallback.exists():
        return send_file(fallback, as_attachment=True)

    abort(404)


@painel_routes.route("/export/resultados/<path:subpath>")
def download_export_resultados(subpath: str):
    latest = _latest_results_dir()
    if not latest:
        abort(404)

    # resolve seguro: impede sair da pasta com ../
    target = (latest / subpath).resolve()
    base = latest.resolve()
    if not str(target).startswith(str(base)) or not target.exists() or not target.is_file():
        abort(404)

    return send_file(target, as_attachment=True)

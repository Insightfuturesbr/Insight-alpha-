# services/processing/fluxo_financeiro.py
"""
Engine de fluxo financeiro do Insight Futures.
Interpreta o P&L padronizado como Empréstimos, Amortizações e Lucros, gerando
identificadores textuais (D#, E#, A#, L#), métricas de dívida e resumos por ciclo/fase.

Compatível com:
- preprocessing.py  → datas/espelhos
- standardization.py → 'pl_*_padronizado' (mapeados aqui como 'Resultado Simulado Padronizado ...')

Funções públicas principais
---------------------------
- calcular_fluxo_estrategia(df) -> pd.DataFrame
- calcular_maxima_media_e_posicao_relativa(df) -> pd.DataFrame
- construir_resumo_ciclos_fases(df_base, df_ciclos, ...) -> pd.DataFrame
- contar_operacoes_por_fase(df_base, df_ciclos, ...) -> pd.DataFrame
- contagens_para_resumo(df) -> pd.DataFrame
- identificar_tipo_operacao(id_operacao) -> str
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

import logging
import re
from collections import deque

import numpy as np
import pandas as pd

from services.utils.metrics import gerar_indicador_posicional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Constantes / colunas esperadas
# ---------------------------------------------------------------------

COL_RES_LIQ = "Resultado Simulado Padronizado Líquido"
COL_RES_LIQ_ACUM = "Resultado Simulado Padronizado Líquido Acumulado"

# Colunas emitidas por este módulo (mantidas por compatibilidade com o painel)
COLS_SAIDA_FLUXO = [
    "ID Operação",
    "Caixa Líquido",
    "ID Dívida",
    "Dívida Acumulada",
    "ID Empréstimo",
    "Valor Emprestado",
    "Valores Recebidos",
    "ID Amortização/ID Empréstimo",
    "Amortização",
    "ID Lucro",
    "Lucro Gerado",
    "ID Sequencias",
    "Sequencia_Valores_Emprestados",
    "Sequencia_Valores_Recebidos",
]

# ---------------------------------------------------------------------
# Estado do engine (imutáveis fora do laço)
# ---------------------------------------------------------------------
import numpy as np
import pandas as pd

def _safe_cell(df: pd.DataFrame, idx, col):
    """Lê df[col] na linha idx; usa .iloc se idx for posicional (int)."""
    if isinstance(idx, (int, np.integer)):
        return df.iloc[idx][col]
    return df.loc[idx, col]

@dataclass
class FluxoState:
    """Estado mutável da varredura linha a linha."""
    emprestimos_pendentes: Deque[float] = field(default_factory=deque)
    ids_emprestimos: Deque[int] = field(default_factory=deque)
    id_atual_divida: int = 0
    contador_divida: int = 0
    id_atual_emprestimo: int = 0
    ultima_divida_acumulada: float = 0.0
    acumulado_emprestimos: float = 0.0
    acumulado_recebidos: float = 0.0
    id_sequencia_sve: int = 0
    id_sequencia_svr: int = 0
    id_lucro_anterior: Optional[int] = None
    amortizacao_por_divida: Dict[int, float] = field(default_factory=dict)
    emprestimo_acumulado_por_divida: Dict[int, float] = field(default_factory=dict)


def _preparar_estado() -> FluxoState:
    return FluxoState()


def _preparar_resultados(n: int) -> Dict[str, List[Any]]:
    """Pré-aloca listas do tamanho n para reduzir overhead de append."""
    return {k: [np.nan] * n for k in COLS_SAIDA_FLUXO}

# ---------------------------------------------------------------------
# Núcleo do engine (opera sobre o estado)
# ---------------------------------------------------------------------

def _processar_emprestimo(valor_negativo: float, st: FluxoState) -> None:
    """Registra um novo empréstimo (valor negativo)."""
    if st.ultima_divida_acumulada == 0:  # novo ciclo
        st.contador_divida += 1
        st.id_atual_divida = st.contador_divida
        st.id_atual_emprestimo = 0

    # fechar sequência de recebidos (SVR) se estava aberta
    if st.acumulado_recebidos > 0:
        st.id_sequencia_svr += 1
        st.acumulado_recebidos = 0.0

    v = abs(valor_negativo)
    st.acumulado_emprestimos += v
    st.emprestimos_pendentes.append(v)
    st.id_atual_emprestimo += 1
    st.ids_emprestimos.append(st.id_atual_emprestimo)

    st.ultima_divida_acumulada = sum(st.emprestimos_pendentes)

    st.amortizacao_por_divida.setdefault(st.id_atual_divida, 0.0)
    st.emprestimo_acumulado_por_divida.setdefault(st.id_atual_divida, 0.0)
    st.emprestimo_acumulado_por_divida[st.id_atual_divida] += v
    st.id_lucro_anterior = st.id_atual_divida


def _registrar_pagamento(valor_positivo: float, st: FluxoState) -> Tuple[float, float, List[int]]:
    """Aplica recebimentos em FIFO sobre a fila de empréstimos."""
    # fechar sequência de empréstimos (SVE) se estava aberta
    if st.acumulado_emprestimos > 0:
        st.id_sequencia_sve += 1
        st.acumulado_emprestimos = 0.0

    valor_recebido = valor_positivo
    st.acumulado_recebidos += valor_recebido

    pago = 0.0
    ids_amort: List[int] = []

    if st.emprestimos_pendentes:
        restante = valor_recebido
        dq_vals, dq_ids = st.emprestimos_pendentes, st.ids_emprestimos

        while restante > 0 and dq_vals:
            v_atual = dq_vals.popleft()
            a_id = dq_ids.popleft()
            ids_amort.append(a_id)

            if restante >= v_atual:
                pago += v_atual
                restante -= v_atual
            else:
                dq_vals.appendleft(v_atual - restante)
                dq_ids.appendleft(a_id)
                pago += restante
                restante = 0.0

    st.ultima_divida_acumulada = sum(st.emprestimos_pendentes)
    return valor_recebido, pago, ids_amort


def _gerar_registro(
    res_liq: float,
    valor_recebido: float,
    amort: float,
    ids_amort: List[int],
    caixa_liq_ac: float,
    st: FluxoState,
) -> Dict[str, Any]:
    """Constrói o dicionário (linha) nas colunas de saída."""
    # Se dívida zerada, zera o marcador D#
    if st.ultima_divida_acumulada == 0:
        st.id_atual_divida = 0

    id_div = f"D{st.id_atual_divida}"
    id_emp = f"D{st.id_atual_divida}E{st.id_atual_emprestimo}" if res_liq < 0 else f"D{st.id_atual_divida}E0"

    # Lucro só quando não há dívida (após amortização)
    lucro = (valor_recebido - amort) if st.id_atual_divida == 0 else 0.0
    id_lucro = f"L{st.id_lucro_anterior}" if lucro > 0 and st.id_lucro_anterior else "L0"

    # Amortização textual (compacta ranges contíguos)
    if ids_amort:
        ids_sorted = sorted(ids_amort)
        id_amort = f"A{ids_sorted[0]}:A{ids_sorted[-1]}" if (len(ids_sorted) > 1 and ids_sorted[-1] - ids_sorted[0] == len(ids_sorted) - 1) else ",".join(f"A{x}" for x in ids_sorted)
    else:
        id_amort = "A0"

    # Sequência SVE/SVR
    if res_liq < 0:
        id_seq = f"SVE{st.id_sequencia_sve}"
    elif res_liq > 0:
        id_seq = f"SVR{st.id_sequencia_svr}"
    else:
        id_seq = "S0"

    # ID Operação (ordem legível, sem ambiguidade)
    if res_liq < 0:
        id_op = f"{id_emp}{id_seq}"
    elif res_liq > 0:
        if lucro > 0 and amort == 0:
            id_op = f"{id_div}{id_lucro}{id_seq}"
        elif lucro > 0 and amort > 0:
            id_op = f"{id_div}{id_amort}{id_lucro}{id_seq}"
        else:
            id_op = f"{id_div}{id_amort}{id_seq}"
    else:
        id_op = id_seq

    return {
        "ID Operação": id_op,
        "Caixa Líquido": caixa_liq_ac,
        "ID Dívida": id_div,
        "Dívida Acumulada": -st.ultima_divida_acumulada,
        "ID Empréstimo": id_emp,
        "Valor Emprestado": res_liq if res_liq < 0 else 0.0,
        "Valores Recebidos": res_liq if res_liq > 0 else 0.0,
        "ID Amortização/ID Empréstimo": id_amort,
        "Amortização": amort,
        "ID Lucro": id_lucro,
        "Lucro Gerado": lucro,
        "ID Sequencias": id_seq,
        "Sequencia_Valores_Emprestados": st.acumulado_emprestimos,
        "Sequencia_Valores_Recebidos": st.acumulado_recebidos,
    }

# ---------------------------------------------------------------------
# API: cálculo do fluxo
# ---------------------------------------------------------------------

def calcular_fluxo_estrategia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói as colunas de fluxo (IDs/textos/valores) a partir do P&L padronizado.
    Requer:
        - 'Resultado Simulado Padronizado Líquido'
        - 'Resultado Simulado Padronizado Líquido Acumulado'
    Retorna:
        DataFrame cópia com as colunas de saída adicionadas.
    """
    logger.info("Iniciando cálculo do fluxo financeiro...")

    if df is None or df.empty:
        return df.copy()

    base = df.copy()

    # Normalização (não altera semântica)
    for c in (COL_RES_LIQ, COL_RES_LIQ_ACUM):
        if c not in base.columns:
            base[c] = 0.0
        base[c] = pd.to_numeric(base[c], errors="coerce").fillna(0.0)

    n = len(base)
    st = _preparar_estado()
    out = _preparar_resultados(n)

    # Converte para arrays p/ acelerar acesso dentro do loop
    res_liq_arr = base[COL_RES_LIQ].to_numpy(dtype=float, copy=False)
    caixa_ac_arr = base[COL_RES_LIQ_ACUM].to_numpy(dtype=float, copy=False)

    # Loop único (FIFO exige ordem)
    for i in range(n):
        # fallback: mantém linha consistente mesmo em exceções
        registro: Dict[str, Any] = {k: (np.nan if k not in ("Sequencia_Valores_Emprestados", "Sequencia_Valores_Recebidos") else 0.0) for k in COLS_SAIDA_FLUXO}

        try:
            res = float(res_liq_arr[i])
            caixa = float(caixa_ac_arr[i])

            valor_recebido = 0.0
            amort = 0.0
            ids_pag: List[int] = []

            if res < 0.0:
                _processar_emprestimo(res, st)
            elif res > 0.0:
                valor_recebido, amort, ids_pag = _registrar_pagamento(res, st)

            registro = _gerar_registro(res, valor_recebido, amort, ids_pag, caixa, st)

        except Exception as e:
            logger.exception("Erro no fluxo (linha %s): %s", i + 1, e)
        finally:
            for k, v in registro.items():
                out[k][i] = v

    # Montagem final
    df_out = base
    for c, vals in out.items():
        # normaliza tipos listáveis (compat com front)
        if c in ("Sequencia_Valores_Emprestados", "Sequencia_Valores_Recebidos"):
            df_out[c] = pd.Series(vals, index=df_out.index).apply(lambda v: v if isinstance(v, (list, tuple)) else ([] if pd.isna(v) else [v]))
        else:
            df_out[c] = vals

    logger.info("Fluxo financeiro concluído.")
    # --- garantir ID Ciclo a partir do D# ---
    if "ID Ciclo" not in df_out.columns:
        if "ID Dívida" in df_out.columns:
            _ciclo = (
                df_out["ID Dívida"].astype(str).str.extract(r"D(\d+)", expand=False)
                .fillna("0").astype(int)
            )
            df_out["ID Ciclo"] = _ciclo + 1  # convenção: D0 -> ciclo 1
        else:
            df_out["ID Ciclo"] = 0

    return df_out

# ---------------------------------------------------------------------
# Métricas de dívida/posição relativa (linha a linha)
# ---------------------------------------------------------------------

def calcular_maxima_media_e_posicao_relativa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula por linha:
      - 'Máxima Dívida Acumulada'         (mínimo mais negativo do ciclo corrente)
      - 'Média das Máximas Dívidas'       (média das mínimas dos ciclos encerrados)
      - 'Percentil 25 das Máximas Dívidas'
      - 'Posição Relativa Dívida'         (|div_atual| / |p25|)
    Requer: 'Dívida Acumulada' e 'ID Dívida' ou 'ID Operação'.
    """
    if df is None or df.empty:
        return df.copy()
    if "Dívida Acumulada" not in df.columns:
        raise KeyError("Faltou 'Dívida Acumulada' (rode calcular_fluxo_estrategia antes).")
    if ("ID Dívida" not in df.columns) and ("ID Operação" not in df.columns):
        raise KeyError("É necessário 'ID Dívida' ou 'ID Operação' para identificar D#.")

    def _divida_num(v) -> Optional[int]:
        if pd.isna(v):
            return None
        m = re.search(r"D(\d+)", str(v))
        return int(m.group(1)) if m else None

    out = df.copy()
    n = len(out)

    id_raw = out["ID Dívida"] if "ID Dívida" in out.columns else out["ID Operação"]
    id_vec = id_raw.astype(str).str.extract(r"D(\d+)", expand=False).fillna("0").astype(int).to_numpy()
    div = pd.to_numeric(out["Dívida Acumulada"], errors="coerce").fillna(0.0).to_numpy()

    col_max, col_mean, col_p25, col_pos = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    current_id = None
    current_min = None
    mins_encerrados: List[float] = []

    for i in range(n):
        d_id = int(id_vec[i])
        v = float(div[i])

        # troca de ciclo → fecha o anterior
        if current_id is not None and d_id != current_id:
            if current_min is not None:
                mins_encerrados.append(current_min)
            current_id = d_id
            current_min = v
        else:
            if current_id is None:
                current_id = d_id
                current_min = v
            else:
                current_min = min(current_min, v)

        max_validas = [x for x in mins_encerrados if x < 0]
        media = float(np.mean(max_validas)) if max_validas else 0.0
        p25 = float(np.percentile(max_validas, 25)) if len(max_validas) >= 2 else media
        pos = (abs(v) / abs(p25)) if p25 else 0.0

        col_max[i] = current_min if current_min is not None else 0.0
        col_mean[i] = media
        col_p25[i] = p25
        col_pos[i] = pos

    out["Máxima Dívida Acumulada"] = np.round(col_max, 2)
    out["Média das Máximas Dívidas"] = np.round(col_mean, 2)
    out["Percentil 25 das Máximas Dívidas"] = np.round(col_p25, 2)
    out["Posição Relativa Dívida"] = np.round(col_pos, 2)
    return out

# ---------------------------------------------------------------------
# Estatísticas para cards do painel (coluna única)
# ---------------------------------------------------------------------

def calcular_estatisticas_painel_a_partir_df(df_periodo: pd.DataFrame, coluna_total: str) -> Dict[str, Any]:
    """
    Extrai média, referência (p75 ou p25 invertido), extremo, valor atual e um
    indicador 'destaque' posicional (via services.utils.metrics.gerar_indicador_posicional).
    """
    try:
        if coluna_total not in df_periodo.columns:
            raise ValueError(f"Coluna '{coluna_total}' não encontrada")
        serie = df_periodo[coluna_total].dropna()
        if serie.empty:
            return {}
        atual = float(serie.iloc[-1])
        media = float(serie.mean())

        inverter = any(k in coluna_total.lower() for k in ("empréstimo", "emprestimo", "divida", "dívida"))
        if inverter:
            extrema = float(serie.min())
            referencia = float(serie.quantile(0.25))
        else:
            extrema = float(serie.max())
            referencia = float(serie.quantile(0.75))

        posicao = (atual / referencia) if referencia != 0 else 0.0
        destaque = gerar_indicador_posicional(valor_atual=atual, referencia=referencia, extrema=extrema, inverter=inverter)

        return {
            "media": round(media, 2),
            "referencia_percentil": round(referencia, 2),
            "extrema": round(extrema, 2),
            "valor_atual": round(atual, 2),
            "posicao_relativa": round(posicao, 2),
            "destaque": destaque,
        }
    except Exception as e:
        logger.error("Erro ao extrair estatísticas de '%s': %s", coluna_total, e)
        return {}

# ---------------------------------------------------------------------
# Fases/contagens por ciclo (com/sem datas)
# ---------------------------------------------------------------------

def _fmt_duracao(td: pd.Timedelta) -> Optional[str]:
    if pd.isna(td) or td is None:
        return None
    total_min = int(td.total_seconds() // 60)
    if total_min < 1:
        return "0min"
    d, rem = divmod(total_min, 1440)
    h, m = divmod(rem, 60)
    out = []
    if d: out.append(f"{d}d")
    if h: out.append(f"{h}h")
    if m or not out: out.append(f"{m}min")
    return " ".join(out)


def _primeiro_indice_abaixo_do_pico(vals: np.ndarray, i_pico: int, i_fundo: int, v_pico: float, atol: float) -> int:
    for k in range(i_pico + 1, i_fundo + 1):
        if vals[k] < v_pico - atol:
            return k
    return min(i_pico + 1, i_fundo)

def construir_resumo_ciclos_fases(
    df_base: pd.DataFrame,
    df_ciclos: pd.DataFrame,
    *,
    coluna_datetime: Optional[str] = None,
    coluna_acumulado: Optional[str] = None,   # <— adicionado para compat
    resumo_antigo: Optional[pd.DataFrame] = None,
    **kwargs,                                  # <— aceita extras sem erro
) -> pd.DataFrame:
    _ = coluna_acumulado  # apenas para manter compatibilidade

    """
    Define as fases de cada ciclo APÓS o ciclo fechar.
    Início do ciclo = Abertura da 1ª operação do ciclo.
    Fim do ciclo    = Fechamento da última operação do ciclo.
    Declínio        = do 1º índice do ciclo até o fundo (mínimo da dívida no ciclo).
    Recuperação     = do fundo até o  último índice do ciclo (fechamento da última operação).
    """
    import numpy as np
    import pandas as pd

    if df_base is None or df_base.empty or df_ciclos is None or df_ciclos.empty:
        return pd.DataFrame()

    df = df_base.copy()

    # datas de abertura/fechamento por linha
    col_abre = None
    for c in ("Abertura", "Data Abertura", "Data_abertura", "open_time"):
        if c in df.columns:
            col_abre = c; break
    col_fecha = None
    for c in ("Data Fechamento", "Fechamento", "Data_fechamento", "close_time"):
        if c in df.columns:
            col_fecha = c; break

    # eixo auxiliar (fallback)
    if not coluna_datetime:
        for cand in ("DataHora", "Datetime", "Data", "timestamp"):
            if cand in df.columns:
                coluna_datetime = cand; break

    # normaliza tempo
    if col_abre:   df[col_abre]  = pd.to_datetime(df[col_abre],  errors="coerce")
    if col_fecha:  df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    if coluna_datetime:
        df[coluna_datetime] = pd.to_datetime(df[coluna_datetime], errors="coerce")

    # dívida e ciclo por linha
    div = pd.to_numeric(df.get("Dívida Acumulada", 0.0), errors="coerce").fillna(0.0)
    if "ID Ciclo" in df.columns:
        ciclo = pd.to_numeric(df["ID Ciclo"], errors="coerce").fillna(0).astype(int)
    else:
        base = (df.get("ID Dívida") or df.get("ID Operação") or pd.Series("", index=df.index)).astype(str)
        ciclo = base.str.extract(r"D(\d+)", expand=False).fillna("0").astype(int) + 1
        df["ID Ciclo"] = ciclo

    # consideramos ciclo "fechado" quando o ÚLTIMO ponto do ciclo tem dívida == 0
    rows = []
    for cid, idxs in df.groupby("ID Ciclo", sort=False).indices.items():
        idxs = np.array(list(idxs))
        if idxs.size == 0:
            continue

        # verificação de fechamento do ciclo
        if float(div.iloc[idxs[-1]]) != 0.0:
            # ciclo ainda aberto → não gera fases
            continue

        # fundo (mínimo da dívida dentro do ciclo)
        vals = div.iloc[idxs].to_numpy()
        i_fundo_local = int(np.argmin(vals))
        i_fundo = idxs[i_fundo_local]

        # marcos temporais do ciclo usando abertura/fechamento reais
        # início = abertura da 1ª operação do ciclo; fim = fechamento da última operação do ciclo
        if col_abre:
            inicio_ciclo = df.loc[idxs[0], col_abre]
        elif coluna_datetime:
            inicio_ciclo = df.loc[idxs[0], coluna_datetime]
        else:
            inicio_ciclo = pd.NaT

        if col_fecha:
            fim_ciclo    = _safe_cell(df, idxs[-1], col_fecha)
        elif coluna_datetime:
            fim_ciclo = df.loc[idxs[-1], coluna_datetime]
        else:
            fim_ciclo = pd.NaT

        # fases (por índice, não por tipo de operação)
        # declínio: do 1º índice do ciclo até o fundo
        i_ini_decl, i_fim_decl = idxs[0], i_fundo
        # recuperação: do fundo até o último índice do ciclo (fechamento da última operação)
        i_ini_rec, i_fim_rec = i_fundo, idxs[-1]

        def _get_time(i):
            if coluna_datetime:
                return df.loc[i, coluna_datetime]
            return pd.NaT

        # datas de fase (se tiver “Data Abertura/Fechamento”, caem no eixo principal via coluna_datetime; caso contrário, NaT)
        dt_ini_decl = _get_time(i_ini_decl)
        dt_fim_decl = _get_time(i_fim_decl)
        dt_ini_rec  = _get_time(i_ini_rec)
        dt_fim_rec  = _get_time(i_fim_rec)

        def _fmt_dur(a, b):
            if pd.isna(a) or pd.isna(b):
                return "0min"

            td = pd.to_datetime(b) - pd.to_datetime(a)
            mins = int(max(round(td.total_seconds() / 60.0), 0))
            h, m = divmod(mins, 60)
            return f"{h}h {m}min" if h else f"{m}min"

        rows.append({
            "ID Ciclo": int(cid),
            "Data Início": None if pd.isna(inicio_ciclo) else str(inicio_ciclo),
            "Data Fim":    None if pd.isna(fim_ciclo)    else str(fim_ciclo),
            "Inicio Fase Declínio":     None if pd.isna(dt_ini_decl) else str(dt_ini_decl),
            "Fim Fase Declínio":        None if pd.isna(dt_fim_decl) else str(dt_fim_decl),
            "Inicio Fase Recuperação":  None if pd.isna(dt_ini_rec)  else str(dt_ini_rec),
            "Fim Fase Recuperação":     None if pd.isna(dt_fim_rec)  else str(dt_fim_rec),
            "Duração do Declínio":      _fmt_dur(dt_ini_decl, dt_fim_decl),
            "Duração da Recuperação":   _fmt_dur(dt_ini_rec, dt_fim_rec),
        })

    fases = pd.DataFrame(rows).sort_values("ID Ciclo").reset_index(drop=True)

    if resumo_antigo is not None and not resumo_antigo.empty:
        out = resumo_antigo.copy()
        out["ID Ciclo"] = pd.to_numeric(out["ID Ciclo"], errors="coerce").astype("Int64")
        fases["ID Ciclo"] = pd.to_numeric(fases["ID Ciclo"], errors="coerce").astype("Int64")

        # 🔒 evite _x/_y: NÃO traga Data Início/Data Fim das fases
        fases_slim = fases.drop(columns=["Data Início", "Data Fim"], errors="ignore")

        # merge limpo, sem sufixos
        return out.merge(fases_slim, on="ID Ciclo", how="left")

    return fases


def _ensure_datetime_series(df_base: pd.DataFrame, coluna_datetime: Optional[str]) -> Optional[pd.Series]:
    if coluna_datetime and coluna_datetime in df_base.columns:
        return pd.to_datetime(df_base[coluna_datetime]).reset_index(drop=True)
    if isinstance(df_base.index, pd.DatetimeIndex):
        return pd.Series(df_base.index).reset_index(drop=True)
    return None


def _flags_por_id_operacao(s: str) -> Tuple[bool, bool, bool]:
    s = "" if s is None else str(s)
    is_emp = bool(re.search(r"D\d+E\d+", s))
    is_amort = bool(re.search(r"A\d+(?:(?::|,)A\d+)*", s))
    is_lucro = bool(re.search(r"L\d+", s))
    return is_emp, is_amort, is_lucro


def contar_operacoes_por_fase(
    df_base: pd.DataFrame,
    df_ciclos: pd.DataFrame,
    coluna_datetime: Optional[str] = None,
    coluna_acumulado: str = "Resultado Líquido Total Acumulado",
    atol_recuperacao: float = 0.0,
) -> pd.DataFrame:
    """
    Conta operações por fase com base nas datas calculadas (ou índice temporal).
    Emite: Ops/Empréstimos/Amortizações/Lucros para Declínio e Recuperação.
    """
    if df_ciclos is None or df_ciclos.empty:
        return df_ciclos

    dts = _ensure_datetime_series(df_base, coluna_datetime)
    base = df_base.reset_index(drop=True).copy()
    n = len(base)

    idops = base.get("ID Operação", pd.Series([""] * n))
    flags = np.array([_flags_por_id_operacao(x) for x in idops], dtype=bool)
    is_emp_all, is_amort_all, is_lucro_all = flags[:, 0], flags[:, 1], flags[:, 2]
    is_op_all = is_emp_all | is_amort_all | is_lucro_all

    def _count(mask: np.ndarray) -> Tuple[int, int, int, int]:
        return (int(is_op_all[mask].sum()),
                int((is_emp_all & mask).sum()),
                int((is_amort_all & mask).sum()),
                int((is_lucro_all & mask).sum()))

    def _mask(ini: Optional[pd.Timestamp], fim: Optional[pd.Timestamp]) -> Optional[np.ndarray]:
        if dts is None or ini is None or pd.isna(ini):
            return None
        dt = pd.to_datetime(dts)
        return (dt >= ini) & (dt <= fim) if (fim is not None and not pd.isna(fim)) else (dt >= ini)

    df = df_ciclos.copy()
    for c in [
        "ops_declinio_total", "emprestimos_declinio", "amortizacoes_declinio", "lucros_declinio",
        "ops_recuperacao_total", "emprestimos_recuperacao", "amortizacoes_recuperacao", "lucros_recuperacao",
    ]:
        if c not in df.columns:
            df[c] = 0

    for i in range(len(df)):
        row = df.iloc[i]
        ini_decl = pd.to_datetime(row.get("Inicio Fase Declínio")) if row.get("Inicio Fase Declínio") is not None else None
        fim_decl = pd.to_datetime(row.get("Fim Fase Declínio")) if row.get("Fim Fase Declínio") is not None else None
        ini_rec = pd.to_datetime(row.get("Inicio Fase Recuperação")) if row.get("Inicio Fase Recuperação") is not None else None
        fim_rec = pd.to_datetime(row.get("Fim Fase Recuperação")) if row.get("Fim Fase Recuperação") is not None else None

        m_decl = _mask(ini_decl, fim_decl)
        m_rec = _mask(ini_rec, fim_rec)

        if m_decl is not None:
            od, ed, ad, ld = _count(m_decl)
            df.at[i, "ops_declinio_total"] = od
            df.at[i, "emprestimos_declinio"] = ed
            df.at[i, "amortizacoes_declinio"] = ad
            df.at[i, "lucros_declinio"] = ld

        if m_rec is not None:
            orc, er, ar, lr = _count(m_rec)
            df.at[i, "ops_recuperacao_total"] = orc
            df.at[i, "emprestimos_recuperacao"] = er
            df.at[i, "amortizacoes_recuperacao"] = ar
            df.at[i, "lucros_recuperacao"] = lr

    return df

# ---------------------------------------------------------------------
# Resumo por ciclo sem datas (rápido, pronto para painel)
# ---------------------------------------------------------------------

_CICLO_RE = re.compile(r"(D\d+)", re.IGNORECASE)

def _col_as_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    """Sempre retorna uma Series numérica do tamanho do df; se a coluna não existir, preenche com default."""
    import pandas as pd
    if isinstance(df, pd.DataFrame) and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    n = len(df) if isinstance(df, pd.DataFrame) else 0
    return pd.Series([default] * n, index=(df.index if hasattr(df, "index") else None), dtype=float)

def contagens_para_resumo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Contagens por ciclo e por fase, usando sub-intervalos:
      Declínio     = [primeira linha do ciclo, índice do fundo]
      Recuperação  = (índice do fundo, última linha do ciclo]
    Dentro de cada fase contam-se: Ops, Empréstimos, Amortizações, Lucros.
    Se o DF for um RESUMO POR CICLO (sem colunas linha-a-linha), devolve zeros por ciclo — não quebra.
    """
    import numpy as np
    import pandas as pd

    # Casos triviais
    if df is None or (hasattr(df, "empty") and df.empty):
        return pd.DataFrame(columns=[
            "ID Ciclo",
            "Ops Declínio", "Empréstimos Declínio", "Amortizações Declínio", "Lucros Declínio",
            "Ops Recuperação", "Empréstimos Recuperação", "Amortizações Recuperação", "Lucros Recuperação",
        ])

    # Garante DataFrame
    out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df)

    # Identifica se é RESUMO por ciclo (tem datas/agregados de ciclo mas não tem colunas linha-a-linha)
    is_resumo = (
        ("Data Início" in out.columns or "Data Fim" in out.columns) and
        ("Dívida Acumulada" not in out.columns and
         "Valor Emprestado" not in out.columns and
         "Amortização" not in out.columns and
         "Lucro Gerado" not in out.columns)
    )

    # Normaliza "ID Ciclo" (1-based) para ambos os casos
    if "ID Ciclo" in out.columns:
        out["ID Ciclo"] = pd.to_numeric(out["ID Ciclo"], errors="coerce").fillna(0).astype(int)
    else:
        base = (out.get("ID Dívida") or out.get("ID Operação") or pd.Series("", index=out.index)).astype(str)
        out["ID Ciclo"] = base.str.extract(r"D(\d+)", expand=False).fillna("0").astype(int) + 1

    if is_resumo:
        # Não há como contar por fase sem as linhas; devolve zeros por ciclo (mas não quebra a pipeline)
        ciclos = (
            out["ID Ciclo"].dropna().astype(int).unique().tolist()
            if "ID Ciclo" in out.columns else []
        )
        rows = [{
            "ID Ciclo": int(cid),
            "Ops Declínio": 0,
            "Empréstimos Declínio": 0,
            "Amortizações Declínio": 0,
            "Lucros Declínio": 0,
            "Ops Recuperação": 0,
            "Empréstimos Recuperação": 0,
            "Amortizações Recuperação": 0,
            "Lucros Recuperação": 0,
        } for cid in sorted(ciclos)]
        return pd.DataFrame(rows, columns=[
            "ID Ciclo",
            "Ops Declínio", "Empréstimos Declínio", "Amortizações Declínio", "Lucros Declínio",
            "Ops Recuperação", "Empréstimos Recuperação", "Amortizações Recuperação", "Lucros Recuperação",
        ])

    # --- Caso "linha-a-linha": calcula de fato as contagens ---
    div = _col_as_series(out, "Dívida Acumulada", 0.0)
    emp = _col_as_series(out, "Valor Emprestado", 0.0)
    amo = _col_as_series(out, "Amortização", 0.0)
    luc = _col_as_series(out, "Lucro Gerado", 0.0)

    is_emp = emp != 0
    is_amo = amo != 0
    is_luc = luc > 0
    is_op  = is_emp | is_amo | is_luc

    rows = []
    for cid, idxs in out.groupby("ID Ciclo", sort=False).indices.items():
        idxs = np.array(list(idxs))
        if idxs.size == 0:
            continue

        # Considera contagem apenas para ciclos FECHADOS (última linha com dívida == 0)
        if float(div.iloc[idxs[-1]]) != 0.0:
            continue

        # Fundo do ciclo = índice do mínimo da dívida dentro do ciclo
        vals = div.iloc[idxs].to_numpy()
        i_fundo_local = int(np.argmin(vals))
        i_fundo = idxs[i_fundo_local]

        # Sub-intervalos por índice (não por tipo)
        decl_mask = idxs <= i_fundo
        rec_mask  = idxs >  i_fundo

        od = int(is_op.iloc[idxs][decl_mask].sum())
        ed = int(is_emp.iloc[idxs][decl_mask].sum())
        ad = int(is_amo.iloc[idxs][decl_mask].sum())
        ld = int(is_luc.iloc[idxs][decl_mask].sum())

        orc = int(is_op.iloc[idxs][rec_mask].sum())
        erc = int(is_emp.iloc[idxs][rec_mask].sum())
        arc = int(is_amo.iloc[idxs][rec_mask].sum())
        lrc = int(is_luc.iloc[idxs][rec_mask].sum())

        rows.append({
            "ID Ciclo": int(cid),
            "Ops Declínio": od,
            "Empréstimos Declínio": ed,
            "Amortizações Declínio": ad,
            "Lucros Declínio": ld,
            "Ops Recuperação": orc,
            "Empréstimos Recuperação": erc,
            "Amortizações Recuperação": arc,
            "Lucros Recuperação": lrc,
        })

    return pd.DataFrame(rows).sort_values("ID Ciclo", kind="stable").reset_index(drop=True)

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def identificar_tipo_operacao(id_operacao: str) -> str:
    """Classifica: Emprestimo / Amortizacao / Lucro / Desconhecido."""
    s = "" if id_operacao is None else str(id_operacao)
    if re.search(r"D\d+E\d+", s):
        return "Emprestimo"
    if re.search(r"A\d+(?:(?::|,)A\d+)*", s):
        return "Amortizacao"
    if re.search(r"L\d+", s):
        return "Lucro"
    return "Desconhecido"

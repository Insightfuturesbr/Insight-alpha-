
__all__ = [
    "gerar_grafico_fluxo_caixa",
    "gerar_grafico_ciclos_drawdown",
    'gerar_grafico_ciclos_lucro',
    "gerar_grafico_divida_acumulada_simulada",
    'gerar_grafico_pizza',
    'gerar_grafico_ciclos_drawdown_e_lucro',
    'gerar_grafico_barras_horizontais_operacoes',
]
import logging

def gerar_grafico_fluxo_caixa(df):
    x = df.index.tolist()
    y = df['Caixa Líquido'].tolist()

    trace = go.Scatter(x=x, y=y, mode='lines+markers', name='Fluxo de Caixa',
                       line=dict(color='#34d399'), marker=dict(color='#34d399'))
    layout = go.Layout(title='Fluxo de Caixa',
                       plot_bgcolor="#112240",
                       paper_bgcolor="#112240",
                       font=dict(color="white"))

    fig = go.Figure(data=[trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


import locale
def formatar_moeda(valor):
    try:
        return locale.currency(valor, grouping=True, symbol=True)
    except:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


import plotly.graph_objs as go


def gerar_grafico_endividamento_por_ciclo(df):
    """
    Gera gráfico de barras com o valor máximo de dívida acumulada por ciclo.

    Pré-requisitos:
    - df deve conter uma coluna chamada 'emprestimo_acumulado_ciclo'

    Retorno:
    - JSON do gráfico Plotly pronto para uso no painel
    """
    try:
        # Detecta os ciclos com base nos resets de dívida
        df = df.copy()
        df['emprestimo_shift'] = df['emprestimo_acumulado_ciclo'].shift(1)
        df['novo_ciclo'] = (df['emprestimo_acumulado_ciclo'] == 0) & (df['emprestimo_shift'] < 0)
        df['ciclo_id'] = df['novo_ciclo'].cumsum()

        # Calcula o valor máximo de dívida (valor mínimo de empréstimo acumulado)
        max_divida_por_ciclo = df.groupby('ciclo_id')['emprestimo_acumulado_ciclo'].min().abs().reset_index()
        max_divida_por_ciclo.columns = ['Ciclo', 'Máxima Dívida']

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=max_divida_por_ciclo['Ciclo'],
            y=max_divida_por_ciclo['Máxima Dívida'],
            text=[f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in max_divida_por_ciclo['Máxima Dívida']],
            textposition='outside',
            marker=dict(
                color='rgba(0, 100, 250, 0.8)',
                line=dict(color='rgba(0, 100, 250, 1.0)', width=1),
                pattern_shape='',  # sem padrão interno
            ),
            hovertemplate='<b>Ciclo %{x}</b><br>Máx. Dívida: R$ %{y:,.2f}<extra></extra>',
        ))

        fig.update_traces(marker_line_width=1.5, width=0.6)

        fig.update_layout(
            title="Máxima Dívida Acumulada por Ciclo",
            xaxis_title="Ciclo",
            yaxis_title="Dívida Máxima (R$)",
            bargap=0.25,
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=400,
        )

        return fig.to_json()

    except Exception as e:
        logging.error("Erro ao gerar gráfico de endividamento máximo por ciclo: %s", e)
        return None
def gerar_grafico_ciclos_drawdown(df_ciclos, df_lucros_raw=None):
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder
    import json
    import pandas as pd

    df = pd.DataFrame(df_ciclos)
    df["Data Início"] = pd.to_datetime(df["Data Início"])
    df["Data Fim"] = pd.to_datetime(df["Data Fim"])

    # Se for o último ciclo e estiver incompleto, desconsidere no cálculo do máximo
    if df_lucros_raw is not None:
        df_lucros = pd.DataFrame(df_lucros_raw)
        df_lucros["Data Fim"] = pd.to_datetime(df_lucros["Data Fim"])
        ultima_data_fim_lucro = df_lucros["Data Fim"].max()
        ultima_data_fim_drawdown = df["Data Fim"].max()

        if ultima_data_fim_drawdown > ultima_data_fim_lucro:
            maximo_valido = df["Máxima Dívida do Ciclo"].astype(float).iloc[:-1].min()
        else:
            maximo_valido = df["Máxima Dívida do Ciclo"].astype(float).min()
    else:
        maximo_valido = df["Máxima Dívida do Ciclo"].astype(float).min()

    fig = go.Figure()

    for _, row in df.iterrows():
        inicio = row["Data Início"]
        fim = row["Data Fim"]
        valor = row["Máxima Dívida do Ciclo"]
        duracao = row["Duração do Ciclo"]

        fig.add_trace(go.Scatter(
            x=[inicio, inicio, fim, fim],
            y=[0, valor, valor, 0],
            fill="toself",
            mode="lines+markers",
            marker=dict(size=0),
            line=dict(width=0),
            fillcolor="rgba(255, 138, 128, 0.7)",
            name=f"{inicio.strftime('%d/%m %H:%M')}",
            hovertemplate=(
                f"<b>Ciclo {row['ID Ciclo']}</b><br>"
                f"Início: {inicio.strftime('%d/%m/%Y %H:%M')}<br>"
                f"Fim: {fim.strftime('%d/%m/%Y %H:%M')}<br>"
                f"Duração: {duracao}<br>"
                f"Máx. Dívida: R$ {valor:,.2f}<extra></extra>"
            )
        ))

    # Linha de valor máximo (desconsiderando último ciclo se necessário)
    fig.add_trace(go.Scatter(
        x=[df["Data Início"].min(), df["Data Fim"].max()],
        y=[maximo_valido] * 2,
        mode="lines",
        name=f"Valor Máximo (R$ {maximo_valido:,.2f})",
        line=dict(color="red", width=2, dash="dot"),
        showlegend=True
    ))

    # Linhas de média e percentil
    fig.add_trace(go.Scatter(
        x=df["Data Início"],
        y=df["Média Máximas Até o Ciclo"].astype(float).tolist(),
        name="Média",
        mode="lines+markers",
        line=dict(color="#A3E635", width=3),
        marker=dict(size=6, symbol="circle")
    ))

    fig.add_trace(go.Scatter(
        x=df["Data Início"],
        y=df["Percentil 75 Máximas Até o Ciclo"].astype(float).tolist(),
        name="Percentil 75",
        mode="lines+markers",
        line=dict(color="#FBBF24", width=3),
        marker=dict(size=6, symbol="circle")
    ))

    fig.update_layout(
        title="📉 Ciclos de Drawdowns e Lucros",
        xaxis=dict(
            title="Início do Ciclo",
            showgrid=False,
            type="date",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[18, 9], pattern="hour")
            ]
        ),
        yaxis=dict(title="Valor (R$)", tickprefix="R$ ", tickformat=".2f", showgrid=True, gridcolor="gray"),
        plot_bgcolor="#0A192F",
        paper_bgcolor="#0A192F",
        font=dict(color="white"),
        barmode="group",
        height=700
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)


import pandas as pd
import numpy as np
from typing import Optional, Tuple, Union


def gerar_grafico_ciclos_lucro(df_ciclos, df_drawdown_raw=None):
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder
    import json
    import pandas as pd

    df = pd.DataFrame(df_ciclos)
    df["Data Início"] = pd.to_datetime(df["Data Início"])
    df["Data Fim"] = pd.to_datetime(df["Data Fim"])

    # ✅ Se receber os ciclos de drawdown, compara para ver se o último lucro está incompleto
    if df_drawdown_raw is not None:
        df_drawdown = pd.DataFrame(df_drawdown_raw)
        df_drawdown["Data Fim"] = pd.to_datetime(df_drawdown["Data Fim"])
        ultima_fim_lucro = df["Data Fim"].max()
        ultima_fim_drawdown = df_drawdown["Data Fim"].max()

        if ultima_fim_lucro > ultima_fim_drawdown:
            maximo_valido = df["Lucro Gerado no Ciclo"].astype(float).iloc[:-1].max()
        else:
            maximo_valido = df["Lucro Gerado no Ciclo"].astype(float).max()
    else:
        maximo_valido = df["Lucro Gerado no Ciclo"].astype(float).max()

    fig = go.Figure()

    for _, row in df.iterrows():
        inicio = row["Data Início"]
        fim = row["Data Fim"]
        valor = row["Lucro Gerado no Ciclo"]
        duracao = row["Duração do Ciclo"]

        fig.add_trace(go.Scatter(
            x=[inicio, inicio, fim, fim],
            y=[0, valor, valor, 0],
            fill="toself",
            mode="lines+markers",
            marker=dict(size=0),
            line=dict(width=0),
            fillcolor="rgba(34, 197, 94, 0.7)",  # Verde
            name=f"{inicio.strftime('%d/%m %H:%M')}",
            hovertemplate=(
                f"<b>Ciclo {row['ID Ciclo de Lucro']}</b><br>"
                f"Início: {inicio.strftime('%d/%m/%Y %H:%M')}<br>"
                f"Fim: {fim.strftime('%d/%m/%Y %H:%M')}<br>"
                f"Duração: {duracao}<br>"
                f"Lucro: R$ {valor:,.2f}<extra></extra>"
            )
        ))

    # ✅ Linha de valor máximo (considerando se o último ciclo está incompleto)
    fig.add_trace(go.Scatter(
        x=[df["Data Início"].min(), df["Data Fim"].max()],
        y=[maximo_valido] * 2,
        mode="lines",
        name=f"Valor Máximo (R$ {maximo_valido:,.2f})",
        line=dict(color="lime", width=2, dash="dot"),
        showlegend=True
    ))

    if "Média Lucros Até o Ciclo" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Data Início"],
            y=df["Média Lucros Até o Ciclo"].astype(float).tolist(),
            name="Média",
            mode="lines+markers",
            line=dict(color="#3B82F6", width=3),
            marker=dict(size=6, symbol="circle")
        ))

    if "Percentil 25 Lucros Até o Ciclo" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Data Início"],
            y=df["Percentil 25 Lucros Até o Ciclo"].astype(float).tolist(),
            name="Percentil 25",
            mode="lines+markers",
            line=dict(color="#FBBF24", width=3),
            marker=dict(size=6, symbol="circle")
        ))

    fig.update_layout(
        title="💸 Ciclos de Lucro",
        xaxis=dict(
            title="Início do Ciclo",
            showgrid=False,
            type="date",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[18, 9], pattern="hour")
            ]
        ),
        yaxis=dict(title="Valor (R$)", tickprefix="R$ ", tickformat=".2f", showgrid=True, gridcolor="gray"),
        plot_bgcolor="#0A192F",
        paper_bgcolor="#0A192F",
        font=dict(color="white"),
        barmode="group",
        height=700
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)


# 

def gerar_grafico_ciclos_drawdown_e_lucro(
    df_divida,
    df_lucro,
    stats_lucro  # dict com media_lucros, percentil_75_lucros, maior_lucro_ciclo
):
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder
    import json
    import pandas as pd
    import numpy as np

    # ---------- helpers ----------
    ALIAS_DD = {
        "ID Ciclo": [
            "ID Ciclo", "id_ciclo", "ciclo_id1", "ciclo_id"
        ],
        "Data Início": [
            "Data Início", "Inicio Fase Declínio", "Início"
        ],
        "Data Fim": [
            "Data Fim", "Fim Fase Recuperação", "Fim"
        ],
        "Máxima Dívida do Ciclo": [
            "Máxima Dívida do Ciclo", "Maxima_Divida_do_Ciclo",
            "Máxima Dívida Acumulada", "Dívida Máxima do Ciclo"
        ],
        "Média Máximas Até o Ciclo": [
            "Média Máximas Até o Ciclo", "Média das Máximas Dívidas",
            "Media_Maximas_Ate_o_Ciclo"
        ],
        "Percentil 75 Máximas Até o Ciclo": [
            "Percentil 75 Máximas Até o Ciclo", "Percentil 75 das Máximas Dívidas",
            "P75_Maximas_Ate_o_Ciclo"
        ],
    }
    ALIAS_LUC = {
        "ID Ciclo de Lucro": ["ID Ciclo de Lucro", "id_ciclo_lucro", "ciclo_lucro"],
        "Data Início": ["Data Início", "Início"],
        "Data Fim": ["Data Fim", "Fim"],
        "Lucro Gerado no Ciclo": ["Lucro Gerado no Ciclo", "Lucro Gerado", "lucro_ciclo"],
    }

    def col(df, target, aliases):
        for name in aliases.get(target, [target]):
            if name in df.columns:
                return name
        return None

    def to_num(s):
        return pd.to_numeric(s, errors="coerce")

    def fmt_dt(dt):
        if pd.isna(dt):
            return ""
        try:
            return pd.to_datetime(dt).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(dt)

    # ---------- preparo de dados ----------
    dfd = pd.DataFrame(df_divida).copy()
    dfl = pd.DataFrame(df_lucro).copy()

    # resolve nomes reais das colunas
    c_id   = col(dfd, "ID Ciclo", ALIAS_DD) or "ID Ciclo"
    c_ini  = col(dfd, "Data Início", ALIAS_DD)
    c_fim  = col(dfd, "Data Fim", ALIAS_DD)
    c_max  = col(dfd, "Máxima Dívida do Ciclo", ALIAS_DD)
    c_med  = col(dfd, "Média Máximas Até o Ciclo", ALIAS_DD)
    c_p75  = col(dfd, "Percentil 75 Máximas Até o Ciclo", ALIAS_DD)

    # garante colunas mínimas
    for need in [c_ini, c_fim, c_max]:
        if need is None:
            # sem dados de drawdown → segue com figura vazia mas sem quebrar
            dfd = pd.DataFrame(columns=["__ini__", "__fim__", "__max__", "__dur__"])
            break

    if not dfd.empty:
        dfd[c_ini] = pd.to_datetime(dfd[c_ini], errors="coerce")
        dfd[c_fim] = pd.to_datetime(dfd[c_fim], errors="coerce")
        dfd["__ini__"] = dfd[c_ini]
        dfd["__fim__"] = dfd[c_fim]
        dfd["__max__"] = to_num(dfd[c_max]).fillna(0.0)
        # duração como string (se quiser usar no hover)
        td = (dfd["__fim__"] - dfd["__ini__"])
        mins = (td.dt.total_seconds() / 60.0).round().astype("Int64")  # minutos inteiros; lida com NaT
        dfd["__dur__"] = mins.apply(
            lambda m: "" if pd.isna(m) else f"{int(m // 1440)}d {int((m % 1440) // 60)}h {int(m % 60)}min"
        )

    # lucro: resolver aliases
    cl_id  = col(dfl, "ID Ciclo de Lucro", ALIAS_LUC) or "ID Ciclo de Lucro"
    cl_ini = col(dfl, "Data Início", ALIAS_LUC)
    cl_fim = col(dfl, "Data Fim", ALIAS_LUC)
    cl_val = col(dfl, "Lucro Gerado no Ciclo", ALIAS_LUC)

    if not dfl.empty and cl_ini and cl_fim and cl_val:
        dfl[cl_ini] = pd.to_datetime(dfl[cl_ini], errors="coerce")
        dfl[cl_fim] = pd.to_datetime(dfl[cl_fim], errors="coerce")
        dfl["__l_ini__"] = dfl[cl_ini]
        dfl["__l_fim__"] = dfl[cl_fim]
        dfl["__l_val__"] = to_num(dfl[cl_val]).fillna(0.0)
        td_l = (dfl["__l_fim__"] - dfl["__l_ini__"])
        mins_l = (td_l.dt.total_seconds() / 60.0).round().astype("Int64")
        dfl["__l_dur__"] = mins_l.apply(
            lambda m: "" if pd.isna(m) else f"{int(m // 1440)}d {int((m % 1440) // 60)}h {int(m % 60)}min"
        )

    else:
        dfl = pd.DataFrame(columns=["__l_ini__", "__l_fim__", "__l_val__", "__l_dur__"])

    # suportes de drawdown (média e p75) – usam aliases se existirem
    sup_media = float(to_num(dfd[c_med]).iloc[-1]) if (c_med and not dfd.empty) else np.nan
    sup_p75   = float(to_num(dfd[c_p75]).iloc[-1]) if (c_p75 and not dfd.empty) else np.nan

    # maior drawdown histórico concluído
    if not dfd.empty and c_fim:
        completed_mask = dfd[c_fim].notna()
        série = dfd.loc[completed_mask, "__max__"] if completed_mask.any() else dfd["__max__"]
        hist_min_completed = float(série.min()) if not série.empty else 0.0
    else:
        hist_min_completed = 0.0

    # ---------- figura ----------
    fig = go.Figure()

    # Drawdowns
    for _, row in dfd.iterrows():
        inicio = row.get("__ini__")
        fim    = row.get("__fim__")
        valor_neg = float(row.get("__max__", 0.0))
        duracao   = row.get("__dur__", "")

        if pd.isna(inicio) or pd.isna(fim):
            # se faltar data, pula (ou desenha uma linha degenerada)
            continue

        fig.add_trace(go.Scatter(
            x=[inicio, inicio, fim, fim],
            y=[0, valor_neg, valor_neg, 0],
            fill="toself",
            mode="lines+markers",
            marker=dict(size=0),
            line=dict(width=0),
            fillcolor="rgba(255, 138, 128, 0.7)",
            name=(inicio.strftime("%d/%m %H:%M") if not pd.isna(inicio) else "Ciclo"),
            hovertemplate=(
                f"<b>Ciclo {int(row.get(c_id, 0))}</b><br>"
                f"Início: {fmt_dt(inicio)}<br>"
                f"Fim: {fmt_dt(fim)}<br>"
                f"Duração: {duracao}<br>"
                f"Máx. Dívida: R$ {valor_neg:,.2f}<extra></extra>"
            ),
            showlegend=True
        ))

    # Lucros
    for _, row in dfl.iterrows():
        inicio = row.get("__l_ini__")
        fim    = row.get("__l_fim__")
        val    = float(row.get("__l_val__", 0.0))
        dur    = row.get("__l_dur__", "")

        if pd.isna(inicio) or pd.isna(fim):
            continue

        fig.add_trace(go.Scatter(
            x=[inicio, inicio, fim, fim],
            y=[0, val, val, 0],
            fill="toself",
            mode="lines+markers",
            marker=dict(size=0),
            line=dict(width=0),
            fillcolor="rgba(124, 221, 160, 0.55)",
            name=(inicio.strftime("%d/%m %H:%M") if not pd.isna(inicio) else "Lucro"),
            hovertemplate=(
                f"<b>Ciclo de Lucro {int(row.get(cl_id, 0) or 0)}</b><br>"
                f"Início: {fmt_dt(inicio)}<br>"
                f"Fim: {fmt_dt(fim)}<br>"
                f"Duração: {dur}<br>"
                f"Lucro: R$ {val:,.2f}<extra></extra>"
            ),
            showlegend=True
        ))

    # Suportes (drawdown)
    if not np.isnan(sup_media):
        fig.add_hline(
            y=sup_media,
            line=dict(color="#A3E635", width=2),
            annotation_text="<b>Suporte Média Drawdowns</b>",
            annotation_position="bottom left",
            annotation_font=dict(size=14),
            annotation_font_color="#A3E635"
        )
    if not np.isnan(sup_p75):
        fig.add_hline(
            y=sup_p75,
            line=dict(color="#FBBF24", width=2, dash="dot"),
            annotation_text="<b>Suporte P75 Drawdowns</b>",
            annotation_position="bottom right",
            annotation_font=dict(size=14),
            annotation_font_color="#FBBF24"
        )
    fig.add_hline(
        y=hist_min_completed,
        line=dict(color="red", width=2, dash="dot"),
        annotation_text="<b>Suporte Maior Drawdown Histórico</b>",
        annotation_position="bottom left",
        annotation_font=dict(size=14),
        annotation_font_color="red"
    )

    # Resistências (lucro)
    if isinstance(stats_lucro, dict) and stats_lucro:
        for key, color, txt, dash in [
            ("media_lucros", "deepskyblue", "<b>Resistência Média Lucros</b>", None),
            ("percentil_75_lucros", "orange", "<b>Resistência P75 Lucros</b>", "dot"),
            ("maior_lucro_ciclo", "limegreen", "<b>Resistência Maior Lucro</b>", None),
        ]:
            v = stats_lucro.get(key)
            if v is not None:
                fig.add_hline(
                    y=float(v),
                    line=dict(color=color, width=2, dash=(dash or None)),
                    annotation_text=txt,
                    annotation_position="top left" if key != "percentil_75_lucros" else "top right",
                    annotation_font=dict(size=14),
                    annotation_font_color=color,
                )

    fig.update_layout(
        title="📉 Ciclos de Drawdowns e Lucros",
        xaxis=dict(
            title="Início do Ciclo",
            showgrid=False,
            type="date",
            domain=[0.0, 0.9],
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[18, 9], pattern="hour"),
            ],
        ),
        yaxis=dict(title="Valor (R$)", tickprefix="R$ ", tickformat=".2f", showgrid=True, gridcolor="gray"),
        legend=dict(x=0.92),
        plot_bgcolor="#0A192F",
        paper_bgcolor="#0A192F",
        font=dict(color="white"),
        barmode="group",
        height=700,
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)


# visual/graficos_plotly.py

import pandas as pd

from plotly.utils import PlotlyJSONEncoder

def gerar_grafico_divida_acumulada_simulada(df_simulado: pd.DataFrame, media: float, percentil25: float, minima: float) -> str:
    fig = go.Figure()


    fig.add_trace(go.Scatter(
        x=df_simulado["Abertura"],
        y=df_simulado["Dívida Acumulada"].astype(float).tolist(),
        mode="lines+markers",
        name="Dívida Acumulada",
        text=df_simulado["Dívida Acumulada"].tolist(),  # ✅ transforma ndarray em lista
        textposition="top center",
        line=dict(color="rgba(255, 138, 128, 0.7)", width=3),
        marker=dict(size=8)
    ))

    # Linha da Média com legenda + anotação
    fig.add_trace(go.Scatter(
        x=[df_simulado["Abertura"].min(), df_simulado["Abertura"].max()],
        y=[media, media],
        mode="lines",
        name=f"Suporte Estatístico (Média: R$ {media:.2f})",
        line=dict(color="orange", width=2, dash="dot"),
        showlegend=True
    ))


    # Linha do Percentil 75
    fig.add_trace(go.Scatter(
        x=[df_simulado["Abertura"].min(), df_simulado["Abertura"].max()],
        y=[percentil25, percentil25],
        mode="lines",
        name=f"Percentil 25 - Ativação (R$ {percentil25:.2f})",
        line=dict(color="limegreen", width=2, dash="dot"),
        showlegend=True
    ))



    # Linha da Mínima Histórica
    fig.add_trace(go.Scatter(
        x=[df_simulado["Abertura"].min(), df_simulado["Abertura"].max()],
        y=[minima, minima],
        mode="lines",
        name=f"Suporte Estatístico (Mínima: R$ {minima:.2f})",
        line=dict(color="red", width=2, dash="dot"),
        showlegend=True
    ))

    # Último ponto da simulação
    ultimo_x = df_simulado["Abertura"].iloc[-1]
    ultimo_y = df_simulado["Dívida Acumulada"].astype(float).iloc[-1]

    fig.add_trace(go.Scatter(
        x=[ultimo_x],
        y=[ultimo_y],
        mode="markers+text",
        name="Sua estratégia<br> está aqui",
        marker=dict(color="cyan", size=12, symbol="circle"),
        text=["Sua Estratégia <br> Está Aqui"],
        textposition="bottom right",
        showlegend=False # Não precisa de legenda para esse ponto
    ))

    fig.update_layout(

        title="📉 Acompanhe o Drawdown em Real-Time",
        xaxis_title="Data/Hora",
        yaxis_title="Valor (R$)",
        plot_bgcolor="#0A192F",
        paper_bgcolor="#0A192F",
        font=dict(color="white"),
        xaxis=dict(
            showgrid=False,
            type="date",
            rangebreaks=[
                # Oculta fins de semana
                dict(bounds=["sat", "mon"]),
                # Oculta horários fora do pregão (antes das 9h e depois das 18h)
                dict(bounds=[18, 9], pattern="hour")
            ]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="gray",
            tickformat=".2f",
            tickprefix="R$ ",
            range=[minima * 1.2, 0]  # 👈 Garante visualização abaixo de zero
        ),
        height=600
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)


def gerar_grafico_pizza(emprestimos, amortizacoes, lucros, labels):
    valores = [abs(emprestimos), amortizacoes, lucros]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=valores,
        hole=0.57,
        textinfo='percent',
        pull=[0, 0, 0.12],  # destacando a fatia do lucro
        marker=dict(colors=[
            'rgb(255, 99, 99)',  # Empréstimos - Vermelho suave (risco)
            'rgb(56, 189, 248)',  # Amortizações - Cyan neon (recuperação)
            'rgb(132, 255, 160)'  # Lucros - Verde lime (lucro real)
        ]),
        hovertemplate = '%{label}<br>%{value}<extra></extra>'
    )])

    fig.update_layout(

        legend=dict(
            orientation='h',
            y=-0.25,
            x=0.5,
            xanchor='center',
            font=dict(color='white')
        ),

        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0.15)",
        paper_bgcolor="rgba(0,0,0,0.15)",
        font=dict(color="white"),
        margin=dict(t=20, b=20, l=10, r=10),
        height=280,
        autosize=True
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)




import plotly.graph_objects as go
import json
import plotly


def gerar_grafico_barras_horizontais_operacoes(positivas, negativas, neutras):
    valores = [positivas, negativas, neutras]
    total = sum(valores)

    percentuais = [f'{(v / total) * 100:.1f}%' if total > 0 else '0%' for v in valores]

    labels = ['Positivas', 'Negativas', 'Neutras']
    cores = ['rgb(132, 255, 160)', 'rgb(255, 99, 99)', '#B0BEC5']  # Cyan, Red, Neutro

    fig = go.Figure(go.Bar(
        x=valores,
        y=labels,
        orientation='h',
        marker=dict(color=cores),
        text=percentuais,  # As porcentagens nas barras
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(color='black', size=14),
    ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0.15)",
        paper_bgcolor="rgba(0,0,0,0.15)",
        margin=dict(t=20, b=20, l=80, r=20),
        height=180,
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=True, visible=True),
        font=dict(color="white"),
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def gerar_placeholder_plotly(mensagem="Aguardando Upload") -> str:
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder

    fig = go.Figure()

    fig.add_annotation(
        text=mensagem,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=18, color="gray"),
        align="center"
    )

    fig.update_layout(
        title=mensagem,
        plot_bgcolor="#0A192F",
        paper_bgcolor="#0A192F",
        font=dict(color="white"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return json.dumps(fig, cls=PlotlyJSONEncoder)
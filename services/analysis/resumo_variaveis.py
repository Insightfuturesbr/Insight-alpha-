
import pandas as pd
from services.utils.metrics import gerar_indicador_posicional, obter_periodo
import logging


__all__ = [
    "obter_variaveis_pre_padronizacao","obter_variaveis_padronizacao", "obter_variaveis_fluxo",
    "classificar_e_contar_resultados",


]
# >>> cole logo após os imports atuais

# mapeia nomes legados -> nomes novos
_ALIASES = {
    # padronização
    "Resultado Simulado Padronizado Bruto":        "pl_bruto_padronizado",
    "Resultado Simulado Padronizado Líquido":      "pl_liquido_padronizado",
    "Resultado Simulado Padronizado Bruto Acumulado":   "pl_bruto_acumulado",
    "Resultado Simulado Padronizado Líquido Acumulado": "pl_liquido_acumulado",
    "Taxas Acumuladas Padronização":               "custos_operacionais_acumulados",
}

def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Cria colunas legadas a partir das novas, quando necessário."""
    df = df.copy()
    for antigo, novo in _ALIASES.items():
        if antigo not in df.columns and novo in df.columns:
            df[antigo] = df[novo]
    return df

def _ensure_id_ciclo(df: pd.DataFrame) -> pd.DataFrame:
    """Garante 'ID Ciclo' a partir de 'ID Dívida' ou 'ID Operação' (D#)."""
    if "ID Ciclo" in df.columns:
        df["ID Ciclo"] = pd.to_numeric(df["ID Ciclo"], errors="coerce").fillna(0).astype(int)
        return df
    base = None
    if "ID Dívida" in df.columns:
        base = df["ID Dívida"].astype(str)
    elif "ID Operação" in df.columns:
        base = df["ID Operação"].astype(str)
    if base is not None:
        cid = (
            base.str.extract(r"D(\d+)", expand=False)
            .fillna("0").astype(int)
        ) + 1
        df["ID Ciclo"] = cid
    else:
        df["ID Ciclo"] = 0
    return df

def obter_variaveis_pre_padronizacao(df: pd.DataFrame) -> dict:
    """
    Retorna métricas importantes antes da padronização da estratégia.
    Mantém as mesmas chaves já usadas no painel.
    """
    from services.input.ativos import identificar_parametros_por_ativo
    try:
        colunas_necessarias = [
            'Resultado líquido antes da padronização',
            'Resultado líquido Total Acumulado antes da padronização',
            'Resultado Total Acumulado em pontos',
            'Resultado da Operação em real antes da padronização',
            'Taxas antes da padronização',
            'Contratos Negociados',
            'Lado',
            'Ativo'
        ]
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatória não encontrada: {col}")

        df = df.copy()

        def _num(s: pd.Series) -> pd.Series:
            return pd.to_numeric(s.astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

        # normalização numérica
        df['Resultado líquido antes da padronização'] = _num(df['Resultado líquido antes da padronização'])
        df['Resultado líquido Total Acumulado antes da padronização'] = _num(df['Resultado líquido Total Acumulado antes da padronização'])
        df['Resultado Total Acumulado em pontos'] = _num(df['Resultado Total Acumulado em pontos'])
        df['Resultado da Operação em real antes da padronização'] = _num(df['Resultado da Operação em real antes da padronização'])
        df['Taxas antes da padronização'] = _num(df['Taxas antes da padronização'])

        ativo = df['Ativo'].dropna().iloc[0]
        parametros = identificar_parametros_por_ativo(ativo)

        resultado_total_pontos = float(df['Resultado Total Acumulado em pontos'].iloc[-1])
        resultado_liquido = float(df['Resultado líquido Total Acumulado antes da padronização'].iloc[-1])
        taxas_totais = float(df['Taxas antes da padronização'].sum())
        resultado_bruto = float(df['Resultado da Operação em real antes da padronização'].sum())

        # validação cruzada
        bruto_alternativo = resultado_liquido + taxas_totais
        desvio = abs(resultado_bruto - bruto_alternativo)
        if desvio > 1:
            logging.warning("⚠️ Alerta: Desvio entre bruto e (líquido + taxas): %.2f", desvio)

        def pct(part, total):
            return round((part / total) * 100, 2) if total and abs(total) > 1e-12 else 0.0

        variaveis_pre = {
            "total_operacoes": len(df),
            "periodo": obter_periodo(df),
            "contratos_media": float(pd.to_numeric(df['Contratos Negociados'], errors='coerce').fillna(0).mean()),
            "contratos_max": float(pd.to_numeric(df['Contratos Negociados'], errors='coerce').fillna(0).max()),
            "contratos_soma": float(pd.to_numeric(df['Contratos Negociados'], errors='coerce').fillna(0).sum()),
            "resultado_liquido_acumulado": round(resultado_liquido, 2),
            "resultado_bruto": round(resultado_bruto, 2),
            "resultado_acumulado_pontos": round(resultado_total_pontos, 2),
            "taxas": round(taxas_totais, 2),
            "percentual_liquido": pct(resultado_liquido, resultado_bruto),
            "percentual_taxas": pct(taxas_totais, resultado_bruto),
            "percentual_restante": round(100.0 - (pct(resultado_liquido, resultado_bruto) + pct(taxas_totais, resultado_bruto)), 2),
            "parametros_ativos": parametros._asdict(),
            "resultado_liquido_media": round(float(df['Resultado líquido antes da padronização'].mean()), 2),
        }
        return variaveis_pre

    except Exception as e:
        logging.error("💥 Erro ao obter variáveis antes da padronização: %s", e)
        return {}




def obter_variaveis_padronizacao(df: pd.DataFrame) -> dict:
    from services.input.ativos import identificar_parametros_por_ativo
    try:
        if df is None or df.empty:
            logging.error("⚠️ ERRO: DataFrame está vazio ou None.")
            return {}

        df = _apply_aliases(df)  # <<< importante

        colunas_necessarias = [
            'Resultado Simulado Padronizado Bruto',
            'Resultado Simulado Padronizado Líquido',
            'Taxas Acumuladas Padronização',
            'Ativo'
        ]
        for col in colunas_necessarias:
            if col not in df.columns:
                logging.error("⚠️ ERRO: Coluna necessária '%s' não encontrada no DataFrame.", col)
                return {}


        # Parâmetros do ativo
        ativo = df['Ativo'].dropna().iloc[0]
        parametros = identificar_parametros_por_ativo(ativo)

        # Totais
        total_operacoes = len(df)
        contratos = parametros.contratos
        taxa_unitaria = parametros.taxa
        taxa_total_por_operacao = contratos * 2 * taxa_unitaria

        resultado_bruto_total = round(df['Resultado Simulado Padronizado Bruto'].sum(), 2)
        resultado_liquido_total = round(df['Resultado Simulado Padronizado Líquido'].sum(), 2)
        taxas_total = round(df['Taxas Acumuladas Padronização'].iloc[-1], 2)


        # Percentuais
        if resultado_bruto_total != 0:
            percentual_liquido = round((resultado_liquido_total / resultado_bruto_total) * 100, 2)
            percentual_taxas = round((taxas_total / resultado_bruto_total) * 100, 2)
        else:
            percentual_liquido = percentual_taxas = 0.0

        percentual_restante = round(100 - percentual_liquido - percentual_taxas, 2)

        variaveis = {
            "ativo": ativo,
            "total_operacoes": total_operacoes,
            "contratos_padronizados": contratos,
            "taxa_simulada_por_operacao": round(taxa_total_por_operacao, 2),
            "taxas_totais_padronizadas": taxas_total,
            "resultado_bruto_padronizado": resultado_bruto_total,
            "resultado_liquido_padronizado": resultado_liquido_total,
            "percentual_liquido": percentual_liquido,
            "percentual_taxas": percentual_taxas,
            "percentual_restante": percentual_restante
        }

        logging.info(
            "📊 Estratégia padronizada com %s contratos e %s operações.\n➡️ Resultado Bruto: R$ %.2f, Resultado Líquido: R$ %.2f, Taxas: R$ %.2f.",
            contratos,
            total_operacoes,
            resultado_bruto_total,
            resultado_liquido_total,
            taxas_total,
        )

        return variaveis

    except Exception:
        import traceback
        logging.error("💥 ERRO durante a obtenção de variáveis da padronização:")
        traceback.print_exc()
        return {}


def obter_variaveis_fluxo(df: pd.DataFrame) -> dict:
    """
    Extrai variáveis-chave do fluxo financeiro da estratégia para o painel.
    Mantém as mesmas chaves retornadas hoje.
    """
    try:
        colunas_necessarias = [
            'Taxas Acumuladas Padronização', 'ID Operação', 'Caixa Líquido',
            'Dívida Acumulada', 'Valor Emprestado', 'Amortização', 'Lucro Gerado',
            'Sequencia_Valores_Emprestados', 'Sequencia_Valores_Recebidos',
            'Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
            'Posição Relativa Dívida', 'Percentil 25 das Máximas Dívidas'
        ]
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatória não encontrada: {col}")

        df = df.copy()

        to_num_cols = [
            'Taxas Acumuladas Padronização', 'Caixa Líquido',
            'Dívida Acumulada', 'Valor Emprestado', 'Amortização', 'Lucro Gerado',
            'Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
            'Posição Relativa Dívida', 'Percentil 25 das Máximas Dívidas'
        ]
        for c in to_num_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

        total_linhas = int(len(df))
        caixa_liquido = round(float(df['Caixa Líquido'].iloc[-1]), 2)
        divida_acumulada = round(float(df['Dívida Acumulada'].iloc[-1]), 2)
        taxas = round(float(df['Taxas Acumuladas Padronização'].iloc[-1]), 2)

        valor_emprestado = round(float(df['Valor Emprestado'].sum()), 2)
        qtde_emprestado = int(df['Valor Emprestado'].ne(0).sum())
        perc_emprestado = round((qtde_emprestado / total_linhas) * 100, 2) if total_linhas else 0.0

        amortizacao = round(float(df['Amortização'].sum()), 2)
        qtde_amortizacao = int(df['Amortização'].ne(0).sum())
        perc_amortizacao = round((qtde_amortizacao / total_linhas) * 100, 2) if total_linhas else 0.0

        lucro_gerado = round(float(df['Lucro Gerado'].sum()), 2)
        qtde_lucro = int(df['Lucro Gerado'].ne(0).sum())
        perc_lucro = round((qtde_lucro / total_linhas) * 100, 2) if total_linhas else 0.0

        maxima_divida = round(float(df['Máxima Dívida Acumulada'].min()), 2)   # mantém seu comportamento atual
        media_maximas = round(float(df['Média das Máximas Dívidas'].iloc[-1]), 2)
        perc25 = round(float(df['Percentil 25 das Máximas Dívidas'].iloc[-1]), 2)
        pr_divida = round(float(df['Posição Relativa Dívida'].iloc[-1]), 2)

        destaque = gerar_indicador_posicional(
            valor_atual=divida_acumulada,
            referencia=perc25,


            extrema=maxima_divida,
            inverter=True  # dívida: quanto menor, melhor
        )

        return {
            "caixa_liquido_atual": caixa_liquido,
            "divida_acumulada": divida_acumulada,
            "valor_emprestado": valor_emprestado,
            "amortizacao": amortizacao,
            "lucro_gerado": lucro_gerado,
            "total_taxas_simuladas": taxas,
            "maxima_divida": maxima_divida,
            "media_das_maximas_dividas": media_maximas,
            "perc25_das_maximas_dividas": perc25,
            "posicao_relativa_final": pr_divida,
            "destaque": destaque,
            "qtde_emprestado": qtde_emprestado,
            "qtde_amortizacao": qtde_amortizacao,
            "qtde_lucro": qtde_lucro,
            "total_linhas": total_linhas,
            "perc_emprestado": perc_emprestado,
            "perc_amortizacao": perc_amortizacao,
            "perc_lucro": perc_lucro,
        }

    except Exception as e:
        logging.error("💥 Erro ao obter variáveis do fluxo financeiro: %s", e)
        return {}



def classificar_e_contar_resultados(
    df: pd.DataFrame,
    coluna_resultado: str = 'Resultado líquido antes da padronização',
    retornar_json: bool = False
):
    """
    Atualiza o DF com 'Tipo Resultado' e devolve métricas (ou JSON se retornar_json=True).
    Mantém as mesmas chaves já usadas pelo painel.
    """
    import json
    try:
        if coluna_resultado not in df.columns:
            raise ValueError(f"A coluna '{coluna_resultado}' não foi encontrada no DataFrame.")

        df = df.copy()
        df[coluna_resultado] = pd.to_numeric(
            df[coluna_resultado].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).fillna(0.0)

        df['Tipo Resultado'] = df[coluna_resultado].apply(
            lambda x: 'Positiva' if x > 0 else ('Negativa' if x < 0 else 'Neutra')
        )

        contagem = df['Tipo Resultado'].value_counts()
        total = int(contagem.sum()) if contagem.sum() > 0 else 1

        soma = df.groupby('Tipo Resultado')[coluna_resultado].sum()
        media = df.groupby('Tipo Resultado')[coluna_resultado].mean()

        def _q(series, q, fallback=0.0):
            s = pd.to_numeric(series, errors='coerce').dropna()
            if len(s) == 0:
                return fallback
            if len(s) == 1:
                return float(s.iloc[0])
            return float(s.quantile(q))

        perc75_pos = _q(df.loc[df['Tipo Resultado']=='Positiva', coluna_resultado], 0.75, fallback=float(media.get('Positiva', 0.0)))
        perc25_neg = _q(df.loc[df['Tipo Resultado']=='Negativa', coluna_resultado], 0.25, fallback=float(media.get('Negativa', 0.0)))

        metricas = {
            "qtd_positivas":  int(contagem.get('Positiva', 0)),
            "qtd_negativas":  int(contagem.get('Negativa', 0)),
            "qtd_neutras":    int(contagem.get('Neutra',   0)),

            "pct_positivas":  round(contagem.get('Positiva', 0) / total * 100, 2),
            "pct_negativas":  round(contagem.get('Negativa', 0) / total * 100, 2),
            "pct_neutras":    round(contagem.get('Neutra',   0) / total * 100, 2),

            "soma_positivas": round(float(soma.get('Positiva', 0.0)), 2),
            "soma_negativas": round(float(soma.get('Negativa', 0.0)), 2),
            "soma_neutras":   round(float(soma.get('Neutra',   0.0)), 2),

            "media_positivas": round(float(media.get('Positiva', 0.0)), 2),
            "media_negativas": round(float(media.get('Negativa', 0.0)), 2),

            "perc75_positivas": round(perc75_pos, 2),
            "perc25_negativas": round(perc25_neg, 2),
        }

        return (json.dumps(metricas, ensure_ascii=False) if retornar_json else (df, metricas))

    except Exception as e:
        logging.error("⚠️ Erro ao classificar resultados: %s", e)
        metricas_zeradas = {k: 0 for k in [
            "qtd_positivas","qtd_negativas","qtd_neutras",
            "pct_positivas","pct_negativas","pct_neutras",
            "soma_positivas","soma_negativas","soma_neutras",
            "media_positivas","media_negativas",
            "perc75_positivas","perc25_negativas"
        ]}
        return (json.dumps(metricas_zeradas, ensure_ascii=False) if retornar_json else (df, metricas_zeradas))

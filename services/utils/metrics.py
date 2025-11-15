"""
PT:
Métricas auxiliares de período e indicadores posicionais.

EN:
Auxiliary period metrics and positional indicators.
"""

import pandas as pd


def obter_periodo(df: pd.DataFrame) -> str:
    """
    PT: Retorna o período coberto (ex.: "01/01/2024 a 31/03/2024") com base no índice datetime.
    EN: Returns covered period (e.g., "01/01/2024 to 31/03/2024") based on datetime index.
    """
    try:
        if df.empty:
            return "⚠️ ERRO: DataFrame está vazio."
        if not isinstance(df.index, pd.DatetimeIndex):
            return "⚠️ ERRO: O índice do DataFrame não é uma série temporal."
        ini = df.index.min()
        fim = df.index.max()
        return f'Período {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}'
    except Exception as e:
        return f"⚠️ ERRO ao obter período: {e}"


def calcular_metricas_por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """
    PT: Exemplo simples de métricas: taxa de recuperação e lucro sobre dívida acumulada.
    EN: Simple example metrics: recovery rate and profit over accumulated debt.
    """
    df['Taxa de Recuperação (%)'] = (df['Total Amortizações Até Agora'] / df['Total Empréstimos Até Agora']).fillna(0) * 100
    df['Lucro sobre Dívida (%)'] = (df['Total Lucro Até Agora'] / df['Dívida Acumulada']).fillna(0) * 100
    return df


def gerar_indicador_posicional(valor_atual, referencia, extrema, inverter: bool = False) -> str:
    """
    PT: Indicador posicional textual comparando valor atual a um percentil (referência) e a um extremo.
    EN: Textual positional indicator comparing current value to a percentile (reference) and an extreme.
    """
    try:
        dentro_fora = ("Dentro" if (valor_atual >= extrema if inverter else valor_atual <= extrema) else "Fora")
        if inverter:
            comparacao = "Acima do Percentil" if valor_atual < referencia else ("Abaixo do Percentil" if valor_atual > referencia else "No Percentil")
        else:
            comparacao = "Abaixo do Percentil" if valor_atual < referencia else ("Acima do Percentil" if valor_atual > referencia else "No Percentil")
        return f"{dentro_fora}, {comparacao}"
    except Exception:
        return "Indefinido"

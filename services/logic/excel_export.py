from services.utils.file_io import salvar_resultados, salvar_json
import pandas as pd
import logging

# --- helpers defensivos -------------------------------------------------------

_ALIASES = {
    # padronização (nomes “novos” -> nomes legados que o export espera)
    "Resultado Simulado Padronizado Bruto":        "pl_bruto_padronizado",
    "Resultado Simulado Padronizado Líquido":      "pl_liquido_padronizado",
    "Resultado Simulado Padronizado Bruto Acumulado":   "pl_bruto_acumulado",
    "Resultado Simulado Padronizado Líquido Acumulado": "pl_liquido_acumulado",
    "Taxas Acumuladas Padronização":               "custos_operacionais_acumulados",
}

_DEFAULTS = {
    # validação/diferenças
    "Diferença": 0.0,
    "Desvio_Diferença_vs_Deslocamento": 0.0,
    "Alerta_Divergência_Diferença": False,
    # métricas de lucro (caso módulo ainda não tenha preenchido)
    "Lucro Acumulado": 0.0,
    "Média das Máximas dos Lucros": 0.0,
    "Percentil 25 das Máximas dos Lucros": 0.0,
    "Posição Relativa Lucro": 0.0,
    # automação
    "Ativação Automação": False,
    # fluxo (sequências podem não existir em alguns caminhos)
    "Sequencia_Valores_Emprestados": [],
    "Sequencia_Valores_Recebidos": [],
}

def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for legado, novo in _ALIASES.items():
        if legado not in df.columns and novo in df.columns:
            df[legado] = df[novo]
    return df

def _ensure_cols(df: pd.DataFrame, defaults: dict) -> pd.DataFrame:
    df = df.copy()
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
            logging.warning("Export: coluna '%s' ausente — criada com default=%r", col, val)
    return df

def _safe_slice(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    cols_exist = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        logging.warning("Export: colunas ausentes ignoradas: %s", missing)
    return df[cols_exist].copy()

# --- função principal ---------------------------------------------------------

def salvar_arquivos_resultados(self, df: pd.DataFrame):
    # dump bruto “pré-padronização”
    salvar_resultados(df, caminho='outputs/prepadronizacao.csv')

    # compat + defaults p/ não quebrar fatias
    df = _apply_aliases(df)
    df = _ensure_cols(df, _DEFAULTS)

    # 1) estratégia padronizada
    colunas_padronizadas = [
        'Diferença',
        'Resultado Simulado Padronizado Bruto',
        'Resultado Simulado Padronizado Bruto Acumulado',
        'Resultado Simulado Padronizado Líquido',
        'Resultado Simulado Padronizado Líquido Acumulado',
        'Taxas Acumuladas Padronização',
        'Desvio_Diferença_vs_Deslocamento',
        'Alerta_Divergência_Diferença',
    ]
    df_padronizado = _safe_slice(df, colunas_padronizadas)
    salvar_resultados(df_padronizado, caminho='outputs/estrategiapadronizada.csv')

    # 2) fluxo calculado
    colunas_fluxo = [
        'ID Operação', 'Caixa Líquido', 'Dívida Acumulada',
        'Valor Emprestado', 'Amortização', 'Lucro Gerado',
        'Sequencia_Valores_Emprestados', 'Sequencia_Valores_Recebidos',
        'Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
        'Posição Relativa Dívida', 'Percentil 25 das Máximas Dívidas',
        'ID Ciclo',  # útil para análises paralelas
    ]
    df_fluxo = _safe_slice(df, colunas_fluxo)
    salvar_resultados(df_fluxo, caminho='outputs/fluxocalculado.csv')

    # 3) JSONs de resumos (já prontos no orchestrator)
    salvar_json(getattr(self, "resumo_ciclos_drawdown", []), "outputs/resumo_ciclos_divida.json")
    salvar_json(getattr(self, "resumo_ciclos_lucro", []), "outputs/resultados_ciclos_lucro.json")

    # 4) resultados finais (cards do painel)
    colunas_resultados_finais = [
       'Dívida Acumulada', 'Valor Emprestado', 'Amortização', 'Lucro Gerado',
       'Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
       'Percentil 25 das Máximas Dívidas', 'Posição Relativa Dívida',
       'Lucro Acumulado', 'Média das Máximas dos Lucros',
       'Percentil 25 das Máximas dos Lucros', 'Posição Relativa Lucro',
       'Ativação Automação'
    ]
    df_insight = _safe_slice(df, colunas_resultados_finais)
    salvar_resultados(df_insight, caminho='outputs/InsightFuturesResults.csv', formatar_monetarios=True)

    # 5) posições relativas (para gráficos/efeitos visuais rápidos)
    colunas_prs = ['ID Operação', 'Máxima Dívida Acumulada', 'Média das Máximas Dívidas', 'Posição Relativa Dívida']
    df_pr = _safe_slice(df, colunas_prs)
    salvar_resultados(df_pr, caminho='outputs/posicoesrelativas.csv')

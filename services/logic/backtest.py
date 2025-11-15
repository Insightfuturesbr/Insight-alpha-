# arquivo: backtest.html
import pandas as pd
from services.processing.fluxo_financeiro import calcular_fluxo_estrategia, calcular_maxima_media_e_posicao_relativa
from services.analysis.endividamento import adicionar_fluxo_por_ciclo_linha_a_linha
from services.analysis.lucro import adicionar_metricas_lucro_linha_a_linha
from services.logic.simulator import simular_ciclo

import logging                      
logger = logging.getLogger(__name__)


def recalcular_fluxo_apos_ativacao(df_backtest):
    df_ativado = df_backtest[df_backtest['Estado Automação'] == 'ativada'].copy()

    if df_ativado.empty:
        logger.warning("⚠️ Nenhuma operação ativada nesse ciclo. Retornando dataframe None.")
        return None

    df_simulado = df_ativado[['Resultado Simulado Padronizado Líquido']].copy()
    df_simulado['Resultado Simulado Padronizado Líquido Acumulado'] = df_simulado['Resultado Simulado Padronizado Líquido'].cumsum()

    df_simulado = calcular_fluxo_estrategia(df_simulado)
    df_simulado = adicionar_fluxo_por_ciclo_linha_a_linha(df_simulado)
    df_simulado = calcular_maxima_media_e_posicao_relativa(df_simulado)
    df_simulado = adicionar_metricas_lucro_linha_a_linha(df_simulado)

    logger.info("✅ Recalculo completo gerado com base nas operações ativadas.")
    return df_simulado


def calcular_metricas_backtest(df, usar_so_ativadas=False):
    if df is None:
        return {
            'resultado_liquido_final': 0,
            'drawdown_maximo': 0,
            'maior_lucro_acumulado': 0,
            'n_operacoes_automacao_ativada': 0,
            'n_operacoes_positivas': 0,
            'n_operacoes_negativas': 0,
            'n_operacoes_amortizacao': 0,
            'soma_lucro_gerado': 0,
            'soma_valor_emprestado': 0,
            'soma_amortizacao': 0
        }
        
    if usar_so_ativadas and 'Ativação Automação' in df.columns:
        df = df[df['Ativação Automação'] == True]

    if df.empty:
        return {
            'resultado_liquido_final': 0,
            'drawdown_maximo': 0,
            'maior_lucro_acumulado': 0,
            'n_operacoes_automacao_ativada': 0,
            'n_operacoes_positivas': 0,
            'n_operacoes_negativas': 0,
            'n_operacoes_amortizacao': 0,
            'soma_lucro_gerado': 0,
            'soma_valor_emprestado': 0,
            'soma_amortizacao': 0
        }

    metricas = {
        'resultado_liquido_final': round(df['Resultado Simulado Padronizado Líquido Acumulado'].iloc[-1], 2),
        'drawdown_maximo': round(df['Dívida Acumulada'].min(), 2),
        'maior_lucro_acumulado': round(df['Resultado Simulado Padronizado Líquido Acumulado'].max(), 2),
        'n_operacoes_automacao_ativada': df.shape[0],
        'n_operacoes_positivas': df[df['Lucro Gerado'] > 0].shape[0],
        'n_operacoes_negativas': df[df['Valor Emprestado'] < 0].shape[0],
        'n_operacoes_amortizacao': df[df['Amortização'] > 0].shape[0],
        'soma_lucro_gerado': round(df['Lucro Gerado'].sum(), 2),
        'soma_valor_emprestado': round(df['Valor Emprestado'].sum(), 2),
        'soma_amortizacao': round(df['Amortização'].sum(), 2)
    }
    return metricas


def comparar_ciclos(df_pre, df_backtest, temp_path=""):
    comparativo = []
    ciclos = df_pre['ID Dívida'].unique()

    for ciclo in ciclos:
        df_pre_ciclo = df_pre[df_pre['ID Dívida'] == ciclo]
        df_back_ciclo = df_backtest[df_backtest['ID Dívida'] == ciclo]

        if df_back_ciclo.empty:
            continue

        inicio = df_back_ciclo.index[0]
        fim = df_back_ciclo.index[-1]

        estados = df_back_ciclo['Estado Automação'].unique().tolist()
        motivos = df_back_ciclo['Motivo da Troca'].unique().tolist()

        comparativo.append({
            'Ciclo': ciclo,
            'Inicio': str(inicio),
            'Fim': str(fim),
            'Estados únicos': estados,
            'Motivos únicos': motivos,
            'Quantidade Linhas PreBack': df_pre_ciclo.shape[0],
            'Quantidade Linhas Backtest': df_back_ciclo.shape[0]
        })

    df_comp = pd.DataFrame(comparativo)

    if temp_path:
        df_comp.to_csv(f"{temp_path}/comparativo_ciclos.csv", index=False)
        logger.info("✅ Comparativo de ciclos salvo em %s/comparativo_ciclos.csv", temp_path)

    return df_comp

def executar_backtest_completo(df_prebacktest, parametros_usuario: dict, temp_path: str = "", salvar_resultados=True):
    from services.logic.save_data import salvar_json
    import os
    from services.utils.formatters import converter_valores_json_serializaveis

    df_prebacktest['Condicao Processada'] = False

    # Passa temp_path para permitir que o simulador carregue as bases fixas do disco
    df_backtest = simular_ciclo(df_prebacktest.copy(), parametros_usuario, temp_path)

    df_backtest['Troca de Estado'] = df_backtest['Motivo da Troca'].ne('Mantém estado')
    df_backtest['Troca de Estado Shiftada'] = df_backtest['Troca de Estado'].shift(1, fill_value=False)
    df_backtest['Estado Final'] = df_backtest['Estado Automação']

    for i in range(1, len(df_backtest)):
        if df_backtest['Troca de Estado Shiftada'].iloc[i]:
            df_backtest.at[df_backtest.index[i], 'Estado Final'] = df_backtest['Estado Automação'].iloc[i - 1]

    df_backtest['Estado Automação'] = df_backtest['Estado Final']
    df_backtest.drop(columns=['Troca de Estado', 'Troca de Estado Shiftada', 'Estado Final'], inplace=True)

    df_backtest_recalculado = recalcular_fluxo_apos_ativacao(df_backtest)

    metricas_original = calcular_metricas_backtest(df_prebacktest)
    metricas_backtest = calcular_metricas_backtest(df_backtest_recalculado, usar_so_ativadas=True)

    df_comparativo = comparar_ciclos(df_prebacktest, df_backtest, temp_path)



    if salvar_resultados and temp_path:
        salvar_json(converter_valores_json_serializaveis(metricas_backtest), os.path.join(temp_path, "metricas_backtest.json"))
        salvar_json(converter_valores_json_serializaveis(metricas_original), os.path.join(temp_path, "metricas_original.json"))
        if df_backtest_recalculado is not None:
            df_backtest_recalculado.to_json(os.path.join(temp_path, "resultado_backtest.json"), orient="split", force_ascii=False)
        if df_comparativo is not None:
            df_comparativo.to_json(os.path.join(temp_path, "comparativo_ciclos.json"), orient="split", force_ascii=False)

    return df_backtest_recalculado, metricas_backtest, metricas_original


def gerar_frase_insight(parametros, metricas):
    """
    Gera o texto do Dr. Drawdown explicando a parametrização.

    parametros: dict com as margens e condições definidas pelo usuário
    metricas: dict com as médias e máximos históricos da estratégia carregada
    """

    risco_maximo = f"R$ {metricas['drawdown_maximo_simulado']:.2f}"
    meta_lucro = f"R$ {metricas['meta_lucro_simulado']:.2f}"

    frase = f"""
    💡 <strong>Com os parâmetros escolhidos, você está ajustando a automação para assumir um risco máximo de {risco_maximo},</strong> buscando um alvo de lucro de {meta_lucro}, com base nos dados históricos da sua estratégia.

    As condições definidas são:

    🔹 <strong>Ativar automação</strong> quando o drawdown atingir <strong>{parametros['ativar_percentual']}%</strong> acima de <strong>{parametros['base_drawdown_ativar']}</strong>.

    🔹 <strong>Pausar automação</strong> quando o lucro atingir <strong>{parametros['pausar_percentual']}%</strong> acima de <strong>{parametros['base_lucro_pausar']}</strong>.

    🔹 <strong>Desativar automação</strong> se o drawdown atingir <strong>{parametros['desativar_percentual']}%</strong> acima de <strong>{parametros['base_drawdown_desativar']}</strong>.

    ⚙️ <em>Esses ajustes definem os ciclos de risco e retorno da sua estratégia no próximo período.</em>
    """
    return frase

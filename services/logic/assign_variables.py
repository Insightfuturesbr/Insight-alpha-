import logging
from services.features_engineering.features import selecionar_colunas_essenciais
from services.processing.fluxo_financeiro import (calcular_estatisticas_painel_a_partir_df, construir_resumo_ciclos_fases)
from services.analysis.endividamento import  extrair_fluxo_final_por_ciclo
from services.input.ativos import (analisar_ativos, identificar_parametros_por_ativo)
from services.analysis.resumo_variaveis import (obter_variaveis_pre_padronizacao, obter_variaveis_padronizacao, obter_variaveis_fluxo,
                                                classificar_e_contar_resultados)
from services.analysis.endividamento import (gerar_resumo_e_dataframe_ciclos_divida, obter_estatisticas_duracao_ciclos)
from visual.graficos_plotly import gerar_grafico_fluxo_caixa
from services.analysis.lucro import  resumir_ciclos_lucro_real, gerar_resumo_e_dataframe_ciclos_lucro
from services.analysis.completo import gerar_dataframe_completo

def atribuir_variaveis_ao_insight(self, df):
    self.variaveis_pre = obter_variaveis_pre_padronizacao(df)
    self.variaveis_padronizacao = obter_variaveis_padronizacao(df)
    self.variaveis_fluxo = obter_variaveis_fluxo(df)

    # Lista de ativos detectados
    self.ativos = analisar_ativos(df) or []

    # usa o primeiro ativo válido para parametrização global
    if isinstance(self.ativos, str):
        ativo_principal = self.ativos
    elif isinstance(self.ativos, list) and self.ativos:
        ativo_principal = self.ativos[0]
    else:
        ativo_principal = ""

    # normaliza ticker
    self.ativo = ativo_principal.replace("[R] ", "").strip().upper()

    # parâmetros do ativo escolhido
    self.parametros_ativo = identificar_parametros_por_ativo(self.ativo)


    self.resultados_fluxo_ciclo = extrair_fluxo_final_por_ciclo(df)

    self.estatisticas_ciclo_emprestimo = calcular_estatisticas_painel_a_partir_df(df, 'emprestimo_acumulado_ciclo')
    self.estatisticas_ciclo_amortizacao = calcular_estatisticas_painel_a_partir_df(df, 'amortizacao_acumulada_ciclo')
    self.estatisticas_ciclo_lucro = calcular_estatisticas_painel_a_partir_df(df, 'lucro_acumulado_ciclo')

    self.estats_qtd_emp_ciclo = calcular_estatisticas_painel_a_partir_df(df, 'qtd_emprestimos_ciclo')
    self.estats_qtd_amo_ciclo = calcular_estatisticas_painel_a_partir_df(df, 'qtd_amortizacoes_ciclo')
    self.estats_qtd_luc_ciclo = calcular_estatisticas_painel_a_partir_df(df, 'qtd_lucros_ciclo')

    self.resumo_ciclos_drawdown, self.ciclos_drawdown = gerar_resumo_e_dataframe_ciclos_divida(df)

    self.ultimo_ciclo = self.resumo_ciclos_drawdown[-1] if self.resumo_ciclos_drawdown else {}
    df, metricas = classificar_e_contar_resultados(
        df, coluna_resultado='Resultado Simulado Padronizado Líquido'
    )
    # depois de montar self.ciclos_drawdown (lista/dict) a partir do detector de ciclos:
    import pandas as pd
    from services.processing.fluxo_financeiro import contagens_para_resumo, contar_operacoes_por_fase,  construir_resumo_ciclos_fases

    df_ciclos = pd.DataFrame(self.ciclos_drawdown)

    # conte por datas (sem idx)
    df_ciclos_contado = contar_operacoes_por_fase(
        self.data,
        df_ciclos,
        coluna_datetime=("Abertura" if "Abertura" in self.data.columns else
                         "DataHora" if "DataHora" in self.data.columns else None),
        coluna_acumulado=("Resultado Líquido Total Acumulado"
                          if "Resultado Líquido Total Acumulado" in self.data.columns else
                          "Resultado Simulado Padronizado Líquido Acumulado"
                          if "Resultado Simulado Padronizado Líquido Acumulado" in self.data.columns else
                          "Caixa Líquido")
    )

    self.df_ciclos_drawdown = df_ciclos_contado
    self.ciclos_drawdown = df_ciclos_contado.to_dict(orient="records")

    # (se você também enriquece o resumo com as 6 datas/durações:)
    resumo_base_df = pd.DataFrame(self.resumo_ciclos_drawdown)
    resumo_fases_df = construir_resumo_ciclos_fases(
        df_base=self.data,
        df_ciclos=self.df_ciclos_drawdown,
        coluna_datetime=("Abertura" if "Abertura" in self.data.columns else
                         "DataHora" if "DataHora" in self.data.columns else None),
        coluna_acumulado=("Resultado Líquido Total Acumulado"
                          if "Resultado Líquido Total Acumulado" in self.data.columns else
                          "Resultado Simulado Padronizado Líquido Acumulado"
                          if "Resultado Simulado Padronizado Líquido Acumulado" in self.data.columns else
                          "Caixa Líquido"),
        resumo_antigo=resumo_base_df
    )

    # mesclar as CONTAGENS no resumo
    contagens_df = contagens_para_resumo(self.df_ciclos_drawdown)
    resumo_final_df = resumo_fases_df.merge(
        contagens_df.assign(**{
            "ID Ciclo": pd.to_numeric(contagens_df["ID Ciclo"], errors="coerce").astype("Int64")
        }),
        on="ID Ciclo", how="left"
    )

    self.resumo_ciclos_drawdown = resumo_final_df.to_dict(orient="records")


    # 🔸 guarda tudo num único atributo
    self.metricas_positivas_negativas = metricas

    # quantidades
    self.qtd_positivas = metricas["qtd_positivas"]
    self.qtd_negativas = metricas["qtd_negativas"]
    self.qtd_neutras = metricas["qtd_neutras"]

    # porcentagens
    self.pct_positivas = metricas["pct_positivas"]
    self.pct_negativas = metricas["pct_negativas"]
    self.pct_neutras = metricas["pct_neutras"]

    # somas
    self.soma_positivas = metricas["soma_positivas"]
    self.soma_negativas = metricas["soma_negativas"]
    self.soma_neutras = metricas["soma_neutras"]

    # médias
    self.media_positivas = metricas["media_positivas"]
    self.media_negativas = metricas["media_negativas"]

    # percentis
    self.perc_positivas = metricas["perc75_positivas"]
    self.perc_negativas = metricas["perc25_negativas"]

    self.estatisticas_duracao_ciclos = obter_estatisticas_duracao_ciclos(self.resumo_ciclos_drawdown)

    #Atruir graficos
    self.grafico_json = gerar_grafico_fluxo_caixa(df)

    self.resumo_ciclos_lucro, self.df_ciclos_lucro = (
        gerar_resumo_e_dataframe_ciclos_lucro(self.data)
    )
    self.resumo_lucros_estatisticos = resumir_ciclos_lucro_real(self.df_ciclos_lucro)

    self.df_completo = gerar_dataframe_completo(df)

    self.df_prebacktest= selecionar_colunas_essenciais(df)

    # Temporary debug logs for drawdown screen (restored)
    logging.info("--- DEBUGGING DRAWDOWN SCREEN ---")
    logging.info("resumo_ciclos_drawdown: %s", self.resumo_ciclos_drawdown)
    logging.info("resumo_ciclos_lucro: %s", self.resumo_ciclos_lucro)
    logging.info("df_completo: %s", getattr(self, 'df_completo', None).head() if hasattr(self, 'df_completo') else None)
    logging.info("ultimo_ciclo: %s", self.ultimo_ciclo)
    logging.info("--- END DEBUGGING ---")

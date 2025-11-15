# app/core/orchestrator.py

import os
import logging


from services.processing.preprocessing import (
    definir_indice_e_datas,
    criar_colunas_operacoes, limpar_colunas_desnecessarias)
from services.processing.standardization import (
    padronizar_estrategia,
    identificar_diferenca_com_validacao,  # alias para validar_delta
)

from services.processing.header_detector import detect_and_normalize_headers

from services.processing.fluxo_financeiro import (
    calcular_fluxo_estrategia,
    calcular_maxima_media_e_posicao_relativa,
)

# Estes módulos podem ser opcionais no teu ambiente atual; mantém se existirem.
from services.analysis.endividamento import (
    adicionar_fluxo_por_ciclo_linha_a_linha,
)
from services.analysis.lucro import (
    adicionar_metricas_lucro_linha_a_linha,
)

from services.input.leitura import ler_arquivo_financeiro
from services.input.escrita import valida_periodo_minimo

from services.logic.assign_variables import atribuir_variaveis_ao_insight
from services.logic.excel_export import salvar_arquivos_resultados
from services.logic.backtest import executar_backtest_completo
from services.logic.save_data import salvar_todos_resultados, salvar_resultados_backtest


# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class InsightFutures:
    def __init__(self, file_path, contratos_usuario=None):
        logging.info("🚀 Entrou na classe InsightFutures!")

        self.file_path = file_path
        logging.info("🚀 Arquivo armazenado com sucesso!")

        self.temp_path = "temp"
        os.makedirs(self.temp_path, exist_ok=True)

        df = self.tratar_planilha(contratos_usuario=contratos_usuario)
        logging.info("🚀 Planilha tratada pela função tratar_planilha!")

        self.data = df
        logging.info("🚀 Dataframe armazenado em Data!")

        atribuir_variaveis_ao_insight(self, self.data)

        salvar_todos_resultados(self, self.temp_path)
        salvar_arquivos_resultados(self, df)

        # depois de salvar_todos_resultados(...) e salvar_arquivos_resultados(...)
        try:
            from scripts.validate_outputs import validate_outputs_dir
            relatorio = validate_outputs_dir(self.temp_path)
            for linha in relatorio:
                # usa INFO pros OK/skip e WARNING pros FAIL
                (logging.warning if linha.startswith("[FAIL]") else logging.info)(linha)
        except Exception as e:
            logging.warning("Validação por JSON Schema não executada: %s", e)

    def tratar_planilha(self, contratos_usuario=None):
        logging.info("Iniciando processamento do arquivo...")

        if not os.path.exists(self.file_path):
            logging.error("⚠️ ERRO: O arquivo '%s' não foi encontrado.", self.file_path)
            return None

        # 1) Leitura
        df = ler_arquivo_financeiro(self.file_path)
        df = definir_indice_e_datas(df, dayfirst=True)
        df = limpar_colunas_desnecessarias(df, keep_extra=["Lado"])
        print(df.columns)

        valida_periodo_minimo(df, min_dias=15)

        out = criar_colunas_operacoes(df)
        if isinstance(out, tuple):
            df, _params_pre = out
        else:
            df, _params_pre = out, None


        # 3) Padronização (também garante que vem DataFrame)
        out = padronizar_estrategia(df, contratos_usuario)
        if isinstance(out, tuple):
            df, parametros = out
        else:
            df = out
            parametros = None

        df = identificar_diferenca_com_validacao(df)


        # guarda um snapshot “pré-backtest” se o teu fluxo precisar depois
        self.df_prebacktest = df.copy()

        # 4) Fluxo Financeiro
        df = calcular_fluxo_estrategia(df)

        # métricas por ciclo linha a linha (se o módulo estiver presente)
        try:
            df = adicionar_fluxo_por_ciclo_linha_a_linha(df)
        except Exception as e:
            logging.warning("Endividamento opcional não aplicado: %s", e)

        # 5) Métricas complementares
        df = calcular_maxima_media_e_posicao_relativa(df)

        try:
            df = adicionar_metricas_lucro_linha_a_linha(df)
        except Exception as e:
            logging.warning("Métricas de lucro opcionais não aplicadas: %s", e)

        return df

    def rodar_backtest_completo(self, parametros_usuario: dict):
        """
        Executa o backtest completo: regras de ativação, fluxo financeiro e métricas.
        Atribui os resultados a atributos do objeto e salva os arquivos resultantes.
        """
        self.df_backtest, self.metricas_backtest, self.metricas_original = executar_backtest_completo(
            getattr(self, "df_prebacktest", self.data),  # ⚠️ fallback se não existir
            parametros_usuario,
            temp_path=self.temp_path,
        )
        salvar_resultados_backtest(self, self.temp_path)

    def recalcular_com_novos_contratos(self, contratos_usuario):
        from services.processing.standardization import padronizar_estrategia
        from services.processing.fluxo_financeiro import (
            calcular_fluxo_estrategia,
            calcular_maxima_media_e_posicao_relativa,
        )
        from services.analysis.endividamento import adicionar_fluxo_por_ciclo_linha_a_linha
        from services.analysis.lucro import adicionar_metricas_lucro_linha_a_linha
        from services.logic.assign_variables import atribuir_variaveis_ao_insight

        df, _ = padronizar_estrategia(self.data, contratos_usuario=contratos_usuario)
        self.df_prebacktest = df.copy()

        df = calcular_fluxo_estrategia(df)
        try:
            df = adicionar_fluxo_por_ciclo_linha_a_linha(df)
        except Exception:
            pass

        df = calcular_maxima_media_e_posicao_relativa(df)

        try:
            df = adicionar_metricas_lucro_linha_a_linha(df)
        except Exception:
            pass

        self.data = df
        atribuir_variaveis_ao_insight(self, df)
        logging.info("✅ Recalculo com novos contratos concluído.")

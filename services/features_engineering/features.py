# Arquivo: features.py
import pandas as pd
import logging

def selecionar_colunas_essenciais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mantém apenas as colunas essenciais para os modelos preditivos.
    :param df: DataFrame original.
    :return: DataFrame contendo apenas as colunas necessárias.
    """
    try:
        colunas_essenciais = ['Resultado Simulado Padronizado Líquido', 'Resultado Simulado Padronizado Líquido Acumulado','Dívida Acumulada', 'Valor Emprestado', 'emprestimo_acumulado_ciclo', 'Amortização','amortizacao_acumulada_ciclo', 'Lucro Gerado',
       'lucro_acumulado_ciclo','Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
       'Percentil 25 das Máximas Dívidas', 'Posição Relativa Dívida', 'Lucro Acumulado', 'Média das Máximas dos Lucros',
       'Percentil 25 das Máximas dos Lucros', 'Posição Relativa Lucro', 'Ativação Automação', 'ID Dívida', 'ID Operação']

        # 📌 Verifica se todas as colunas necessárias existem no DataFrame
        colunas_existentes = [col for col in colunas_essenciais if col in df.columns]

        if not colunas_existentes:
            logging.error("⚠️ ERRO: Nenhuma coluna essencial encontrada. Retornando DataFrame original.")
            return df

        df = df[colunas_existentes]
        logging.info("✅ DataFrame reduzido para colunas essenciais.")

        return df

    except Exception as e:
        logging.error("⚠️ ERRO ao selecionar colunas essenciais: %s", e)
        return df


def criar_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria as colunas defasadas (lag features) para garantir que o modelo só veja informações do passado.
    :param df: DataFrame com as features calculadas.
    :return: DataFrame atualizado com as lag features.
    """
    try:
        if df.empty:
            logging.error("⚠️ ERRO: DataFrame está vazio.")
            return df

        # 🔹 Criando lag features para todas as colunas úteis
        colunas_lag = [
             'Dívida Acumulada', 'Valor Emprestado', 'Amortização', 'amortizacao_acumulada_ciclo', 'Lucro Gerado', 'lucro_acumulado_ciclo'
       'Máxima Dívida Acumulada', 'Média das Máximas Dívidas',
       'Percentil 25 das Máximas Dívidas', 'Posição Relativa Dívida', 'Ativação Automação']

        for col in colunas_lag:
            if col in df.columns:
                df[f"{col} Lag"] = df[col].shift(1)

        # Remover primeiras linhas com NaN devido ao shift
        df = df.dropna().reset_index(drop=True)

        logging.info("✅ Lag features criadas com sucesso.")
        return df

    except Exception as e:
        logging.error("⚠️ ERRO ao criar lag features: %s", e)
        return df



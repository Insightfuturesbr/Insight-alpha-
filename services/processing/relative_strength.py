def calcular_forcas_financeiras(df):
    """
    Calcula métricas avançadas de controle da dívida com base no ID Operação:
    - Empréstimo → Força de Endividamento (%)
    - Amortização → Força de Recuperação (%)
    - Lucro Real → Força de Acumulação (%)
    """

    # Criar uma cópia do DataFrame para evitar problemas de views
    df = df.copy()

    # Criar novas colunas
    df.loc[:, 'Força_Endividamento_%'] = 0.00
    df.loc[:, 'Força_Recuperação_%'] = 0.00
    df.loc[:, 'Força_Acumulação_%'] = 0.00
    df.loc[:, 'Lucro_Gerado_Cumulativo'] = 0.00

    # Variáveis para armazenar valores acumulados
    lucro_acumulado = 0
    total_emprestimos = 0
    total_amortizacoes = 0

    logging.info("✅ Iniciando o cálculo das forças financeiras com base no ID Operação...")

    for i in range(len(df)):
        try:
            # Verificar se o ID Operação existe
            if 'ID Operação' not in df.columns:
                logging.error("🚨 ERRO: A coluna 'ID Operação' não foi encontrada no DataFrame.")
                return df

            id_operacao = df.loc[i, 'ID Operação']
            tipo_operacao = identificar_tipo_operacao(id_operacao)

            # Garantir que só acessamos `i-1` se `i > 0`
            divida_anterior = df.loc[i - 1, 'Dívida Acumulada'] if i > 0 else df.loc[i, 'Dívida Acumulada']

            # Evitar divisão por zero
            if divida_anterior == 0:
                logging.warning(f"Linha {i}: Dívida acumulada anterior é 0, ajustando para 1 para evitar erro de divisão.")
                divida_anterior = 1

            # Determinar valores da linha
            valor_emprestado = df.loc[i, 'Valor Emprestado']
            amortizacao = df.loc[i, 'Amortização']
            lucro_gerado = df.loc[i, 'Lucro Gerado']

            # 📌 Calcular conforme o tipo de operação
            if tipo_operacao == "Emprestimo" and valor_emprestado > 0:
                total_emprestimos += valor_emprestado
                df.loc[i, 'Força_Endividamento_%'] = round((total_emprestimos / divida_anterior) * 100, 2)

            elif tipo_operacao == "Amortizacao" and amortizacao > 0:
                total_amortizacoes += amortizacao
                df.loc[i, 'Força_Recuperação_%'] = round((total_amortizacoes / divida_anterior) * 100, 2)

            elif tipo_operacao == "Lucro" and lucro_gerado > 0:
                lucro_acumulado += lucro_gerado
                df.loc[i, 'Lucro_Gerado_Cumulativo'] = round(lucro_acumulado, 2)
                df.loc[i, 'Força_Acumulação_%'] = round((lucro_acumulado / divida_anterior) * 100, 2)

        except KeyError as e:
            logging.error(f"Linha {i}: Erro ao acessar uma coluna. Verifique os dados. {e}")
        except Exception as e:
            logging.error(f"Linha {i}: Erro inesperado ao calcular forças financeiras. {e}")

    logging.info("✅ Cálculo das forças financeiras concluído com sucesso!")

    return df



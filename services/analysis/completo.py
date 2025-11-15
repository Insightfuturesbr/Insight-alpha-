import pandas as pd

def gerar_dataframe_completo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria um dataframe combinado com informações de lucro e dívida.
    """
    colunas_selecionadas = [
        'ID Operação',
        'Dívida Acumulada',
        'Lucro Gerado',
        'emprestimo_acumulado_ciclo',
        'amortizacao_acumulada_ciclo',
        'lucro_acumulado_ciclo',
        'qtd_emprestimos_ciclo',
        'qtd_amortizacoes_ciclo',
        'qtd_lucros_ciclo',
        'ciclo',
        'Lucro Acumulado',
        'Média das Máximas dos Lucros',
        'Percentil 25 das Máximas dos Lucros',
        'Posição Relativa Lucro'
    ]
    
    # Filter out columns that are not in the dataframe
    colunas_existentes = [col for col in colunas_selecionadas if col in df.columns]
    
    df_combinado = df[colunas_existentes].copy()
    
    return df_combinado

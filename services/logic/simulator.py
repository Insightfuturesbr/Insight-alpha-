# arquivo: simulator.py

from services.logic.conditions import condicao_ativacao, condicao_pausa, condicao_desativacao


def calcular_bases_fixas(ultima_linha, temp_path):
    from services.utils.file_io import carregar_json

    estat_divida = carregar_json(temp_path, 'variaveis_fluxo.json')
    estat_lucro = carregar_json(temp_path, 'estatisticas_ciclos_lucro.json')

    bases_fixas = {
        'media_drawdown': estat_divida['media_das_maximas_dividas'],
        'percentil25_drawdown': estat_divida['perc25_das_maximas_dividas'],
        'maior_drawdown': ultima_linha['Máxima Dívida Acumulada'],  # Se quiser manter o drawdown atual
        'media_lucro': estat_lucro['media_lucros'],
        'percentil75_lucro': estat_lucro['percentil_75_lucros']
    }

    return bases_fixas



def processar_linha(row, estado_atual, parametros, bases_fixas, entrada_drawdown):
    divida = row['Dívida Acumulada']
    lucro = row['Lucro Gerado']

    novo_estado = estado_atual
    nova_entrada = entrada_drawdown
    motivo = 'Mantém estado'

    base_ativacao = bases_fixas.get(parametros["ativacao_base"], 0)
    base_pausa = bases_fixas.get(parametros["pausa_base"], 0)
    base_desativacao = bases_fixas.get(parametros["desativacao_base"], 0)

    if estado_atual == 'desativada':
        if condicao_ativacao(divida, base_ativacao, parametros):
            novo_estado = 'ativada'
            nova_entrada = divida
            motivo = '🔼 Ativada'

    elif estado_atual == 'ativada':
        if condicao_desativacao(divida, base_desativacao, parametros):
            novo_estado = 'desativada'
            nova_entrada = None
            motivo = '🔴 Desativada por risco'

        elif condicao_pausa(lucro, divida, entrada_drawdown, base_pausa, parametros, row):
            novo_estado = 'pausada'
            motivo = '🟡 Pausada'


    elif estado_atual == 'pausada':

        if condicao_desativacao(divida, base_desativacao, parametros):

            novo_estado = 'desativada'

            nova_entrada = None

            motivo = '🔴 Desligada em pausa'


        elif condicao_ativacao(divida, base_ativacao, parametros):

            novo_estado = 'ativada'

            nova_entrada = divida

            motivo = '🔁 Retomada por nova condição de ativação'

    return novo_estado, nova_entrada, motivo



def simular_ciclo(df, parametros, temp_path=None):
    estado = 'desativada'
    entrada_drawdown = None

    ultima_linha = df.iloc[-1]
    bases_fixas = calcular_bases_fixas(ultima_linha, temp_path)

    estados, motivos = [], []

    for idx, row in df.iterrows():
        estado, entrada_drawdown, motivo = processar_linha(row, estado, parametros, bases_fixas, entrada_drawdown)
        estados.append(estado)
        motivos.append(motivo)

    df['Estado Automação'] = estados
    df['Motivo da Troca'] = motivos

    return df

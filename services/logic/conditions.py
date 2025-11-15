
from typing import Any, Tuple

def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)

def _get_param(d: dict, key: str, default: float = 0.0) -> float:
    if not isinstance(d, dict):
        return float(default)
    return _as_float(d.get(key, default), default)




def calcular_limite(valor_base, margem_percentual, comparador):
    if comparador == 'maior':
        return valor_base * (1 + margem_percentual / 100)
    elif comparador == 'menor':
        return valor_base * (1 - margem_percentual / 100)
    else:
        return valor_base  # Nenhum ajuste

def condicao_ativacao(divida_atual, base, parametros):
    limite = calcular_limite(base, parametros["ativacao_percentual"], parametros["comparador_ativacao"])

    if parametros["comparador_ativacao"] == "menor":
        return divida_atual < limite
    else:
        return divida_atual > limite
def condicao_pausa(lucro, divida, entrada_drawdown, base, parametros, row):
    base_nome = parametros["pausa_base"]

    if base_nome == "valor_recuperacao":
        return divida == 0

    elif base_nome == "alvo_simetrico":
        if entrada_drawdown is None:
            return False
        return lucro >= abs(entrada_drawdown) * 2

    elif base_nome == "amortizacao_entrada":
        if entrada_drawdown is None:
            return False
        if "Amortizacao Backtest" not in row or "Máxima Dívida Acumulada" not in row:
            return False

        maior_drawdown_do_ciclo = row["Máxima Dívida Acumulada"]
        ativacao = entrada_drawdown
        necessario_amortizar = (maior_drawdown_do_ciclo - ativacao) + abs(ativacao)

        return row["Amortizacao Backtest"] >= necessario_amortizar

    else:
        limite = calcular_limite(base, parametros["pausa_percentual"], parametros["comparador_pausa"])
        if parametros["comparador_pausa"] == "menor":
            return lucro < limite
        else:
            return lucro > limite

def condicao_desativacao(divida_atual, base, parametros):
    limite = calcular_limite(base, parametros["desativacao_percentual"], parametros["comparador_desativacao"])

    if parametros["comparador_desativacao"] == "maior":
        return divida_atual > limite
    else:
        return divida_atual < limite

# --- decisão consolidada para consumo pelo painel/HTMX ---

def decidir_estado_atual(
    divida_atual: float,
    lucro_atual: float,
    entrada_drawdown: float,
    base_ativacao: float,
    base_pausa: float,
    base_desativacao: float,
    parametros: dict,
    row=None
) -> Tuple[str, str]:
    """
    Retorna (recomendacao, motivo).
    Prioridade: DESLIGAR > PAUSAR > ATIVAR > MANTER

    Parâmetros
    ----------
    divida_atual         : valor atual da dívida (pode ser negativo)
    lucro_atual          : lucro acumulado no ciclo atual (ou total)
    entrada_drawdown     : referência (ex.: último topo / entrada do ciclo)
    base_ativacao        : limiar para ativação (ex.: p25/p50 da dívida ou critério seu)
    base_pausa           : limiar para pausar (ex.: p90/p95 de lucro)
    base_desativacao     : limiar para desligar (ex.: p95 de dívida)
    parametros           : dicionário com parâmetros adicionais já usados nas suas condições
    row                  : linha/registro bruto opcional (compat com sua condicao_pausa)

    Observação: esta função apenas orquestra suas condições já existentes,
    sem alterar a lógica interna de cada uma.
    """
    try:
        d_atual  = _as_float(divida_atual)
        l_atual  = _as_float(lucro_atual)
        ent_dd   = _as_float(entrada_drawdown)
        b_ativa  = _as_float(base_ativacao)
        b_pausa  = _as_float(base_pausa)
        b_deslig = _as_float(base_desativacao)

        # 1) DESLIGAR tem prioridade máxima (segurança)
        try:
            if condicao_desativacao(d_atual, b_deslig, parametros):
                return "DESLIGAR", "Dívida excedeu limite de segurança (base_desativacao)."
        except NameError:
            # Se a função tiver outro nome no seu arquivo, ajuste aqui.
            pass

        # 2) PAUSAR (proteção de lucro/topo)
        try:
            if condicao_pausa(l_atual, d_atual, ent_dd, b_pausa, parametros, row):
                return "PAUSAR", "Proteção de lucro ou proximidade de topo (base_pausa)."
        except NameError:
            pass

        # 3) ATIVAR (fim de declínio / recuperação favorável)
        try:
            if condicao_ativacao(d_atual, b_ativa, parametros):
                return "ATIVAR", "Condição de ativação atendida (base_ativacao)."
        except NameError:
            pass

        # 4) Caso nenhum gatilho dispare
        return "MANTER", "Sem gatilhos atendidos no momento."

    except Exception as e:
        # Nunca quebrar o painel; retornar estado neutro com motivo
        return "MANTER", f"Falha ao decidir estado: {e}"
def decidir_estado_a_partir_df(df, parametros: dict) -> Tuple[str, str]:
    """
    Lê a última linha do DF padronizado/fluxo e chama `decidir_estado_atual`.
    Ajuste os nomes das colunas conforme estiverem no seu DF.
    """
    try:
        if df is None or df.empty:
            return "MANTER", "Sem dados para decidir."

        row = df.iloc[-1]

        divida_atual     = row.get("Dívida Acumulada", 0.0)
        lucro_atual      = row.get("Lucro Gerado", 0.0)  # ajuste se você usa outro agregado
        entrada_drawdown = row.get("Entrada do Drawdown", 0.0)  # se não existir, deixe 0.0 ou derive

        # Bases/limiares que você já computa em colunas
        base_ativacao     = row.get("Percentil 25 das Máximas Dívidas", 0.0)
        base_pausa        = row.get("Percentil 95 Lucros", row.get("Posição Relativa Lucro", 0.0))
        base_desativacao  = row.get("Percentil 95 das Máximas Dívidas", row.get("Média das Máximas Dívidas", 0.0))

        return decidir_estado_atual(
            divida_atual=divida_atual,
            lucro_atual=lucro_atual,
            entrada_drawdown=entrada_drawdown,
            base_ativacao=base_ativacao,
            base_pausa=base_pausa,
            base_desativacao=base_desativacao,
            parametros=parametros,
            row=row,
        )
    except Exception as e:
        return "MANTER", f"Falha ao decidir a partir do DF: {e}"

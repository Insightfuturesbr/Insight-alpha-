# contracts/models.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, conint, confloat

# ---------------------------------------------------------------------
# Config base (Pydantic v2): impede chaves desconhecidas e permite usar aliases
# ---------------------------------------------------------------------
class StrictModel(BaseModel):
    model_config = {
        "extra": "forbid",               # recusa campos não definidos
        "populate_by_name": True,        # permite popular por nome do atributo
        "validate_assignment": True,     # valida ao atribuir após criar
    }

# ---------------------------------------------------------------------
# 1) variaveis_pre.json  (espelha 100% teu arquivo atual)
# ---------------------------------------------------------------------
class VariaveisPreV1(StrictModel):
    total_operacoes: conint(ge=0)
    periodo: str
    contratos_media: float
    contratos_max: float
    contratos_soma: float

    resultado_liquido_acumulado: float
    resultado_bruto: float
    resultado_acumulado_pontos: float
    taxas: float

    percentual_liquido: confloat(ge=0, le=100)
    percentual_taxas: confloat(ge=0, le=100)
    percentual_restante: confloat(ge=0, le=100)

    # Objeto com 5 chaves: multiplicador, taxa, deslocamento_min, valor_por_ponto, contratos
    parametros_ativos: dict
    resultado_liquido_media: float

# ---------------------------------------------------------------------
# 2) variaveis_fluxo.json  (espelha 100% teu arquivo atual)
# ---------------------------------------------------------------------
class VariaveisFluxoV1(StrictModel):
    caixa_liquido_atual: float
    divida_acumulada: float
    valor_emprestado: float
    amortizacao: float
    lucro_gerado: float
    total_taxas_simuladas: float

    maxima_divida: float
    media_das_maximas_dividas: float
    perc25_das_maximas_dividas: float
    posicao_relativa_final: float
    destaque: str

    qtde_emprestado: conint(ge=0)
    qtde_amortizacao: conint(ge=0)
    qtde_lucro: conint(ge=0)
    total_linhas: conint(ge=0)

    perc_emprestado: float
    perc_amortizacao: float
    perc_lucro: float

# ---------------------------------------------------------------------
# 3) ultimo_ciclo.json  (objeto simples com chaves PT-BR)
#    Usamos aliases para aceitar chaves com espaço/acentos.
# ---------------------------------------------------------------------
class UltimoCicloV1(StrictModel):
    id_ciclo: conint(ge=1) = Field(alias="ID Ciclo")
    data_inicio: str = Field(alias="Data Início")
    data_fim: str = Field(alias="Data Fim")
    duracao_ciclo: str = Field(alias="Duração do Ciclo")

    maxima_divida_do_ciclo: float = Field(alias="Máxima Dívida do Ciclo")
    media_maximas_ate_o_ciclo: float = Field(alias="Média Máximas Até o Ciclo")
    percentil_75_maximas_ate_o_ciclo: float = Field(alias="Percentil 75 Máximas Até o Ciclo")

# ---------------------------------------------------------------------
# 4) ciclos_drawdown.json  (lista de objetos; este é o item)
# ---------------------------------------------------------------------
class CicloDrawdownItemV1(StrictModel):
    id_ciclo: conint(ge=1) = Field(alias="ID Ciclo")
    data_inicio: str = Field(alias="Data Início")
    data_fim: str = Field(alias="Data Fim")
    duracao_ciclo: str = Field(alias="Duração do Ciclo")

    maxima_divida_do_ciclo: float = Field(alias="Máxima Dívida do Ciclo")
    media_maximas_ate_o_ciclo: float = Field(alias="Média Máximas Até o Ciclo")
    percentil_75_maximas_ate_o_ciclo: float = Field(alias="Percentil 75 Máximas Até o Ciclo")

    ops_declinio_total: conint(ge=0)
    emprestimos_declinio: conint(ge=0)
    amortizacoes_declinio: conint(ge=0)
    lucros_declinio: conint(ge=0)

    ops_recuperacao_total: conint(ge=0)
    emprestimos_recuperacao: conint(ge=0)
    amortizacoes_recuperacao: conint(ge=0)
    lucros_recuperacao: conint(ge=0)

# ---------------------------------------------------------------------
# 5) estatisticas_ciclo_*.json  (amortizacao / emprestimo / lucro)
#    Mesmo shape em todos: media, referencia_percentil, extrema, valor_atual, posicao_relativa, destaque
# ---------------------------------------------------------------------
class StatsCicloV1(StrictModel):
    media: float
    referencia_percentil: float
    extrema: float
    valor_atual: float
    posicao_relativa: float
    destaque: str

# ---------------------------------------------------------------------
# 6) Ativo(s) — hoje são formatos simples
#    - ativo.json   => string (símbolo)           -> validar com isinstance(…, str)
#    - ativos.json  => lista de strings (símbolos) -> validar com AtivosV1
# ---------------------------------------------------------------------
class AtivosV1(StrictModel):
    # Se você quiser validar exatamente o arquivo atual (lista "solta"),
    # pode validar com List[str] diretamente (ver exemplo de uso abaixo).
    symbols: List[str]

# ---------------------------------------------------------------------
# (Opcional) helper para validar listas "soltas" com pydantic:
# ---------------------------------------------------------------------
def validar_lista_simbolos(simbolos: List[str]) -> List[str]:
    # Garante que todos são strings não vazias
    if not isinstance(simbolos, list):
        raise TypeError("Esperado uma lista de strings.")
    for s in simbolos:
        if not isinstance(s, str) or not s.strip():
            raise ValueError(f"Símbolo inválido na lista: {s!r}")
    return simbolos

__all__ = [
    "VariaveisPreV1",
    "VariaveisFluxoV1",
    "UltimoCicloV1",
    "CicloDrawdownItemV1",
    "StatsCicloV1",
    "AtivosV1",
    "validar_lista_simbolos",
]

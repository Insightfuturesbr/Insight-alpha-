"""
PT:
Pacote de entrada (input) do Insight Futures.
Responsável por ler planilhas/CSVs, validar período mínimo, e obter parâmetros por ativo.

EN:
Insight Futures input package.
Responsible for reading spreadsheets/CSVs, validating minimal period, and getting asset parameters.
"""

from .leitura import ler_arquivo_financeiro
from .escrita import intervalo_de_datas, valida_periodo_minimo
from .ativos import analisar_ativos, identificar_parametros_por_ativo, ParametrosAtivo

__all__ = [
    "ler_arquivo_financeiro",
    "intervalo_de_datas",
    "valida_periodo_minimo",
    "analisar_ativos",
    "identificar_parametros_por_ativo",
    "ParametrosAtivo",
]

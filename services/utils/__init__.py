"""
PT:
Pacote de utilitários do Insight Futures (formatters, file_io, metrics, tables).

EN:
Insight Futures utilities package (formatters, file_io, metrics, tables).
"""

from .file_io import (
    arquivo_permitido,
    carregar_json,
    salvar_resultados,
    salvar_json,
    salvar_json_com_timestamp,

)

from .formatters import (
    formatar_colunas_para_br,
    converter_valores_json_serializaveis,
    converter_lista_json_serializavel,
    excluir_colunas,
    ordenar_colunas,
    extrair_id_divida,
    # novas utilitárias de normalização
    tratar_formatos_monetarios,
    corrigir_valores_numericos,
    normalizar_colunas_monetarias,
)

from .metrics import (
    obter_periodo,
    calcular_metricas_por_periodo,
    gerar_indicador_posicional,
)

from .tables import (
    detectar_e_definir_cabecalho_real,
    definir_indice_datetime_por_candidatos,
)

# services/utils/__init__.py
from .process_lock import (
    create_processing_lock,
    clear_processing_lock,
    is_processing_locked,
)


__all__ = [
    # file_io
    'arquivo_permitido',
    'carregar_json',
    'salvar_resultados',
    'salvar_json',
    'salvar_json_com_timestamp',

    # formatters
    'formatar_colunas_para_br',
    'converter_valores_json_serializaveis',
    'converter_lista_json_serializavel',
    'excluir_colunas',
    'ordenar_colunas',
    'extrair_id_divida',
    'tratar_formatos_monetarios',
    'corrigir_valores_numericos',
    'normalizar_colunas_monetarias',
    # metrics
    'obter_periodo',
    'calcular_metricas_por_periodo',
    'gerar_indicador_posicional',
    # tables
    'detectar_e_definir_cabecalho_real',
    'definir_indice_datetime_por_candidatos',
    #process_lock
    "create_processing_lock",
    "clear_processing_lock",
    "is_processing_locked",
]

"""
criar_estrutura_insightfutures.py

Este script cria a estrutura de diretórios e arquivos Python do projeto Insight Futures,
baseado em uma arquitetura modular avançada. Ele inclui arquivos `__init__.py` apenas
nas pastas de código, e gera arquivos iniciais com comentários de identificação.

Uso:
    Execute este script uma única vez a partir da raiz do projeto:
        python criar_estrutura_insightfutures.py
"""

import os
import logging

# Lista de diretórios a serem criados
estrutura = [
    "insight_futures",
    "insight_futures/core",
    "insight_futures/input",
    "insight_futures/processing",
    "insight_futures/analysis",
    "insight_futures/features_engineering",
    "insight_futures/visual",
    "insight_futures/web",
    "insight_futures/web/templates",
    "insight_futures/infra",
    "insight_futures/web/static",
    "insight_futures/web/static/css",
    "insight_futures/web/static/img",
    "insight_futures/web/static/js"
]

# Arquivos principais sugeridos por pasta
arquivos_por_pasta = {
    "insight_futures/core": ["orchestrator.py"],
    "insight_futures/input": ["leitura.py", "escrita.py", "limpeza.py", "ativos.py"],
    "insight_futures/processing": [
        "standardization.py", "fluxo_financeiro.py", "sequencias.py",
        "relative_strength.py", "classificacao.py", "acumulados.py", "preprocessing.py"
    ],
    "insight_futures/analysis": [
        "resumo_variaveis.py", "por_periodo.py", "estrategia.py", "endividamento.py"
    ],
    "insight_futures/features_engineering": ["features.py", "utils.py"],
    "insight_futures/visual": ["graficos_plotly.py"],
    "insight_futures/web": ["routes.py"],
    "insight_futures/web/templates": [
        "home.html", "login.html", "register1.html", "upload.html", "painel.html", "apis.html"
    ],
    "insight_futures/infra": ["webserver.py"],
    "insight_futures/web/static/css": ["styles.css"],
    "insight_futures/web/static/img": ["logo.png"],
}

# Pastas que devem conter __init__.py (apenas código Python)
pastas_com_codigo = [
    p for p in estrutura
    if not any(p.endswith(x) for x in ['templates', 'static', '/css', '/img', '/js'])
]

def criar_estrutura():
    """
    Cria a estrutura de diretórios e arquivos base do projeto Insight Futures.
    Inclui `__init__.py` somente nas pastas de código.
    """
    for pasta in estrutura:
        os.makedirs(pasta, exist_ok=True)

        if pasta in pastas_com_codigo:
            init_path = os.path.join(pasta, "__init__.py")
            with open(init_path, "w") as f:
                f.write("# Inicializa o pacote " + pasta.split("/")[-1] + "\n")

        if pasta in arquivos_por_pasta:
            for nome_arquivo in arquivos_por_pasta[pasta]:
                caminho = os.path.join(pasta, nome_arquivo)
                if not os.path.exists(caminho):
                    with open(caminho, "w") as f:
                        f.write(f"# Arquivo: {nome_arquivo}\n\n")

    logging.info("✅ Estrutura InsightFutures criada com sucesso!")

if __name__ == "__main__":
    criar_estrutura()




from flask import Blueprint

# Cria o blueprint raiz da API (usado só como agrupador)
bp = Blueprint("api_routes", __name__)

# Importa e registra as rotas reais da API
from api.routes import (api_process_status, api_prepadronizacao,
                        api_ativos)
from api.routes import api_ciclos, api_graficos, api_insights, api_comparativo, api_padronizacao, \
    api_ciclos_estatisticas, api_backtest, api_fluxo, api_fases, api_strategies, api_orchestrator

bp.register_blueprint(api_process_status.bp)
bp.register_blueprint(api_graficos.bp)
bp.register_blueprint(api_fluxo.bp)
bp.register_blueprint(api_ciclos.bp)
bp.register_blueprint(api_backtest.bp)
bp.register_blueprint(api_orchestrator.bp)
bp.register_blueprint(api_ciclos_estatisticas.bp)
bp.register_blueprint(api_prepadronizacao.bp)
bp.register_blueprint(api_padronizacao.bp)
bp.register_blueprint(api_strategies.bp)
bp.register_blueprint(api_insights.bp)
bp.register_blueprint(api_ativos.bp)
bp.register_blueprint(api_comparativo.api_routes)
bp.register_blueprint(api_fases.bp)

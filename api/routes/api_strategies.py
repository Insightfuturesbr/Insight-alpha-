# api/routes/api_strategies.py
from flask import Blueprint, session, jsonify, url_for, request, current_app
from services.repository.strategy_service import list_strategy_cards , update_strategy, get_strategy
from itsdangerous import URLSafeSerializer



bp = Blueprint("api_strategies", __name__, url_prefix="/api/strategies")

@bp.get("/recent")
def recent_strategies():
    """
    Retorna cards de estratégias do usuário logado.
    Pode receber ?limit=6 (padrão) para limitar a quantidade.
    """
    user = session.get("user")
    if not user:
        return jsonify({"items": [], "count": 0}), 200

    try:
        limit = int(request.args.get("limit", 6))
    except ValueError:
        limit = 6

    rows = list_strategy_cards(owner=user) or []

    items = []
    for r in rows[:limit]:
        last_upload = (r.get("last_upload") or {})
        items.append({
            "id": r.get("id"),
            "title": r.get("nome") or f"Estratégia #{r.get('id')}",
            "filename": last_upload.get("filename"),
            "created_at": r.get("created_at"),
            "result_dir": r.get("result_dir"),
            "actions": {
                "analise_pre": url_for("painel_routes.analise_pre"),
                "analise_padronizada": url_for("painel_routes.analise_pad"),
                "drawdown": url_for("painel_routes.analise_drawdown"),
                "backtest": url_for("painel_routes.parametrizacao"),
                "insights": url_for("painel_routes.insights"),
            }
        })

    return jsonify({"items": items, "count": len(items)})
@bp.patch("/<int:strategy_id>")
def rename_strategy(strategy_id: int):
    """Renomeia a estratégia (apenas do owner atual). body: {"nome": "..."}"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    novo_nome = (data.get("nome") or "").strip()
    if not novo_nome:
        return jsonify({"error": "nome inválido"}), 400

    st = get_strategy(strategy_id)
    if not st or st.get("owner") != user:
        return jsonify({"error": "not_found_or_forbidden"}), 404

    out = update_strategy(strategy_id, {"nome": novo_nome})
    return jsonify(out), 200


@bp.post("/<int:strategy_id>/share")
def share_strategy(strategy_id: int):
    """
    Gera um link de compartilhamento somente leitura (estilo Canva).
    Não precisa salvar no DB: assina com segredo da app.
    """
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    st = get_strategy(strategy_id)
    if not st or st.get("owner") != user:
        return jsonify({"error": "not_found_or_forbidden"}), 404

    secret = current_app.config.get("SECRET_KEY", "insightfutures-dev")
    s = URLSafeSerializer(secret, salt="strategy-share")
    token = s.dumps({"sid": strategy_id, "owner": user})

    # URL pública de visualização (crie essa rota de leitura pública no painel)
    public_url = url_for("painel_routes.view_strategy_public", token=token, _external=True)
    return jsonify({"url": public_url})
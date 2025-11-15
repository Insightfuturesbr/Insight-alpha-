from flask import Blueprint, request,  session, jsonify
bp = Blueprint("contratos_routes", __name__)

@bp.route('/atualizar_contratos', methods=['POST'])
def atualizar_contratos():
    req = request.get_json()
    contratos = int(req.get('contratos', 1))
    session['contratos_desejados'] = contratos

    # Opcional: salvar esse valor em um json separado para manter histórico
    return jsonify({'status': 'ok'})



@bp.route('/recalcular_fluxo_contratos', methods=['POST'])
def recalcular_fluxo_contratos():
    from app.core import InsightFutures
    req = request.get_json()
    contratos = int(req.get('contratos', 1))
    session['contratos_desejados'] = contratos

    filepath = session.get("filepath", "")
    temp_path = session.get("temp_path", "")

    try:
        insight = InsightFutures(filepath)
        insight.recalcular_com_novos_contratos(contratos_usuario=contratos)

        from services.features_engineering import salvar_todos_resultados
        salvar_todos_resultados(insight, temp_path)

        return jsonify({"status": "ok", "mensagem": "Fluxo recalculado com sucesso!"})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})


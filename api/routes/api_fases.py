# api_fases.py
from flask import Blueprint, jsonify, session
from services.utils.file_io import carregar_json

bp = Blueprint("api_fases", __name__, url_prefix="/api")

def _load_json_duplo(temp_path: str, nome: str):
    """
    Tenta carregar do namespace drawdown/ e, se não achar, tenta na raiz.
    Mantém compatibilidade com versões anteriores do salvamento.
    """
    # 1ª tentativa: dentro de /drawdown
    dado = carregar_json(temp_path, f"drawdown/{nome}")
    if dado is None:
        # 2ª tentativa: na raiz do temp_path
        dado = carregar_json(temp_path, nome)
    return dado

@bp.route("/fases", methods=["GET"])
def get_fases():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Sessão não iniciada. Faça o upload de um arquivo para começar a análise."
        }), 400

    # Carrega os três artefatos
    stats  = _load_json_duplo(temp_path, "estatisticas_fases_fechadas.json") or {}
    ciclos = _load_json_duplo(temp_path, "ciclos_drawdown.json") or []
    resumo = _load_json_duplo(temp_path, "resumo_ciclos_divida.json") or []

    # Indexa o resumo por ciclo_id (0-based): "ID Ciclo" é 1-based no resumo
    mapa_resumo = {}
    for r in resumo:
        try:
            cid0 = int(r.get("ID Ciclo", 0)) - 1
            mapa_resumo[cid0] = r
        except Exception:
            pass

    # Helper para pegar os nomes com e sem acento
    def get_or(*pairs):
        for r, key in pairs:
            v = r.get(key)
            if v is not None:
                return v
        return None

    # Enriquecer cada ciclo com os campos de fase
    ciclos_enriquecidos = []
    for c in ciclos:
        try:
            cid = int(c.get("ciclo_id"))
        except Exception:
            ciclos_enriquecidos.append(c)
            continue

        r = mapa_resumo.get(cid)
        if r:
            extra = {
                # datas/horas
                "Inicio Fase Declínio":     r.get("Inicio Fase Declínio"),
                "Fim Fase Declínio":        r.get("Fim Fase Declínio"),
                "Inicio Fase Recuperação":  r.get("Inicio Fase Recuperação"),
                "Fim Fase Recuperação":     r.get("Fim Fase Recuperação"),
                # durações (aceita com/sem acento)
                "Duração do Declínio":      get_or((r, "Duração do Declínio"), (r, "Duração do Declinio")),
                "Duração da Recuperação":   r.get("Duração da Recuperação"),
            }
            c = {**c, **{k: v for k, v in extra.items() if v is not None}}
        ciclos_enriquecidos.append(c)

    has_data = bool(stats) or bool(ciclos_enriquecidos) or bool(resumo)

    return jsonify({
        "status": "ok" if has_data else "vazio",
        "total_ciclos_fechados": stats.get("total_ciclos_fechados"),
        "fases_fechadas": stats,
        "ciclos_drawdown": ciclos_enriquecidos,   # ← agora com as 6 chaves coladas
        "resumo_ciclos_divida": resumo            # ← continua disponível “puro”, se o front quiser
    })

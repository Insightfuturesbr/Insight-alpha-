# api_routes.py (exemplo dentro do mesmo blueprint já existente)
from flask import Blueprint, jsonify
from pathlib import Path
import json
import csv
from datetime import datetime

api_routes = Blueprint('api_routes', __name__)  # se já existir, reutilize o mesmo

RESULTS_ROOT = Path("outputs/resultados")

def _latest_results_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    # ordenar pela data do nome (…_YYYYMMDD_HHMMSS) ou pela mtime se preferir
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]

def _safe_float(x):
    try:
        if x is None or x == "":
            return None
        return float(str(x).replace(",", "."))
    except:
        return None

def _read_insight_futures_results(dirpath: Path) -> dict | None:
    """
    Lê InsightFuturesResults.csv e monta agregados básicos:
    - total_operacoes, operacoes_negativas, operacoes_amortizacao, operacoes_lucro
    - lucro_final (Resultado líquido acumulado)
    - drawdown_maximo (mínimo de Dívida Acumulada)
    - maior_lucro_acumulado (máximo de Lucro Acumulado)
    """
    csv_path = dirpath / "InsightFuturesResults.csv"
    if not csv_path.exists():
        return None

    total = neg = amort = lucros = 0
    lucro_final = 0.0
    dd_min = None
    lucro_max = None

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            tipo = (row.get("Tipo Resultado") or "").strip().lower()
            if "negativo" in tipo or "perda" in tipo:
                neg += 1
            if "amort" in tipo or "recupera" in tipo:
                amort += 1
            if "lucro" in tipo or "positivo" in tipo:
                lucros += 1

            # acumulados
            dd = _safe_float(row.get("Dívida Acumulada"))
            if dd is not None:
                dd_min = dd if dd_min is None else min(dd_min, dd)
            la = _safe_float(row.get("Lucro Acumulado"))
            if la is not None:
                lucro_max = la if lucro_max is None else max(lucro_max, la)

            # no final do arquivo tende a haver o acumulado final
            rl = _safe_float(row.get("Resultado Simulado Padronizado Líquido Acumulado")) \
                 or _safe_float(row.get("Resultado líquido Total Acumulado antes da padronização"))
            if rl is not None:
                lucro_final = rl

    return {
        "total_operacoes": total,
        "operacoes_negativas": neg,
        "operacoes_amortizacao": amort,
        "operacoes_lucro": lucros,
        "lucro_final": round(lucro_final, 2),
        "drawdown_maximo": round(dd_min or 0.0, 2),
        "maior_lucro_acumulado": round(lucro_max or 0.0, 2),
    }

def _read_backtest(dirpath: Path) -> dict | None:
    """
    Tenta ler um JSON com resultado de backtest, caso seu backtest salve algo como backtest_results.json.
    Ajuste os nomes abaixo se você já salva com outro nome.
    """
    for name in ["backtest_results.json", "resultado_backtest.json", "comparativo_backtest.json"]:
        p = dirpath / name
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except:
                pass
    return None

@api_routes.route("/api/comparativo", methods=["GET"])
def api_comparativo():
    latest = _latest_results_dir(RESULTS_ROOT)
    if not latest:
        return jsonify({"error": "sem_resultados"}), 404

    base = _read_insight_futures_results(latest)
    if not base:
        return jsonify({"error": "sem_csv_base"}), 404

    bt = _read_backtest(latest)
    if bt is None:
        # Fallback: usa a base também para “insight”, mas marcando que é fallback
        insight = dict(base)
        insight["from_fallback"] = True
    else:
        # Normalize possíveis chaves do seu JSON de backtest
        # Esperado: mesmas chaves do base
        insight = {
            "total_operacoes": bt.get("total_operacoes") or bt.get("ops_total") or bt.get("qtd_operacoes"),
            "operacoes_negativas": bt.get("operacoes_negativas") or bt.get("qtd_negativas"),
            "operacoes_amortizacao": bt.get("operacoes_amortizacao") or bt.get("qtd_amortizacoes"),
            "operacoes_lucro": bt.get("operacoes_lucro") or bt.get("qtd_lucros"),
            "lucro_final": bt.get("lucro_final") or bt.get("resultado_liquido"),
            "drawdown_maximo": bt.get("drawdown_maximo") or bt.get("dd_maximo"),
            "maior_lucro_acumulado": bt.get("maior_lucro_acumulado") or bt.get("lucro_max_acum"),
        }

    payload = {
        "sempre_ligada": base,
        "insight_futures": insight,
        "dir": latest.name,
        "ts": datetime.now().isoformat(timespec="seconds")
    }
    return jsonify(payload), 200

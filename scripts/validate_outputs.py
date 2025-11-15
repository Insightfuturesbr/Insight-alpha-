#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida todos os JSONs gerados contra seus JSON Schemas (V1).
Uso:
  python scripts/validate_outputs.py --dir outputs/resultados/meu_lote
  python scripts/validate_outputs.py --file outputs/resultados/meu_lote/variaveis_fluxo.json
"""
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

# ajuste o caminho base se necessário
SCHEMA_DIR = Path("contracts/jsonschema")

# 1) registry: arquivo_de_dados -> arquivo_de_schema
STATS_REUSAVEL = "stats_ciclo.v1.json"
REGISTRY = {
    "variaveis_pre.json":                 "variaveis_pre.v1.json",
    "variaveis_fluxo.json":               "variaveis_fluxo.v1.json",
    "ultimo_resultado.json":              "ultimo_resultado.v1.json",
    "prebacktest.json":                   "prebacktest.v1.json",
    "ultimo_ciclo.json":                  "ultimo_ciclo.v1.json",
    "ultimo_ciclo_completo.json":         "ultimo_ciclo_completo.v1.json",
    "resultados_completos.json":          "resultados_completos.v1.json",
    "resultados_fluxo_ciclo.json":        "resultados_fluxo_ciclo.v1.json",
    "resultados_ciclos_lucro.json":       "resultados_ciclos_lucro.v1.json",
    "resumo_ciclos_divida.json":          "resumo_ciclos_divida.v1.json",
    "padronizacao.json":                  "padronizacao.v1.json",
    "parametros_ativo.json":              "parametros_ativo.v1.json",
    "ciclos_drawdown.json":               "ciclos_drawdown.v1.json",
    "estatisticas_ciclos_lucro.json":     "estatisticas_ciclos_lucro.v1.json",
    "estatisticas_duracao_ciclos.json":   "estatisticas_duracao_ciclos.v1.json",
    "estatisticas_positivas_negativas.json": "estatisticas_positivas_negativas.v1.json",

    # Reutilizam o mesmo schema (stats_ciclo.v1.json):
    "estatisticas_ciclo_amortizacao.json": STATS_REUSAVEL,
    "estatisticas_ciclo_emprestimo.json":  STATS_REUSAVEL,
    "estatisticas_ciclo_lucro.json":       STATS_REUSAVEL,
    "estats_qtd_luc_ciclo.json":           STATS_REUSAVEL,
    "estats_qtd_emp_ciclo.json":           STATS_REUSAVEL,
    "estats_qtd_amo_ciclo.json":           STATS_REUSAVEL,

    # seleção de ativos
    "ativo.json":  "ativo.v1.json",
    "ativos.json": "ativos.v1.json",
}

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_one(data_path: Path) -> tuple[bool, str]:
    name = data_path.name
    schema_name = REGISTRY.get(name)
    if not schema_name:
        return (False, f"[SKIP] Sem schema cadastrado para {name} (adicione no REGISTRY).")

    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        return (False, f"[ERRO] Schema {schema_name} não encontrado em {SCHEMA_DIR}.")

    data = load_json(data_path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msgs = []
        for e in errors:
            loc = " → ".join([str(p) for p in e.path]) if e.path else "(raiz)"
            msgs.append(f"- {name}: {loc}: {e.message}")
        return (False, "\n".join(msgs))
    return (True, f"[OK] {name} validado com {schema_name}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="Pasta com JSONs de saída", default=None)
    ap.add_argument("--file", help="Arquivo JSON único para validar", default=None)
    args = ap.parse_args()

    targets = []
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"[ERRO] Arquivo não encontrado: {p}", file=sys.stderr)
            sys.exit(2)
        targets = [p]
    elif args.dir:
        base = Path(args.dir)
        if not base.exists():
            print(f"[ERRO] Pasta não encontrada: {base}", file=sys.stderr)
            sys.exit(2)
        targets = [p for p in base.iterdir() if p.suffix == ".json"]
    else:
        print("Use --dir ou --file", file=sys.stderr)
        sys.exit(2)

    ok, fail = 0, 0
    reports = []
    for path in sorted(targets):
        is_ok, msg = validate_one(path)
        reports.append(msg)
        if is_ok:
            ok += 1
        else:
            fail += 1

    print("\n".join(reports))
    print(f"\nResumo: {ok} OK, {fail} com problemas.")
    sys.exit(0 if fail == 0 else 1)

if __name__ == "__main__":
    main()

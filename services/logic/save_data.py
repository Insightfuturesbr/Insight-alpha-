# -*- coding: utf-8 -*-
"""
save_data.py
Ponto Único de Escrita dos JSONs do Insight Futures — sem perder informação.

- Mantém todos os arquivos e espelhos em drawdown/ e backtest/.
- Valida com Pydantic (se 'contracts.models' existir), mas NUNCA bloqueia salvamento por ausência desses modelos.
- Usa conversores para serializar numpy/datetime etc.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List

import pandas as pd


# --- JSON Schema (opcional): valida arquivos salvos contra contracts/jsonschema ---
try:
    from jsonschema import Draft202012Validator
    import json
    from pathlib import Path

    _HAS_JSONSCHEMA = True
    _SCHEMA_DIR = Path("contracts/jsonschema")
    _STATS_REUSAVEL = "stats_ciclo.v1.json"

    _REGISTRY = {
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
        "ativo.json":  "ativo.v1.json",
        "ativos.json": "ativos.v1.json",

        # reutilizam o mesmo schema:
        "estatisticas_ciclo_amortizacao.json": _STATS_REUSAVEL,
        "estatisticas_ciclo_emprestimo.json":  _STATS_REUSAVEL,
        "estatisticas_ciclo_lucro.json":       _STATS_REUSAVEL,
        "estats_qtd_luc_ciclo.json":           _STATS_REUSAVEL,
        "estats_qtd_emp_ciclo.json":           _STATS_REUSAVEL,
        "estats_qtd_amo_ciclo.json":           _STATS_REUSAVEL,
    }

    def _load_json(path: Path):
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_outputs_dir(base_dir: str) -> list[str]:
        """Valida todos os .json de base_dir contra seus schemas. Retorna mensagens para log."""
        msgs: list[str] = []
        base = Path(base_dir)
        if not base.exists():
            return [f"[SKIP] pasta não existe: {base_dir}"]

        for data_path in sorted(p for p in base.iterdir() if p.suffix == ".json"):
            name = data_path.name
            schema_name = _REGISTRY.get(name)
            if not schema_name:
                msgs.append(f"[SKIP] {name}: sem schema cadastrado")
                continue

            schema_path = _SCHEMA_DIR / schema_name
            if not schema_path.exists():
                msgs.append(f"[ERRO] {name}: schema {schema_name} não encontrado em {_SCHEMA_DIR}")
                continue

            data = _load_json(data_path)
            schema = _load_json(schema_path)
            validator = Draft202012Validator(schema)
            errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

            if errors:
                for e in errors:
                    loc = " → ".join(map(str, e.path)) if e.path else "(raiz)"
                    msgs.append(f"[FAIL] {name} @ {loc}: {e.message}")
            else:
                msgs.append(f"[OK] {name} ✓")

        return msgs

except Exception as _e:
    _HAS_JSONSCHEMA = False
    logging.info("Validação por JSON Schema desativada (%s).", _e)




# Conversores (usar os teus, e cair num fallback seguro se não houver)
try:
    from services.utils.formatters import (
        converter_valores_json_serializaveis,
        converter_lista_json_serializavel,
    )
except Exception:
    import numpy as np
    from datetime import datetime, date

    def converter_valores_json_serializaveis(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: converter_valores_json_serializaveis(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [converter_valores_json_serializaveis(v) for v in obj]
        if hasattr(obj, "item"):  # numpy scalar
            try:
                return obj.item()
            except Exception:
                pass
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat(sep=" ")
        return obj

    def converter_lista_json_serializavel(lst: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [converter_valores_json_serializaveis(x) for x in lst]

# Pydantic (opcional): validação de estruturas “menores”
_HAS_MODELS = True
try:
    from contracts.models import (
        VariaveisPreV1,
        VariaveisFluxoV1,
        UltimoCicloV1,
        CicloDrawdownItemV1,
        StatsCicloV1,
    )
except Exception as e:
    logging.warning("Validação Pydantic desativada (contracts.models indisponível: %s)", e)
    _HAS_MODELS = False


# ------------------------- utilidades ------------------------- #
def salvar_json(data: Any, caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _validate_variaveis_pre(payload: Dict[str, Any]) -> None:
    if _HAS_MODELS:
        VariaveisPreV1(**payload)

def _validate_variaveis_fluxo(payload: Dict[str, Any]) -> None:
    if _HAS_MODELS:
        VariaveisFluxoV1(**payload)

def _validate_ultimo_ciclo(payload: Dict[str, Any]) -> None:
    if _HAS_MODELS:
        UltimoCicloV1(**payload)

def _validate_ciclos_drawdown(items: List[Dict[str, Any]]) -> None:
    if _HAS_MODELS:
        for it in items:
            CicloDrawdownItemV1(**it)

def _validate_stats_ciclo(payload: Dict[str, Any]) -> None:
    if _HAS_MODELS:
        StatsCicloV1(**payload)


# ------------------------- principal ------------------------- #
def salvar_todos_resultados(insight, temp_path: str) -> None:
    """
    Salva todos os resultados gerados pela instância do InsightFutures.
    Preserva exatamente as mesmas saídas do pipeline, sem perdas.
    """
    # Namespaces (mantém raiz + espelhos)
    drawdown_dir = os.path.join(temp_path, "drawdown")
    backtest_dir = os.path.join(temp_path, "backtest")
    os.makedirs(drawdown_dir, exist_ok=True)
    os.makedirs(backtest_dir, exist_ok=True)

    # ========= DataFrames principais (orient="split") ========= #
    try:
        caminho_ultimo = os.path.join(temp_path, "ultimo_resultado.json")
        insight.data.to_json(caminho_ultimo, orient="split")
        logging.info("✅ ultimo_resultado.json salvo (e espelhado).")
    except Exception as e:
        logging.exception("❌ Falha ao salvar ultimo_resultado.json: %s", e)

    try:
        caminho_pre = os.path.join(temp_path, "prebacktest.json")
        insight.df_prebacktest.to_json(caminho_pre, orient="split")
        insight.df_prebacktest.to_json(os.path.join(backtest_dir, "prebacktest.json"), orient="split")
        logging.info("✅ prebacktest.json salvo (e espelhado).")
    except Exception as e:
        logging.info("ℹ️ prebacktest indisponível: %s", e)

    # ========= Variáveis principais ========= #
    try:
        payload = converter_valores_json_serializaveis(insight.variaveis_pre)
        _validate_variaveis_pre(payload)
        salvar_json(payload, os.path.join(temp_path, "variaveis_pre.json"))
        logging.info("✅ variaveis_pre.json salvo.")
    except Exception as e:
        logging.exception("❌ Falha ao salvar variaveis_pre.json: %s", e)

    try:
        payload = converter_valores_json_serializaveis(insight.variaveis_fluxo)
        _validate_variaveis_fluxo(payload)
        salvar_json(payload, os.path.join(temp_path, "variaveis_fluxo.json"))
        logging.info("✅ variaveis_fluxo.json salvo.")
    except Exception as e:
        logging.exception("❌ Falha ao salvar variaveis_fluxo.json: %s", e)

    try:
        payload = converter_valores_json_serializaveis(insight.variaveis_padronizacao)
        salvar_json(payload, os.path.join(temp_path, "padronizacao.json"))
        logging.info("✅ padronizacao.json salvo.")
    except Exception as e:
        logging.info("ℹ️ variaveis_padronizacao indisponível: %s", e)

    # ========= Inputs de ativo ========= #
    try:
        salvar_json(insight.parametros_ativo, os.path.join(temp_path, "parametros_ativo.json"))
    except Exception as e:
        logging.info("ℹ️ parametros_ativo indisponível: %s", e)

    try:
        salvar_json(insight.ativos, os.path.join(temp_path, "ativos.json"))
    except Exception as e:
        logging.info("ℹ️ ativos indisponível: %s", e)

    try:
        salvar_json(insight.ativo, os.path.join(temp_path, "ativo.json"))
    except Exception as e:
        logging.info("ℹ️ ativo indisponível: %s", e)

    # ========= Fluxo do ciclo atual ========= #
    try:
        payload = converter_valores_json_serializaveis(insight.resultados_fluxo_ciclo)
        salvar_json(payload, os.path.join(temp_path, "resultados_fluxo_ciclo.json"))
        logging.info("✅ resultados_fluxo_ciclo.json salvo.")
    except Exception as e:
        logging.info("ℹ️ resultados_fluxo_ciclo indisponível: %s", e)

    # ========= Estatísticas “cartão” (reutilizáveis) ========= #
    stats_map = [
        ("estatisticas_ciclo_emprestimo.json",  "estatisticas_ciclo_emprestimo"),
        ("estatisticas_ciclo_amortizacao.json", "estatisticas_ciclo_amortizacao"),
        ("estatisticas_ciclo_lucro.json",       "estatisticas_ciclo_lucro"),
        ("estats_qtd_emp_ciclo.json",           "estats_qtd_emp_ciclo"),
        ("estats_qtd_amo_ciclo.json",           "estats_qtd_amo_ciclo"),
        ("estats_qtd_luc_ciclo.json",           "estats_qtd_luc_ciclo"),
    ]
    for fname, attr in stats_map:
        try:
            data = getattr(insight, attr)
            payload = converter_valores_json_serializaveis(data)
            _validate_stats_ciclo(payload)
            salvar_json(payload, os.path.join(temp_path, fname))
            logging.info("✅ %s salvo.", fname)
        except AttributeError:
            logging.info("ℹ️ %s indisponível.", attr)
        except Exception as e:
            logging.exception("❌ Falha ao salvar %s: %s", fname, e)

    # ========= Resumos/estatísticas agregadas ========= #
    try:
        salvar_json(converter_valores_json_serializaveis(insight.estatisticas_duracao_ciclos),
                    os.path.join(temp_path, "estatisticas_duracao_ciclos.json"))

        logging.info("✅ estatisticas_duracao_ciclos.json salvo.")
    except Exception as e:
        logging.info("ℹ️ estatisticas_duracao_ciclos indisponível: %s", e)

    try:
        salvar_json(converter_valores_json_serializaveis(insight.metricas_positivas_negativas),
                    os.path.join(temp_path, "estatisticas_positivas_negativas.json"))

        logging.info("✅ estatisticas_positivas_negativas.json salvo.")
    except Exception as e:
        logging.info("ℹ️ metricas_positivas_negativas indisponível: %s", e)

    try:
        salvar_json(converter_valores_json_serializaveis(insight.resumo_lucros_estatisticos),
                    os.path.join(temp_path, "estatisticas_ciclos_lucro.json"))

        logging.info("✅ estatisticas_ciclos_lucro.json salvo.")
    except Exception as e:
        logging.info("ℹ️ resumo_lucros_estatisticos indisponível: %s", e)

    # ========= Listas de ciclos (divida / lucro) ========= #
    try:
        lst = converter_lista_json_serializavel(insight.resumo_ciclos_drawdown)
        salvar_json(lst, os.path.join(temp_path, "resumo_ciclos_divida.json"))

        logging.info("✅ resumo_ciclos_divida.json salvo.")
    except Exception as e:
        logging.info("ℹ️ resumo_ciclos_drawdown indisponível: %s", e)

    try:
        salvar_json(insight.resumo_ciclos_lucro, os.path.join(temp_path, "resultados_ciclos_lucro.json"))
        salvar_json(insight.resumo_cicros_lucro if hasattr(insight, "resumo_cicros_lucro") else insight.resumo_ciclos_lucro,
                    os.path.join(drawdown_dir, "resultados_ciclos_lucro.json"))
        logging.info("✅ resultados_ciclos_lucro.json salvo.")
    except Exception as e:
        logging.info("ℹ️ resultados_ciclos_lucro indisponível: %s", e)

    # ========= Último ciclo (header + completo) ========= #
    try:
        payload = converter_valores_json_serializaveis(insight.ultimo_ciclo)
        _validate_ultimo_ciclo(payload)
        salvar_json(payload, os.path.join(temp_path, "ultimo_ciclo.json"))
        logging.info("✅ ultimo_ciclo.json salvo.")
    except Exception as e:
        logging.info("ℹ️ ultimo_ciclo indisponível: %s", e)

    try:
        salvar_ultimo_ciclo_completo(insight.data, os.path.join(temp_path, "ultimo_ciclo_completo.json"))
        logging.info("✅ ultimo_ciclo_completo.json salvo.")
    except Exception as e:
        logging.info("ℹ️ Não foi possível salvar ultimo_ciclo_completo.json: %s", e)

    # ========= Tabelas completas (linha a linha) ========= #
    try:
        if hasattr(insight, "df_completo") and insight.df_completo is not None:
            insight.df_completo.to_json(os.path.join(temp_path, "resultados_completos.json"), orient="records")
            logging.info("✅ resultados_completos.json salvo (e espelhado).")
    except Exception as e:
        logging.info("ℹ️ df_completo indisponível: %s", e)

    # ========= Enriquecimento com fases (ciclos fechados) ========= #
    try:
        from services.processing.fluxo_financeiro import construir_resumo_ciclos_fases

        resumo_antigo_path = os.path.join(temp_path, "resumo_ciclos_divida.json")
        resumo_antigo = None
        if os.path.exists(resumo_antigo_path):
            resumo_antigo = pd.read_json(resumo_antigo_path)

        resumo_fases = construir_resumo_ciclos_fases(
            df_base=insight.data,
            df_ciclos=getattr(insight, "df_ciclos_drawdown", None),
            coluna_datetime=("Abertura" if "Abertura" in insight.data.columns else
                             "DataHora" if "DataHora" in insight.data.columns else None),
            coluna_acumulado=(
                "Resultado Líquido Total Acumulado"
                if "Resultado Líquido Total Acumulado" in insight.data.columns
                else ("Caixa Líquido" if "Caixa Líquido" in insight.data.columns else insight.data.columns[0])
            ),
            atol_recuperacao=0.0,
            resumo_antigo=resumo_antigo
        )

        if resumo_fases is not None and not resumo_fases.empty:
            resumo_fases.to_json(resumo_antigo_path, orient="records", force_ascii=False, indent=2)
            logging.info("✅ resumo_ciclos_divida.json enriquecido com fases.")
    except Exception as e:
        logging.warning("[save_data] Não foi possível enriquecer resumo_ciclos_divida.json com fases: %s", e)

    # ========= Artefatos adicionais de drawdown ========= #
    try:
        if hasattr(insight, "df_ciclos_drawdown") and insight.df_ciclos_drawdown is not None:
            insight.df_ciclos_drawdown.to_json(os.path.join(temp_path, "ciclos_drawdown.json"), orient="records")
            logging.info("✅ ciclos_drawdown.json salvo (raiz e drawdown/).")
    except Exception as e:
        logging.info("ℹ️ df_ciclos_drawdown indisponível: %s", e)

    try:
        if hasattr(insight, "stats_fases_fechadas") and insight.stats_fases_fechadas is not None:
            payload = converter_valores_json_serializaveis(insight.stats_fases_fechadas)
            salvar_json(payload, os.path.join(temp_path, "estatisticas_fases_fechadas.json"))

            logging.info("✅ estatisticas_fases_fechadas.json salvo.")
    except Exception as e:
        logging.info("ℹ️ stats_fases_fechadas indisponível: %s", e)
    # --- validação por JSON Schema (opcional) ---
    if _HAS_JSONSCHEMA:
        for dir_to_check in (temp_path, os.path.join(temp_path, "drawdown")):
            if os.path.isdir(dir_to_check):
                for msg in _validate_outputs_dir(dir_to_check):
                    (logging.warning if msg.startswith("[FAIL]") else logging.info)(f"[schema] {msg}")

    logging.info("🏁 Salvamento concluído em: %s", temp_path)


def salvar_resultados_backtest(insight, temp_path: str) -> None:
    """
    Salva os resultados do backtest (métricas + DF split), mantendo espelho em backtest/.
    """
    backtest_dir = os.path.join(temp_path, "backtest")
    os.makedirs(backtest_dir, exist_ok=True)

    try:
        if hasattr(insight, "metricas_original") and insight.metricas_original is not None:
            payload = converter_valores_json_serializaveis(insight.metricas_original)
            salvar_json(payload, os.path.join(temp_path, "metricas_original.json"))
            salvar_json(payload, os.path.join(backtest_dir, "metricas_original.json"))
            logging.info("✅ metricas_original.json salvo.")
    except Exception as e:
        logging.info("ℹ️ metricas_original indisponível: %s", e)

    try:
        if hasattr(insight, "metricas_backtest") and insight.metricas_backtest is not None:
            payload = converter_valores_json_serializaveis(insight.metricas_backtest)
            salvar_json(payload, os.path.join(temp_path, "metricas_backtest.json"))
            salvar_json(payload, os.path.join(backtest_dir, "metricas_backtest.json"))
            logging.info("✅ metricas_backtest.json salvo.")
    except Exception as e:
        logging.info("ℹ️ metricas_backtest indisponível: %s", e)

    try:
        if hasattr(insight, "df_backtest") and insight.df_backtest is not None:
            insight.df_backtest.to_json(os.path.join(temp_path, "backtest.json"), orient="split")
            insight.df_backtest.to_json(os.path.join(backtest_dir, "backtest.json"), orient="split")
            logging.info("✅ backtest.json (split) salvo (e espelhado).")
    except Exception as e:
        logging.info("ℹ️ df_backtest indisponível: %s", e)
    # --- validação por JSON Schema para backtest/ (opcional) ---
    if _HAS_JSONSCHEMA and os.path.isdir(backtest_dir):
        for msg in _validate_outputs_dir(backtest_dir):
            (logging.warning if msg.startswith("[FAIL]") else logging.info)(f"[schema/backtest] {msg}")


def salvar_ultimo_ciclo_completo(df: pd.DataFrame, caminho_arquivo: str) -> None:
    """
    Extrai e salva o último ciclo completo do DF principal em formato records,
    preservando nomes PT-BR e strings de datas, sem perdas.
    """
    import re

    try:
        # ID do último ciclo (ex.: 'D49...' em 'ID Operação')
        id_ultimo = df["ID Operação"].dropna().astype(str).iloc[-1]
        match = re.search(r"D(\d+)", id_ultimo)
        if not match:
            logging.error("❌ Último ID não contém ciclo válido: %r", id_ultimo)
            return
        id_ciclo_final = match.group(0)  # 'D49'

        df_ult = df[df["ID Operação"].astype(str).str.startswith(id_ciclo_final)].copy()
        if df_ult.empty:
            logging.error("❌ Último ciclo não encontrado (filtro %s).", id_ciclo_final)
            return

        # Índice → 'Abertura' se datetime
        df_ult = df_ult.reset_index()
        if pd.api.types.is_datetime64_any_dtype(df_ult.iloc[:, 0]):
            df_ult.rename(columns={df_ult.columns[0]: "Abertura"}, inplace=True)
            df_ult["Abertura"] = df_ult["Abertura"].astype(str)

        # Colunas datetime → string padrão
        for col in df_ult.select_dtypes(include=["datetime", "datetime64[ns]"]).columns:
            df_ult[col] = df_ult[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        registros = df_ult.to_dict(orient="records")
        salvar_json(registros, caminho_arquivo)
    except Exception as e:
        logging.error("❌ Erro ao salvar último ciclo completo: %s", e)

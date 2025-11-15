"""
PT:
Leitura robusta de planilhas/CSVs de backtests (BR), integrada ao
detector de cabeçalho/normalização (header_detector.py + headers_helper.py).

Comportamento:
- XLSX: lê a planilha toda sem header e usa o detector para
        encontrar a linha de cabeçalho e normalizar nomes canônicos.
        Se o detector não estiver disponível ou falhar, usa o legado:
        header na linha 6 (0-index=5).
- CSV: também usa o detector por padrão (varrendo as primeiras linhas,
       mesmo quando há "capa" antes do cabeçalho). Se falhar/ausente,
       cai no legado: (;, ISO-8859-1) → (,, utf-8) → auto-inferência.

Pós-leitura:
- Converte 'Abertura' e 'Fechamento' para datetime (se existirem).

EN:
Robust reader for Brazilian trading spreadsheets, using header detection
for both XLSX and CSV, with safe legacy fallbacks.
"""

import os
import io
import logging
import pandas as pd

# ---------- Optional imports (header detector) ----------
_HAS_DETECTOR = False
try:
    # header_detector.py e headers_helper.py devem estar no PYTHONPATH
    from header_detector import detect_and_normalize_headers  # type: ignore
    _HAS_DETECTOR = True
except Exception:
    _HAS_DETECTOR = False


# ---------- Helpers ----------

def _coerce_dates_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Converte apenas colunas de datas usadas no pipeline canônico."""
    for col in ("Abertura", "Fechamento"):
        if col in df.columns:
            # dayfirst=True é seguro para BR/Profit (dd/mm/aaaa hh:mm)
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df


def _read_text_binary(file_path: str) -> tuple[str, str]:
    """
    Lê binário e tenta decodificar como utf-8; se falhar, latin-1.
    Retorna (texto, encoding_usado).
    """
    with open(file_path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


# ---------- Main ----------

def ler_arquivo_financeiro(file_path: str) -> pd.DataFrame | None:
    """
    PT:
        Lê .xlsx ou .csv e retorna DataFrame bruto normalizado de header.
        - XLSX: usa header_detector; fallback linha 6.
        - CSV: usa header_detector (header=None para permitir detecção);
               fallbacks legados se detector falhar/ausente.
        - Pós: converte 'Abertura' e 'Fechamento' (se existirem).
    EN:
        Reads .xlsx/.csv and returns a raw DataFrame with normalized headers.
    """
    logging.info("📂 Tentando ler o arquivo: %s", file_path)

    try:
        ext = os.path.splitext(file_path)[-1].lower()

        # ----------------------- XLSX -----------------------
        if ext == ".xlsx":
            # Lê toda a planilha sem header para permitir detecção flexível.
            df_full = pd.read_excel(file_path, sheet_name=0, engine="openpyxl", header=None)
            logging.info("✅ XLSX carregado (sem header).")

            if _HAS_DETECTOR:
                try:
                    df_norm, report = detect_and_normalize_headers(df_full, limit=50)
                    try:
                        logging.info(
                            "🧭 XLSX header detector: linha=%s | recognized=%s | unknown=%s | fuzzy=%s",
                            report.get("headerRow"),
                            len(report.get("recognized", [])),
                            len(report.get("unknown", [])),
                            report.get("usedFuzzy"),
                        )
                    except Exception:
                        pass
                    df = df_norm.reset_index(drop=True)
                    df = _coerce_dates_basic(df)
                    logging.info("✅ XLSX normalizado via header_detector.")
                    return df
                except Exception as e:
                    logging.warning("⚠️ Falha no header_detector XLSX (%s). Usando fallback linha 6.", e)

            # Fallback legado: assume header na linha 6 (0-index=5)
            header_row = df_full.iloc[5]  # linha visual 6
            df = df_full[6:].copy()
            df.columns = header_row
            df = df.reset_index(drop=True)
            df = _coerce_dates_basic(df)
            logging.info("✅ Conteúdo XLSX parseado manualmente (linha 6 como header).")
            return df

        # ----------------------- CSV -----------------------
        if ext == ".csv":
            # Caminho preferencial: usar detector (permitindo "capa" antes do header).
            if _HAS_DETECTOR:
                try:
                    text, enc = _read_text_binary(file_path)
                    # header=None e sep=None → engine detecta separador; detector varre várias linhas.
                    df_full = pd.read_csv(io.StringIO(text), sep=None, engine="python", header=None, low_memory=False)
                    logging.info("✅ CSV carregado (sem header | sep auto | %s).", enc)

                    df_norm, report = detect_and_normalize_headers(df_full, limit=50)
                    try:
                        logging.info(
                            "🧭 CSV header detector: linha=%s | recognized=%s | unknown=%s | fuzzy=%s",
                            report.get("headerRow"),
                            len(report.get("recognized", [])),
                            len(report.get("unknown", [])),
                            report.get("usedFuzzy"),
                        )
                    except Exception:
                        pass
                    df = df_norm.reset_index(drop=True)
                    df = _coerce_dates_basic(df)
                    logging.info("✅ CSV normalizado via header_detector.")
                    return df
                except Exception as e:
                    logging.warning("⚠️ Falha no header_detector CSV (%s). Usando fallbacks legados.", e)

            # Fallbacks legados (mantêm contrato anterior)
            try:
                df = pd.read_csv(file_path, sep=";", encoding="ISO-8859-1", header=0, low_memory=False)
                logging.info("✅ CSV lido (sep=';' | ISO-8859-1 | header=0).")
            except Exception:
                try:
                    df = pd.read_csv(file_path, sep=",", encoding="utf-8", header=0, low_memory=False)
                    logging.warning("⚠️ Fallback: CSV lido (sep=',' | utf-8 | header=0).")
                except Exception:
                    text, enc = _read_text_binary(file_path)
                    df = pd.read_csv(io.StringIO(text), sep=None, engine="python", header=0, low_memory=False)
                    logging.warning("⚠️ Auto-inferência: CSV lido (sep=None | %s | header=0).", enc)

            df = _coerce_dates_basic(df)
            return df

        # ------------------- Tipo não suportado -------------------
        logging.error("🚫 Tipo de arquivo não suportado. Use .xlsx ou .csv.")
        return None

    except PermissionError:
        logging.error("⚠️ Permissão negada ao acessar o arquivo.")
    except ValueError:
        logging.error("⚠️ Formato de arquivo inválido ou corrompido.")
    except Exception as e:
        logging.error("⚠️ Erro desconhecido ao abrir a planilha: %s", e)

    return None

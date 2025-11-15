import logging
import os
from pathlib import Path
import pandas as pd
import hashlib
import uuid

from flask import Blueprint, request, flash, session, redirect, render_template, url_for, jsonify
from werkzeug.utils import secure_filename

from app.core.orchestrator import InsightFutures  # seu orchestrator
from services.logic.save_data import salvar_todos_resultados
from app.core.paths import criar_diretorio_resultado, ALLOWED_EXTENSIONS
from app.core.config import settings

from services.utils.file_io import arquivo_permitido
from services.utils.process_lock import create_processing_lock, clear_processing_lock, is_processing_locked
from services.repository.strategy_service import (
    register_upload,
    attach_upload,
    list_strategy_cards,
    create_strategy,
    update_upload_result_dir,  # <-- salvar result_dir no upload
)

# ------------ THUMB SETUP (por upload) ------------
# backend headless para gerar imagens com matplotlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

bp = Blueprint("upload_routes", __name__)

# Garante que as pastas existem
UPLOAD_FOLDER = str(settings.uploads_dir)
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

THUMBS_DIR = os.path.join(settings.static_dir, "thumbs")
Path(THUMBS_DIR).mkdir(parents=True, exist_ok=True)


def _save_upload_thumb(upload_id: int, df) -> str:
    """
    Gera um thumb 16:9 a partir do DataFrame processado e salva em static/thumbs/upload_<id>.png.
    Retorna o caminho absoluto salvo (ou string vazia em caso de falha).
    """
    try:
        if df is None or getattr(df, "empty", True):
            return ""

        # coluna preferencial para plot
        y = None
        preferred = [
            "Caixa Líquido",
            "Resultado Líquido Total Acumulado",
            "Resultado líquido dia",
            "ResultadoDiario",
        ]
        for col in preferred:
            if col in df.columns:
                y = df[col]
                break
        if y is None:
            # fallback: primeira coluna numérica
            num_cols = [c for c in df.columns if str(df[c].dtype).startswith(("float", "int"))]
            if num_cols:
                y = df[num_cols[0]]
            else:
                return ""

        # eixo x: índice se for datetime, senão range
        try:
            x = df.index if str(df.index.dtype).startswith("datetime64") else range(len(y))
        except Exception:
            x = range(len(y))

        out_path = os.path.join(THUMBS_DIR, f"upload_{int(upload_id)}.png")

        plt.figure(figsize=(12, 6))  # ~16:8 (parecido com 16:9)
        try:
            plt.plot(x, y)
            plt.xticks([])
            plt.yticks([])
            plt.tight_layout(pad=0.2)
            # facecolor combinando com tema escuro
            plt.savefig(out_path, dpi=110, facecolor="#0c1526")
        finally:
            plt.close()

        return out_path
    except Exception:
        logging.exception("Falha ao gerar thumb do upload %s", upload_id)
        return ""


def _md5(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _estrutura_minima_ok(path: str) -> bool:
    """
    Valida de forma tolerante se o arquivo tem, em alguma linha de cabeçalho,
    as colunas mínimas exigidas (ex.: 'Ativo' e 'Abertura'), independentemente
    da linha onde o cabeçalho real aparece.
    """
    obrigatorias = {"ativo", "abertura"}  # compare em lower()
    _, ext = os.path.splitext(path.lower())

    def tem_colunas_minimas(cols) -> bool:
        try:
            cols_norm = {str(c).strip().lower() for c in cols if c is not None}
            return obrigatorias.issubset(cols_norm)
        except Exception:
            return False

    try:
        if ext == ".xlsx":
            # 1) Sem header
            df_raw = pd.read_excel(path, header=None, nrows=12)
            for i in range(min(10, len(df_raw))):
                possivel_header = df_raw.iloc[i].tolist()
                if tem_colunas_minimas(possivel_header):
                    return True

            # 2) Headers em diferentes linhas
            for h in range(0, 10):
                try:
                    df_try = pd.read_excel(path, header=h, nrows=5)
                    if tem_colunas_minimas(df_try.columns):
                        return True
                except Exception:
                    continue
        else:
            # CSV: vários separadores
            for sep in (";", ",", "\t", "|"):
                try:
                    df_raw = pd.read_csv(path, sep=sep, header=None, nrows=12, encoding="latin1")
                    ok = False
                    for i in range(min(10, len(df_raw))):
                        if tem_colunas_minimas(df_raw.iloc[i].tolist()):
                            ok = True
                            break
                    if ok:
                        return True

                    for h in range(0, 10):
                        try:
                            df_try = pd.read_csv(path, sep=sep, header=h, nrows=5, encoding="latin1")
                            if tem_colunas_minimas(df_try.columns):
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
    except Exception:
        pass

    # Mantém tolerante: deixa o Orchestrator decidir
    return True


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    logging.getLogger(__name__).setLevel(logging.INFO)
    logging.info("Entrou na rota /upload - method: %s", request.method)

    if False:
        logging.info("🚫 Usuário não está logado. Redirecionando para /login")
        flash("Faça login para acessar essa página.", "warning")
        return redirect(url_for("auth_routes.login"))

    if request.method == "POST":
        logging.info("📨 Requisição POST recebida")

        if "file" not in request.files:
            logging.info("❌ Nenhum arquivo enviado no request.")
            flash("Nenhum arquivo enviado.", "danger")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            logging.info("❌ Nenhum arquivo selecionado.")
            flash("Nenhum arquivo selecionado.", "danger")
            return redirect(request.url)

        if file and arquivo_permitido(file.filename, ALLOWED_EXTENSIONS):
            original_name = secure_filename(file.filename)
            name, ext = os.path.splitext(original_name)
            unique_name = f"{name}-{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_name)
            file.save(filepath)
            logging.info("✅ Arquivo salvo: %s (original: %s)", filepath, original_name)

            # valida a estrutura do arquivo do usuário
            if not _estrutura_minima_ok(filepath):
                msg = "Estrutura do arquivo inválida. Campos obrigatórios ausentes (ex.: 'Ativo', 'Abertura')."
                if request.path.endswith("_inline"):
                    return jsonify({"status": "erro", "mensagem": msg}), 400
                flash(msg, "danger")
                return redirect(request.url)

            # Registrar upload no banco
            owner = str(session.get("user", "anonimo"))
            ext_lower = ext.lower()
            filetype = "xlsx" if ext_lower == ".xlsx" else "csv"

            upload_row = register_upload(
                owner=owner,
                filename=unique_name,
                path=os.path.abspath(filepath),
                filetype=filetype,
                size_bytes=os.path.getsize(filepath),
                checksum=_md5(filepath),
            )

            # Estratégia: usa a existente OU cria automaticamente e anexa este upload
            strategy_id = request.form.get("strategy_id") or request.args.get("strategy_id")
            if not strategy_id:
                strategy = create_strategy({
                    "nome": original_name,
                    "ativo": None,   # podemos extrair do arquivo futuramente
                    "owner": owner,
                    "status": "draft"
                })
                strategy_id = strategy["id"]
                logging.info("🆕 Strategy criada automaticamente: id=%s nome=%s", strategy_id, original_name)

            # Anexa upload à estratégia
            attach_upload(int(strategy_id), upload_row["id"])

            # ====== LOCK + processamento ======
            usuario = session.get("user", "anonimo")
            temp_path, user_id = criar_diretorio_resultado(usuario)
            session["user_id"] = str(user_id)
            session["temp_path"] = str(temp_path)  # ✅ sessão só com strings

            lock_created = False
            try:
                create_processing_lock(str(temp_path)); lock_created = True
                logging.info("🚧 Lock criado em %s/.processing.lock", temp_path)

                logging.info("🔍 Iniciando processamento com InsightFutures...")
                insight = InsightFutures(filepath)

                salvar_todos_resultados(insight, str(temp_path))

                # salva na sessão (compat)
                session["json_path"] = os.path.join(str(temp_path), "ultimo_resultado.json")
                session["filepath"] = os.path.abspath(filepath)

                # persistir result_dir no upload (POR UPLOAD)
                try:
                    update_upload_result_dir(int(upload_row["id"]), str(temp_path))
                    logging.info("💾 result_dir salvo no upload %s: %s", upload_row["id"], temp_path)
                except Exception:
                    logging.exception("Falha ao salvar result_dir no upload %s", upload_row["id"])

                # gerar thumb específica deste upload
                df = getattr(insight, "data", None)
                if df is None or getattr(df, "empty", False):
                    logging.info("⚠️ DataFrame vazio ou inválido após processamento.")
                    flash("O processamento falhou. O arquivo pode estar com estrutura inválida.", "danger")
                    return redirect(request.url)
                try:
                    _save_upload_thumb(int(upload_row["id"]), df)
                except Exception:
                    logging.exception("Falha ao gerar thumb do upload %s", upload_row["id"])

                logging.info("✅ Processamento concluído")
                flash("Análise concluída! Veja os resultados abaixo.", "success")
                logging.info("➡️ Redirecionando para /painel")
                return redirect(url_for("painel_routes.analise_pre", upload_id=upload_row["id"]))

            except Exception:
                logging.exception("💥 Erro durante o processamento:")
                flash("Erro ao processar o arquivo.", "danger")
                return redirect(request.url)

            finally:
                if lock_created:
                    clear_processing_lock(str(temp_path))
                    logging.info("✅ Lock removido de %s/.processing.lock", temp_path)
        else:
            flash("Formato de arquivo não permitido.", "danger")
            return redirect(request.url)

    logging.info("🖼️ Renderizando templates upload.html")
    strategies = list_strategy_cards(owner=session.get("user"))
    return render_template("painel/upload.html", strategies=strategies)


@bp.route("/upload_inline", methods=["POST"])
def upload_inline():
    if "file" not in request.files:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo enviado."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo selecionado."}), 400

    if file and arquivo_permitido(file.filename, ALLOWED_EXTENSIONS):
        original_name = secure_filename(file.filename)
        name, ext = os.path.splitext(original_name)
        unique_name = f"{name}-{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(filepath)
        logging.info("✅ Arquivo salvo: %s (original: %s)", filepath, original_name)

        # valida a estrutura do arquivo do usuário
        if not _estrutura_minima_ok(filepath):
            msg = "Estrutura do arquivo inválida. Campos obrigatórios ausentes (ex.: 'Ativo', 'Abertura')."
            if request.path.endswith("_inline"):
                return jsonify({"status": "erro", "mensagem": msg}), 400
            flash(msg, "danger")
            return redirect(request.url)

        owner = str(session.get("user", "anonimo"))
        upload_row = register_upload(
            owner=owner,
            filename=unique_name,
            path=os.path.abspath(filepath),
            filetype=("xlsx" if unique_name.lower().endswith(".xlsx") else "csv"),
            size_bytes=os.path.getsize(filepath),
            checksum=_md5(filepath),
        )
        logging.info("📚 Upload registrado no DB: id=%s", upload_row["id"])

        # Estratégia: usa a existente OU cria automaticamente e anexa este upload
        strategy_id = request.form.get("strategy_id") or request.args.get("strategy_id")
        if not strategy_id:
            strategy = create_strategy({
                "nome": original_name,
                "ativo": None,   # podemos extrair do arquivo futuramente
                "owner": owner,
                "status": "draft"
            })
            strategy_id = strategy["id"]
            logging.info("🆕 Strategy criada automaticamente (inline): id=%s nome=%s", strategy_id, original_name)

        # Anexa upload à estratégia
        if attach_upload(int(strategy_id), upload_row["id"]):
            logging.info("📎 Upload %s anexado à estratégia %s", upload_row["id"], strategy_id)
        else:
            logging.warning("⚠️ Falha ao anexar upload à estratégia %s", strategy_id)

        # ====== LOCK + processamento ======
        usuario = session.get("user", "anonimo")
        temp_path, user_id = criar_diretorio_resultado(usuario)
        session["user_id"] = str(user_id)
        session["temp_path"] = str(temp_path)

        lock_created = False
        try:
            create_processing_lock(str(temp_path)); lock_created = True
            logging.info("🚧 Lock criado em %s/.processing.lock", temp_path)

            insight = InsightFutures(filepath)
            salvar_todos_resultados(insight, str(temp_path))

            # salva na sessão (compat)
            session["json_path"] = os.path.join(str(temp_path), "ultimo_resultado.json")
            session["filepath"] = os.path.abspath(filepath)

            # persistir result_dir no upload (POR UPLOAD)
            try:
                update_upload_result_dir(int(upload_row["id"]), str(temp_path))
                logging.info("💾 result_dir salvo no upload %s: %s", upload_row["id"], temp_path)
            except Exception:
                logging.exception("Falha ao salvar result_dir no upload %s", upload_row["id"])

            # gerar thumb específica deste upload
            try:
                df = getattr(insight, "data", None)
                if df is not None and not getattr(df, "empty", False):
                    _save_upload_thumb(int(upload_row["id"]), df)
            except Exception:
                logging.exception("Falha ao gerar thumb do upload %s (inline)", upload_row["id"])

            logging.info("✅ Processamento concluído")

            return jsonify({
                "status": "ok",
                "mensagem": "Arquivo processado com sucesso!",
                "redirect": url_for("painel_routes.dashboard"),
                "temp_path": str(temp_path)
            }), 200


        # em web/routes/upload_routes.py, dentro de upload_inline()

        except Exception as e:

            logging.exception("Erro no processamento")

            return jsonify({

                "status": "erro",

                "mensagem": f"{type(e).__name__}: {e}"

            }), 400


        finally:
            if lock_created:
                clear_processing_lock(str(temp_path))
                logging.info("✅ Lock removido de %s/.processing.lock", temp_path)

    return jsonify({"status": "erro", "mensagem": "Formato de arquivo não permitido."}), 400


# --- READY CHECK -------------------------------------------------------------
REQUIRED_FILES = [
    "ativos.json",
    "parametros_ativo.json",
    "estatisticas_ciclo_emprestimo.json",
    "estatisticas_ciclo_amortizacao.json",
    "estatisticas_ciclo_lucro.json",
    "estats_qtd_emp_ciclo.json",
    "estats_qtd_amo_ciclo.json",
    "estats_qtd_luc_ciclo.json",
]

@bp.get("/api/process/ready")
def process_ready():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"ready": False, "reason": "no_temp_path"}), 200

    locked = is_processing_locked(temp_path)
    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(temp_path, f))]
    ready = (not locked) and (len(missing) == 0)

    return jsonify({
        "ready": ready,
        "locked": locked,
        "missing": missing,
        "temp_path": temp_path,
    }), 200

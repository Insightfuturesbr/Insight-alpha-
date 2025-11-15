from flask import Blueprint, request, flash, session, redirect, url_for, jsonify, render_template, current_app
from datetime import timedelta

bp = Blueprint("auth_routes", __name__)

@bp.before_app_request
def make_session_permanent():
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(hours=6)


@bp.route("/login_api", methods=["POST"])
def login_api():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == "admin" and password == "123":
        session["user"] = username
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'erro', 'mensagem': 'Usuário ou senha incorretos'})


# 📌 Logout
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("public_routes.home"))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Aqui você pode adicionar lógica de salvar no banco, se quiser.
        session['user'] = username  # Simulando o login
        return jsonify({'status': 'ok'})  # Retorna JSON em vez de redirect

    return render_template("register.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Simulação de usuário (troque por validação real)
        if username == "admin" and password == "123":
            session["user"] = username  # ✅ Agora correto

            flash("Login bem-sucedido!", "success")
            return redirect(url_for("upload_routes.upload"))  # 👈 Redireciona para upload após login
        else:
            flash("Usuário ou senha incorretos", "error")

    # 🧠 Retorna a tela de login se for GET ou se o login falhar
    return render_template("login.html")
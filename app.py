from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests  # 👈 novo
import os
import json
import datetime 



app = Flask(__name__)


MELI_CLIENT_ID = "6251319117668473"
MELI_CLIENT_SECRET = "FBy99j4vTBEtF9reEuLUJTp061MXPagv"
MELI_REDIRECT_URI = "https://d3b2-2804-7f0-9740-8f8a-45b0-330b-4100-5991.ngrok-free.app/callback"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MELI_TOKENS_JS_PATH = os.path.join(BASE_DIR, "meli_tokens.js")




def criar_conexao():
    conexao = mysql.connector.connect(
        host="localhost",
        user="root",          
        password="",          
        database="faculdade"
    )
    return conexao





@app.route("/")
def inicio():
    return redirect(url_for("login"))






@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None

    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        # buscar usuário no banco
        conexao = criar_conexao()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, nome, email, senha_hash FROM usuarios WHERE email = %s AND ativo = 1",
            (email,)
        )
        usuario = cursor.fetchone()

        cursor.close()
        conexao.close()

        # conferir senha
        if usuario and check_password_hash(usuario["senha_hash"], senha):
            # depois a gente coloca sessão, por enquanto só manda pro painel
            return redirect(url_for("painel"))
        else:
            erro = "email ou senha estao errados"

    return render_template("login.html", erro=erro)






@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    erro = None
    mensagem = None

    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        # validação bem simples
        if not nome or not email or not senha:
            erro = "PREENCHA TODOS OS CAMPOSSSSSSSS."
        else:
            conexao = criar_conexao()
            cursor = conexao.cursor(dictionary=True)

            # ver se já existe e-mail
            cursor.execute(
                "SELECT id FROM usuarios WHEREE email = %s",
                (email,)
            )
            existente = cursor.fetchone()

            if existente:
                erro = "ja existe usuário com esse e-mail."
            else:
                senha_hash = generate_password_hash(senha)

                cursor.execute(
                    "INSERT INTO usuarios (nome, email, senha_hash) VALUES (%s, %s, %s)",
                    (nome, email, senha_hash)
                )
                conexao.commit()

                mensagem = "usuario criado"

            cursor.close()
            conexao.close()

    return render_template("registrar.html", erro=erro, mensagem=mensagem)


@app.route("/painel")
def painel():
    return render_template("painel.html")





@app.route("/conectar_mercado_livre")
def conectar_mercado_livre():
    auth_url = (
        "https://auth.mercadolibre.com/authorization"
        f"?response_type=code&client_id={MELI_CLIENT_ID}&redirect_uri={MELI_REDIRECT_URI}"
    )
    return redirect(auth_url)






@app.route("/callback")
def callback_mercado_livre():
    code = request.args.get("code")

    if not code:
        return "Erro: nenhum código foi recebido do Mercado Livre.", 400

    dados = {
        "grant_type": "authorization_code",
        "client_id": MELI_CLIENT_ID,
        "client_secret": MELI_CLIENT_SECRET,
        "code": code,
        "redirect_uri": MELI_REDIRECT_URI,
    }

    resposta = requests.post("https://api.mercadolibre.com/oauth/token", data=dados)

    if resposta.status_code != 200:
        return f"Erro ao obter token: {resposta.status_code} - {resposta.text}", 500

    token_info = resposta.json()

    dados_para_salvar = {
        "access_token": token_info.get("access_token"),
        "refresh_token": token_info.get("refresh_token"),
        "user_id": token_info.get("user_id"),
        "expires_in": token_info.get("expires_in"),
        "scope": token_info.get("scope"),
        "criado_em": "gerado_pelo_callback"
    }

    try:
        with open(MELI_TOKENS_JS_PATH, "w", encoding="utf-8") as f:
            f.write("Arquivo gerado\n")
            f.write("module.exports = ")
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
            f.write(";\n")
    except Exception as e:
        return f"erro {e}", 500

    html = f"""
    <h1>Tokens oks</h1>
    <p>Arquivo: <code>{MELI_TOKENS_JS_PATH}</code></p>
    <pre>{json.dumps(dados_para_salvar, indent=2, ensure_ascii=False)}</pre>
    <p></p>
    <p><a href="/painel">Voltar para o painel</a></p>
    """
    return html


# O callback do Mercado Lvire está configurado para devolver na URL pública do ngrok (dominio temporario).
# Como a URL do ngrok muda toda hora, sempre que for criar um túnel novo é preciso atualizar a MELI_REDIRECT_URI

# O Mercado Livre não permite usar localhost (127.0.0.1) direto como URL de callback,
# por conta disso usei o ngrok: ele recebe a requisição externa e repassa para 127.0.0.1:5000 onde o Flask está rodando.
# mas quando for conectar para solicitar o token é necessário alterar manualmente o ip do ngrok no navegador para o ip localmente

if __name__ == "__main__":
    app.run(debug=True)

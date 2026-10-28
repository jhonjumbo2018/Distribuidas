from flask import Blueprint, request, jsonify
from flask_cors import CORS
import secrets
import pytds
import certifi
import os
from datetime import datetime, timedelta

token_bp = Blueprint("token", __name__)

token_actual = None
expiracion_token = None

def getConnection():
    return pytds.connect(
        server=os.environ["DB_SERVER"],
        database=os.environ["DB_DATABASE"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        port=1433,
        cafile=certifi.where(),
        validate_host=True
    )

def generar_token():
    return secrets.token_urlsafe(32)

@token_bp.route("/token", methods=["POST"])
def obtener_token():
    global token_actual, expiracion_token

    data = request.get_json()
    usuario = data.get("usuario")
    password = data.get("password")

    conn = getConnection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT ID FROM dbo.USERS WHERE USUARIO = %s AND [PASSWORD] = %s",
        (usuario, password)
    )

    usuario_encontrado = cursor.fetchone()

    cursor.close()
    conn.close()

    if not usuario_encontrado:
        return jsonify({
            "error": "Usuario o contraseña incorrectos"
        }), 401

    token_actual = generar_token()
    expiracion_token = datetime.utcnow() + timedelta(seconds=20)

    return jsonify({
        "token": token_actual,
        "expiracion": expiracion_token.isoformat() + "Z"
    })

def validar_token():
    global token_actual, expiracion_token

    if token_actual is None or expiracion_token is None:
        return False

    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        return False

    token = auth[7:]

    if token != token_actual:
        return False

    if datetime.utcnow() > expiracion_token:
        return False

    return True

@token_bp.route("/")
def inicio():
    return jsonify({
        "mensaje": "Api funcionando correctamente"
    })

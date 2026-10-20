import pytds
import certifi
import requests
from flask import Flask, jsonify, request
import os

app = Flask(__name__)

def getConnection():
    return pytds.connect(
        server = os.environ["DB_SERVER"],
        database = os.environ["DB_DATABASE"],
        user = os.environ["DB_USER"],
        password = os.environ["DB_PASS"],
        port = 1433,
        cafile = certifi.where(),
        validate_host = True,
        row_strategy = pytds.namedtuple_row_strategy,
    )

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("SELECT DB_NAME()")
        database = cursor.fetchone()[0]
        conn.close()

        return jsonify(
            {
                "message": "Conexión exitosa a la base de datos", 
                "base de datos": database
            }
        ), 200
    
    except Exception as e:
        return jsonify({"message": "Error al conectar a la base de datos", "error": str(e)}), 500

@app.route('/api/products/', methods=['GET'])
def get_products():
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("""SELECT id, names, price, stock, version from vw_Products""")
        products = []

        for row in cursor.fetchall():
            products.append({
                "id": row.id,
                "name": row.names,
                "price": row.price,
                "stock": row.stock,
                "version": row.version
            })
        cursor.close()
        conn.close()

        return jsonify(products), 200

    except Exception as e:
        return jsonify({"message": "Error al obtener los productos", "error": str(e)}), 500

@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    try:
        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute("""SELECT id, names, price, stock from products_vw WHERE id = ?""",id)
        row = cursor.fetchone()

        if row:
            return jsonify({
                "id": row.id,
                "name": row.names,
                "price": row.price,
                "stock": row.stock,
                "version": row.version
            }), 200

        cursor.close()
        conn.close()

        return jsonify({"message": "Producto no encontrado"}), 404
    except Exception as e:
        return jsonify({"message": "Error al obtener el producto", "error": str(e)}), 500

@app.route('/api/products/', methods=['POST'])
def create_product():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "Se requiere un cuerpo en formato JSON"}), 400

        names = data.get('name') 
        price = data.get('price')
        stock = data.get('stock')
        if not names or price is None or stock is None:
            return jsonify({"message": "Faltan datos requeridos (name, price, stock)"}), 400

        conn = getConnection()
        cursor = conn.cursor()

        cursor.execute(
            "EXEC [dbo].[products_inser_sp] @names=?, @price=?, @stock=?", 
            (names, price, stock)
        )
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"mensaje": "Producto creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"mensaje": "Error interno del servidor", "error": str(e)}), 500

import time

@app.route("/api/products", methods=['PUT'])
def update_products():
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    'error':'Sin data'
                })
            conn=getConnection()
            cursor=conn.cursor()
            time.sleep(5)
            cursor.execute("UPDATE products set names=?, price=?, stock=? where id=?", 
                           data.get('names'), data.get('price'), data.get('stock'), data.get('id'))
            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({
                    'msg':'Registro no encontrado'
                }),404
            
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({
                'mensaje':'Producto actualizado exitosamente'
            })
        except Exception as e:
            return jsonify({
                'error':'Error al actualizar',
                'msg': str(e)
            })
import time
import threading
product_lock=threading.Lock()
@app.route("/api/products/lock", methods=['PUT'])
def update_lock():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Datos inválidos"}), 400

        with product_lock:
            print("Entra al bloqueo")

            conn = getConnection()
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET names = ?, price = ?, stock = ? WHERE id = ?",
                            data.get('names'), float(data.get('price')), int(data.get('stock')), int(data.get('id')));

            if cursor.rowcount == 0:
                conn.rollback()
                cursor.close()
                conn.close()

                return jsonify({"message": "Producto no encontrado"}), 404

            conn.commit()
            cursor.close() 
            conn.close()
            

            print("Sale del bloqueo")

            return jsonify({"message": "Producto actualizado exitosamente con bloqueo"}), 200
    except Exception as e:
        return jsonify({"message": "Error al actualizar el producto con bloqueo", "error": str(e)}), 500

@app.route("/api/products/version", methods=['PUT'])
def update_version():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "msg":"Datos imcompletos"
            }),400
        if data.get("version") is None:
            return jsonify({
                "msg":"Falta parametros(version)"
            }),400
        conn=getConnection()
        cursor=conn.cursor()
        cursor.execute("UPDATE products set names=?, price=?, stock=?, version=version+1 where id=? and version=?", 
                       data.get('names'), data.get('price'), data.get('stock'), data.get('id'), data.get('version'))
        if cursor.rowcount == 0:
            cursor.execute("SELECT version from products where id=?", data.get('id'))
            row = cursor.fetchone()
            conn.rollback()
            cursor.close()
            conn.close()
            if row:
                producto_actual={
                    "id": data.get('id'),
                    "version": row.version
                }
                return jsonify({
                    "msg":"Ya actualizaron este registro",
                    "error":producto_actual
                }),409
            return jsonify({
                "msg":"Producto no encontrado"
            }),404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "msg":"Producto actualizado con exito"
        }),200
    
    except Exception as e:
        return jsonify({"msg": "Error al actualizar", "error": str(e)}), 500

@app.route('/api/send-email', methods=['POST'])
def send_email():
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "api-key": os.environ["BREVO_API_KEY"],
            "content-type": "application/json"
        }
        
        # ATENCIÓN: El "email" del sender DEBE ser tu correo registrado en Brevo
        payload = {
            "sender": {"name": "Mi Sitio Web", "email": "9da17e001@smtp-brevo.com"},
            "to": [{"email": "shinjilouch@gmail.com", "name": "Admin"}],
            "subject": "Nueva notificación desde WordPress",
            "htmlContent": "<html><body><h1>¡Han presionado el botón en la web!</h1><p>Revisa tu sistema.</p></body></html>"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            return jsonify({"message": "Correo enviado con éxito"}), 200
        else:
            return jsonify({"message": "Error en Brevo", "detalle": response.json()}), 400
            
    except Exception as e:
        return jsonify({"message": "Error interno al enviar correo", "error": str(e)}), 500
if __name__ == '__main__':
    app.run(
        host='0.0.0.0', port=5000, debug=True
    )
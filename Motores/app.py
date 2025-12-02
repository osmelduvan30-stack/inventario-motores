from flask import Flask, render_template, request, redirect, send_from_directory
import sqlite3
import qrcode
import os
from datetime import datetime

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
app = Flask(__name__)

ADMIN_PASSWORD = "1234"   # Cambiar si quieres

# =====================================================
# CONEXIÓN A BD
# =====================================================
def obtener_conexion():
    return sqlite3.connect("motores.db")

def crear_base():
    con = obtener_conexion()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS motores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            marca TEXT,
            potencia TEXT,
            frame TEXT,
            ubicacion TEXT,
            estado TEXT,
            fecha TEXT,
            observaciones TEXT,
            qr TEXT
        )
    """)
    con.commit()
    con.close()

crear_base()


# =====================================================
# RUTA: LOGIN ADMIN
# =====================================================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            return redirect("/admin_inventario")
        return render_template("login.html", error="Contraseña incorrecta")

    return render_template("login.html")


# =====================================================
# RUTA: INVENTARIO ADMIN
# =====================================================
@app.route("/admin_inventario")
def admin_inventario():
    con = obtener_conexion()
    cur = con.cursor()
    cur.execute("SELECT * FROM motores")
    motores = cur.fetchall()
    con.close()
    return render_template("inventario_admin.html", motores=motores)


# =====================================================
# RUTA: INVENTARIO PÚBLICO
# =====================================================
@app.route("/")
@app.route("/inventario")
def inventario_publico():
    q = request.args.get("q", "")
    con = obtener_conexion()
    cur = con.cursor()
    if q:
        cur.execute("SELECT * FROM motores WHERE codigo LIKE ? OR potencia LIKE ?", (f"%{q}%", f"%{q}%"))
    else:
        cur.execute("SELECT * FROM motores")
    motores = cur.fetchall()
    con.close()
    return render_template("inventario_publico.html", motores=motores, q=q)


# =====================================================
# RUTA: REGISTRAR MOTOR
# =====================================================
@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        codigo = request.form["codigo"]
        marca = request.form["marca"]
        potencia = request.form["potencia"]
        frame = request.form["frame"]
        ubicacion = request.form["ubicacion"]
        estado = request.form["estado"]
        obs = request.form["observaciones"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ==== URL DE RENDER QUE SE ABRE DESDE EL QR ====
        # Reemplaza ESTE dominio con el que Render te dará
        BASE_URL = "https://TU_DOMINIO.onrender.com"

        url_qr = f"{BASE_URL}/retiro/{codigo}"

        # Crear carpeta QR si no existe
        if not os.path.exists("qr_codes"):
            os.makedirs("qr_codes")

        qr_path = f"qr_codes/{codigo}.png"
        img = qrcode.make(url_qr)
        img.save(qr_path)

        # Guardar en BD
        con = obtener_conexion()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO motores (codigo, marca, potencia, frame, ubicacion, estado, fecha, observaciones, qr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, marca, potencia, frame, ubicacion, estado, fecha, obs, qr_path))
        con.commit()
        con.close()

        return redirect("/admin_inventario")

    return render_template("registrar.html")


# =====================================================
# RUTA: RETIRO DE MOTOR (ESCANEADO DESDE QR)
# =====================================================
@app.route("/retiro/<codigo>", methods=["GET", "POST"])
def retiro(codigo):
    con = obtener_conexion()
    cur = con.cursor()
    cur.execute("SELECT * FROM motores WHERE codigo=?", (codigo,))
    motor = cur.fetchone()

    if not motor:
        return "Motor no encontrado"

    if request.method == "POST":
        nueva_ubicacion = request.form["ubicacion"]
        nuevo_estado = request.form["estado"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            UPDATE motores SET ubicacion=?, estado=?, fecha=?
            WHERE codigo=?
        """, (nueva_ubicacion, nuevo_estado, fecha, codigo))
        con.commit()
        con.close()

        return f"Registro actualizado correctamente para el motor {codigo}"

    return render_template("retiro.html", motor=motor)


# =====================================================
# ELIMINAR MOTOR
# =====================================================
@app.route("/eliminar/<int:id>")
def eliminar(id):
    con = obtener_conexion()
    cur = con.cursor()

    cur.execute("SELECT qr FROM motores WHERE id=?", (id,))
    qr = cur.fetchone()

    if qr and os.path.exists(qr[0]):
        os.remove(qr[0])

    cur.execute("DELETE FROM motores WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect("/admin_inventario")


# =====================================================
# SERVIR QRs
# =====================================================
@app.route("/qr_codes/<path:filename>")
def qr_codes(filename):
    return send_from_directory("qr_codes", filename)


# =====================================================
# RUN (solo local)
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)






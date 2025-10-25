from flask import Flask, render_template, request, jsonify
import numpy as np
import cv2
import re
import traceback

app = Flask(__name__)

# Tamaño máximo (súbelo si usas fotos enormes)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

URL_REGEX = re.compile(r'^(https?://|www\.)[^\s/$.?#].[^\s]*$', re.IGNORECASE)

def decode_qr_cv2(image_bgr):
    detector = cv2.QRCodeDetector()
    # Multi-QR (si está disponible en tu OpenCV)
    try:
        ok, decoded, points, _ = detector.detectAndDecodeMulti(image_bgr)
        if ok and decoded:
            return [d for d in decoded if d]
    except Exception:
        pass
    # Fallback a único
    data, points, _ = detector.detectAndDecode(image_bgr)
    return [data] if data else []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No se envió archivo"}), 400
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"ok": False, "error": "Archivo vacío"}), 400

        raw = file.read()
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"ok": False, "error": "No se pudo leer la imagen (formato no válido)"}), 400

        results = decode_qr_cv2(img)
        if not results:
            return jsonify({"ok": True, "qr_data": [], "message": "No se detectaron códigos QR"}), 200

        first = results[0].strip()
        if URL_REGEX.match(first):
            if first.lower().startswith("www."):
                first = "https://" + first
            return jsonify({"ok": True, "redirect_url": first, "qr_data": results}), 200

        return jsonify({"ok": True, "qr_data": results}), 200

    except Exception as e:
        print("ERROR en /upload:", e)
        traceback.print_exc()
        return jsonify({"ok": False, "error": "Error interno procesando la imagen"}), 500

# --- Handlers para que SIEMPRE sean JSON, incluso en errores del servidor ---
@app.errorhandler(413)
def too_large(e):
    return jsonify({"ok": False, "error": "La imagen excede el límite de tamaño (MAX_CONTENT_LENGTH)."}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Ruta no encontrada."}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"ok": False, "error": "Método HTTP no permitido."}), 405

@app.errorhandler(Exception)
def all_errors(e):
    # Si algo se escapó fuera de /upload, igual devolvemos JSON
    print("ERROR no controlado:", e)
    traceback.print_exc()
    return jsonify({"ok": False, "error": "Fallo inesperado en el servidor."}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)




import logging
import sys
import traceback
from flask import Flask, request, send_file, jsonify, render_template

from translate_service import translate_image_to_text
from pdf_service import create_pdf

# ======================
# Logging
# ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ======================
# LP
# ======================
@app.route('/')
def index():
    return render_template("index.html")


# ======================
# UI（ローディング付き）
# ======================
@app.route('/translate')
def translate_page():
    return render_template("translate.html")


# ======================
# API
# ======================
@app.route('/process', methods=['POST'])
def process():
    try:
        img = request.files['image']
        name = request.form.get("name", "")
        address = request.form.get("address", "")
        doc_type = request.form.get("doc_type", "cenomar")

        image_bytes = img.read()

        data = translate_image_to_text(image_bytes, doc_type)
        pdf = create_pdf(data, name, address, doc_type)

        return send_file(pdf, mimetype='application/pdf')

    except Exception as e:
        traceback.print_exc()
        error_str = str(e)

        # ★ここが重要
        if "混雑" in error_str:
            return jsonify({"error": "現在アクセスが集中しています。少し待って再度お試しください"}), 503

        return jsonify({"error": error_str}), 500


# ======================
# Run
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
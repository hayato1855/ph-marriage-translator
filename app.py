import os
import io
import logging
import sys
import time
import traceback
import json
from flask import Flask, request, send_file, jsonify, Response
from google import genai
from google.genai import types
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

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
# ENV
# ======================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# ======================
# Font
# ======================
FONT_NAME = "NotoSansJP"
FONT_PATH = "NotoSansJP-Regular.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
else:
    FONT_NAME = "Helvetica"

# ======================
# Gemini
# ======================
def translate_image_to_text(image_bytes, mime_type):
    prompt = """
画像はフィリピンの独身証明書（CENOMAR）です。
JSON形式で情報を抽出し、日本語に翻訳してください。
JSONのみ返してください。

{
  "title": "",
  "country": "",
  "agency": "",
  "location": "",
  "office": "",
  "date": "",
  "body": "",
  "sign_name": "",
  "sign_title": "",
  "sign_org": ""
}
"""

    for _ in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type
                            )
                        ]
                    )
                ]
            )

            text = res.text.strip()

            if text.startswith("```"):
                text = text.replace("```json", "").replace("```", "").strip()

            return json.loads(text)

        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            time.sleep(1)

    raise Exception("AIエラー")

# ======================
# PDF生成
# ======================
def create_pdf(data, name="", address=""):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    left = 50
    right = width - 50
    center = width / 2

    y = height - 60

    c.setFont(FONT_NAME, 12)
    c.drawString(left, y, data.get("title", ""))
    c.drawRightString(right, y, data.get("date", ""))

    y -= 30

    c.setFont(FONT_NAME, 13)
    for key in ["country", "agency", "location", "office"]:
        c.drawCentredString(center, y, data.get(key, ""))
        y -= 20

    y -= 20

    c.setFont(FONT_NAME, 11)
    for line in data.get("body", "").split("\n"):
        c.drawString(left, y, line)
        y -= 15

    # 署名
    sign_y = 150
    c.drawRightString(right, sign_y, data.get("sign_name", ""))
    sign_y -= 15
    c.drawRightString(right, sign_y, data.get("sign_title", ""))
    sign_y -= 15
    c.drawRightString(right, sign_y, data.get("sign_org", ""))

    # 翻訳情報
    footer_y = 100
    today = datetime.now().strftime("%Y年%m月%d日")

    c.drawString(left, footer_y, f"翻訳日: {today}")
    footer_y -= 15
    c.drawString(left, footer_y, f"翻訳者: {name}")
    footer_y -= 15
    c.drawString(left, footer_y, f"住所: {address}")

    c.save()
    buffer.seek(0)
    return buffer

# ======================
# LP + UI
# ======================
@app.route('/')
def index():
    return Response("""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI翻訳サービス</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-gray-100">

<!-- 警告バナー -->
<div id="warning" class="hidden bg-red-500 text-white text-center p-3">
⚠ LINE内ブラウザではPDF保存ができない場合があります。<br>
右上メニューから「ブラウザで開く」を選択してください。
</div>

<div class="max-w-xl mx-auto mt-10 bg-white p-6 rounded-xl shadow">

<h1 class="text-2xl font-bold text-center mb-4">
📄 AI翻訳サービス
</h1>

<p class="text-center mb-6 text-gray-600">
画像をアップロードするだけで日本語PDFを生成します
</p>

<form id="form" class="space-y-3">
<input type="file" id="file" accept="image/*" class="w-full">
<input type="text" id="name" placeholder="翻訳者名" class="w-full border p-2 rounded">
<input type="text" id="address" placeholder="住所" class="w-full border p-2 rounded">

<button class="w-full bg-blue-600 text-white p-2 rounded">
PDF生成
</button>
</form>

<p id="error" class="text-red-500 mt-3 text-sm"></p>

</div>

<script>
// ======================
// LINE内ブラウザ検知
// ======================
if (navigator.userAgent.includes("Line")) {
  document.getElementById("warning").classList.remove("hidden");
}

// ======================
// 外部ブラウザ強制誘導
// ======================
const params = new URLSearchParams(window.location.search);

if (!params.get("openExternalBrowser") && navigator.userAgent.includes("Line")) {
  const url = window.location.href + "?openExternalBrowser=1";
  window.location.href = url;
}

// ======================
// フォーム送信
// ======================
document.getElementById("form").addEventListener("submit", async e => {
 e.preventDefault()

 const file = document.getElementById("file").files[0]
 const name = document.getElementById("name").value
 const address = document.getElementById("address").value

 if(!file){
  alert("画像を選択してください")
  return
 }

 const fd = new FormData()
 fd.append("image", file)
 fd.append("name", name)
 fd.append("address", address)

 try{
  const res = await fetch("/process",{method:"POST",body:fd})

  if(res.ok){
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)

    const a = document.createElement("a")
    a.href = url
    a.download = "translated.pdf"
    a.click()

  }else{
    const data = await res.json()
    document.getElementById("error").textContent = data.error
  }

 }catch{
  document.getElementById("error").textContent = "通信エラー"
 }
})
</script>

</body>
</html>
""", mimetype='text/html')

# ======================
# API
# ======================
@app.route('/process', methods=['POST'])
def process():
    try:
        img = request.files['image']
        name = request.form.get("name", "")
        address = request.form.get("address", "")

        image_bytes = img.read()

        data = translate_image_to_text(image_bytes, img.content_type)
        pdf = create_pdf(data, name, address)

        return send_file(pdf, mimetype='application/pdf')

    except Exception as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 500

# ======================
# Run
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
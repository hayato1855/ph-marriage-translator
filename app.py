import os
import io
import logging
import sys
import time
import traceback
from flask import Flask, request, send_file, jsonify
from google import genai
from google.genai import types
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import json

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
# Gemini
# ======================
API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    logger.error("❌ GEMINI_API_KEY 未設定")

client = genai.Client(api_key=API_KEY)

# ======================
# Font
# ======================
FONT_NAME = "NotoSansJP"
FONT_PATH = "NotoSansJP-Regular.ttf"

if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
        logger.info("✅ フォント読み込み成功")
    except Exception as e:
        logger.error(f"❌ フォントエラー: {e}")
        FONT_NAME = "Helvetica"
else:
    logger.warning("⚠ フォント未検出 → Helvetica使用")
    FONT_NAME = "Helvetica"

# ======================
# 安定JSON変換
# ======================
def safe_json_parse(text):
    try:
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        logger.error(f"❌ JSONパース失敗: {text}")
        raise Exception("AIの応答形式が不正です")

# ======================
# Gemini
# ======================
def translate_image_to_text(image_bytes):
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

    for attempt in range(3):
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
                                mime_type="image/jpeg"
                            )
                        ]
                    )
                ]
            )

            text = res.text.strip()
            logger.info(f"AIレスポンス: {text[:200]}")

            return safe_json_parse(text)

        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            time.sleep(2 * (attempt + 1))

    raise Exception("AIが混雑しています")

# ======================
# PDF生成
# ======================
def create_pdf(data, name, address):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    left = 50
    right = width - 50
    center = width / 2

    y = height - 60

    # タイトル
    c.setFont(FONT_NAME, 12)
    c.drawString(left, y, data.get("title", ""))

    # 日付
    c.setFont(FONT_NAME, 11)
    c.drawRightString(right, y, data.get("date", ""))

    y -= 25

    # ヘッダー
    c.setFont(FONT_NAME, 13)
    for key in ["country", "agency", "location", "office"]:
        c.drawCentredString(center, y, data.get(key, ""))
        y -= 20

    y -= 40

    # 本文
    c.setFont(FONT_NAME, 11)
    max_width = width - 100

    def split_line(line):
        result = []
        current = ""

        for ch in line:
            try:
                w = pdfmetrics.stringWidth(current + ch, FONT_NAME, 11)
            except:
                w = max_width + 1

            if w <= max_width:
                current += ch
            else:
                if current:
                    result.append(current)
                current = ch

        if current:
            result.append(current)

        return result

    y_text = y

    for line in data.get("body", "").split("\n"):
        for l in split_line(line.strip()):
            if y_text < 200:
                break
            c.drawString(left, y_text, l)
            y_text -= 16

    # 署名
    sign_y = 150
    c.drawRightString(right, sign_y, "署名")
    sign_y -= 20
    c.drawRightString(right, sign_y, data.get("sign_name", ""))
    sign_y -= 18
    c.drawRightString(right, sign_y, data.get("sign_title", ""))
    sign_y -= 18
    c.drawRightString(right, sign_y, data.get("sign_org", ""))

    # フッター
    footer_y = 100
    today = datetime.now().strftime("%Y年%m月%d日")

    c.drawString(left, footer_y, f"翻訳日: {today}")
    footer_y -= 18
    c.drawString(left, footer_y, f"翻訳者: {name}")
    footer_y -= 18
    c.drawString(left, footer_y, f"住所: {address}")

    c.save()
    buffer.seek(0)

    return buffer   # ← これ絶対この中

# ======================
# UI（ローディング付き）
# ======================
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI翻訳</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">

<div class="bg-white p-8 rounded-xl shadow w-96">
<h1 class="text-xl font-bold mb-4 text-center">翻訳PDF生成</h1>

<form id="form">
<input type="file" id="file" class="mb-2">
<input type="text" id="name" placeholder="翻訳者名" class="border p-2 w-full mb-2">
<input type="text" id="address" placeholder="住所" class="border p-2 w-full mb-2">
<button class="bg-blue-600 text-white w-full p-2 rounded">生成</button>
</form>

<p id="error" class="text-red-500 mt-2"></p>
</div>

<!-- ローディング -->
<div id="overlay" class="hidden fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
  <div class="bg-white p-6 rounded-xl w-80 text-center">
    <div class="h-10 w-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
    <p class="mt-4 font-bold">処理中...</p>
  </div>
</div>

<script>
const form = document.getElementById("form")
const overlay = document.getElementById("overlay")
const error = document.getElementById("error")

form.onsubmit = async e=>{
 e.preventDefault()

 const file = document.getElementById("file").files[0]
 const name = document.getElementById("name").value
 const address = document.getElementById("address").value

 if(!file){
  alert("画像を選択してください")
  return
 }

 error.textContent = ""
 overlay.classList.remove("hidden")

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
    // 👇ここが重要（完全対応）
    let msg = "エラーが発生しました"

    try{
      const data = await res.json()
      msg = data.error || msg
    }catch{}

    if(res.status === 503){
      msg = "AIが混雑しています。少し待って再度お試しください"
    }

    if(res.status === 429){
      msg = "利用制限に達しました"
    }

    error.textContent = msg
  }

 }catch(e){
  error.textContent = "通信エラー"
 }

 overlay.classList.add("hidden")
}
</script>
</body>
</html>
"""

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

        data = translate_image_to_text(image_bytes)
        pdf = create_pdf(data, name, address)

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
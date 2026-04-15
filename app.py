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
import re


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
# Translation（安定版）
# ======================
def translate_image_to_text(image_bytes, mime_type):
    prompt = """
画像はフィリピンの独身証明書（CENOMAR）です。

以下のJSON形式で情報を抽出し、
すべて日本語に翻訳してください。

必ずJSONのみ返してください。

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

                            # ★ここが正解（画像を渡す）
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type
                            )
                        ]
                    )
                ]
            )

            if res and res.text:
                text = res.text.strip()

                # ```json 対策
                if text.startswith("```"):
                    text = text.replace("```json", "").replace("```", "").strip()

                return json.loads(text)

            raise Exception("JSON取得失敗")

        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini Error: {error_str}")

            # 混雑
            if "503" in error_str:
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise Exception("AIが混雑しています")

            # 制限
            if "429" in error_str:
                raise Exception("利用制限に達しました")

            # JSONエラー対策
            if "Expecting value" in error_str:
                raise Exception("AIの応答形式が不正です")

            raise e

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

    # タイトル（左）
    c.setFont(FONT_NAME, 12)
    c.drawString(left, y, data.get("title", ""))

    # 日付（右）
    c.setFont(FONT_NAME, 11)
    c.drawRightString(right, y, data.get("date", ""))

    y -= 25

    # 中央ヘッダー
    c.setFont(FONT_NAME, 13)
    c.drawCentredString(center, y, data.get("country", ""))
    y -= 20
    c.drawCentredString(center, y, data.get("agency", ""))
    y -= 20
    c.drawCentredString(center, y, data.get("location", ""))
    y -= 20
    c.drawCentredString(center, y, data.get("office", ""))

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

    # 署名（右）
    sign_y = 150
    c.drawRightString(right, sign_y, "署名")
    sign_y -= 20
    c.drawRightString(right, sign_y, data.get("sign_name", ""))
    sign_y -= 18
    c.drawRightString(right, sign_y, data.get("sign_title", ""))
    sign_y -= 18
    c.drawRightString(right, sign_y, data.get("sign_org", ""))

    # 翻訳情報（左下）
    footer_y = 100
    today = datetime.now().strftime("%Y年%m月%d日")

    c.drawString(left, footer_y, f"翻訳日: {today}")
    footer_y -= 18
    c.drawString(left, footer_y, f"翻訳者: {name}")
    footer_y -= 18
    c.drawString(left, footer_y, f"住所: {address}")

    c.save()
    buffer.seek(0)
    return buffer

# ======================
# UI（そのまま維持）
# ======================
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI Translator</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">

<div class="bg-white p-8 rounded-2xl shadow w-96">
<h1 class="text-xl font-bold mb-4 text-center">翻訳PDF生成</h1>

<form id="form" class="space-y-3">
<input type="file" id="file" accept="image/*" class="w-full">
<input type="text" id="name" placeholder="翻訳者名" class="w-full border p-2 rounded">
<input type="text" id="address" placeholder="住所" class="w-full border p-2 rounded">
<button id="btn" class="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
PDF生成
</button>
</form>

<p id="error" class="text-red-500 mt-3 text-sm"></p>
</div>

<!-- ローディング -->
<div id="overlay" class="hidden fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
<div class="bg-white p-6 rounded-xl w-80 text-center">

<div class="h-10 w-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>

<p id="phase" class="mt-4 font-bold">準備中...</p>

<div class="w-full bg-gray-200 h-3 mt-4 rounded">
<div id="bar" class="h-3 bg-blue-600 w-0"></div>
</div>

<p id="percent" class="text-sm mt-2">0%</p>
<p id="timer" class="text-xs text-gray-500 mt-1">0.0秒</p>

</div>
</div>

<script>
const form = document.getElementById("form")
const error = document.getElementById("error")
const overlay = document.getElementById("overlay")
const btn = document.getElementById("btn")

const phase = document.getElementById("phase")
const bar = document.getElementById("bar")
const percent = document.getElementById("percent")
const timer = document.getElementById("timer")

let interval, timerInt

function startUI(){
 overlay.classList.remove("hidden")
 btn.disabled = true
 btn.textContent = "処理中..."

 let p = 0
 interval = setInterval(()=>{
  if(p < 90){
    p += Math.random()*10
    p = Math.min(p,90)
    bar.style.width = p+"%"
    percent.textContent = Math.floor(p)+"%"
  }
 },500)

 const start = Date.now()
 timerInt = setInterval(()=>{
  timer.textContent = ((Date.now()-start)/1000).toFixed(1)+"秒"
 },100)

 setTimeout(()=>phase.textContent="翻訳中...",1500)
 setTimeout(()=>phase.textContent="PDF生成中...",3500)
}

function endUI(){
 clearInterval(interval)
 clearInterval(timerInt)
 bar.style.width="100%"
 percent.textContent="100%"
 phase.textContent="完了"

 setTimeout(()=>{
  overlay.classList.add("hidden")
  btn.disabled=false
  btn.textContent="PDF生成"
 },800)
}

form.addEventListener("submit", async e=>{
 e.preventDefault()

 const file = document.getElementById("file").files[0]
 const name = document.getElementById("name").value
 const address = document.getElementById("address").value

 if(!file){
  alert("画像を選択してください")
  return
 }

 error.textContent=""
 startUI()

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

    if(res.status===503){
      error.textContent="AIが混雑しています。少し待ってください"
    }else if(res.status===429){
      error.textContent="利用制限に達しました"
    }else{
      error.textContent=data.error
    }
  }

 }catch{
  error.textContent="通信エラー"
 }

 endUI()
})
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
        if 'image' not in request.files:
            return jsonify({"error": "画像がありません"}), 400

        img = request.files['image']

        if img.filename == "":
            return jsonify({"error": "ファイルが選択されていません"}), 400

        name = request.form.get("name", "")
        address = request.form.get("address", "")

        logger.info(f"📥 file: {img.filename}")

        image_bytes = img.read()

        if not image_bytes:
            return jsonify({"error": "ファイルが空です"}), 400

        # ★ここが重要（置き換え）
        data = translate_image_to_text(image_bytes, img.content_type)

        logger.info("✅ 翻訳成功")

        # ★ここもdataに変更
        pdf = create_pdf(data, name, address)

        return send_file(
            pdf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='translated.pdf'
        )

    except Exception as e:
        traceback.print_exc()

        error_str = str(e)
        logger.error(f"❌ ERROR: {error_str}")

        if "混雑" in error_str or "503" in error_str:
            return jsonify({"error": "AIが混雑しています。少し待ってください"}), 503

        if "制限" in error_str or "429" in error_str:
            return jsonify({"error": "利用制限に達しました"}), 429

        return jsonify({"error": f"サーバーエラー: {error_str}"}), 500

# ======================
# Run
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
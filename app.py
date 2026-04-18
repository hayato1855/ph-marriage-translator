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
# LP
# ======================
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="ja" class="scroll-smooth">
<head>
<meta charset="UTF-8">
<title>AI翻訳サービス</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-gray-50 text-gray-800">

<!-- ===== HERO ===== -->
<section class="bg-white text-center py-20 px-6 shadow-sm">
  <h1 class="text-3xl font-bold leading-relaxed">
    フィリピン人との結婚手続きで必要な<br>
    CENOMARを<br>
    <span class="text-blue-600">そのまま提出できる形式で翻訳</span>
  </h1>

  <p class="mt-6 text-gray-600">
    翻訳会社に頼まず、数秒でPDF生成
  </p>

  <a href="/translate"
     class="mt-8 inline-block bg-blue-600 text-white px-8 py-4 rounded-xl text-lg hover:bg-blue-700 shadow">
     無料で翻訳する
  </a>
</section>

<!-- ===== 悩み ===== -->
<section class="bg-gray-50 py-16 px-6">
  <div class="max-w-3xl mx-auto text-center">

    <h2 class="text-xl font-bold mb-8">
      こんな不安はありませんか？
    </h2>

    <div class="flex justify-center">
      <div class="space-y-5 text-gray-700 text-left">

        <div class="flex items-start gap-3">
          <span class="w-6 text-blue-600 font-bold">✔</span>
          <p>CENOMARは何を提出すればいいのか分からない</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 text-blue-600 font-bold">✔</span>
          <p>翻訳会社に依頼すると費用や時間がかかる</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 text-blue-600 font-bold">✔</span>
          <p>自己翻訳で役所に差し戻されないか不安</p>
        </div>

      </div>
    </div>

  </div>
</section>

<!-- ===== 解決 ===== -->
<section class="py-16 px-6">
  <div class="max-w-3xl mx-auto text-center">

    <h2 class="text-xl font-bold mb-6">
      その悩み、このツールで解決できます
    </h2>

    <div class="flex justify-center">
      <div class="space-y-4 text-gray-700 text-left">

        <div class="flex items-start gap-3">
          <span class="w-6 text-green-600 font-bold">✔</span>
          <p>役所提出を想定した翻訳フォーマット</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 text-green-600 font-bold">✔</span>
          <p>翻訳者署名・住所を自動付与</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 text-green-600 font-bold">✔</span>
          <p>PDF形式ですぐ提出可能</p>
        </div>

      </div>
    </div>

  </div>
</section>

<!-- ===== 信頼 ===== -->
<section class="py-16 px-6">
  <div class="max-w-3xl mx-auto text-center">

    <h2 class="text-xl font-bold mb-6">
      安心してご利用いただくために
    </h2>

    <div class="flex justify-center">
      <div class="text-left max-w-2xl">

        <p class="text-gray-700 leading-relaxed">
          本サービスはAIを活用して翻訳を行い、
          公的書類として提出することを想定した形式でPDFを生成します。
        </p>

        <p class="mt-4 text-sm text-gray-500">
          ※翻訳内容の最終確認は必ずご自身で行ってください
        </p>

      </div>
    </div>

  </div>
</section>

<!-- ===== フロー ===== -->
<section class="bg-gray-50 py-16 px-6">
  <div class="max-w-3xl mx-auto text-center">

    <h2 class="text-xl font-bold mb-8">
      ご利用の流れ
    </h2>

    <div class="flex justify-center">
      <div class="space-y-4 text-gray-700 text-left">

        <div class="flex items-start gap-3">
          <span class="w-6 font-bold text-blue-600">①</span>
          <p>証明書画像をアップロード</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 font-bold text-blue-600">②</span>
          <p>AIが内容を解析し、日本語へ翻訳</p>
        </div>

        <div class="flex items-start gap-3">
          <span class="w-6 font-bold text-blue-600">③</span>
          <p>翻訳済みPDFをダウンロードし、そのまま提出可能</p>
        </div>

      </div>
    </div>

  </div>
</section>

<!-- ===== CTA ===== -->
<section class="bg-blue-600 text-white text-center py-16">
  <h2 class="text-xl font-bold mb-6">
    今すぐ無料で翻訳を作成
  </h2>

  <a href="/translate"
     class="bg-white text-blue-600 px-8 py-4 rounded-xl text-lg shadow">
     翻訳を開始
  </a>
</section>

<!-- ===== 規約 ===== -->
<section id="legal" class="bg-white py-16 px-6">
  <h2 class="text-xl font-bold mb-8 text-center">利用規約・プライバシーポリシー</h2>

  <div class="max-w-4xl mx-auto grid md:grid-cols-2 gap-8 text-sm leading-relaxed">

    <div>
      <h3 class="font-bold mb-2">利用規約</h3>

      <p class="font-semibold mt-3">免責事項</p>
      <p>本サービスはAI翻訳です。提出前に必ずご確認ください。責任は負いません。</p>

      <p class="font-semibold mt-3">データの取り扱い</p>
      <p>画像は処理後すぐ削除されます。</p>
    </div>

    <div>
      <h3 class="font-bold mb-2">プライバシーポリシー</h3>

      <p class="font-semibold mt-3">個人情報</p>
      <p>翻訳目的以外では使用しません。</p>

      <p class="font-semibold mt-3">外部サービス</p>
      <p>Google Gemini APIを利用しています。</p>
    </div>

  </div>
</section>

<footer class="text-center p-6 text-sm text-gray-500">
  <a href="#legal" class="text-blue-600 underline">規約を見る</a>
</footer>

</body>
</html>
"""


# ======================
# UI（ローディング付き）
# ======================
@app.route('/translate')
def translate_page():
    return """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI翻訳サービス</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-gray-100 flex items-center justify-center min-h-screen">

<div class="bg-white p-8 rounded-2xl shadow-xl w-96">

<h2 class="text-xl font-bold mb-4 text-center">翻訳PDF生成</h2>

<form id="form">

<input type="file" id="file" class="mb-3 w-full">
<input type="text" id="name" placeholder="翻訳者名" class="border p-2 w-full mb-3">
<input type="text" id="address" placeholder="住所" class="border p-2 w-full mb-3">

<button class="bg-blue-600 text-white w-full p-3 rounded-lg text-lg hover:bg-blue-700">
PDFを生成する
</button>

<p class="text-xs text-gray-500 mt-4 text-center">
ダウンロードすることで
<a href="/#legal" class="text-blue-600 underline">利用規約</a>
に同意したものとみなします
</p>

</form>

<p id="error" class="text-red-500 mt-3 text-center"></p>
</div>

<div id="overlay" class="hidden fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
<div class="bg-white p-6 rounded-xl">
<div class="h-10 w-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin"></div>
</div>
</div>

<script>
const form = document.getElementById("form")
const overlay = document.getElementById("overlay")
const error = document.getElementById("error")

form.onsubmit = async e=>{
 e.preventDefault()

 const file = document.getElementById("file").files[0]
 if(!file){ alert("画像を選択してください"); return }

 overlay.classList.remove("hidden")
 error.textContent = ""

 const fd = new FormData()
 fd.append("image", file)
 fd.append("name", document.getElementById("name").value)
 fd.append("address", document.getElementById("address").value)

 try{
  const res = await fetch("/process",{method:"POST",body:fd})

  if(res.ok){
    const blob = await res.blob()
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = "translated.pdf"
    a.click()
  }else{
    let msg="エラー"
    try{
      const d = await res.json()
      msg=d.error
    }catch{}

    if(res.status===503) msg="AIが混雑しています"
    error.textContent=msg
  }

 }catch{
  error.textContent="通信エラー"
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
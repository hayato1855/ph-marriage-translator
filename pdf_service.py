import io
import os
import logging
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

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
# PDF生成
# ======================
def create_pdf(data, name, address, doc_type="cenomar"):
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

    return buffer
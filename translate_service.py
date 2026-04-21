import os
import time
import logging
from google import genai
from google.genai import types

from utils import safe_json_parse

logger = logging.getLogger(__name__)

# ======================
# Gemini
# ======================
API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    logger.error("❌ GEMINI_API_KEY 未設定")

client = genai.Client(api_key=API_KEY)

# ======================
# Gemini
# ======================
def translate_image_to_text(image_bytes, doc_type="cenomar"):
    if doc_type == "birth_certificate":
        prompt = """
画像はフィリピンの出生証明書です。
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
    else:
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
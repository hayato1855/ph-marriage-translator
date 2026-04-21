import json
import logging

logger = logging.getLogger(__name__)

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
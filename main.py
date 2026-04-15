import sys
from google import genai

# 有料枠を有効にした最新のAPIキー
client = genai.Client(api_key="AIzaSyDOqqcLSXk25bSQ3a5hBh98ciJfwNNn7Tg")

try:
    print("Connecting to the newest model: Gemini 2.5 Flash...") 
    
    response = client.models.generate_content(
        # 2.0ではなく、最新の「2.5」を指定
        model="gemini-2.5-flash", 
        contents="Say 'System success! Gemini 2.5 is online and ready.'"
    )
    
    # 成功結果を保存
    with open("result.txt", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print("--- SUCCESS! ---")
    print("Please open 'result.txt'.")

except Exception as e:
    with open("error_log.txt", "w", encoding="utf-8", errors="replace") as f:
        f.write(str(e))
    print("--- ERROR ---")
    print("Check 'error_log.txt' for details.")
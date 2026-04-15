import sys
from google import genai
from google.genai import types
import PIL.Image

# 1. クライアント設定
client = genai.Client(api_key="AIzaSyDOqqcLSXk25bSQ3a5hBh98ciJfwNNn7Tg")

# 2. 解析したい画像のパス（画像ファイル名を書き換えてください）
image_path = "sample.jpg" 

try:
    print(f"Analyzing {image_path}...")
    
    # 画像の読み込み
    img = PIL.Image.open(image_path)
    
    # 3. 解析の実行
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Please extract all information from this Philippine Marriage Certificate and output it in JSON format. Fields should include: Registry No, Husband's Name, Wife's Name, Date of Marriage, Place of Marriage, etc.",
            img
        ]
    )
    
    # 4. 結果の保存
    with open("analysis_result.json", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print("--- ANALYSIS COMPLETE! ---")
    print("Check 'analysis_result.json' for the extracted data.")

except Exception as e:
    with open("error_log.txt", "w", encoding="utf-8", errors="replace") as f:
        f.write(str(e))
    print("--- ERROR ---")
    print("Check error_log.txt")
import json
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def main():
    # 1. データの読み込み
    try:
        with open("final_submission_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("エラー: final_submission_data.jsonが見つかりません。")
        return

    # 2. PDFの作成
    file_name = "translation_certificate.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    
    # フォントの設定（Mac標準の日本語フォントを指定）
    # フォントの設定（Macで一般的に存在するパスをいくつか試す）
    font_paths = [
        '/System/Library/Fonts/Supplemental/ヒラギノ明朝 ProN W3.ttc',
        '/System/Library/Fonts/ヒラギノ明朝 ProN W3.ttc',
        '/System/Library/Fonts/jpn/Hiragino Mincho ProN.ttc',
        '/Library/Fonts/Arial Unicode.ttf' # 代替案
    ]
    
    success_font = False
    for path in font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont('HeiseiMin-W3', path))
            success_font = True
            break
            
    if not success_font:
        print("エラー: 日本語フォントが見つかりませんでした。font_pathを確認してください。")
        return

    c.setFont('HeiseiMin-W3', 12)

    # 3. 内容の書き込み
    width, height = A4

    # タイトル
    c.setFont('HeiseiMin-W3', 18)
    c.drawCentredString(width/2, height - 30*mm, "訳 文 証 明 書 (CENOMAR)")

    # 本文
    c.setFont('HeiseiMin-W3', 12)
    y = height - 50*mm
    
    lines = [
        f"書類種別： 婚姻記録不在証明書 (CENOMAR)",
        f"対象者氏名： {data['final_data']['name_ja']}",
        f"生年月日： {data['original_data']['birthday']}",
        f"管理番号： {data['original_data']['registry_no']}",
        f"現在の状況： {data['final_data']['status']}",
    ]

    for line in lines:
        c.drawString(30*mm, y, line)
        y -= 10*mm

    # 追記事項（ミドルネーム等）
    if data['final_data']['middle_name_note']:
        c.drawString(30*mm, y, f"備考： {data['final_data']['middle_name_note']}")
        y -= 20*mm
    else:
        y -= 10*mm

    c.drawString(30*mm, y, "上記の内容は、添付された原本の正確な翻訳であることを証明します。")
    
    # 翻訳者情報（右側に寄せる）
    y -= 30*mm
    c.drawString(100*mm, y, f"翻訳日： 2026年4月12日")
    y -= 10*mm
    c.drawString(100*mm, y, f"翻訳者氏名： {data['translator']['name']}")
    y -= 10*mm
    c.drawString(100*mm, y, f"住所： {data['translator']['address']}")

    # 4. 保存
    c.save()
    print(f"--- 成功 ---")
    print(f"提出用PDF '{file_name}' が作成されました！")

if __name__ == "__main__":
    main()
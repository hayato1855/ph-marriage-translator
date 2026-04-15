import json
import os
import re

def main():
    input_file = "analysis_result.json"
    if not os.path.exists(input_file):
        print(f"エラー: {input_file} が見つかりません。")
        return

    # ファイルをテキストとして一旦すべて読み込む
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # --- 強力なクレンジング処理 ---
    # 文字列の中から、最初に見つかる { から 最後に見つかる } までを抽出
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        print("エラー: ファイル内に有効なJSONデータ（ { ... } ）が見つかりませんでした。")
        return
    
    clean_json = match.group(0)

    try:
        # 抽出した文字列をJSONとして読み込む
        raw_data = json.loads(clean_json)
    except json.JSONDecodeError as e:
        print(f"JSONの解析に失敗しました。中身を確認してください。\nエラー内容: {e}")
        return
    # --- クレンジング完了 ---

    print("--- ステップ2: データの確認と修正 ---")

    # JSONの構造に合わせてデータを取得（階層が深くても落ちないように .get を多用）
    subject = raw_data.get("subject_of_certification", {})
    marriage_status = raw_data.get("marriage_status", {})
    identifiers = raw_data.get("document_identifiers", {})
    
    current_name = subject.get("full_name", "不明")
    current_bday = subject.get("alleged_birth_date", "不明")
    
    print(f"\n 名前確認: {current_name}")
    new_name = input("修正後の氏名（空欄ならそのまま）: ")
    final_name = new_name if new_name else current_name

    print(f"\n ミドルネーム修正")
    middle_fix = input("ミドルネームに関する注記があれば入力: ")

    print(f"\n 翻訳者情報")
    translator_name = input("翻訳者の氏名: ")
    translator_address = input("翻訳者の住所: ")

    edited_data = {
        "original_data": {
            "name": current_name,
            "birthday": current_bday,
            "registry_no": identifiers.get("request_reference_number", "")
        },
        "final_data": {
            "name_ja": final_name,
            "middle_name_note": middle_fix,
            "status": "独身（婚姻記録なし）" if not marriage_status.get("record_found") else "記録あり"
        },
        "translator": {
            "name": translator_name,
            "address": translator_address
        }
    }

    output_file = "final_submission_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(edited_data, f, ensure_ascii=False, indent=2)

    print(f"\n--- 保存完了 ---")
    print(f"'{output_file}' を作成しました。")

if __name__ == "__main__":
    main()
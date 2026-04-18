#!/bin/bash

# =========================
# 設定読み込み
# =========================
source ./secrets.sh

# =========================
# サービス名
# =========================
SERVICE_NAME="ph-marriage-translator"

# =========================
# デプロイ
# =========================
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

# =========================
# 完了メッセージ
# =========================
echo "======================================"
echo "🚀 デプロイ完了"
echo "======================================"

# 1024pxを保ち、JPEG圧縮だけを加える版

- バッチ: `batch_20261124_011217_9030cc64`
- 設定: `configs/realvis10_jpegonly.json`
- 前回の1024px PNG版と同じ画像内容に、最終JPEG圧縮のみを追加。品質55、色差サブサンプリング4:2:0。
- 画像モデルの再推論・低解像度化・追加のぼかし・追加ノイズなし。既存の肌・髪・色・ノイズ設定を保持。
- 前回の配布PNGを直接JPEG化したバイト列と今回のJPEGが10枚すべて完全一致することを確認。全画像1024px、個人情報と生年月日も一致。
- 10人物・17ファイルのハッシュ・画像・CSV/JSONL一致、ZIP再展開検証に合格。
- 一覧: `outputs/batch_20261124_011217_9030cc64_review/index.html`
- PNGとJPEG比較: 同フォルダの`versions.html`
- ZIP: `outputs/batch_20261124_011217_9030cc64.zip`、967,495 bytes。
- ZIP SHA-256: `f2097aae3e7d4692665cdaab4739438b2a2ef473066f3b6b97004870515003a7`

# 環境・生成記録

確認日: 2026-11-23 JST

- Windowsネイティブ、RTX 4070 Ti / VRAM 12282 MiB、driver 610.88
- Intel Core i7-13700F、RAM約32GB
- Python 3.10.11、独立した`.venv`
- torch 2.6.0+cu124、torchvision 0.21.0+cu124、CUDA利用可を実機確認
- 依存全版: `requirements-lock.txt`
- StyleGAN2-ADA commit: `d72cc7d041b42ec8e806021a205ed9349f87c6a4`
- FFHQ weights SHA-256: `a205a346e86a9ddaae702e118097d014b7b8bd719491396a162cca438f2f524c`
- Qwen repo revision: `530227a7d994db8eca5ab5ced2fb692b614357fd`
- llama.cpp: b12651、CUDA 12.4、配布ZIPのSHA-256確認済み

## 実機確認

StyleGANの1024px PNG生成に成功。独自CUDA拡張のビルド環境がないため、公式reference演算をCUDA上で実行。vendorのソースファイルは変更していない。最初に不足したsetuptoolsを専用環境へ追加した。

1枚生成→別実行で次の1枚→残り98枚という順で実行し、IDと完了済み画像を保持して100枚へ再開できた。通常の推論・PNG保存は約0.13〜0.17秒/枚（初回を除く）。最終集計はバッチのgeneration.jsonを正本とする。

バッチID: `batch_20261123_221506_fb1fa890`。100枚のPNG復号を確認し、SHA-256は100件すべて異なる。推論・PNG保存の合計15.597秒（モデル読み込み・ハッシュ計算・状態保存は含まない）。原本100枚は約131.07MiB。

100枚の一覧と1枚の1024px原本を目視した。顔写真としての質感は確認できる一方、子ども、笑顔、帽子、斜め向き、他人の顔が写り込む背景などを含む。証明写真の条件と日本人限定の条件は未達。全画像の拡大目視選別は未実施。

## Qwen実機確認

- Qwen3-14B Q6_K SHA-256: `ec1f1d1421d7636a23e17645cac6fda39ee4b5f1f11e42eb09238089705ef699`
- HF LFSのSHA-256と照合済み。
- llama.cpp b12651、GPU層36、context 4096、parallel 1、Flash Attention有効。
- 読み込み後のGPUメモリ使用量は約11937〜11949MiB（Windowsデスクトップ等を含むGPU全体）。
- native `/completion` + JSON Schema + Qwen3非thinking ChatMLで実推論成功。
- 初回の採用プロフィールは約6.65秒、約16token/s。最終100人の合計はgeneration.jsonに記録。
- チャットAPIでのgrammar初期化エラーを確認し、native APIで回避。初回の銀行名・支店名が混在した試作はwork/trialsへ退避し、指示・検査を修正して再生成した。
- 顔一覧に基づくおおまかな創作年齢を設定。正確な年齢推定ではなく、人による整合性確認も未実施。

## 完了結果

- 顔100枚・Qwenプロフィール100人分を実生成した。氏名は100件すべて異なる。
- 採用プロフィールのリクエスト時間合計683.774秒（約11分24秒）。初期試作、重複等で破棄した応答、ダウンロード・読み込み時間は含まない。
- 途中で氏名の重複・カナ表記の不合格を検出。生成済み氏名の提示、重複時の名字候補、カナのgrammar制約を追加して完了した。
- `outputs/batch_20261123_221506_fb1fa890/profiles.csv`に顔パスと全プロフィール項目を結合。
- `outputs/batch_20261123_221506_fb1fa890.zip`、11,195,029 bytes。
- ZIP SHA-256: `d78b510542c6fff2655d7cefa12536d9f024a5d10c2408bb5fd4a24111d42285`
- 100レコード、画像100枚、manifest対象105ファイルについて、形式、CSV/JSONL一致、画像復号・サイズ、サイズ/SHA-256を検査。ZIP再展開後にも同じ検査に合格。
- 完成したプロフィール工程を再実行し、state.jsonのSHA-256が変化せず完了済みデータを再利用することを確認。
- 単体・統合テスト5件に合格（ZIP危険パス、改変検知、CSV、設定変更拒否、プロフィール表記検査等）。
- `outputs/batch_20261123_221506_fb1fa890_review/index.html`に100人分の一覧。
- 本タスクで起動したQwenサーバーは停止済み。再起動はREADMEの手順を使用。
- 今回の実行に相当する一括コマンド: `powershell -ExecutionPolicy Bypass -File scripts/run_test100.ps1 -GpuLayers 36`（既存バッチでは再利用する）。

## 未確認

- RTX 4090、WSL2、Mac実機でのインポート
- 日本人・証明写真条件を満たす最終モデル
- 外見と創作年齢、氏名とカナの意味上の整合性
- 10,000人での実測

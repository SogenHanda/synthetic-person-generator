# Synthetic Person Generator

顔写真と人物プロフィールをローカル生成し、CSV・JSONL・閲覧用HTML・画像フォルダ・ZIPにまとめるPythonツールです。テストデータ、プロトタイプ、デモ用データセットの作成に利用できます。

画像生成にはRealVisXL V5.0、プロフィールにはローカルの辞書・テンプレートを使用します。顔の類似候補を除外し、解像度・JPEG品質・肌の質感・構図にばらつきを持たせられます。生成状態を保存するため、中断後も採用済み画像を再利用して続行できます。

付属プリセットは、日本語プロフィールと日本人設定の証明写真風画像です。言語・地域の変更には生成辞書やプロンプトの変更が必要です。StyleGAN / Qwenの過去の実験も含みますが、以下はRealVisXLを使う標準手順です。

## Windowsでのビルド・セットアップ

ソースをcloneし、Python環境とモデルを用意して実行します。実行ファイルへのパッケージ化や、独自CUDA拡張のコンパイルは行いません。

### 動作環境

- Windows 10 / 11、PowerShell
- NVIDIA製CUDA対応GPUとNVIDIAドライバー（RTX 4070 Ti / VRAM 12GBで動作確認）
- Python **3.10 x64**、Git
- RAM 32GB、空きSSD 30GB以上を推奨。生成する人数によって保存容量は増加します。

CUDA対応PyTorchの配布wheelを使うため、通常はCUDA ToolkitやVisual Studio Build Toolsの別途導入は不要です。

### 1. 必要なツールとソースを取得

Python・Git・GitHub CLIがない場合は、PowerShellで次を実行します。インストール後はターミナルを開き直してください。

```powershell
winget install --id Python.Python.3.10 --exact
winget install --id Git.Git --exact
winget install --id GitHub.cli --exact
```

このリポジトリは非公開です。アクセス権のあるアカウントでログインします。

```powershell
gh auth login
gh repo clone SogenHanda/synthetic-person-generator
cd synthetic-person-generator
$env:PYTHONUTF8 = "1"
```

### 2. Python環境と依存関係を構築

```powershell
py -3.10 -m venv .venv
.venv/Scripts/python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
.venv/Scripts/python.exe -m pip install -r requirements-diffusion.txt -r requirements-similarity.txt -c requirements-lock.txt
.venv/Scripts/python.exe -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

最後に`CUDA: True`と使用するGPU名が表示されれば、GPUを認識しています。Falseやエラーの場合はNVIDIAドライバーとPyTorchのCUDA版を確認してください。activateやPowerShellの実行ポリシー変更は不要です。

### 3. モデルをダウンロード

```powershell
.venv/Scripts/python.exe -u scripts/download_realvis.py
.venv/Scripts/python.exe -u scripts/download_face_similarity.py
```

モデルはGitには含めません。公式配布元の固定リビジョンから取得し、SHA-256を検証します。RealVisXLは約6.5GiBです。ダウンロード中断時は同じコマンドを再実行できます。

| 用途 | モデル | 固定リビジョン |
| --- | --- | --- |
| 顔写真 | [SG161222/RealVisXL_V5.0](https://huggingface.co/SG161222/RealVisXL_V5.0) | `ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc` |
| 単一顔検出・類似候補の除外 | [OpenCV Zoo YuNet / SFace](https://github.com/opencv/opencv_zoo) | `48b10fa505aeb51fbd127fc60a5c660040e823b7` |

RealVisXLの利用条件はモデルカード、OpenCVモデルのライセンスは取得後の`models/face_similarity/*.LICENSE`を参照してください。

### 4. 環境を確認

```powershell
.venv/Scripts/python.exe -m generator doctor --config configs/example.json
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

テストは小さなフィクスチャを使って、CSV・画像・ZIP・相対パス・整合性検証等を確認します。GPU画像生成の全工程をテストで実行するわけではありません。

## 10件のデータセットを新規生成

`configs/example.json`は保存済みデータに依存しない10人分のサンプル設定です。

```powershell
.venv/Scripts/python.exe -X utf8 -u -m generator resume --config configs/example.json
```

顔写真 → プロフィール → 出力 → 検証 → ZIP → HTML確認の順に処理します。進捗はターミナルへ表示されます。中断する場合はCtrl+C、続行する場合は同じコマンドを再実行してください。同じ設定を複数のターミナルから同時実行しないでください。

作業状態は`work/example/state.json`、採用原本は`work/example/originals/`へ保存します。出力先の`batch_id`も状態ファイルに記録されます。

```powershell
$batchState = Get-Content work/example/state.json -Raw -Encoding UTF8 | ConvertFrom-Json
$batchDir = Join-Path outputs $batchState.batch_id
Start-Process (Join-Path $batchDir index.html)
```

同じ設定で再実行すると完成済みのバッチを再利用します。別のデータセットを作る場合は新しい設定ファイル名を使用してください。

## 設定を変更する

```powershell
Copy-Item configs/example.json configs/my_batch.json
notepad configs/my_batch.json
.venv/Scripts/python.exe -X utf8 -u -m generator resume --config configs/my_batch.json
```

| 設定 | 内容 |
| --- | --- |
| `count` | バッチの人数。1〜1000。`portrait_specs`も同じ人数分用意します。 |
| `seed`, `face_seed_start` | プロフィール・画像生成の乱数設定 |
| `as_of` | 年齢と生年月日の基準日。例では`2026-01-01`に固定。 |
| `portrait_specs` | 1人ごとの年齢・外見・服装・背景・撮影条件 |
| `diffusion.steps`, `guidance_scale` | 画像モデルの推論設定 |
| `face_diversity.threshold` | 採用済み顔との類似度閾値。小さいほど候補が除外されやすくなります。 |
| `face_diversity.max_attempts` | 1人あたりの生成試行上限。超過時は停止してエラーを表示。 |
| `portrait_specs[].finish` | 最終寸法・JPEG品質・傾き・ぼけ・色・粒状感など |

`portrait_specs`を増減した場合、`age_distribution`も実際の年齢配分に合わせて更新してください。この設定は既存の生成条件を保存するための形式で、コマンドだけで人数に応じた外見設定を自動作成する機能はありません。

作業状態がある設定ファイルの内容を変更すると再開を拒否します。条件を変える場合は新しいファイル名を使ってください。

## 出力形式と使い方

完成時に`outputs/<batch_id>/`と同名のZIPを作成します。

```text
outputs/<batch_id>/
  index.html           一覧・検索用HTML
  profiles.csv         人物情報18列（UTF-8）
  profiles.jsonl       同じ情報のJSONL
  faces/               CSV・HTMLから相対パスで参照する画像
  people.*             基本データ
  profiles_admin.*     管理・連携用データ
  generation.json      モデル・推論・仕上げの記録
  manifest.json        ファイルのサイズ・SHA-256
  README.txt           データ利用手順
```

`index.html`はブラウザーで直接開けます。外部ライブラリやサーバーは不要です。画像参照は`faces/person_<UUID>.jpg`という相対パスなので、フォルダ全体を別PCへ移して利用できます。CSV単体では写真は移動しません。番号・口座等は文字列として読み込むと先頭の0を保持できます。

公開用CSVの列は`name, name_kana, birth_date, address, email, phone, employer, workplace_address, workplace_phone, occupation, personal_number, payment_number, bank_name, bank_branch, bank_account_type, bank_account_number, account_holder_kana, face_path`です。生成seedや管理用IDは管理データに保持します。

## 実装と制約

標準設定は1024px / 35 steps / DPM++ SDE Karras / fp16、CPU offloadを使用します。VAEは必要時にfp32へupcastします。顔の修復・美肌化・アップスケールは行いません。

YuNetで単一顔を検出し、SFaceで合成顔間の類似候補を除外します。この閾値は、人の目で全画像が別人に見える保証ではありません。「日本人」は付属プリセットの人物設定であり、国籍・属性を判定する仕組みではありません。

プロフィールは合成データです。住所・メール・電話は実在のものと偶然一致する可能性があり、送信・発信・認証には使用しないでください。個人番号・カード番号は桁数を保ち、チェックサムを意図的に不正にしたテスト値です。

## ディレクトリ構成・追加資料

| パス | 内容 |
| --- | --- |
| `generator/` | 顔・プロフィール生成、画像仕上げ、出力と検証 |
| `configs/example.json` | 新規生成用の10人サンプル設定 |
| `configs/` | サンプル・過去のバッチ設定 |
| `scripts/` | モデル取得、進捗確認、データ検証、保存状態の復元 |
| `schemas/`, `tests/` | データ形式とテスト |
| `models/`, `work/`, `outputs/` | ローカル生成物。Git管理対象外 |

- [既存500人サンプル・保存状態の取得と復元](docs/RELEASE_500.md)
- [過去の実験記録](docs/HISTORY.md)
- `reports/`：過去のバッチの検証結果。標準セットアップには不要です。

`scripts/init_*`、`run_realvis1000.py`などは過去のバッチ用補助スクリプトです。新規生成は上記の`python -m generator ... --config ...`から実行してください。

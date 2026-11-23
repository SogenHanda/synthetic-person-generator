# 合成人物データセット — RealVisXL

作品用の合成顔写真と人物情報をローカル生成するプロジェクトです。現在はRealVisXL V5.0を使用しています。StyleGANとQwenの実験もコード・設定・[履歴](docs/HISTORY.md)に残しています。人物情報は現在、高速なローカル生成を使用し、Qwenサーバーは不要です。

## 500人の完成データと停止位置

2026年11月24日、500人分の生成・出力・検証を完了し、生成を停止しました。500人版は`work/realvis500_checkpoint/`、続きの1000人版は`work/realvis1000_diverse/`です。1000人版にも採用原本500枚を引き継ぎ、停止状態を保存しています。復元だけで画像生成が始まることはありません。

完成データは`deliverables/people_500/`、配布用ZIPは`deliverables/people_500.zip`です。

- `index.html`：500人全員の写真・人物情報を一覧・検索。ブラウザーで直接開けます。
- `profiles.csv`：人物情報18列。画像参照は`faces/person_<UUID>.jpg`という相対パスです。
- `faces/`：写真500枚。240〜480px、JPEG品質27〜52、構図・傾き・質感を人物別に変更。
- JSONL、管理用データ、生成条件、SHA-256マニフェストも同梱。

別PCやWebサイトへはフォルダ全体をコピーするか、ZIPを展開して使用してください。CSV単体では画像は移りません。番号・口座等は文字列として読み込むと先頭の0を維持できます。

コードはGit、原本・生成状態・完成データは同じ**非公開リポジトリのRelease**で配布します。GitHubの自動生成「Source code」ZIPだけには原本・データセットは入っていません。

## RTX 4090のPCへ移す：Windows / PowerShell

前提はWindows 10/11、NVIDIAドライバー、Python **3.10 x64**、Git、GitHub CLIです。32GB以上のRAM、空きSSDは30GB以上を目安にしてください。CUDA対応PyTorchを使用するため、通常はCUDA Toolkitの別途インストールは不要です。実動作確認はRTX 4070 Ti / 12GBで行っています。4090での実測は未実施です。

Git / Python / GitHub CLIがない場合、PowerShellから導入できます。インストール後は新しいターミナルを開いてください。

```powershell
winget install --id Git.Git --exact
winget install --id Python.Python.3.10 --exact
winget install --id GitHub.cli --exact
```

### 1. 非公開リポジトリをclone

```powershell
gh auth login
gh repo clone SogenHanda/newmedia-synthetic-people
cd newmedia-synthetic-people
$env:PYTHONUTF8 = "1"
```

GitHubへのアクセス権があるアカウントでログインします。

### 2. Python環境を作成

`.venv`は移植せず、このPCで作り直します。activateやPowerShellの実行ポリシー変更は不要です。

```powershell
py -3.10 -m venv .venv
.venv/Scripts/python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
.venv/Scripts/python.exe -m pip install -r requirements-diffusion.txt -r requirements-similarity.txt -c requirements-lock.txt
.venv/Scripts/python.exe -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

最後の表示が`CUDA: True`でRTX 4090を示すことを確認してください。Falseやエラーなら、ドライバーとPyTorchのCUDA版を確認し、生成前に解消してください。

### 3. 完成データと生成状態をダウンロード・復元

```powershell
gh release download checkpoint-500-20261124 --repo SogenHanda/newmedia-synthetic-people --pattern "checkpoint500.*" --dir transfer/checkpoint500
.venv/Scripts/python.exe scripts/migration_bundle.py restore transfer/checkpoint500/checkpoint500.parts.json
```

512MiB以下の分割ファイルを、復元スクリプトが結合し、全ファイルのSHA-256を検証します。手作業で結合・展開しないでください。異なる既存ファイルがあれば上書きせず停止するため、最初は新規clone先で復元してください。

復元対象は完成500人のHTML/CSV/JPEG/ZIP、採用原本500枚（1024px）、500人版と1000人版の生成状態、モデルの取得記録・ライセンスです。同じ原本は移行ZIPに一度だけ格納し、復元時に両方の作業状態へ配置します。不採用画像と過去の試作出力は含めません。種・試行記録・生成条件は状態ファイルに保存しています。

```powershell
Start-Process deliverables/people_500/index.html
.venv/Scripts/python.exe scripts/verify_portable.py deliverables/people_500 --count 500
.venv/Scripts/python.exe scripts/status_realvis1000.py --config configs/realvis1000_diverse.json
```

1000人版の状態は`paused`、生成済み500、目標1000です。完成500人の確認・利用だけなら、以下のモデル取得と追加生成は不要です。

### 4. 画像生成モデルを公式配布元から取得

```powershell
.venv/Scripts/python.exe -u scripts/download_realvis.py
.venv/Scripts/python.exe -u scripts/download_face_similarity.py
```

RealVisXLは約6.5GiBです。中断時は同じコマンドで再実行できます。モデルをGitや移行ZIPに再配布せず、公式の固定リビジョンから取得し、ハッシュを検証します。

| 用途 | モデル | 固定リビジョン |
| --- | --- | --- |
| 顔写真 | [SG161222/RealVisXL_V5.0](https://huggingface.co/SG161222/RealVisXL_V5.0) | `ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc` |
| 顔の検出・類似候補の除外 | [OpenCV Zoo YuNet / SFace](https://github.com/opencv/opencv_zoo) | `48b10fa505aeb51fbd127fc60a5c660040e823b7` |

RealVisXLのモデルカードにライセンス情報、OpenCVモデルのLICENSEは`models/face_similarity/*.LICENSE`にあります。各モデルの条件を確認して利用してください。

### 5. 必要なときだけ残り500人を生成

**以下を実行すると1000人まで追加生成します。500人で止めておく場合は実行しません。**

```powershell
.venv/Scripts/python.exe -X utf8 -u scripts/run_realvis1000.py --config configs/realvis1000_diverse.json
```

前景で実行され、進捗がターミナルに表示されます。採用済み原本をハッシュ検証して再利用し、未完分から再開します。同じ作業状態を二重起動しないでください。中断はCtrl+C、再開は同じコマンドです。採用済み画像・プロフィールは保存されます。類似候補を再生成するため、候補1枚の所要時間より全体の時間は長くなります。

別のPowerShellで進捗を確認できます。

```powershell
.venv/Scripts/python.exe scripts/status_realvis1000.py --config configs/realvis1000_diverse.json --watch
```

完成すると`outputs/batch_20261124_015156_656d1c80/`と同名ZIPに1000人のHTML/CSV/写真が出力され、移動・展開後の参照検証まで行います。`worker_status.json`が`complete`なら完了、`failed`なら実行ターミナルのエラーを確認してください。完成500人のデータは別フォルダに保持されます。500人版と1000人版で管理用person_idは異なり、対応表を1000人版stateの`checkpoints`に保存しています。

## 生成条件・人物情報

1024px / 35 steps / DPM++ SDE Karras / fp16、VAEは必要時fp32へupcast。検証済みのCPU offload設定を4090でも引き継ぎます。顔の復元・美肌化・アップスケールは使いません。輪郭・鼻・口・目・眉・髪・眼鏡・服装・肌を組み合わせ、YuNetで単一顔を検出し、SFaceのコサイン類似度0.65以上の候補を再生成します。合成顔間の類似度対策であり、人の目で全画像が別人に見える保証ではありません。「日本人」は創作上の設定としてプロンプトに記述しています。

500人の年齢配分：6〜15歳5、16〜19歳35、20代85、30代90、40代90、50代80、60代60、70代40、80代15。作品用の配分で、人口統計ではありません。生年月日との整合性を確認し、撮影時点の年齢は別に保持します。

公開CSVの18列：`name, name_kana, birth_date, address, email, phone, employer, workplace_address, workplace_phone, occupation, personal_number, payment_number, bank_name, bank_branch, bank_account_type, bank_account_number, account_holder_kana, face_path`。seed・連番・年齢ラベルは表示せず、seed等は管理用データに残します。

顔・人物情報は合成です。実在者や連絡先の収集・照会はしません。メール・電話・住所は実在のものと偶然一致する可能性があるため、送信・発信・認証には使用しないでください。個人番号・カード番号は桁数を保ち、チェックサムを意図的に不正にしたテスト値です。

## 検証と構成

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/verify_diverse_batch.py --config configs/realvis500_checkpoint.json
```

| パス | 内容 |
| --- | --- |
| `generator/` | 生成、仕上げ、CSV/HTML/ZIP出力・検証 |
| `configs/` | 固定条件。既存stateと異なる設定への変更時は再開を拒否 |
| `scripts/` | モデル取得、進捗、移行、検証 |
| `schemas/`, `tests/` | 形式定義、整合性・復元等のテスト |
| `reports/` | 検証結果・制作記録 |
| `docs/HISTORY.md` | StyleGAN/Qwen・質感調整の履歴 |
| `models/`, `work/`, `outputs/`, `deliverables/`, `transfer/` | ローカル生成物。Git管理対象外 |

新しい実験では既存の設定・保存状態を直接変更せず、新しいファイル名の設定を作成してください。`scripts/init_checkpoint500.py`等は今回の初期化用で、復元後の通常再開には不要です。

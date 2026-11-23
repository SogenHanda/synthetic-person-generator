# 生成方式・写真の質感調整の履歴（2026-11-23〜24）

過去の試作記録です。現在の実行手順・停止状態・移行方法はリポジトリ直下のREADME.mdを参照してください。以下の「現在」「生成中」は記録当時の記述です。

## 現在の目標：500人で生成停止し、受け渡し用データを確定

ユーザーの指示により500人でいったん停止します。`configs/realvis500_checkpoint.json`、バッチ`batch_20261124_045134_edfed9af`が現在の対象です。保存済み330枚を再利用し、残り170枚を生成します。年齢配分も半分にし、15歳以下5人、16〜19歳35人、20〜39歳175人、40〜59歳170人、60〜79歳100人、80〜89歳15人としました。男女各250人です。

生成上限を500人の独立設定にしているため、501人目には進みません。完成後はHTML・CSV・画像一式・ZIPを確定し、未完だった1000人版の作業状態にも500枚の原本を引き継いで停止状態を保存します。1000人版の生成は自動で再開しません。

```powershell
.venv/Scripts/python.exe scripts/status_realvis1000.py
# 中断から500人版を再開する場合のみ
.venv/Scripts/python.exe -X utf8 -u scripts/run_realvis1000.py --config configs/realvis500_checkpoint.json
```

## 1000人版・顔の多様性を広げる修正版（生成中）

年齢は6〜15歳10人、16〜19歳70人、20〜29歳170人、30〜39歳180人、40〜49歳180人、50〜59歳160人、60〜69歳120人、70〜79歳80人、80〜89歳30人へ調整しました。作品用の配分です。15歳以下の写真は全体の1%とし、若年層は最近の写真、80代は撮影時点でも80代の写真となるよう設定しています。氏名と完成済みの成人写真を保持し、未生成分の生年月日・職業等を年齢に合わせて更新しました。

現在の対象は`configs/realvis1000_diverse.json`、バッチ`batch_20261124_015156_656d1c80`です。旧111枚の段階で似た顔が多いとの指摘を受け、輪郭・鼻・口・目の形・眉・髪型・眼鏡を別々に組み合わせる生成へ変更しました。旧10枚も似たペアが含まれていたため、新しく生成し直します。プロフィール1000件と、写真ごとの粗さ・構図の設定は保持します。

生成時に、合成顔だけを対象にYuNet/SFaceで特徴を比較し、既採用画像とのコサイン類似度が0.65以上の候補、単一の顔を検出できない候補を再生成します。これは今回の合成顔用の選別基準であり、実在者の本人判定や、全ての顔が人の目で別人に見える保証ではありません。モデルは公式OpenCV Zooから取得し、Git LFSのSHA-256と照合しています。

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-similarity.txt
.venv/Scripts/python.exe scripts/status_realvis1000.py
.venv/Scripts/python.exe -X utf8 -u scripts/run_realvis1000.py
```

試作24枚の一覧は`outputs/realvis1000_diversity_preview/index.html`です。完成版の受け渡し先は`outputs/batch_20261124_015156_656d1c80/`と同名ZIP。`index.html`、`profiles.csv`、`faces/`を含むフォルダを丸ごと移せます。参照は全て相対パスです。`work/realvis1000_diverse/worker_status.json`の`complete`は、生成・出力・ZIP・別フォルダへの展開検証まで完了したことを示します。途中成果と類似候補の除外記録を保存し、再開できます。

## 旧1000人版：多様性の見直しのため111枚で中止

バッチは`batch_20261124_012709_ddfb66e9`、設定は`configs/realvis1000.json`です。確認済みの10人を保持し、新しい990人をRealVisXL V5.0で生成します。プロフィール1000件は先に作成済みです。男女各500人、人物設定20〜85歳。JPEG品質27〜52・240〜480px・構図のずれを写真ごとに変えます。顔原本は1024pxで保持します。

完了後の受け渡し先は`outputs/batch_20261124_012709_ddfb66e9/`、同名ZIPです。フォルダ内の`index.html`で1000人すべてを一覧・検索でき、`profiles.csv`に18項目の人物情報、`faces/`に画像を格納します。CSVの`face_path`とHTMLの参照は`faces/person_<UUID>.jpg`という相対パスです。フォルダごと他のPCへコピーできます。CSVだけでは画像は移らないため、CSVとfacesを一緒に渡してください。

```powershell
# 進捗を確認
.venv/Scripts/python.exe scripts/status_realvis1000.py
# 再開（同時に二重起動しない）
.venv/Scripts/python.exe -X utf8 -u scripts/run_realvis1000.py
```

`work/realvis1000/worker_status.json`が`complete`になれば生成・CSV/HTML・ZIP出力・別フォルダへ移動した後の参照検証まで完了しています。`failed`の場合は`work/realvis1000/run.err`を確認してください。再開時には保存済み原本のハッシュを確認し、未完の画像から続けます。検証記録は`reports/realvis1000_portability.json`です。

## 現在の試作：構図・余白・傾きにもばらつきを加える版

CLI標準は`configs/realvis10_framing.json`です。同じ原本10枚を使い、画像ごとに左右・上下の切り取り位置、寄り具合、約0.5〜2度の傾きを変更します。顔が少し左右に寄り、頭上の余白・頭頂や肩の切れ方が変わります。既存画素の範囲内で切り取るため、顔パーツの変形や背景の生成・拡張は行いません。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_uncompressed.py --framing
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_framing.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --compare realvis10_varied realvis10_framing
```

一覧は`outputs/batch_20261124_012032_00c911a8_review/index.html`、前回比較は同フォルダの`versions.html`です。前回の240〜480px・JPEG品質27〜52、色・ノイズ・ぼけの設定、人物情報は保持しています。設定と検証記録は`reports/20261124_framing_capture.md`。

## 前回の試作：写真ごとに240〜480px・JPEG品質27〜52へ分散

設定は`configs/realvis10_varied.json`です。同じ10人の画像を使い、実際のファイル寸法を240〜480px、JPEG品質を27〜52へ分散させました。全画像が前回の768pxより小さく、それぞれ異なる寸法・品質です。元のPNGから既存の色・ノイズ等の仕上げを保ち、最後の縮小とJPEG圧縮だけを調整しています。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_uncompressed.py --varied
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_varied.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --compare realvis10_jpeg768_q40 realvis10_varied
```

一覧は`outputs/batch_20261124_011718_cb967a8d_review/index.html`、前回比較は同フォルダの`versions.html`です。個別寸法は管理用`generation.json`の`image_sizes`にperson_idごとに記録し、バッチ全体の`image_size`はnullです。検証も個別寸法に対応しています。設定一覧・検証記録は`reports/20261124_varied_capture.md`。

## 前回の試作：768px・JPEG品質40

設定は`configs/realvis10_jpeg768_q40.json`です。前回の1024px・JPEG品質55から768px・品質40へ変更しました。同じ顔・肌の原本と既存仕上げを使い、最後の縮小とJPEG圧縮だけを調整します。前回のJPEGを再圧縮せず、PNGから処理しています。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_uncompressed.py --jpeg-quality 40 --size 768
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_jpeg768_q40.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --compare realvis10_jpegonly realvis10_jpeg768_q40
```

一覧は`outputs/batch_20261124_011454_bf826f48_review/index.html`、前回比較は同フォルダの`versions.html`です。全10枚で、既存PNGを768pxへ縮小し品質40でJPEG化したバイト列との完全一致を確認しています。

## 前回の試作：1024pxを保ち、JPEG圧縮だけを加える版

設定は`configs/realvis10_jpegonly.json`です。前回の1024px PNG版に、最終JPEG圧縮（品質55、色差4:2:0）だけを加えます。低解像度化やぼかし・ノイズの追加変更はありません。10枚すべて、前回のPNGを直接JPEG化したバイト列と完全一致することを確認しています。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_uncompressed.py --jpeg-quality 55
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_jpegonly.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --jpeg
```

一覧は`outputs/batch_20261124_011217_9030cc64_review/index.html`、PNGとの比較は同フォルダの`versions.html`です。前回のPNG版も保持しています。

## 前回の試作：低解像度化とJPEG圧縮を取り除く版

設定は`configs/realvis10_uncompressed.json`です。同じ生成原本10枚を再利用し、176〜288px相当への低解像度化と途中・配布時のJPEG圧縮を外しました。配布画像は1024px PNGです。肌・目元・髪の内容、色・フェード・ぼけ・追加ノイズの強度設定は保持します。ノイズの空間的な細かさは解像度に伴って変わります。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_uncompressed.py
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_uncompressed.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --clear
```

一覧は`outputs/batch_20261124_010916_95f5bf32_review/index.html`、前回比較は同フォルダの`versions.html`です。画像モデルの再推論は不要で、前回の確定済みデータは保持します。

## 前回の試作：顔の質感を保ち、圧縮・ノイズを少し減らす版

設定は`configs/realvis10_softgrain.json`。荒れ・粗さを強めた版と同じ1024px原本10枚・人物情報を再利用し、追加する輝度・色ノイズを35%減らし、中間JPEG品質を14、配布JPEG品質を12上げました。肌・しわ・髪・目元、色・ぼけ・解像度の設定は同じです。仕上げの乱数も元の写真に揃えています。今回の変更には画像モデルの再推論は不要です。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_softgrain.py
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_softgrain.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py --finishing
```

一覧は`outputs/batch_20261124_010341_9c053e78_review/index.html`。同フォルダの`versions.html`で前回と今回、`comparison.html`で原本と仕上げ後を比較できます。前回のデータは保持しています。

## 前回の試作：肌・目元・髪と写真の粗さを強める版

設定は`configs/realvis10_worn.json`です。RealVisXL V5.0で、肌の凹凸・ニキビ跡・色むら・しわ・疲れた目元、細めの目や自然なまぶたの左右差、不揃いな前髪を分散して指定します。目の形や髪は生成時の指定で、後から顔の形を変形していません。全員に同じ特徴を付ける構成ではありません。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_worn.py
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_worn.json
.venv/Scripts/python.exe scripts/compare_capture_versions.py
```

新しい10人分は`outputs/batch_20261124_005843_e01f56ea_review/index.html`。同フォルダの`versions.html`で初回・前回・今回、`comparison.html`で今回の原本と仕上げ後を比較できます。人物情報と顔生成の乱数は基準版から再利用しますが、プロンプト変更によって顔の同一性は固定されません。

1024px PNG原本を残し、配布写真は384px JPEG。写真ごとに176〜288px相当への低解像度化、JPEG品質36〜62での中間圧縮、輝度粒子ノイズ5〜10/255・色ノイズ0.8〜2/255、色偏りやフェードを変えます。前回の確定済みデータは保持しています。肌荒れ・加齢表現・左右差の出方にはばらつきがあるため、一覧と原本で確認する比較用です。

## 前回の試作：撮影条件と保存状態にばらつきを持たせる版

前回の設定は`configs/realvis10_livedin.json`です。写真向けモデルはRealVisXL V5.0のまま、スーツ・普段着、軽い姿勢差、肌の色むらや荒れ、照明、数年前に撮影した想定を10枚へ分散させました。全員に同じ粒状感を加える構成にはしていません。

```powershell
.venv/Scripts/python.exe scripts/init_realvis_livedin.py
.venv/Scripts/python.exe -m generator resume --config configs/realvis10_livedin.json
```

一覧は`outputs/batch_20261124_004411_b680df5e_review/index.html`、生成原本と仕上げ後の比較は同フォルダの`comparison.html`、個人情報CSVは`outputs/batch_20261124_004411_b680df5e/profiles.csv`、画像付きZIPは同名`.zip`です。元の10人版は保持しています。

生成原本は1024px PNG、配布写真は384px JPEGです。写真ごとに240〜384px相当への低解像度化、控えめな焦点の甘さ、色・コントラストの変動、粒状感、JPEG圧縮、微小なスキャン傾き等を加えます。`generator/photo_finish.py`は元画像を変更せず、各写真の設定と乱数を管理用generation.jsonへ記録します。原本と仕上げ後を比較できます。

人物情報は基準版10人から再利用し、撮影設定だけを比較しています。一部の古い写真は人物設定より1〜8年前の年齢として生成します。姿勢を強く指定した3枚は職場の顔写真という指示とCFG 6.0、他の7枚はCFG 4.0です。顔の大きな回頭は依然として弱く、正面寄りの出力もあります。目視で最終選別する前の比較用です。

## 比較の基準：RealVisXL 10人

基準版の設定は`configs/realvis10.json`です。RealVisXL V5.0を用い、日本人を想定した架空人物10人（男女各5人、24〜72歳）を証明写真構図・白/薄青背景で生成します。人物設定の年齢を生年月日にも使います。これは国籍の判定・保証ではありません。

実生成した10人の一覧は`outputs/batch_20261124_002023_0e5b4592_review/index.html`、個人情報の表は`outputs/batch_20261124_002023_0e5b4592/profiles.csv`、画像付きZIPは同名`.zip`です。生成合計は約2分3秒（初回のモデル取得・読込を除く）。白/薄青の指定が灰色寄りに出た背景もあります。検証記録は`reports/20261124_realvis10.md`を参照してください。

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-diffusion.txt
.venv/Scripts/python.exe scripts/download_realvis.py
.venv/Scripts/python.exe -m generator resume --config configs/realvis10.json
```

RealVisXLのモデルrevisionは`ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc`。公式HFリポジトリのfp16重みをLFSのSHA-256と照合して保存し、推論時はローカルのファイルだけを使います。取得情報は`models/realvisxl-assets.json`です。DPM++ SDE Karras / 35 steps / CFG 4.5 / 1024px / model CPU offloadを使用。顔修復、美肌化、アップスケールは加えません。

新しい人物一覧と`profiles.csv`／`profiles.jsonl`は、氏名・読み・生年月日・住所・メール・電話・職業・勤務先・勤務先住所と電話・番号・口座等だけを表示します。seed、連番、創作年齢、生成フラグは含みません。画像対応用のファイル名は不透明なUUIDです。

共通インポート用の`people.*`はv1の内部IDを保持します。`profiles_admin.*`、`generation.json`は管理用です。seedや設定・検査情報を確認する場合だけ使用します。表示・配布向けの表は`profiles.csv`を使用してください。

メールは氏名の読みを元にした文字列と一般的なメールサービスのドメイン、電話は国内の番号形式で生成します。実在確認やメール送信・架電は行いません。勤務先は生成した名称と住所で、職業に合わせて会社・医療法人・農園等を使い分けます。無職・学生等は勤務先を空欄にします。

旧100人分の一覧も、再描画時はseed・連番・創作年齢を表示しない形式になりました。旧バッチの確定済みCSV・ZIPは上書きしません。

## 2026-11-24 更新：プロフィール高速版

高速100件の設定は`configs/test100_fast.json`です。旧Qwen逐次生成の設定は`configs/test100.json`として残しています。

```powershell
.venv/Scripts/python.exe scripts/revise_profiles.py
.venv/Scripts/python.exe -m generator validate
.venv/Scripts/python.exe scripts/benchmark_profiles.py
```

修正版は`outputs/batch_20261124_000752_4b6a3b7a/`、一覧は同名`_review/index.html`、ZIPは同名`.zip`です。旧バッチを上書きせず、顔PNGとQwen製の氏名・読みを再利用しました。**顔は旧FFHQのままで、日本人の条件は未解決です。**

住所は47都道府県と対応する実在の市区名を使い、町名・丁目・番地・建物をテンプレートから生成します。実際の住居との照合や個人情報の収集は行いません。住所文字列の偶然の一致は許容します。表示上の「架空」は取り除き、`synthetic=true`等の管理情報は残します。

個人番号は12桁、カード番号は16桁、口座番号は7桁の数字列です。個人番号とカード番号はチェックディジットを意図的に不正にします。口座番号は表示用の乱数で、銀行のルーティング識別子は`TEST`です。カード・個人番号の妥当性検査に通るデータは出力検査で拒否します。これらはすべて文字列としてJSONへ保存します。

既存のQwen製の氏名・読みを再利用し、住所・職業・銀行支店・番号をPythonで生成します。新規にキャッシュのない人物を作る場合は、姓名とカナの対のローカル辞書を使用します。LLMのAPI・モデル起動は不要です。氏名をさらに増やしたい場合に限り、Qwenで名前候補をまとめて生成する方式へ拡張できます。

実測は修正版100件のプロフィール処理が約0.009秒、独立した辞書方式の1万件生成が約0.369秒でした。画像処理、モデル取得、CSV/ZIP書き出しを除いた時間です。実測記録は`reports/profile_benchmark.json`です。旧方式の採用100応答は合計683.774秒でした。

以下は旧Qwen逐次生成テストの記録・手順です。旧方式を再現する場合は各コマンドへ`--config configs/test100.json`を付けてください。

Windows / RTX 4070 Ti 12GBで、架空人物100人の顔写真と日本語プロフィールを作る比較実験です。モデルは最終決定ではありません。

## 今回のモデル

- 顔: NVIDIA StyleGAN2-ADA PyTorch実装 + 公式FFHQ 1024px重み。`truncation_psi=0.85`、固定noise、seed 1000〜1099。
- 文章: Qwen公式 `Qwen3-14B-GGUF`、Q6_K量子化（約12.12GB）、非thinkingモード。
- 顔と文章を順次実行し、VRAMを解放してからQwenを起動します。QwenのGPU層数は初期30、残りはCPUです。
- 元画像は1024×1024のPNGを保存し、美顔化・顔修復・アップスケールを加えません。受け渡し用は512×512のJPEG quality=95 / chroma subsamplingなしです。

**これは未選別のモデル比較用データです。** FFHQは日本人特化のモデルではなく、子ども・笑顔・横向き・複雑な背景なども含まれます。日本人限定、成人限定、証明写真の条件にはまだ適合しません。外見から国籍を分類する処理はありません。今回の100枚には、一覧の見た目を参考におおまかな創作年齢を割り当てました（`reports/test100_age_direction.json`）。正確な年齢推定や人による確認は未実施です。氏名と顔は独立した創作情報です。画像が実在者と偶然似る可能性は排除できません。

## 導入

今回の動作環境はPython 3.10.11 / PyTorch 2.6.0+cu124 / torchvision 0.21.0+cu124です。最新Pythonへ置き換えず、既存Pythonから独立した`.venv`を作成しました。

PowerShellでこのプロジェクトへ移動して実行します。

```powershell
uv venv --python 3.10 .venv
uv pip install --python .venv/Scripts/python.exe torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git vendor/stylegan2-ada-pytorch
git -C vendor/stylegan2-ada-pytorch checkout d72cc7d041b42ec8e806021a205ed9349f87c6a4
python scripts/download_assets.py
.venv/Scripts/python.exe -m generator doctor
```

重みとllama.cppのダウンロードにはネット接続と約20GB以上の空きが必要です。Qwenは範囲分割で取得し、完了済みの範囲を再利用します。モデルとllama.cppはSHA-256を検査します。FFHQの初回取得ハッシュは`reports/environment.md`にも記録します。取得後の推論はローカルだけで行います。

StyleGANの独自CUDAカーネルをこのPCでビルドするためのNVCC/MSVC環境は未確認です。この実装では**公式のreference演算をCUDAテンソル上で実行**します。CPU画像生成の代替ではありません。vendorコードは変更せず、任意のCUDA拡張を無効にしています。FP32推論を使用します。

## 100人分を生成・再開

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_test100.ps1
```

同じコマンドを再実行すると、`work/test100/state.json`を読み、完成済みの顔・プロフィールを再利用します。人物IDとseedは保持します。設定を変えて比較する場合は`configs/test100.json`を別名へコピーし、新しいファイル名を`-Config`で指定してください。既存バッチの設定を変更するとエラーになります。

GPUメモリが足りない場合は次を試します。既存のQwenサーバーがある場合は先に自分で停止してください。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_test100.ps1 -GpuLayers 24
```

顔画像生成は1枚ずつです。途中でOOMになっても完了済みのファイルは保持されます。

### 工程を分けて実行

```powershell
.venv/Scripts/python.exe -m generator faces --limit 1
.venv/Scripts/python.exe -m generator faces
python scripts/apply_test_age_specs.py
```

`apply_test_age_specs.py`は今回のseed 1000〜1099の100枚に限る任意の創作年齢設定です。すでに適用済みなら変更せず、プロフィール生成後の変更は拒否します。別のモデルやseedの比較には使用しないでください。

Qwenを別PowerShellで起動します。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_qwen.ps1 -GpuLayers 30
```

その後、元のPowerShellで次を実行します。

```powershell
.venv/Scripts/python.exe -m generator profiles --limit 1
.venv/Scripts/python.exe -m generator profiles
.venv/Scripts/python.exe -m generator export
.venv/Scripts/python.exe -m generator validate
.venv/Scripts/python.exe -m generator package
.venv/Scripts/python.exe -m generator preview
```

サーバーは`127.0.0.1:8765`だけで待ち受けます。LLMはJSON Schemaで出力制約し、JSON構文、必須項目、架空住所・銀行の接頭辞、銀行名と支店名の分離、カナ表記、口座名義の一致、氏名重複を検査します。形式検査と氏名重複検査はそれぞれ最大3回再生成し、合格した人物だけを保存します。名前と読みの意味上の正しさは目視確認が必要です。

生成済みの氏名をQwenへ渡して重複を避けます。それでも重複が続く場合だけ、一般的な名字の候補をローカル辞書から指示します。名前と読みは引き続きQwenが生成します。カナ欄はJSON Schemaの文字種制約も使用します。

llama.cpp b12651のチャットAPIでは、Qwen3の非thinking入力とJSON grammarの組み合わせでエラーが発生しました。この実装ではnative `/completion` APIへ、Qwen3のChatML形式・閉じたthinkingプレフィックス・`json_schema`を渡して回避します。文章モデルや量子化を変更した代替ではありません。別系統のQwenを試す場合は、そのモデルの入力テンプレートも確認してください。

## 出力

```text
work/test100/
  state.json                  再開用の人物ID・条件・結果
  originals/*.png            1024pxの生成原本100枚
outputs/<batch_id>/
  manifest.json
  people.jsonl               共通v1の正本
  people.csv                 共通v1のCSV
  profiles.jsonl             追加プロフィールを含む全項目
  profiles.csv               氏名・生年月日・画像パス・番号・銀行口座を1表へ結合
  generation.json            モデル、ハッシュ、seed、環境、実測、未確認事項
  faces/*.jpg                512px受け渡し用画像
outputs/<batch_id>.zip
outputs/<batch_id>_review/
  index.html                 顔とプロフィールの一覧。画像クリックで1024px原本
  contact_sheet.jpg          seed付き100枚一覧
```

`profiles.csv`はUTF-8（BOMなし）です。Excelで文字が崩れる場合は「データ→テキストまたはCSVから」でUTF-8として取り込んでください。番号は`TEST-`で始まる無効な識別値です。有効なマイナンバー、カード番号、銀行口座は生成しません。生年月日と番号はPython、氏名・カナ・架空住所・職業・架空銀行・支店・口座名義はQwenが生成します。

添付計画の共通v1レコードとCSV列順は維持します。銀行口座等は`profiles.*`という拡張ファイルに分離し、同じperson_idで結合します。追加ファイルもmanifestのハッシュ対象です。Macのv1インポーターは`people.jsonl`を取り込めますが、追加項目を表示するには拡張ファイルを読む実装が別途必要です。Mac実機では未検証です。

## 検査と引き渡し

`validate`は人数、必須項目・型、ID、CSV/JSONL一致、画像復号とサイズ、全ファイルのサイズ/SHA-256、画像の過不足を検査します。`package`はZIPのルート構成を保ち、再展開して同じ検査に通ってから確定します。同じバッチの異なる内容で完成ZIPを上書きしません。ZIP内の絶対パス、親参照、シンボリックリンク、重複パス、1GBを超える展開を拒否します。

Macへは`outputs/<batch_id>.zip`を渡します。1024px原本も評価する場合は`work/test100/originals`を別途渡してください。モデル・Python・CUDAをMacへ渡す必要はありません。

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

テスト内の画像は検査用の単色fixtureで、StyleGAN推論結果とは区別しています。

## モデル比較を続ける

1. 今回の100枚で肌の自然さ、眼鏡・歯・耳・髪の破綻、顔の反復を確認する。
2. 日本人を想定した容姿・年齢分布・正面・無表情に適した別重みを比較する。
3. 白／青背景への統一と証明写真構図を検証する。
4. 顔の見かけ年齢とプロフィールの整合性を選別・確認する。
5. 合格率と時間を測り、採用済み10,000人へ増やす。

今回は1〜4の合格を自動で保証しません。`review_status=unreviewed`で出力します。

## 取得元と利用条件

- NVIDIA実装・ライセンス: https://github.com/NVlabs/stylegan2-ada-pytorch （research/evaluationに限る非商用条件。まず本テストで使用。展示・公開段階では採用重みと条件を確認する。）
- FFHQ重み: https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/ffhq.pkl
- FFHQデータの説明: https://github.com/NVlabs/ffhq-dataset （学習データを本実装で取得・再配布しない。）
- Qwen: https://huggingface.co/Qwen/Qwen3-14B-GGUF （Apache-2.0）
- llama.cpp: https://github.com/ggml-org/llama.cpp （MIT、b12651 / CUDA 12.4版）

秘密鍵、VPS設定、自動公開、攻撃処理はこの生成実装に含みません。

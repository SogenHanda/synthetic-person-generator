# 500人版・RTX 4090移行用チェックポイント

500人分の生成を完了し、このPCでの追加生成を停止しました。

完成データだけを使う場合は`people_500.zip`をダウンロード・展開し、`index.html`を開いてください。`profiles.csv`と`faces/`は相対パスでつながっているため、フォルダごと別PCへ移せます。

続きの生成も移す場合はリポジトリをcloneし、READMEの手順でPython環境を作成してください。その後：

```powershell
gh release download checkpoint-500-20261124 --repo SogenHanda/newmedia-synthetic-people --pattern "checkpoint500.*" --dir transfer/checkpoint500
.venv/Scripts/python.exe scripts/migration_bundle.py restore transfer/checkpoint500/checkpoint500.parts.json
```

`checkpoint500.zip.part001`、`part002`と`checkpoint500.parts.json`をすべて取得します。分割ファイルは単独のZIPではありません。復元スクリプトが結合と全ファイルのSHA-256検証を行います。

完成500人のHTML/CSV/JPEG/ZIP、採用原本500枚（1024px）、500人版の完成状態、1000人版の500枚生成済み・停止状態を収録。移行アーカイブは699,633,337 bytesです。モデル本体は含めず、READMEのコマンドで公式固定リビジョンから取得します。

復元だけでは追加生成しません。1000人まで続ける場合に限り、モデル取得後に次を実行します。

```powershell
.venv/Scripts/python.exe -X utf8 -u scripts/run_realvis1000.py --config configs/realvis1000_diverse.json
```

検証：24件のテスト、500件のCSV/画像/HTML参照・ZIP展開、採用原本のハッシュ、年齢配分と生年月日、合成顔間の類似度、新規clone先への移行パッケージ復元に合格。新しいPCでのGPU推論は未実施です。実行手順はREADMEを参照してください。

完成データZIP SHA-256：`1a872a69b143de90795ec6900ea12acfdbca4f656ee44a8990341a5435e8933d`

結合後の移行ZIP SHA-256：`5d6f9a6ab4b79fba56ceacd1eee6c6fcec87eb56c25ffdd492fe16840b4a4d2c`

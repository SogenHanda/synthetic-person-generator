"""Self-contained, offline HTML with relative image links and no external assets."""
import html
from .review import LABELS

def render(dest,records):
    cards=[]
    for row in records:
        name=html.escape(row['name'])
        path=html.escape(row['face_path'],quote=True)
        search=html.escape(' '.join(str(row.get(k,'')) for k in ('name','name_kana','address','occupation','employer')),quote=True)
        fields=''.join(f'<div><dt>{label}</dt><dd>{html.escape(str(row.get(key,"")))}</dd></div>' for key,label in LABELS if row.get(key) not in ('',None))
        cards.append(f'<article data-search="{search}"><a href="{path}" target="_blank"><img loading="lazy" decoding="async" src="{path}" alt="{name}" width="320" height="320"></a><div class="body"><h2>{name}</h2><p class="kana">{html.escape(row.get("name_kana",""))}</p><p>{html.escape(row["birth_date"])}</p><p>{html.escape(row["address"])}</p><details><summary>プロフィールの詳細</summary><dl>{fields}</dl></details></div></article>')
    document='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人物データセット一覧</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f1f0ec;color:#252a2c;font:14px/1.65 Meiryo,"Yu Gothic",sans-serif}header{padding:28px;max-width:1600px;margin:auto}h1{font-size:26px;margin:0 0 8px}header p{color:#687075;margin:6px 0}.tools{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:18px}input{font:inherit;padding:10px 14px;border:1px solid #cdd0ca;border-radius:6px;min-width:280px}a{color:#344f61}.grid{padding:0 28px 40px;max-width:1600px;margin:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}article{background:white;border:1px solid #dddeda;border-radius:7px;overflow:hidden}article[hidden]{display:none}article>a{display:block;background:#dfe3e4}img{display:block;width:100%;height:auto;aspect-ratio:1;object-fit:contain}.body{padding:17px}h2{font-size:20px;letter-spacing:.06em;margin:0}.body p{margin:7px 0}.kana{font-size:11px;color:#7b8388}summary{cursor:pointer;color:#59666e;margin-top:16px}dl{margin:8px 0 0}dl>div{padding:7px 0;border-top:1px solid #edf0ed}dt{font-size:11px;color:#7b8388}dd{margin:2px 0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}footer{padding:20px 28px;color:#687075}@media(max-width:600px){header{padding:20px 16px}.grid{padding:0 16px 24px;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.body{padding:10px}h2{font-size:17px}input{min-width:0;width:100%}}</style>
<header><h1>人物データセット一覧</h1><p>写真をクリックすると原寸画像を開きます。フォルダごと移動して、そのまま閲覧できます。</p><div class="tools"><input id="search" type="search" placeholder="氏名・住所・職業・勤務先で検索" aria-label="人物を検索"><span id="count">COUNT件</span><a href="profiles.csv" download>CSVを保存</a><a href="profiles.jsonl" download>JSONLを保存</a></div></header><main class="grid">'''.replace('COUNT',str(len(records)))+''.join(cards)+'''</main><footer>画像とプロフィールは作品用に生成した合成データです。</footer>
<script>const cards=[...document.querySelectorAll('article')];document.querySelector('#search').addEventListener('input',e=>{const q=e.target.value.trim().toLocaleLowerCase();let n=0;for(const c of cards){c.hidden=!c.dataset.search.toLocaleLowerCase().includes(q);if(!c.hidden)n++;}document.querySelector('#count').textContent=n+' / '+cards.length+'件';});</script></html>'''
    (dest/'index.html').write_text(document,encoding='utf-8')
    (dest/'README.txt').write_text('''このフォルダを丸ごと別のPCへコピーしてください。
index.html: 全人物の一覧。ダブルクリックで開けます。外部ライブラリ・サーバー不要。
profiles.csv: 管理・インポート向け。UTF-8、18列。face_pathはこのフォルダ基準の相対パス。
profiles.jsonl: 同じ人物情報をJSONL形式で保存。
faces/: CSV・HTMLから参照する画像。CSVだけでは画像は移動できません。
people.* / profiles_admin.* / generation.json / manifest.json: 連携・再現・整合性確認用。

Webサイトへ移す場合はCSVとfacesフォルダを一緒に渡してください。
CSVインポーターが画像を自動登録できるかは、移行先の実装によります。
face_pathの例: faces/person_<英数字>.jpg。Cドライブや元PCの絶対パスは不要です。
個人番号・カード番号・口座番号・電話番号等は文字列として取り込んでください。
ExcelでCSVを直接開くと桁・先頭ゼロが変わる場合があるため、データ取り込みで番号列を文字列に指定してください。
データは架空人物の合成データです。実在確認・メール送信・架電は行っていません。
''',encoding='utf-8')

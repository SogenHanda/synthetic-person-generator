"""Personal-information-only review view, with technical fields kept elsewhere."""
import html
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .common import ROOT,photo_delivery_size

LABELS=[('birth_date','生年月日'),('address','住所'),('email','メールアドレス'),('phone','電話番号'),
        ('occupation','職業'),('employer','勤務先'),('workplace_address','勤務先住所'),('workplace_phone','勤務先電話番号'),
        ('personal_number','個人番号'),('payment_number','カード番号'),('bank_name','銀行名'),('bank_branch','支店名'),
        ('bank_account_type','預金種別'),('bank_account_number','口座番号'),('account_holder_kana','口座名義')]

def render(config,path,saved):
    dest=ROOT/'outputs'/saved['batch_id']
    review=ROOT/'outputs'/(saved['batch_id']+'_review')
    review.mkdir(parents=True,exist_ok=True)
    people=saved['people']
    columns=min(5,len(people))
    cell=256
    sheet=Image.new('RGB',(columns*cell,((len(people)+columns-1)//columns)*(cell+38)),'#f1f0ec')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.load_default()
    for candidate in ('C:/Windows/Fonts/meiryo.ttc','C:/Windows/Fonts/YuGothM.ttc'):
        if Path(candidate).exists():
            font=ImageFont.truetype(candidate,18)
            break
    cards=[]
    for i,person in enumerate(people):
        raw=path.parent/'originals'/(person['person_id']+'.png')
        if not raw.exists():
            continue
        profile=person.get('profile') or {}
        name=profile.get('name','')
        exported=dest/'faces'/(person['person_id']+'.'+config.get('output_format','jpg'))
        shown=exported if exported.exists() else raw
        with Image.open(shown) as image:
            image=image.convert('RGB')
            if config.get('photo_finish') and not exported.exists():
                from .photo_finish import finish,parameters
                settings,seed=parameters(config,person)
                image=finish(image,settings,photo_delivery_size(config,person),seed)
            sheet.paste(image.resize((cell,cell),Image.Resampling.LANCZOS),((i%columns)*cell,(i//columns)*(cell+38)))
        draw.text(((i%columns)*cell+10,(i//columns)*(cell+38)+cell+5),name,font=font,fill='#242424')
        image_src='../'+dest.name+'/faces/'+exported.name if exported.exists() else raw.as_uri()
        record={**profile,'birth_date':person['birth_date']}
        fields=''.join(f'<div class="field"><dt>{label}</dt><dd>{html.escape(str(record.get(key,"")))}</dd></div>' for key,label in LABELS if record.get(key) not in ('',None))
        full_src=exported.as_uri() if exported.exists() else raw.as_uri()
        cards.append(f'<article><a class="portrait" href="{html.escape(full_src,quote=True)}"><img loading="lazy" src="{html.escape(image_src,quote=True)}" alt="{html.escape(name,quote=True)}"></a><div class="body"><h2>{html.escape(name)}</h2><p class="kana">{html.escape(profile.get("name_kana",""))}</p><dl>{fields}</dl></div></article>')
    sheet.save(review/'contact_sheet.jpg',quality=95,subsampling=0)
    document='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人物プロフィール</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f1f0ec;color:#252a2c;font:14px/1.65 "Yu Gothic",Meiryo,system-ui,sans-serif}header{max-width:1400px;margin:0 auto;padding:36px 28px 24px}h1{font-size:28px;letter-spacing:.06em;margin:0 0 8px}header p{margin:0;color:#687075;font-size:13px}.grid{max-width:1400px;margin:0 auto;padding:0 28px 40px;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}article{background:#fff;border:1px solid #dddeda;border-radius:8px;overflow:hidden}.portrait{display:block;background:#e8ebed}.portrait img{display:block;width:100%;aspect-ratio:1;object-fit:contain}.body{padding:22px}h2{font-size:23px;letter-spacing:.08em;margin:0}.kana{margin:3px 0 20px;color:#7b8388;font-size:12px}dl{margin:0}.field{padding:9px 0;border-top:1px solid #edf0ed}dt{font-size:11px;letter-spacing:.05em;color:#7b8388}dd{margin:2px 0 0;overflow-wrap:anywhere;font-size:13px;font-variant-numeric:tabular-nums}@media(max-width:680px){header{padding:24px 16px}.grid{padding:0 16px 24px;grid-template-columns:1fr}}</style>
<header><h1>人物プロフィール</h1><p>生成した顔写真とプロフィールのサンプルです。写真をクリックすると原寸で表示します。</p></header><main class="grid">'''+''.join(cards)+'</main></html>'
    if config.get('capture_comparison'):
        comparison_cards=[]
        for person in people:
            raw=path.parent/'originals'/(person['person_id']+'.png')
            delivered=dest/'faces'/(person['person_id']+'.'+config.get('output_format','jpg'))
            if raw.exists() and delivered.exists():
                name=html.escape((person.get('profile') or {}).get('name',''))
                comparison_cards.append(f'<section><h2>{name}</h2><div class="pair"><figure><img src="{raw.as_uri()}"><figcaption>生成原本</figcaption></figure><figure><img src="{delivered.as_uri()}"><figcaption>仕上げ後</figcaption></figure></div></section>')
        compare='''<!doctype html><html lang="ja"><meta charset="utf-8"><title>写真の仕上げ比較</title><style>body{font:14px/1.6 Meiryo,sans-serif;background:#f1f0ec;margin:30px;color:#252a2c}main{max-width:1000px;margin:auto}section{background:white;padding:24px;margin-bottom:24px}h2{margin:0 0 16px;font-size:20px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;display:block}figcaption{text-align:center;padding-top:10px;color:#687075}</style><main><h1>写真の仕上げ比較</h1>'''+''.join(comparison_cards)+'</main></html>'
        (review/'comparison.html').write_text(compare,encoding='utf-8')
        document=document.replace('<main class="grid">','<p style="max-width:1344px;margin:0 auto 24px;padding:0 28px"><a href="comparison.html">生成原本と仕上げ後を比較する</a></p><main class="grid">')
    (review/'index.html').write_text(document,encoding='utf-8')
    print('Preview:',review/'index.html')
    return review

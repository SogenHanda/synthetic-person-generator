"""Build a local-only comparison of the three completed portrait experiments."""
import html
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json

def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--finishing',action='store_true',help='Compare identical originals with lower noise/compression')
    group.add_argument('--clear',action='store_true',help='Compare previous JPEG with full-resolution lossless PNG')
    group.add_argument('--jpeg',action='store_true',help='Compare full-resolution PNG with JPEG-only compression')
    group.add_argument('--compare',nargs=2,metavar=('BEFORE','AFTER'),help='Two config stems to compare')
    options=parser.parse_args()
    names=('realvis10_worn','realvis10_softgrain') if options.finishing else ('realvis10','realvis10_livedin','realvis10_worn')
    configs=[read_json(ROOT/f'configs/{name}.json') for name in names]
    states=[read_json(ROOT/f'work/{name}/state.json') for name in names]
    titles=['前回','今回：圧縮とノイズを少し弱める'] if options.finishing else ['初回','前回','今回：荒れ・粗さを強める']
    if options.clear:
        names=('realvis10_softgrain','realvis10_uncompressed')
        configs=[read_json(ROOT/f'configs/{name}.json') for name in names]
        states=[read_json(ROOT/f'work/{name}/state.json') for name in names]
        titles=['前回：低解像度JPEG','今回：1024px PNG']
    if options.jpeg:
        names=('realvis10_uncompressed','realvis10_jpegonly')
        configs=[read_json(ROOT/f'configs/{name}.json') for name in names]
        states=[read_json(ROOT/f'work/{name}/state.json') for name in names]
        quality=configs[-1]['portrait_specs'][0]['finish']['delivery_jpeg_quality']
        titles=['前回：1024px PNG',f'今回：1024px JPEG（品質{quality}）']
    if options.compare:
        names=options.compare
        configs=[read_json(ROOT/f'configs/{name}.json') for name in names]
        states=[read_json(ROOT/f'work/{name}/state.json') for name in names]
        titles=[f'{label}：{config["output_size"]}px JPEG（品質{config["portrait_specs"][0]["finish"]["delivery_jpeg_quality"]}）' for label,config in zip(('前回','今回'),configs)]
    cards=[]
    for people in zip(*(s['people'] for s in states)):
        name=html.escape(people[-1]['profile']['name'])
        pictures=[]
        for config,saved,person,title in zip(configs,states,people,titles):
            photo=ROOT/'outputs'/saved['batch_id']/'faces'/(person['person_id']+'.'+config['output_format'])
            if not photo.is_file():
                raise ValueError('Complete and export all experiments before comparing')
            settings=person.get('portrait_spec',{}).get('finish',{})
            if options.compare and 'delivery_size' in settings:
                title=title.split('：')[0]+f'：{settings["delivery_size"]}px JPEG（品質{settings["delivery_jpeg_quality"]}）'
            pictures.append(f'<figure><a href="{photo.as_uri()}"><img loading="lazy" src="{photo.as_uri()}" alt="{name}"></a><figcaption>{title}</figcaption></figure>')
        cards.append(f'<section><h2>{name}</h2><div class="row">'+''.join(pictures)+'</div></section>')
    dest=ROOT/'outputs'/(states[-1]['batch_id']+'_review')
    document='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>顔写真の比較</title>
<style>*{box-sizing:border-box}body{margin:24px;background:#f1f0ec;color:#252a2c;font:14px/1.65 Meiryo,sans-serif}main{max-width:1200px;margin:auto}h1{font-size:26px}h2{font-size:19px;margin:0 0 16px}section{background:white;padding:24px;margin:24px 0}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}img{width:100%;display:block}figcaption{text-align:center;margin-top:10px}a{color:inherit}@media(max-width:600px){body{margin:12px}section{padding:12px}.row{gap:6px}figcaption{font-size:11px}}</style><main><h1>顔写真の比較</h1><p>同じ人物情報・乱数を使った生成条件の比較です。顔の同一性は固定していません。写真をクリックすると原寸で表示します。</p>'''+''.join(cards)+'</main></html>'
    if options.finishing:
        document=document.replace('repeat(3,1fr)','repeat(2,1fr)').replace('同じ人物情報・乱数を使った生成条件の比較です。顔の同一性は固定していません。','同じ生成原本を使い、圧縮と追加ノイズだけを変えた比較です。')
    if options.clear:
        document=document.replace('repeat(3,1fr)','repeat(2,1fr)').replace('同じ人物情報・乱数を使った生成条件の比較です。顔の同一性は固定していません。','同じ生成原本を使い、低解像度化とJPEG圧縮を取り除いた比較です。')
    if options.jpeg:
        document=document.replace('repeat(3,1fr)','repeat(2,1fr)').replace('同じ人物情報・乱数を使った生成条件の比較です。顔の同一性は固定していません。','同じ1024px画像に、JPEG圧縮だけを加えた比較です。')
    if options.compare:
        description='同じ生成原本から、構図の位置・余白・傾きを調整した比較です。' if any('frame_crop' in p['portrait_spec'].get('finish',{}) for p in states[-1]['people']) else '同じ生成原本から、解像度とJPEG圧縮を調整した比較です。'
        document=document.replace('repeat(3,1fr)','repeat(2,1fr)').replace('同じ人物情報・乱数を使った生成条件の比較です。顔の同一性は固定していません。',description)
    (dest/'versions.html').write_text(document,encoding='utf-8')
    index=dest/'index.html'
    content=index.read_text(encoding='utf-8')
    if 'href="versions.html"' not in content:
        label='前回と今回の仕上げを比較する' if options.finishing or options.clear or options.jpeg or options.compare else '初回・前回・今回の写真を比較する'
        content=content.replace('<main class="grid">',f'<p style="max-width:1344px;margin:0 auto 24px;padding:0 28px"><a href="versions.html">{label}</a></p><main class="grid">')
        index.write_text(content,encoding='utf-8')
    print('Version comparison:',dest/'versions.html')

if __name__=='__main__':
    main()

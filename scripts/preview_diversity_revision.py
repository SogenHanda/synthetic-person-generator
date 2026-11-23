"""Show newly generated faces from the diversity revision without claiming completion."""
import json
import argparse
import math
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,PUBLIC_KEYS,photo_delivery_size
from generator.photo_finish import finish,parameters
from generator.pipeline import write_csv
from generator.portable import render

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--all-completed',action='store_true')
    parser.add_argument('--config',default='configs/realvis1000_diverse.json')
    args=parser.parse_args()
    work=ROOT/'work'/Path(args.config).stem
    state=read_json(work/'state.json')
    config=state['config']
    target=config['count']
    people=[p for p in (state['people'] if args.all_completed else state['people'][10:]) if p['face_result']]
    if not args.all_completed: people=people[:24]
    dest=ROOT/'outputs'/(f'realvis{target}_progress' if args.all_completed else 'realvis1000_diversity_preview')
    (dest/'faces').mkdir(parents=True,exist_ok=True)
    columns=8 if args.all_completed else 6
    ordered=sorted(people,key=lambda p:p['portrait_spec']['photo_age']) if args.all_completed else people
    samples=[ordered[round(i*(len(ordered)-1)/(min(48,len(ordered))-1))] for i in range(min(48,len(ordered)))] if len(ordered)>1 else ordered
    sample_positions={p['person_id']:i for i,p in enumerate(samples)}
    sheet=Image.new('RGB',(columns*192,max(1,math.ceil(len(samples)/columns))*192),'#f1f0ec')
    rows=[]
    for i,p in enumerate(people):
        relative='faces/'+p['person_id']+'.jpg'
        with Image.open(work/'originals'/(p['person_id']+'.png')) as image:
            settings,seed=parameters(config,p)
            result=finish(image,settings,photo_delivery_size(config,p),seed)
            result.save(dest/relative,format='JPEG',quality=settings['delivery_jpeg_quality'],subsampling=2)
        if p['person_id'] in sample_positions:
            position=sample_positions[p['person_id']]
            with Image.open(dest/relative) as actual:
                sheet.paste(actual.resize((192,192),Image.Resampling.LANCZOS),((position%columns)*192,(position//columns)*192))
        record={**p['profile'],'birth_date':p['birth_date'],'face_path':relative}
        rows.append({key:record.get(key,'') for key in PUBLIC_KEYS})
    write_csv(dest/'profiles.csv',rows,PUBLIC_KEYS)
    (dest/'profiles.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    render(dest,rows)
    html=dest/'index.html'
    title=f'生成途中：{len(rows)} / {target}人（保存済みの確認用）' if args.all_completed else f'顔の多様性・試作{len(rows)}枚（{target}人版の一部）'
    html.write_text(html.read_text(encoding='utf-8').replace('人物データセット一覧',title),encoding='utf-8')
    if args.all_completed:
        readme=dest/'README.txt'
        readme.write_text(f'生成途中の確認用です。現時点の保存済み{len(rows)}人を収録しています。{target}人分の完成版とは別フォルダです。\n\n'+readme.read_text(encoding='utf-8'),encoding='utf-8')
    sheet.save(dest/'contact_sheet.jpg',quality=95,subsampling=0)
    print('Diversity preview:',len(rows),dest/'index.html')

if __name__=='__main__': main()

"""Reuse existing face PNGs and Qwen names; create a new fast-profile batch."""
import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,sha256,write_json
from generator.pipeline import state,generate_profiles,export_batch,package,preview

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='configs/test100.json')
    parser.add_argument('--config',default='configs/test100_fast.json')
    args=parser.parse_args()
    source_path=ROOT/'work'/Path(args.source).stem/'state.json'
    if not source_path.is_file():
        raise ValueError('Source generation state is missing')
    source=read_json(source_path)
    if not all(p['face_result'] and p['profile'] for p in source['people']):
        raise ValueError('Source batch must be complete')
    config_path=ROOT/args.config
    if not config_path.exists():
        config=read_json(ROOT/args.source)
        config['profiles']={'mode':'local'}
        config['as_of']=date.today().isoformat()
        write_json(config_path,config)
    config,path,saved=state(config_path)
    if config.get('profiles',{}).get('mode')!='local' or len(saved['people'])!=len(source['people']):
        raise ValueError('Destination must be a matching-count local-profile batch')
    if saved.get('source_batch') not in (None,source['batch_id']):
        raise ValueError('Source batch conflict')
    for old,new in zip(source['people'],saved['people']):
        raw=source_path.parent/'originals'/(old['person_id']+'.png')
        if sha256(raw)!=old['face_result']['sha256']:
            raise ValueError('Source face hash mismatch')
        target=path.parent/'originals'/(new['person_id']+'.png')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copy2(raw,target)
        elif sha256(target)!=old['face_result']['sha256']:
            raise ValueError('Conflicting existing destination image')
        new['face_seed']=old['face_seed']
        new['face_result']=old['face_result']
        new['birth_date']=old['birth_date']
        reference=date.fromisoformat(config['as_of'])
        birth=date.fromisoformat(old['birth_date'])
        new['age']=reference.year-birth.year-((reference.month,reference.day)<(birth.month,birth.day))
        new['name_cache']={k:old['profile'][k] for k in ('name','name_kana')}
    saved['face_model']=source['face_model']
    saved['source_batch']=source['batch_id']
    saved['age_assignment_method']=source.get('age_assignment_method','copied fictional birth date')
    write_json(path,saved)
    generate_profiles(config_path)
    export_batch(config_path)
    package(config_path)
    preview(config_path)

if __name__=='__main__':
    main()

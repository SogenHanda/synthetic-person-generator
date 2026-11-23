"""Reuse the worn portraits and reduce only added noise and JPEG compression."""
import copy
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.pipeline import state
from generator.photo_finish import parameters

def main():
    source_config=read_json(ROOT/'configs/realvis10_worn.json')
    config=copy.deepcopy(source_config)
    for spec in config['portrait_specs']:
        settings=spec['finish']
        settings['grain']=round(settings['grain']*.65,3)
        settings['chroma_noise']=round(settings['chroma_noise']*.65,3)
        settings['camera_jpeg_quality']=min(95,settings['camera_jpeg_quality']+14)
        settings['delivery_jpeg_quality']=min(95,settings['delivery_jpeg_quality']+12)
    target=ROOT/'configs/realvis10_softgrain.json'
    if target.exists() and read_json(target)!=config:
        raise ValueError('Existing experiment differs; use a new config name')
    write_json(target,config)
    _,path,saved=state(target)
    if saved.get('source_batch'):
        print('Experiment already initialized:',saved['batch_id'])
        return
    source_path=ROOT/'work/realvis10_worn/state.json'
    source=read_json(source_path)
    for previous,current in zip(source['people'],saved['people']):
        original=source_path.parent/'originals'/(previous['person_id']+'.png')
        if not previous['face_result'] or sha256(original)!=previous['face_result']['sha256']:
            raise ValueError('Source portrait incomplete or changed')
        destination=path.parent/'originals'/(current['person_id']+'.png')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,destination)
        current['face_result']=copy.deepcopy(previous['face_result'])
        current['face_result'].update({'seconds':0,'source_generation_seconds':previous['face_result']['seconds'],
                                      'source_person_id':previous['person_id'],'reused_from_batch':source['batch_id']})
        current['profile']=copy.deepcopy(previous['profile'])
        current['profile_result']={'seconds':0,'engine':'reused source profile','source_person_id':previous['person_id']}
        current['birth_date']=previous['birth_date']
        current['photo_finish_seed']=str(parameters(source_config,previous)[1])
    saved['face_model']=copy.deepcopy(source['face_model'])
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine'].update({'generation_seconds':0,'count_this_run':0})
    saved['source_profiles_batch']=source['batch_id']
    saved['source_batch']=source['batch_id']
    write_json(path,saved)
    print('Lower-noise finishing experiment initialized:',saved['batch_id'])

if __name__=='__main__':
    main()

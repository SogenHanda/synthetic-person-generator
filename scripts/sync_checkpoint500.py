"""Preserve all checkpoint originals in the paused 1000-person work state."""
import copy
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256,now

def main():
    checkpoint=read_json(ROOT/'work/realvis500_checkpoint/state.json')
    assert len(checkpoint['people'])==500 and all(p['face_result'] for p in checkpoint['people'])
    path=ROOT/'work/realvis1000_diverse/state.json'
    source=read_json(path)
    by_id={p['person_id']:p for p in source['people']}
    mapping={p['person_id']:p['source_person_id'] for p in checkpoint['people']}
    for person in checkpoint['people']:
        old=by_id[person['source_person_id']]
        original=ROOT/'work/realvis500_checkpoint/originals'/(person['person_id']+'.png')
        assert sha256(original)==person['face_result']['sha256']
        dest=path.parent/'originals'/(old['person_id']+'.png')
        if dest.exists() and sha256(dest)!=person['face_result']['sha256']:
            if old['face_result']:raise ValueError('Previously accepted original changed')
            backup=ROOT/'work/trials/checkpoint500_stale_candidates'
            backup.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,backup/(old['person_id']+'_'+sha256(dest)[:12]+'.png'))
            shutil.copyfile(original,dest)
        elif not dest.exists():shutil.copyfile(original,dest)
        assert sha256(dest)==person['face_result']['sha256']
        if not old['face_result']:
            for key in ('face_result','face_seed','portrait_spec','face_attempts','face_seed_initial'):
                if key in person:old[key]=copy.deepcopy(person[key])
            for decision in [old['face_result'].get('diversity_check',{})]+old.get('face_attempts',[]):
                if decision.get('nearest_person_id') in mapping:decision['nearest_person_id']=mapping[decision['nearest_person_id']]
    source['checkpoints']=[{'batch_id':checkpoint['batch_id'],'person_count':500,'created_at':now(),
                           'person_id_mapping':mapping}]
    write_json(path,source)
    status_path=path.parent/'worker_status.json'
    status=read_json(status_path)
    status.update({'status':'paused','faces_completed':500,'target':1000,'pause_reason':'User requested stop at 500.',
                   'checkpoint_batch_id':checkpoint['batch_id']})
    write_json(status_path,status)
    print('1000-person work state preserved at exactly 500 completed images; generation remains paused.')

if __name__=='__main__':main()

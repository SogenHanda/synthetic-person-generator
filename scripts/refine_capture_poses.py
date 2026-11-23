"""Refine three unpublished capture trials, retaining first-attempt originals."""
import copy
import shutil
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,config_digest,now

def main():
    config_path=ROOT/'configs/realvis10_livedin.json'
    path=ROOT/'work/realvis10_livedin/state.json'
    config,saved=read_json(config_path),read_json(path)
    updates={2:'three-quarter view, face angled left, eyes near camera',
             5:'three-quarter view, face angled right, gaze slightly aside',
             8:'three-quarter view, head tilted left, eyes near camera'}
    if all(config['portrait_specs'][i]['pose']==pose and config['portrait_specs'][i].get('view_emphasis')=='off-angle' for i,pose in updates.items()):
        print('Pose refinements already applied')
        return
    if (ROOT/'outputs'/saved['batch_id']/'manifest.json').exists():
        raise ValueError('Cannot revise a completed batch')
    if not all(p['face_result'] for p in saved['people']):
        raise ValueError('Wait for initial capture generation to finish')
    backup=ROOT/'work/trials'/('livedin_pose_attempt_'+time.strftime('%H%M%S'))
    backup.mkdir(parents=True,exist_ok=True)
    write_json(backup/'config.json',config)
    write_json(backup/'state.json',saved)
    previous=config_digest(config)
    for i,pose in updates.items():
        person=saved['people'][i]
        raw=path.parent/'originals'/(person['person_id']+'.png')
        shutil.copy2(raw,backup/raw.name)
        config['portrait_specs'][i]['pose']=pose
        config['portrait_specs'][i].update({'view_emphasis':'off-angle','guidance_scale':6.0})
        person['portrait_spec']=copy.deepcopy(config['portrait_specs'][i])
        person['face_result']=None
    saved['config']=config
    saved['config_sha256']=config_digest(config)
    saved.setdefault('draft_adjustments',[]).append({'time':now(),'previous_config_sha256':previous,
                                                   'reason':'Small angle wording produced frontal faces; use explicit three-quarter wording for three captures.'})
    write_json(config_path,config)
    write_json(path,saved)
    print('Prepared three pose refinements; initial originals retained')

if __name__=='__main__':
    main()

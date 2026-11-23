"""Unpublished draft migration: apply the same diversity screen to the initial ten."""
import copy
import time
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,config_digest

def main():
    config_path=ROOT/'configs/realvis1000_diverse.json'
    state_path=ROOT/'work/realvis1000_diverse/state.json'
    config=read_json(config_path)
    saved=read_json(state_path)
    if saved.get('all_faces_diverse'):
        print('Initial portraits already migrated')
        return
    if (ROOT/'outputs'/saved['batch_id']/'manifest.json').exists():
        raise ValueError('Never migrate a published batch')
    backup=ROOT/'work/trials'/('diversity_initial_ten_'+time.strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    write_json(backup/'config.json',config)
    write_json(backup/'state.json',saved)
    traits=[
        ('round full face','broad flat nose','full lips','small hooded eyes','thick straight brows','short cropped hair','no glasses'),
        ('long narrow face','long prominent nose','thin tight lips','wide-set eyes','sparse eyebrows','buzz cut','wire glasses'),
        ('square angular jaw','short rounded nose','small mouth','round open eyes','arched eyebrows','tied-back hair','thick glasses'),
        ('round full face','wide low nose','wide mouth','round open eyes','low heavy brows','curly short hair','no glasses'),
        ('long narrow face','narrow straight nose','thin tight lips','close-set eyes','arched eyebrows','wavy shoulder-length hair','rimless glasses'),
        ('wide jaw, narrow forehead','short rounded nose','full lips','small hooded eyes','thick straight brows','balding head','no glasses'),
        ('triangular face, pointed chin','narrow straight nose','wide mouth','downturned eyes','sparse eyebrows','short grey hair','wire glasses'),
        ('oval face, prominent chin','long prominent nose','small mouth','wide-set eyes','thick straight brows','side-parted grey hair','no glasses'),
        ('round full face','wide low nose','full lips','small hooded eyes','sparse eyebrows','short grey hair','round glasses'),
        ('square angular jaw','broad flat nose','thin tight lips','close-set eyes','low heavy brows','bald head','thick glasses'),
    ]
    for i,trait in enumerate(traits):
        spec=config['portrait_specs'][i]
        shape,nose,mouth,eyes,brows,hair,accessory=trait
        spec.update({'capture_style':'diverse-v3','face_structure':shape,'nose':nose,'mouth':mouth,
                     'eyes':eyes,'brows':brows,'appearance':hair,'accessory':accessory})
        spec.pop('pose',None)
        person=saved['people'][i]
        raw=state_path.parent/'originals'/(person['person_id']+'.png')
        if raw.exists(): raw.replace(backup/raw.name)
        person.update({'portrait_spec':copy.deepcopy(spec),'face_result':None,
                       'face_seed':config['face_seed_start']+i,'face_attempts':[],
                       'face_seed_initial':config['face_seed_start']+i})
    saved.update({'config':config,'config_sha256':config_digest(config),'source_batch':None,
                  'style_reference_batch':'batch_20261124_012032_00c911a8','all_faces_diverse':True})
    saved.setdefault('draft_adjustments',[]).append({'reason':'Screen all 1000 faces; cached ten also contained a high-similarity pair.',
                                                   'backup':backup.relative_to(ROOT).as_posix()})
    write_json(config_path,config)
    write_json(state_path,saved)
    print('Initial ten scheduled for fresh diverse generation; previous pixels preserved:',backup)

if __name__=='__main__': main()

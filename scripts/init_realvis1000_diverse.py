"""A separate revision with balanced face morphology and online similarity screening."""
import copy
import random
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.pipeline import state
from generator.photo_finish import parameters

def main():
    target=ROOT/'configs/realvis1000_diverse.json'
    if target.exists():
        print('Already initialized:',state(target)[2]['batch_id'])
        return
    source_config=read_json(ROOT/'configs/realvis1000.json')
    source=read_json(ROOT/'work/realvis1000/state.json')
    config=copy.deepcopy(source_config)
    config['face_seed_start']=190000
    config['face_diversity']={'threshold':.65,'max_attempts':16}
    rng=random.Random(2026112419)
    shapes=['round full face','long narrow face','square angular jaw','broad cheekbones, short chin',
            'triangular face, pointed chin','oval face, prominent chin','wide jaw, narrow forehead','broad forehead, small chin']
    noses=['broad flat nose','narrow straight nose','short rounded nose','long prominent nose','small upturned nose','wide low nose']
    eyes=['narrow monolid eyes','round open eyes','small hooded eyes','wide-set eyes','close-set eyes','downturned eyes','unequal eyelid folds']
    mouths=['thin tight lips','full lips','wide mouth','small mouth','uneven lips']
    brows=['thick straight brows','sparse eyebrows','arched eyebrows','low heavy brows']
    structures=[]
    for shape in shapes:
        for nose in noses:
            for eye in eyes:
                for mouth in mouths:
                    for brow in brows:
                        structures.append((shape,nose,eye,mouth,brow))
    rng.shuffle(structures)
    for i,spec in enumerate(config['portrait_specs']):
        if i<10: continue
        shape,nose,eye,mouth,brow=structures.pop()
        spec.update({'capture_style':'diverse-v3','face_structure':shape,'nose':nose,'eyes':eye,
                     'mouth':mouth,'brows':brow,'accessory':rng.choice(['no glasses']*6+['wire glasses','thick glasses','rimless glasses'])})
        age=spec['photo_age']
        if spec['presentation']=='man':
            hair=['short side-parted hair','buzz cut','curly short hair','shaggy hair','slicked-back hair','uneven bangs']
            if age>=40: hair+=['receding hairline','balding head','sparse greying hair']
            if age>=60: hair+=['bald head','white short hair']
        else:
            hair=['tied-back hair','short bob','wavy shoulder-length hair','long straight hair','short cropped hair','uneven bangs']
            if age>=50: hair+=['short grey hair','loosely tied greying hair']
        spec['appearance']=rng.choice(hair)
    write_json(target,config)
    _,path,saved=state(target)
    approved_path=ROOT/'work/realvis10_framing/state.json'
    approved=read_json(approved_path)
    approved_config=read_json(ROOT/'configs/realvis10_framing.json')
    for i,(old,new) in enumerate(zip(source['people'],saved['people'])):
        new['profile']=copy.deepcopy(old['profile'])
        new['birth_date']=old['birth_date']
        new['profile_result']={'seconds':0,'engine':'reused existing structured profile','source_person_id':old['person_id']}
        if i<10:
            previous=approved['people'][i]
            new['face_seed']=previous['face_seed']
            original=approved_path.parent/'originals'/(previous['person_id']+'.png')
            assert sha256(original)==previous['face_result']['sha256']
            dest=path.parent/'originals'/(new['person_id']+'.png')
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(original,dest)
            new['face_result']=copy.deepcopy(previous['face_result'])
            new['face_result'].update({'seconds':0,'reused_from_batch':approved['batch_id']})
            new['photo_finish_seed']=str(parameters(approved_config,previous)[1])
    saved['face_model']=copy.deepcopy(source['face_model'])
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine'].update({'generation_seconds':0,'count_this_run':0})
    saved['source_profiles_batch']=source['batch_id']
    saved['source_batch']=approved['batch_id']
    saved['diversity_revision']='v3: randomized morphology plus SFace near-duplicate rejection'
    write_json(path,saved)
    print('Initialized diversity revision:',saved['batch_id'])

if __name__=='__main__': main()

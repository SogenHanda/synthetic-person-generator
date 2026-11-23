"""Initialize 1,000 unique portraits/profiles using the approved ten-person finish."""
import copy
import random
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.pipeline import state,generate_profiles
from generator.photo_finish import parameters
from generator.local_profiles import SURNAMES,GIVEN_NAMES

def main():
    target=ROOT/'configs/realvis1000.json'
    if target.exists():
        _,_,saved=state(target)
        print('Existing 1000-person batch:',saved['batch_id'])
        generate_profiles(target)
        return
    source_config=read_json(ROOT/'configs/realvis10_framing.json')
    source_path=ROOT/'work/realvis10_framing/state.json'
    source=read_json(source_path)
    config=copy.deepcopy(source_config)
    config.update({'count':1000,'seed':2026112401,'portable':True,'capture_comparison':False})
    rng=random.Random(config['seed'])
    presentations=['man']*495+['woman']*495
    rng.shuffle(presentations)
    for presentation in presentations:
        age=rng.choices([(20,29),(30,39),(40,49),(50,59),(60,69),(70,79),(80,85)],[16,20,20,18,14,10,2])[0]
        age=rng.randint(*age)
        candidates=[s for s in source_config['portrait_specs'] if s['presentation']==presentation]
        spec=copy.deepcopy(min(candidates,key=lambda s:abs(s['age']-age)))
        photo_age=max(18,age-rng.randint(0,8))
        spec.update({'age':age,'photo_age':photo_age,'years_before_reference':age-photo_age})
        spec.pop('pose',None)
        spec['background']=rng.choice(['white','white','light blue'])
        spec['eyes']=rng.choice(['narrow eyes, unequal eyelid folds','one eyelid droops slightly','small hooded eyes',
                                 'slightly uneven eyelids','natural asymmetric eyelids'])
        if photo_age<35:
            skins=['acne scars, oily blotchy skin','pitted acne scars, dark eye circles','rough dry skin, tired eye bags','enlarged pores, small blemishes']
        elif photo_age<55:
            skins=['enlarged pores, tired eye bags','rough skin, forehead wrinkles','pitted scars, uneven skin tone','dry skin, dark eye circles']
        else:
            skins=['sun spots, coarse wrinkles','weathered skin, forehead creases','age spots, sagging skin','mottled skin, deep eye bags']
        spec['skin']=rng.choice(skins)
        if presentation=='man':
            spec['appearance']=rng.choice(['untidy black fringe','messy short hair','uneven side-parted hair'] if photo_age<50 else ['thinning messy hair','untidy greying hair','sparse short hair'])
            spec['clothes']=rng.choice(['navy suit','dark suit and tie','charcoal suit','grey jacket','worn dark suit','plain cardigan'])
        else:
            spec['appearance']=rng.choice(['uneven messy bangs','stray wispy bangs','untidy thin bangs','messy shoulder-length hair'] if photo_age<55 else ['messy greying fringe','sparse uneven bangs','short untidy greying hair'])
            spec['clothes']=rng.choice(['navy suit','grey business jacket','dark cardigan','beige jacket','brown cardigan','plain blouse'])
        spec['lighting']=rng.choice(['fluorescent light','direct flash','office light','booth flash','compact camera flash'])
        finish=copy.deepcopy(rng.choice(source_config['portrait_specs'])['finish'])
        width=rng.uniform(.88,.98)
        left=rng.uniform(.003,1-width-.003)
        top=rng.uniform(.003,min(.08,1-width-.003))
        size=rng.choice([240,256,272,288,320,352,384,416,448,480])
        quality=max(27,min(52,round(27+(size-240)*25/240+rng.randint(-5,5))))
        finish.update({'delivery_size':size,'delivery_jpeg_quality':quality,
                       'frame_crop':[round(left,6),round(top,6),round(left+width,6),round(top+width,6)],
                       'scan_angle':round(rng.choice([-1,1])*rng.uniform(.4,2),2)})
        spec['finish']=finish
        config['portrait_specs'].append(spec)
    write_json(target,config)
    _,path,saved=state(target)
    used_names={p['profile']['name'] for p in source['people']}
    pools={}
    for presentation,givens in [('man',GIVEN_NAMES[:20]),('woman',GIVEN_NAMES[20:])]:
        pool=[{'name':surname+' '+given,'name_kana':sk+' '+gk,'source':'local paired dictionary sampled without replacement'}
              for surname,sk in SURNAMES for given,gk in givens if surname+' '+given not in used_names]
        rng.shuffle(pool)
        pools[presentation]=pool
    for i,current in enumerate(saved['people']):
        if i<10:
            previous=source['people'][i]
            original=source_path.parent/'originals'/(previous['person_id']+'.png')
            if sha256(original)!=previous['face_result']['sha256']:
                raise ValueError('Approved source hash changed')
            dest=path.parent/'originals'/(current['person_id']+'.png')
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(original,dest)
            current.update({'profile':copy.deepcopy(previous['profile']),'birth_date':previous['birth_date'],
                            'face_result':copy.deepcopy(previous['face_result']),
                            'photo_finish_seed':str(parameters(source_config,previous)[1]),
                            'profile_result':{'seconds':0,'engine':'reused approved profile','source_person_id':previous['person_id']}})
            current['face_result'].update({'seconds':0,'reused_from_batch':source['batch_id'],'source_person_id':previous['person_id']})
        else:
            current['name_cache']=pools[current['portrait_spec']['presentation']].pop()
    saved['face_model']=copy.deepcopy(source['face_model'])
    saved['source_batch']=source['batch_id']
    saved['source_reuse_count']=10
    write_json(path,saved)
    generate_profiles(target)
    print('1000-person batch initialized:',saved['batch_id'])

if __name__=='__main__':
    main()

"""Rebalance an unpublished batch, retaining completed, correctly aged portraits."""
import copy
import random
import shutil
import sys
import time
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,config_digest
from generator.pipeline import generate_profiles

TARGETS=[(6,15,10),(16,19,70),(20,29,170),(30,39,180),(40,49,180),
         (50,59,160),(60,69,120),(70,79,80),(80,89,30)]

def main():
    target=ROOT/'configs/realvis1000_diverse.json'
    state_path=ROOT/'work/realvis1000_diverse/state.json'
    config=read_json(target);saved=read_json(state_path)
    if saved.get('age_distribution_revision'):
        print('Age distribution already adjusted')
        return
    if (ROOT/'outputs'/saved['batch_id']/'manifest.json').exists():
        raise ValueError('Never change a published batch')
    backup=ROOT/'work/trials'/('age_distribution_'+time.strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    write_json(backup/'config.json',config);write_json(backup/'state.json',saved)
    rejected=state_path.parent/'rejected'
    if rejected.exists(): shutil.copytree(rejected,backup/'rejected')
    rng=random.Random(2026112420)
    reference=date.fromisoformat(config['as_of'])
    for presentation in ('man','woman'):
        completed=[p for p in saved['people'] if p['face_result'] and p['portrait_spec']['presentation']==presentation]
        pending=[(i,p) for i,p in enumerate(saved['people']) if not p['face_result'] and p['portrait_spec']['presentation']==presentation]
        ages=[]
        for low,high,total in TARGETS:
            remaining=total//2-sum(low<=p['age']<=high for p in completed)
            if remaining<0: raise ValueError('Completed images exceed the new quota')
            ages.extend(rng.randint(low,high) for _ in range(remaining))
        if len(ages)!=len(pending): raise ValueError('Age quota mismatch')
        rng.shuffle(ages)
        for (i,p),age in zip(pending,ages):
            spec=config['portrait_specs'][i]
            minimum=6 if age<=15 else 16 if age<=19 else 80 if age>=80 else 18
            maximum_years=1 if age<=15 else 2 if age<=19 else 4 if age>=80 else 8
            photo_age=age-rng.randint(0,min(maximum_years,max(0,age-minimum)))
            spec.update({'age':age,'photo_age':photo_age,'years_before_reference':age-photo_age})
            if photo_age<20:
                spec['skin']=rng.choice(['natural uneven skin','mild acne, natural skin'] if photo_age>=13 else ['natural skin, small freckles','natural uneven skin'])
                spec['appearance']=rng.choice(['short dark hair','messy fringe','straight dark hair'])
                spec['clothes']=rng.choice(['white shirt','school blazer','plain cardigan'])
            elif photo_age<35:
                spec['skin']=rng.choice(['acne scars, oily blotchy skin','rough dry skin, tired eyes','enlarged pores, small blemishes'])
            elif photo_age<55:
                spec['skin']=rng.choice(['enlarged pores, eye bags','rough skin, forehead wrinkles','dry uneven skin'])
            else:
                spec['skin']=rng.choice(['sun spots, coarse wrinkles','weathered skin, forehead creases','age spots, sagging skin'])
            if photo_age>=65:
                spec['appearance']=rng.choice(['short white hair','sparse grey hair','untidy greying hair']+(['bald head'] if presentation=='man' else []))
            elif photo_age>=20:
                hair=['short side-parted hair','buzz cut','curly short hair','shaggy hair','slicked-back hair','uneven bangs'] if presentation=='man' else ['tied-back hair','short bob','wavy shoulder-length hair','long straight hair','short cropped hair','uneven bangs']
                spec['appearance']=rng.choice(hair)
            earliest=reference.replace(year=reference.year-age-1)+timedelta(days=1)
            latest=reference.replace(year=reference.year-age)
            p['birth_date']=(earliest+timedelta(days=rng.randint(0,(latest-earliest).days))).isoformat()
            old=p['profile']
            p['name_cache']={'name':old['name'],'name_kana':old['name_kana'],'source':'preserved paired name across age revision'}
            p.update({'age':age,'portrait_spec':copy.deepcopy(spec),'profile':None,'face_seed':config['face_seed_start']+i})
            if p.get('face_attempts'):
                p['prior_face_attempts']=p['face_attempts']
            p['face_attempts']=[]
            p['face_seed_initial']=p['face_seed']
    config['age_distribution']={'purpose':'artwork sampling design; not an estimate of population prevalence',
                                'groups':[{'min':a,'max':b,'count':n} for a,b,n in TARGETS]}
    saved.update({'config':config,'config_sha256':config_digest(config),'age_distribution_revision':'v1: 15 and under 1%; age 6..89'})
    saved.setdefault('draft_adjustments',[]).append({'reason':'Broaden age range with very few under-16 portraits; completed adults retained.',
                                                   'backup':backup.relative_to(ROOT).as_posix()})
    write_json(target,config);write_json(state_path,saved)
    generate_profiles(target)
    result=read_json(state_path)
    counts={f'{low}-{high}':sum(low<=p['age']<=high for p in result['people']) for low,high,_ in TARGETS}
    assert list(counts.values())==[n for _,_,n in TARGETS]
    assert len({p['profile']['name'] for p in result['people']})==1000
    print('Age distribution:',counts)
    print('Completed portraits retained:',sum(bool(p['face_result']) for p in result['people']))

if __name__=='__main__': main()

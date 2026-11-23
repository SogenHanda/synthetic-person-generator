"""Fictional age direction for this uncurated 100-image comparison only.

Approximate visual estimates by the assistant, not verified ages or identities.
Keeps face IDs/seeds and refuses to overwrite generated Qwen profiles.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AGES=[40,60,30,28,8,35,3,40,65,45,
      45,24,6,45,45,25,35,28,50,65,
      3,40,60,40,35,55,28,40,30,50,
      40,38,8,40,23,45,25,45,20,30,
      25,55,70,25,45,35,24,45,45,22,
      25,35,25,8,3,30,50,28,25,35,
      30,45,40,25,30,50,50,50,7,50,
      3,40,28,25,35,25,60,35,55,60,
      35,40,30,25,6,35,25,50,45,4,
      60,55,70,45,16,40,60,55,3,25]

def main():
    path=ROOT/'work/test100/state.json'
    state=json.loads(path.read_text(encoding='utf-8'))
    if state.get('age_assignment_method')=='approximate_visual_fictional_setting_v1':
        print('Age direction already applied; no changes.')
        return
    if [p['face_seed'] for p in state['people']]!=list(range(1000,1100)):
        raise ValueError('Age notes apply only to this seed range')
    if any(p['profile'] for p in state['people']):
        raise ValueError('Refusing to change an existing profile')
    reference=date.fromisoformat(state['config']['as_of'])
    for index,(person,age) in enumerate(zip(state['people'],AGES)):
        earliest=reference.replace(year=reference.year-age-1)+timedelta(days=1)
        latest=reference.replace(year=reference.year-age)
        rng=random.Random(state['config']['seed']+index)
        person['birth_date']=(earliest+timedelta(days=rng.randint(0,(latest-earliest).days))).isoformat()
        person['age']=age
    state['age_assignment_method']='approximate_visual_fictional_setting_v1'
    temp=path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
    notes={'method':state['age_assignment_method'],'batch_id':state['batch_id'],
           'note':'Approximate appearance-based fictional age settings by assistant; unverified, not actual ages.',
           'people':[{'person_id':p['person_id'],'face_seed':p['face_seed'],'fictional_age':p['age'],'birth_date':p['birth_date']} for p in state['people']]}
    (ROOT/'reports/test100_age_direction.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Applied 100 fictional age settings; images and IDs unchanged.')

if __name__=='__main__':
    main()

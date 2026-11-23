"""Keep completed portraits and select a balanced 500-person checkpoint."""
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
    target=ROOT/'configs/realvis500_checkpoint.json'
    if target.exists():
        print('Checkpoint already initialized:',state(target)[2]['batch_id']);return
    source_path=ROOT/'work/realvis1000_diverse/state.json'
    source=read_json(source_path);original=source['config']
    completed=[p for p in source['people'] if p['face_result']]
    if len(completed)>500:raise ValueError('More than 500 portraits already exist')
    rng=random.Random(20261124500)
    groups=[];odd=False
    for group in original['age_distribution']['groups']:
        total=group['count']//2
        members=[p for p in source['people'] if group['min']<=p['age']<=group['max']]
        done=[p for p in members if p['face_result']]
        if len(done)>total:raise ValueError('Completed age cohort exceeds checkpoint quota')
        done_f=sum(p['portrait_spec']['presentation']=='woman' for p in done)
        done_m=len(done)-done_f
        female=total//2
        if total%2:
            odd=not odd;female+=int(odd)
        female=max(done_f,min(total-done_m,female))
        groups.append({'min':group['min'],'max':group['max'],'count':total,'female':female,'lo':done_f,'hi':total-done_m,'members':members})
    delta=250-sum(g['female'] for g in groups)
    for g in groups:
        change=min(delta,g['hi']-g['female']) if delta>0 else -min(-delta,g['female']-g['lo'])
        g['female']+=change;delta-=change
    assert delta==0
    chosen=[]
    for group in groups:
        for presentation,total in [('woman',group['female']),('man',group['count']-group['female'])]:
            members=[p for p in group['members'] if p['portrait_spec']['presentation']==presentation]
            done=[p for p in members if p['face_result']]
            pending=[p for p in members if not p['face_result']]
            rng.shuffle(pending)
            chosen+=done+pending[:total-len(done)]
    chosen_ids={p['person_id'] for p in chosen}
    chosen=[p for p in source['people'] if p['person_id'] in chosen_ids]
    assert len(chosen)==500 and all(p['person_id'] in chosen_ids for p in completed)
    config=copy.deepcopy(original)
    config.update({'count':500,'portrait_specs':[copy.deepcopy(p['portrait_spec']) for p in chosen]})
    config['age_distribution']['groups']=[{k:g[k] for k in ('min','max','count')} for g in groups]
    write_json(target,config)
    _,path,saved=state(target)
    mapping={old['person_id']:new['person_id'] for old,new in zip(chosen,saved['people'])}
    for old,new in zip(chosen,saved['people']):
        new.update({k:copy.deepcopy(old[k]) for k in ('age','birth_date','profile','face_seed','profile_seed','portrait_spec','face_attempts','face_seed_initial') if k in old})
        new['source_person_id']=old['person_id']
        new['profile_result']={'seconds':0,'engine':'reused existing profile for checkpoint','source_person_id':old['person_id']}
        new['photo_finish_seed']=str(parameters(original,old)[1])
        for attempt in new.get('face_attempts',[]):
            if attempt.get('nearest_person_id') in mapping: attempt['nearest_person_id']=mapping[attempt['nearest_person_id']]
        if old['face_result']:
            raw=source_path.parent/'originals'/(old['person_id']+'.png')
            assert sha256(raw)==old['face_result']['sha256']
            dest=path.parent/'originals'/(new['person_id']+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(raw,dest)
            new['face_result']=copy.deepcopy(old['face_result'])
            new['face_result'].update({'source_generation_seconds':old['face_result']['seconds'],'seconds':0,
                                       'source_person_id':old['person_id'],'reused_from_batch':source['batch_id']})
            check=new['face_result'].get('diversity_check',{})
            if check.get('nearest_person_id') in mapping:check['nearest_person_id']=mapping[check['nearest_person_id']]
    saved['face_model']=copy.deepcopy(source['face_model'])
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine'].update({'generation_seconds':0,'count_this_run':0})
    saved['source_batch']=source['batch_id']
    saved['checkpoint_source_config']='configs/realvis1000_diverse.json'
    saved['source_reuse_count']=len(completed)
    saved['draft_adjustments']=[{'reason':'User requested stop at 500; retain all completed faces and halve planned age quotas.'}]
    write_json(path,saved)
    status_path=source_path.parent/'worker_status.json'
    status=read_json(status_path)
    status.update({'status':'paused','pause_reason':'User requested generation stop at 500; checkpoint worker handles the remainder.',
                   'checkpoint_batch_id':saved['batch_id']})
    write_json(status_path,status)
    print('Checkpoint initialized:',saved['batch_id'],'reused:',len(completed),'remaining:',500-len(completed))
    print('Age quotas:',config['age_distribution']['groups'])

if __name__=='__main__':main()

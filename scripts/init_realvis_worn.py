"""Independent stronger realism experiment; preserves completed earlier batches."""
import copy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json
from generator.pipeline import state

def main():
    config=read_json(ROOT/'configs/realvis10_livedin.json')
    config['diffusion']['guidance_scale']=5.0
    # Hair, eyes and skin are intentionally distributed rather than identical on every face.
    traits=[
        ('uneven messy bangs','narrow eyes, unequal eyelid folds','acne scars, oily blotchy skin'),
        ('untidy black fringe','one eyelid droops slightly','pitted acne scars, dark eye circles'),
        ('stray wispy bangs','narrow eyes, uneven eyelids','rough dry skin, tired eye bags'),
        ('messy short hair','small eyes, unequal eyelid folds','enlarged pores, shaving rash'),
        ('untidy thin bangs','one eye slightly narrower','deep eye bags, mottled skin'),
        ('thinning messy hair','narrow eyes, uneven eyelids','pitted scars, forehead wrinkles'),
        ('messy greying fringe','unequal drooping eyelids','sun spots, coarse wrinkles'),
        ('untidy greying hair','small hooded eyes','weathered skin, deep forehead creases'),
        ('sparse uneven bangs','one eyelid droops slightly','age spots, sagging wrinkled skin'),
        ('disheveled grey hair','narrow asymmetric eyelids','coarse wrinkles, mottled age spots'),
    ]
    # Stronger camera degradation, ranging from legible to conspicuously old/compressed.
    finishes=[
        (256,58,.22,6.0,1.0,[3,1,-4],.87,.98,.93),
        (192,40,.35,9.0,1.7,[5,2,-5],.78,.94,.89),
        (288,62,.18,5.0,.8,[0,2,1],.91,1.00,.96),
        (224,46,.40,7.5,1.3,[4,2,-5],.82,1.02,.91),
        (256,54,.23,6.5,1.1,[-2,2,3],.89,.96,.92),
        (176,36,.42,10.0,2.0,[4,0,-4],.76,.95,.88),
        (224,44,.32,8.0,1.4,[6,3,-6],.77,1.01,.89),
        (288,60,.20,5.5,.9,[2,0,-3],.87,.98,.94),
        (192,38,.48,9.5,1.8,[7,3,-6],.73,1.03,.87),
        (240,48,.30,7.0,1.2,[2,2,-2],.83,.97,.91),
    ]
    clothes=['navy suit','dark suit and tie','grey business jacket','navy suit and tie',
             'dark cardigan','charcoal suit','beige jacket','dark suit and tie','brown cardigan','worn dark suit']
    lights=['fluorescent light','direct flash','office light','booth flash','fluorescent light',
            'direct flash','booth light','compact camera flash','old booth light','fluorescent light']
    for i,(spec,trait,values) in enumerate(zip(config['portrait_specs'],traits,finishes)):
        hair,eyes,skin=trait
        effective,quality,softness,grain,chroma,tint,saturation,brightness,contrast=values
        spec.update({'capture_style':'worn-v2','appearance':hair,'eyes':eyes,'skin':skin,
                     'clothes':clothes[i],'lighting':lights[i]})
        spec.pop('guidance_scale',None)
        spec.pop('view_emphasis',None)
        spec['finish'].update({'effective_size':effective,'camera_jpeg_quality':quality,
                              'delivery_jpeg_quality':quality+6,'softness':softness,'grain':grain,
                              'chroma_noise':chroma,'color_shift':tint,'saturation':saturation,
                              'brightness':brightness,'contrast':contrast,'black_lift':2.0,
                              'vignette':.045})
    target=ROOT/'configs/realvis10_worn.json'
    if target.exists() and read_json(target)!=config:
        raise ValueError('Existing experiment differs; use another config name')
    write_json(target,config)
    _,path,saved=state(target)
    if saved.get('source_profiles_batch'):
        print('Experiment already initialized:',saved['batch_id'])
        return
    source=read_json(ROOT/'work/realvis10/state.json')
    for previous,current in zip(source['people'],saved['people']):
        current['profile']=copy.deepcopy(previous['profile'])
        current['profile_result']={'seconds':0,'engine':'reused source profile','source_person_id':previous['person_id']}
        current['birth_date']=previous['birth_date']
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine'].update({'generation_seconds':0,'count_this_run':0,
                                   'names':'all personal data reused for image comparison'})
    saved['source_profiles_batch']=source['batch_id']
    saved['comparison_previous_batch']=read_json(ROOT/'work/realvis10_livedin/state.json')['batch_id']
    write_json(path,saved)
    print('Stronger realism experiment initialized:',saved['batch_id'])

if __name__=='__main__':
    main()

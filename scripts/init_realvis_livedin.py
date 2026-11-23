"""Create a new ten-person capture-variation experiment from the clean baseline."""
import copy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json
from generator.pipeline import state

def main():
    config=read_json(ROOT/'configs/realvis10.json')
    config.update({'output_size':384,'output_format':'jpg','photo_finish':True,'capture_comparison':True})
    config['diffusion']['guidance_scale']=4.0
    # Variations are deliberate camera/capture conditions, not a blanket filter.
    settings=[
        ('head turned slightly left, eyes near camera','a navy suit jacket and white shirt','mild acne marks, uneven skin','fluorescent booth light',1,320,78,0.12,1.4,[1,0,-1],0.96,1.00,-0.4),
        ('head turned ten degrees right','a dark suit, white shirt and striped tie','slight acne scars, oily forehead','compact camera flash',4,256,64,0.20,2.1,[3,1,-3],0.90,0.98,0.7),
        ('three-quarter view, face angled left, eyes near camera','a grey business jacket and blouse','dry skin, small blemishes','uneven office light',2,384,82,0.18,1.2,[0,1,1],0.94,0.97,0.0),
        ('head turned slightly left','a navy suit, white shirt and plain tie','uneven skin, faint shaving shadow','old photo booth flash',6,280,66,0.28,2.4,[4,2,-4],0.85,1.01,-0.6),
        ('almost frontal, slightly off center','a plain dark cardigan','visible pores, mild redness','flat office fluorescent light',0,360,80,0.12,1.6,[-1,1,2],0.98,1.02,0.0),
        ('three-quarter view, face angled right, gaze slightly aside','a charcoal suit and white shirt','rough skin, pitted acne scars','direct camera flash',5,240,60,0.30,2.6,[2,0,-3],0.88,0.96,0.5),
        ('slight head tilt to the left','a simple beige jacket and blouse','mild sun spots, uneven skin tone','uneven photo booth light',7,300,68,0.22,2.0,[4,2,-3],0.83,0.99,-0.8),
        ('head turned slightly right','a dark business suit and tie','coarse pores, wrinkles','small compact camera flash',3,320,74,0.20,1.8,[1,0,-2],0.93,1.00,0.3),
        ('three-quarter view, head tilted left, eyes near camera','a plain brown cardigan','age spots, dry skin, wrinkles','old photo booth lighting',8,256,62,0.32,2.5,[5,2,-5],0.82,1.02,-0.5),
        ('head turned slightly left','a worn dark suit and white shirt','age spots, coarse skin, wrinkles','uneven fluorescent lighting',5,300,72,0.22,2.1,[1,1,-1],0.89,0.97,0.6)
    ]
    for spec,values in zip(config['portrait_specs'],settings):
        pose,clothes,skin,lighting,years,effective,quality,softness,grain,tint,saturation,brightness,angle=values
        spec.update({'capture_style':'lived-in-v1','pose':pose,'clothes':clothes,'skin':skin,'lighting':lighting,
                     'photo_age':spec['age']-years,'years_before_reference':years,
                     'finish':{'effective_size':effective,'camera_jpeg_quality':quality,'delivery_jpeg_quality':quality+4,
                               'softness':softness,'grain':grain,'chroma_noise':0.35,'color_shift':tint,
                               'saturation':saturation,'brightness':brightness,'contrast':0.96,
                               'black_lift':1.2 if years>=4 else 0,'vignette':0.025,'scan_angle':angle}})
        if 'three-quarter' in pose:
            spec.update({'view_emphasis':'off-angle','guidance_scale':6.0})
    target=ROOT/'configs/realvis10_livedin.json'
    if target.exists() and read_json(target)!=config:
        raise ValueError('Existing experiment config differs')
    write_json(target,config)
    _,path,saved=state(target)
    if saved.get('source_profiles_batch'):
        print('Experiment already initialized')
        return
    source=read_json(ROOT/'work/realvis10/state.json')
    for previous,current in zip(source['people'],saved['people']):
        current['profile']=copy.deepcopy(previous['profile'])
        current['profile_result']={'seconds':0,'engine':'reused completed source profile','source_person_id':previous['person_id']}
        current['birth_date']=previous['birth_date']
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine']['generation_seconds']=0
    saved['profile_engine']['count_this_run']=0
    saved['profile_engine']['names']='all personal data reused from source batch for image comparison'
    saved['source_profiles_batch']=source['batch_id']
    write_json(path,saved)
    print('Capture-variation experiment initialized:',saved['batch_id'])

if __name__=='__main__':
    main()

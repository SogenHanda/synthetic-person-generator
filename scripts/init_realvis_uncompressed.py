"""Keep the existing faces and grain, remove simulated JPEG and low resolution."""
import copy
import argparse
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.pipeline import state
from generator.photo_finish import parameters

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--jpeg-quality',type=int,help='Add only final JPEG compression to the completed PNG version')
    parser.add_argument('--size',type=int,default=1024,help='Delivery size; finishing stays at 1024px before final resize')
    parser.add_argument('--varied',action='store_true',help='Per-photo delivery sizes 240..480px and JPEG qualities 27..52')
    parser.add_argument('--framing',action='store_true',help='Reuse the varied batch and add per-photo crop/position/tilt')
    args=parser.parse_args()
    if args.framing:
        args.varied=True
    if args.jpeg_quality is not None and not 1<=args.jpeg_quality<=95:
        parser.error('JPEG quality must be between 1 and 95')
    if not 128<=args.size<=1024 or (args.size!=1024 and args.jpeg_quality is None):
        parser.error('Delivery size must be 128..1024; reduced size requires --jpeg-quality')
    if args.varied and (args.jpeg_quality is not None or args.size!=1024):
        parser.error('--varied supplies its own sizes and qualities')
    jpeg=args.jpeg_quality is not None or args.varied
    source_name='realvis10_uncompressed' if jpeg else 'realvis10_softgrain'
    target_name='realvis10_jpegonly' if jpeg else 'realvis10_uncompressed'
    if args.size!=1024:
        target_name=f'realvis10_jpeg{args.size}_q{args.jpeg_quality}'
    if args.varied:
        target_name='realvis10_varied'
    if args.framing:
        source_name='realvis10_varied'
        target_name='realvis10_framing'
    source_config=read_json(ROOT/f'configs/{source_name}.json')
    config=copy.deepcopy(source_config)
    config.update({'output_size':args.size,'output_format':'jpg' if jpeg else 'png'})
    variation=[(384,44),(256,30),(480,52),(320,36),(416,46),(240,27),(288,33),(448,49),(272,31),(352,40)]
    framing=[(.01,.005,.94,-1.8),(.085,.01,.90,2.0),(.005,.015,.97,-.6),
             (.005,.08,.91,1.4),(.045,.005,.95,-.9),(.01,.035,.88,1.8),
             (.075,.015,.92,-1.5),(.008,.003,.98,.5),(.015,.08,.90,1.1),(.055,.01,.94,-1.7)]
    if args.varied:
        config['output_size']=480
    for i,spec in enumerate(config['portrait_specs']):
        spec['finish']['effective_size']=1024
        spec['finish']['camera_jpeg_enabled']=False
        spec['finish'].pop('camera_jpeg_quality',None)
        spec['finish'].pop('delivery_jpeg_quality',None)
        if jpeg:
            spec['finish']['delivery_jpeg_quality']=args.jpeg_quality
        if args.varied:
            spec['finish'].update({'delivery_size':variation[i][0],'delivery_jpeg_quality':variation[i][1]})
        if args.framing:
            left,top,width,angle=framing[i]
            spec['finish'].update({'frame_crop':[left,top,round(left+width,6),round(top+width,6)],'scan_angle':angle})
    target=ROOT/f'configs/{target_name}.json'
    if target.exists() and read_json(target)!=config:
        raise ValueError('Existing experiment differs; use a new config name')
    write_json(target,config)
    _,path,saved=state(target)
    if saved.get('source_batch'):
        print('Experiment already initialized:',saved['batch_id'])
        return
    source_path=ROOT/f'work/{source_name}/state.json'
    source=read_json(source_path)
    for previous,current in zip(source['people'],saved['people']):
        original=source_path.parent/'originals'/(previous['person_id']+'.png')
        if not previous['face_result'] or sha256(original)!=previous['face_result']['sha256']:
            raise ValueError('Source portrait incomplete or changed')
        destination=path.parent/'originals'/(current['person_id']+'.png')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,destination)
        current['face_result']=copy.deepcopy(previous['face_result'])
        current['face_result'].update({'seconds':0,'source_person_id':previous['person_id'],
                                      'reused_from_batch':source['batch_id']})
        current['profile']=copy.deepcopy(previous['profile'])
        current['profile_result']={'seconds':0,'engine':'reused source profile','source_person_id':previous['person_id']}
        current['birth_date']=previous['birth_date']
        current['photo_finish_seed']=str(parameters(source_config,previous)[1])
    saved['face_model']=copy.deepcopy(source['face_model'])
    saved['profile_engine']=copy.deepcopy(source['profile_engine'])
    saved['profile_engine'].update({'generation_seconds':0,'count_this_run':0})
    saved['source_profiles_batch']=source['batch_id']
    saved['source_batch']=source['batch_id']
    write_json(path,saved)
    print('Photo finishing experiment initialized:',saved['batch_id'])

if __name__=='__main__':
    main()

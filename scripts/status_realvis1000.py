"""Print durable batch progress; optionally watch without loading a model."""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,now

def progress(config_name='realvis1000_diverse'):
    saved=read_json(ROOT/f'work/{config_name}/state.json')
    worker=read_json(ROOT/f'work/{config_name}/worker_status.json')
    faces=[p['face_result'] for p in saved['people'] if p['face_result']]
    actual=[sum(a['seconds'] for a in p['face_attempts']) if p.get('face_attempts') else p['face_result']['seconds'] for p in saved['people'] if p['face_result'] and p['face_result']['seconds']>0]
    target=saved['config']['count']
    remaining=target-len(faces)
    eta=round(sum(actual)/len(actual)*remaining/60) if actual else None
    return {'time':now(),'status':worker['status'],'faces_completed':len(faces),'target':target,
            'profiles_completed':sum(bool(p['profile']) for p in saved['people']),
            'rejected_candidates':sum(not a['accepted'] for p in saved['people'] for a in p.get('face_attempts',[])),
            'estimated_minutes_remaining':eta,'batch_id':saved['batch_id']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--config',default='configs/realvis500_checkpoint.json')
    args=parser.parse_args()
    while True:
        result=progress(Path(args.config).stem)
        print(json.dumps(result),flush=True)
        if not args.watch or result['status'] in ('complete','failed','paused'): break
        time.sleep(50)

if __name__=='__main__': main()

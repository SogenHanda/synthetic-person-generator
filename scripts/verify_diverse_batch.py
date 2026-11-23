"""Audit accepted synthetic faces and planned ages using saved originals."""
import argparse
import sys
from datetime import date
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.face_similarity import FaceDiversity

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/realvis500_checkpoint.json')
    args=parser.parse_args()
    config=read_json(ROOT/args.config)
    work=ROOT/'work'/Path(args.config).stem
    state=read_json(work/'state.json')
    people=state['people']
    count=config['count']
    assert len(people)==count and all(p['face_result'] for p in people)
    gate=FaceDiversity(config['face_diversity']['threshold'])
    vectors=[];hashes=[]
    for p in people:
        path=work/'originals'/(p['person_id']+'.png')
        digest=sha256(path)
        assert digest==p['face_result']['sha256']
        hashes.append(digest)
        vector=gate.feature(path)
        assert vector is not None
        vectors.append(vector)
    assert len(set(hashes))==count
    matrix=np.asarray(vectors)@np.asarray(vectors).T
    np.fill_diagonal(matrix,-1)
    maximum=float(matrix.max())
    assert maximum<gate.threshold+1e-6,maximum
    reference=date.fromisoformat(config['as_of'])
    for p in people:
        birth=date.fromisoformat(p['birth_date'])
        age=reference.year-birth.year-((reference.month,reference.day)<(birth.month,birth.day))
        assert age==p['age']==p['portrait_spec']['age']
    cohorts=[]
    for group in config['age_distribution']['groups']:
        actual=sum(group['min']<=p['age']<=group['max'] for p in people)
        assert actual==group['count']
        cohorts.append({**group,'actual':actual})
    assert sum(p['portrait_spec']['photo_age']<=15 for p in people)==sum(g['count'] for g in config['age_distribution']['groups'] if g['max']<=15)
    assert sum(p['portrait_spec']['photo_age']>=80 for p in people)==sum(g['count'] for g in config['age_distribution']['groups'] if g['min']>=80)
    result={'people':count,'all_single_faces':True,'unique_original_hashes':True,
            'maximum_pair_cosine':maximum,'screen_threshold':gate.threshold,
            'scope':'Synthetic faces only; not proof of separate real identities.',
            'age_cohorts':cohorts,'birth_dates_match_age_specs':True,
            'rejected_candidates':sum(not a['accepted'] for p in people for a in p.get('face_attempts',[]))}
    write_json(ROOT/f'reports/{Path(args.config).stem}_diversity_final.json',result)
    print(result)

if __name__=='__main__': main()

"""Benchmark profile synthesis alone, excluding images/packaging/LLM setup."""
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.local_profiles import generate,mynumber_valid,luhn_valid
from generator.common import write_json

def main():
    results=[]
    for count in (100,10000):
        used={key:set() for key in ('personal_number','payment_number','bank_account_number')}
        start=time.perf_counter()
        profiles=[generate({'person_id':f'benchmark_{i:06d}','age':20+i%60},20261124,used) for i in range(count)]
        seconds=time.perf_counter()-start
        assert all(not mynumber_valid(p['personal_number']) and not luhn_valid(p['payment_number']) for p in profiles)
        assert all(len(values)==count for values in used.values())
        results.append({'count':count,'generation_seconds':round(seconds,6),'profiles_per_second':round(count/seconds,1),
                        'unique_numbers':True,'mynumber_and_card_checksums':'all intentionally invalid',
                        'scope':'dictionary-based profiles only; no images, export, disk persistence, or LLM calls'})
    write_json(ROOT/'reports/profile_benchmark.json',{'engine':'local structured generator v1','results':results})
    print(json.dumps(results,indent=2))

if __name__=='__main__':
    main()

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['schema_version','person_id','batch_id','face_path','name','birth_date','address','personal_number','payment_number','generated_at','synthetic']
PUBLIC_KEYS=['name','name_kana','birth_date','address','email','phone','employer','workplace_address','workplace_phone','occupation','personal_number','payment_number','bank_name','bank_branch','bank_account_type','bank_account_number','account_holder_kana','face_path']

def photo_delivery_size(config,person):
    size=person.get('portrait_spec',{}).get('finish',{}).get('delivery_size',config['output_size'])
    if type(size) is not int or not 1<=size<=4096:
        raise ValueError('Photo delivery size must be an integer between 1 and 4096')
    return size

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Windows readers/AV may briefly deny replacing an otherwise valid JSON file.
    # Keep the previous snapshot intact and retry the atomic commit, not the write.
    for attempt in range(50):
        try:
            temp.replace(path)
            break
        except PermissionError:
            if attempt==49:
                raise
            time.sleep(min(.05*(attempt+1),.5))

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def config_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def safe_csv(value):
    if isinstance(value,bool):
        return str(value).lower()
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')):
        return "'"+value
    return value

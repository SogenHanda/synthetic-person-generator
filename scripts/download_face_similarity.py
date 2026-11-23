"""Pin official OpenCV Zoo YuNet/SFace assets and verify their Git LFS hashes."""
import hashlib
import json
import sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import write_json,sha256

def main():
    repo='opencv/opencv_zoo'
    revision='48b10fa505aeb51fbd127fc60a5c660040e823b7'
    paths=['models/face_detection_yunet/face_detection_yunet_2023mar.onnx',
           'models/face_recognition_sface/face_recognition_sface_2021dec.onnx']
    assets=[]
    for path in paths:
        pointer=requests.get(f'https://raw.githubusercontent.com/{repo}/{revision}/{path}',timeout=60)
        pointer.raise_for_status()
        lines=pointer.text.splitlines()
        expected=next(s.split('sha256:')[1] for s in lines if s.startswith('oid sha256:'))
        size=int(next(s.split()[1] for s in lines if s.startswith('size ')))
        dest=ROOT/'models/face_similarity'/Path(path).name
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or sha256(dest)!=expected:
            response=requests.get(f'https://media.githubusercontent.com/media/{repo}/{revision}/{path}',timeout=180)
            response.raise_for_status()
            assert len(response.content)==size and hashlib.sha256(response.content).hexdigest()==expected
            dest.write_bytes(response.content)
        assets.append({'path':dest.relative_to(ROOT).as_posix(),'sha256':expected,'size_bytes':size})
        license_path=path.rsplit('/',1)[0]+'/LICENSE'
        license=requests.get(f'https://raw.githubusercontent.com/{repo}/{revision}/{license_path}',timeout=60)
        license.raise_for_status()
        dest.with_suffix('.LICENSE').write_text(license.text,encoding='utf-8')
    write_json(ROOT/'models/face_similarity/assets.json',{'repository':repo,'revision':revision,'assets':assets})
    print(json.dumps({'repository':repo,'revision':revision,'assets':assets}))

if __name__=='__main__': main()

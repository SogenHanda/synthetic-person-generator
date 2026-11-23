"""Pinned official RealVisXL fp16 Diffusers snapshot, verified by HF LFS hashes."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from download_assets import get,download,download_large

REPO='SG161222/RealVisXL_V5.0'
REV='ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc'
DEST='models/realvisxl-v5'

def main():
    files=json.loads(get(f'https://huggingface.co/api/models/{REPO}/tree/{REV}?recursive=true'))
    selected=[]
    for entry in files:
        name=entry['path']
        if entry['type']!='file':
            continue
        if (name in ('model_index.json','README.md','.gitattributes') or
            name.startswith(('scheduler/','tokenizer/','tokenizer_2/')) or
            (name.startswith(('unet/','vae/','text_encoder/','text_encoder_2/')) and (name.endswith('.json') or name.endswith('.fp16.safetensors')))):
            selected.append(entry)
    if len([f for f in selected if f['path'].endswith('.safetensors')])!=4:
        raise ValueError('Unexpected model file inventory')
    records=[]
    # Small configs first, then largest models. Each weight is independently resumable.
    selected.sort(key=lambda f:(f['size']>10000000,-f['size'] if f['size']>10000000 else 0))
    for entry in selected:
        url=f'https://huggingface.co/{REPO}/resolve/{REV}/{entry["path"]}'
        target=f'{DEST}/{entry["path"]}'
        expected=entry.get('lfs',{}).get('oid')
        if entry['size']>100*1024*1024:
            if not expected:
                raise ValueError('No SHA-256 for large weight')
            chunk_size=512*1024*1024 if entry['path'].startswith('unet/') else 64*1024*1024
            record=download_large(url,target,expected,entry['size'],chunk_size=chunk_size)
        else:
            record=download(url,target,expected)
        records.append(record)
    (ROOT/'models/realvisxl-assets.json').write_text(json.dumps({'repository':REPO,'revision':REV,'assets':records},indent=2)+'\n',encoding='utf-8')
    print('RealVisXL snapshot verified and ready.',flush=True)

if __name__=='__main__':
    main()

"""Build/restore the stopped 500-person checkpoint without duplicating PNGs in transit."""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256,config_digest

def relative(name):
    p=PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or p.as_posix()!=name:
        raise ValueError('Unsafe archive path: '+name)
    return p

def build(root=ROOT):
    checkpoint=read_json(root/'work/realvis500_checkpoint/state.json')
    source=read_json(root/'work/realvis1000_diverse/state.json')
    assert len(checkpoint['people'])==500 and all(p['face_result'] for p in checkpoint['people'])
    assert sum(bool(p['face_result']) for p in source['people'])==500
    assert read_json(root/'work/realvis1000_diverse/worker_status.json')['status']=='paused'
    assert read_json(root/'work/realvis500_checkpoint/worker_status.json')['status']=='complete'
    for stem,state in [('realvis500_checkpoint',checkpoint),('realvis1000_diverse',source)]:
        assert config_digest(read_json(root/f'configs/{stem}.json'))==state['config_sha256']
    files=[]
    for stem in ('realvis500_checkpoint','realvis1000_diverse'):
        files.extend([f'work/{stem}/state.json',f'work/{stem}/worker_status.json'])
    derived={}
    for p in checkpoint['people']:
        src=f'work/realvis1000_diverse/originals/{p["source_person_id"]}.png'
        dst=f'work/realvis500_checkpoint/originals/{p["person_id"]}.png'
        assert sha256(root/src)==p['face_result']['sha256']==sha256(root/dst)
        files.append(src)
        derived[dst]=src
    files.extend(p.relative_to(root).as_posix() for p in (root/'deliverables/people_500').rglob('*') if p.is_file())
    files.append('deliverables/people_500.zip')
    for path in ('models/realvisxl-assets.json','models/face_similarity/assets.json',
                 'models/face_similarity/face_detection_yunet_2023mar.LICENSE',
                 'models/face_similarity/face_recognition_sface_2021dec.LICENSE',
                 'models/realvisxl-v5/README.md'):
        files.append(path)
    inventory={name:{'sha256':sha256(root/name),'bytes':(root/name).stat().st_size} for name in sorted(set(files))}
    meta={'format':1,'people':500,'resume_target':1000,'files':inventory,'derived_originals':derived,
          'description':'Accepted synthetic originals, complete 500-person export, both saved states. Model weights are downloaded separately.'}
    out=root/'transfer/checkpoint500'
    out.mkdir(parents=True,exist_ok=True)
    archive=out/'checkpoint500.zip'
    temp=archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
        z.writestr('migration_manifest.json',json.dumps(meta,ensure_ascii=False,indent=2))
        for name in inventory:z.write(root/name,name)
    temp.replace(archive)
    parts=[]
    with archive.open('rb') as source_file:
        index=1
        while data:=source_file.read(512*1024*1024):
            part=out/f'checkpoint500.zip.part{index:03d}'
            part.write_bytes(data)
            parts.append({'name':part.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            index+=1
    write_json(out/'checkpoint500.parts.json',{'format':1,'archive_sha256':sha256(archive),
               'archive_bytes':archive.stat().st_size,'parts':parts})
    print(json.dumps({'directory':str(out),'bytes':archive.stat().st_size,'parts':len(parts)}),flush=True)
    return out/'checkpoint500.parts.json'

def restore(manifest,root=ROOT,verify_only=False):
    manifest=Path(manifest).resolve()
    parts=read_json(manifest)
    if parts.get('format')!=1 or not parts.get('parts'):raise ValueError('Unknown bundle format')
    with tempfile.TemporaryDirectory(prefix='synthetic-checkpoint-') as tempdir:
        assembled=Path(tempdir)/'checkpoint.zip'
        with assembled.open('wb') as target:
            for part in parts['parts']:
                if relative(part['name']).name!=part['name']:raise ValueError('Part must be a basename')
                path=manifest.parent/part['name']
                if path.stat().st_size!=part['bytes'] or sha256(path)!=part['sha256']:raise ValueError('Part checksum failed: '+part['name'])
                with path.open('rb') as src:shutil.copyfileobj(src,target)
        if assembled.stat().st_size!=parts['archive_bytes'] or sha256(assembled)!=parts['archive_sha256']:
            raise ValueError('Archive checksum failed')
        with zipfile.ZipFile(assembled) as z:
            names=z.namelist()
            if len(names)!=len(set(names)):raise ValueError('Duplicate archive members')
            meta=json.loads(z.read('migration_manifest.json'))
            if meta.get('format')!=1:raise ValueError('Unknown archive format')
            files=meta['files']
            if set(names)!=set(files)|{'migration_manifest.json'}:raise ValueError('Unexpected archive member')
            expected=dict(files)
            for dest,src in meta['derived_originals'].items():
                if dest in expected:raise ValueError('Duplicate derived original')
                expected[dest]=files[src]
            # Verify every byte and every pre-existing destination before writing anything.
            for name,entry in files.items():
                relative(name)
                h=hashlib.sha256()
                size=0
                with z.open(name) as src:
                    while chunk:=src.read(8*1024*1024):h.update(chunk);size+=len(chunk)
                if size!=entry['bytes'] or h.hexdigest()!=entry['sha256']:raise ValueError('File checksum failed: '+name)
            for name,entry in expected.items():
                relative(name)
                dest=root/name
                if not dest.resolve().is_relative_to(root.resolve()):raise ValueError('Destination escapes project')
                if dest.exists() and (not dest.is_file() or sha256(dest)!=entry['sha256']):
                    raise ValueError('Refusing to overwrite different existing file: '+name)
            if not verify_only:
                for name in files:
                    dest=root/name
                    if dest.exists():continue
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    partial=dest.with_suffix(dest.suffix+'.restore.tmp')
                    with z.open(name) as src,partial.open('wb') as target:shutil.copyfileobj(src,target)
                    partial.replace(dest)
                for dest,src in meta['derived_originals'].items():
                    target=root/dest
                    if not target.exists():
                        target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(root/src,target)
                for name,entry in expected.items():
                    if sha256(root/name)!=entry['sha256']:raise ValueError('Restored file changed: '+name)
    print('Bundle verified.' if verify_only else 'Restored 500-person checkpoint. Generation remains stopped.',flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('build')
    p=sub.add_parser('restore');p.add_argument('manifest');p.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if args.command=='build':build()
    else:restore(args.manifest,verify_only=args.verify_only)

if __name__=='__main__':main()

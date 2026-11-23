"""Copy a verified checkpoint into a plainly named, portable delivery folder."""
import shutil
import sys
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,sha256
from generator.validation import validate_directory
from scripts.verify_portable import verify

def main():
    state=read_json(ROOT/'work/realvis500_checkpoint/state.json')
    assert len(state['people'])==500 and all(p['face_result'] for p in state['people'])
    source=ROOT/'outputs'/state['batch_id']
    verify(source,500)
    parent=ROOT/'deliverables'
    parent.mkdir(exist_ok=True)
    dest=parent/'people_500'
    if dest.exists():
        validate_directory(dest)
        if sha256(dest/'manifest.json')!=sha256(source/'manifest.json'):
            raise ValueError('An unrelated delivery already exists; do not overwrite')
    else:
        staging=parent/('.people_500_'+uuid.uuid4().hex)
        assert staging.resolve().is_relative_to(ROOT.resolve()) and dest.resolve().is_relative_to(ROOT.resolve())
        shutil.copytree(source,staging)
        verify(staging,500)
        staging.rename(dest)
    archive=parent/'people_500.zip'
    if archive.exists() and sha256(archive)!=sha256(source.with_suffix('.zip')):
        raise ValueError('An unrelated ZIP already exists; do not overwrite')
    if not archive.exists():
        temp=archive.with_suffix('.zip.tmp')
        shutil.copyfile(source.with_suffix('.zip'),temp)
        temp.replace(archive)
    assert sha256(archive)==sha256(source.with_suffix('.zip'))
    write_json(ROOT/'reports/people_500_delivery.json',{'people':500,'batch_id':state['batch_id'],
               'directory':dest.relative_to(ROOT).as_posix(),'archive':archive.relative_to(ROOT).as_posix(),
               'zip_sha256':sha256(archive),'all_paths_relative':True})
    print('Delivery ready:',dest,'ZIP:',archive)

if __name__=='__main__':main()

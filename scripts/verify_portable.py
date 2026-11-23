"""Validate CSV/image/HTML links after moving a complete batch to a new directory."""
import argparse
import csv
import json
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse,unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.validation import validate_directory,safe_extract,relative_path
from generator.common import sha256,write_json

class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img': self.images.append(a['src'])
        if tag=='a': self.links.append(a['href'])

def verify(dest,count):
    validate_directory(dest)
    rows=list(csv.DictReader((dest/'profiles.csv').open(encoding='utf-8',newline='')))
    assert len(rows)==count and len({r['name'] for r in rows})==count
    for key in ('face_path','personal_number','payment_number','bank_account_number','email','phone'):
        assert len({r[key] for r in rows})==count, 'Duplicate '+key
    refs=References()
    content=(dest/'index.html').read_text(encoding='utf-8')
    refs.feed(content)
    assert len(refs.images)==count and set(refs.images)=={r['face_path'] for r in rows}
    for value in refs.images+refs.links:
        assert not urlparse(value).scheme and not value.startswith(('/','\\'))
        relative_path(unquote(value))
        assert (dest/unquote(value)).is_file(),value
    assert 'file://' not in content and 'C:/' not in content and 'C:\\' not in content
    hashes=[sha256(dest/r['face_path']) for r in rows]
    assert len(set(hashes))==count,'Duplicate delivered images'
    return {'people':count,'images':count,'html_images':len(refs.images),'all_paths_relative':True,
            'unique_names_and_numbers_contacts':True,'unique_image_hashes':True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=verify(args.directory,args.count)
    with tempfile.TemporaryDirectory(prefix='portable_relocation_') as tmp:
        relocated=Path(tmp)/'moved_dataset'
        archive=args.directory.with_suffix('.zip')
        if archive.exists():
            safe_extract(archive,relocated)
        else:
            shutil.copytree(args.directory,relocated)
        verify(relocated,args.count)
    result['relocation_verified']=True
    if args.report: write_json(args.report,result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()

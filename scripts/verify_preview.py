"""Check that a local review HTML references 100 existing previews/originals."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlparse
from urllib.request import url2pathname

class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='img':
            self.images.append(attrs['src'])
        if tag=='a' and urlparse(attrs.get('href','')).path.lower().endswith(('.png','.jpg','.jpeg')):
            self.links.append(attrs['href'])

def main():
    args=argparse.ArgumentParser()
    args.add_argument('html',type=Path)
    args.add_argument('--count',type=int,default=100)
    options=args.parse_args()
    parser=References()
    parser.feed(options.html.read_text(encoding='utf-8'))
    assert len(parser.images)==options.count
    assert len(parser.links)==options.count
    for source in parser.images+parser.links:
        url=urlparse(source)
        if url.scheme=='file':
            path=Path(url2pathname(url.path))
        elif not url.scheme:
            path=options.html.parent/unquote(source)
        else:
            raise ValueError('Unexpected external asset')
        if not path.is_file():
            raise ValueError('Missing preview reference: '+str(path))
    print(f'Preview verified: {len(parser.images)} images and {len(parser.links)} original-image links')

if __name__=='__main__':
    main()

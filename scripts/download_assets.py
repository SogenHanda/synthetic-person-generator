"""Download official, pinned test assets. Run with Python's standard library."""
import hashlib
import json
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = '530227a7d994db8eca5ab5ced2fb692b614357fd'
TAG = 'b12651'

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'synthetic-person-local-test/1'}), timeout=120) as r:
        return r.read()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def download(url, target, expected=None):
    target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not expected or digest(target) == expected):
        print('Already present:', target.name, flush=True)
        return {'url': url, 'path': str(target.relative_to(ROOT)), 'sha256': digest(target), 'size_bytes': target.stat().st_size}
    part = target.with_suffix(target.suffix+'.part')
    for attempt in range(5):
        try:
            request_url = url + ('&' if '?' in url else '?') + 'download=true&cache_bust=' + str(int(time.time()))
            req = urllib.request.Request(request_url, headers={'User-Agent':'synthetic-person-local-test/1'})
            with urllib.request.urlopen(req, timeout=120) as response, part.open('wb') as f:
                total = int(response.headers.get('Content-Length', 0))
                done = last = 0
                while chunk := response.read(8*1024*1024):
                    f.write(chunk)
                    done += len(chunk)
                    if done-last > 256*1024*1024:
                        print(f'{target.name}: {done/1024**3:.2f} / {total/1024**3:.2f} GiB', flush=True)
                        last = done
            actual = digest(part)
            if expected and actual != expected:
                raise ValueError(f'Hash mismatch: {target.name}: {actual}')
            part.replace(target)
            print('Verified:', target.name, actual, flush=True)
            return {'url':url,'path':str(target.relative_to(ROOT)),'sha256':actual,'size_bytes':target.stat().st_size}
        except Exception as e:
            print(f'Download attempt {attempt+1} failed: {type(e).__name__}: {e}', flush=True)
            if attempt == 4:
                raise
            time.sleep(3)

def download_large(url,target,expected,size,chunk_size=512*1024*1024):
    """Bounded ranged downloads; preserve completed ranges across interruptions."""
    target=ROOT/target
    target.parent.mkdir(parents=True,exist_ok=True)
    record={'url':url,'path':str(target.relative_to(ROOT)),'sha256':expected,'size_bytes':size}
    if target.exists() and target.stat().st_size==size and digest(target)==expected:
        return record
    part=target.with_suffix(target.suffix+'.part')
    prefix=target.with_suffix(target.suffix+'.prefix')
    if part.exists() and not prefix.exists():
        part.replace(prefix)
    offset=prefix.stat().st_size if prefix.exists() else 0
    spans=[(i,start,min(start+chunk_size,size)-1) for i,start in enumerate(range(offset,size,chunk_size))]
    def fetch(span):
        index,start,end=span
        file=target.with_suffix(f'.range-{offset}-{index}')
        if file.exists() and file.stat().st_size==end-start+1:
            return index,file
        for attempt in range(5):
            try:
                have=file.stat().st_size if file.exists() else 0
                if have>end-start+1:
                    raise ValueError('Existing partial range is oversized')
                first=start+have
                req=urllib.request.Request(url+'?download=true&range_nonce='+str(time.time()),headers={'Range':f'bytes={first}-{end}'})
                with urllib.request.urlopen(req,timeout=120) as response,file.open('ab') as f:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {first}-{end}/{size}':
                        raise ValueError('Server did not honor requested range')
                    while chunk:=response.read(8*1024*1024):
                        f.write(chunk)
                if file.stat().st_size!=end-start+1:
                    raise ValueError('Truncated range')
                return index,file
            except Exception as error:
                print(f'Range {index} retry {attempt+1}: {type(error).__name__}',flush=True)
                if attempt==4:
                    raise
                time.sleep(2)
    chunks={}
    with ThreadPoolExecutor(max_workers=20) as pool:
        for future in as_completed([pool.submit(fetch,span) for span in spans]):
            index,file=future.result()
            chunks[index]=file
            done=offset+sum(p.stat().st_size for p in chunks.values())
            print(f'{target.name}: {done/1024**3:.2f}/{size/1024**3:.2f} GiB ({len(chunks)}/{len(spans)} ranges)',flush=True)
    with part.open('wb') as out:
        sources=([prefix] if prefix.exists() else [])+[chunks[i] for i in range(len(spans))]
        for source in sources:
            with source.open('rb') as f:
                while chunk:=f.read(8*1024*1024):
                    out.write(chunk)
    if digest(part)!=expected:
        raise ValueError('Combined model SHA-256 mismatch')
    part.replace(target)
    for file in sources:
        file.unlink()
    print('Verified:',target.name,expected,flush=True)
    return record

def main():
    records = []
    records.append(download('https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/ffhq.pkl','models/stylegan2/ffhq.pkl'))
    for name, sha in [
        ('llama-b12651-bin-win-cuda-12.4-x64.zip','1a6c090f76fab41260b5b7597c6fb1add1fad2efaac692ae2673a22366220a29'),
        ('cudart-llama-bin-win-cuda-12.4-x64.zip','8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6')]:
        record = download(f'https://github.com/ggml-org/llama.cpp/releases/download/{TAG}/{name}',f'tools/downloads/{name}',sha)
        records.append(record)
        with zipfile.ZipFile(ROOT/record['path']) as z:
            dest = (ROOT/'tools/llama').resolve()
            for item in z.infolist():
                resolved = (dest/item.filename).resolve()
                if not resolved.is_relative_to(dest):
                    raise ValueError('Unsafe archive path')
            z.extractall(dest)
    listing = json.loads(get(f'https://huggingface.co/api/models/Qwen/Qwen3-14B-GGUF/tree/{REV}'))
    info = next(x for x in listing if x['path']=='Qwen3-14B-Q6_K.gguf')
    records.append(download_large(f'https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/{REV}/Qwen3-14B-Q6_K.gguf', 'models/qwen/Qwen3-14B-Q6_K.gguf',info['lfs']['oid'],info['size']))
    (ROOT/'models/assets.json').write_text(json.dumps({'qwen_revision':REV,'llama_release':TAG,'assets':records},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()

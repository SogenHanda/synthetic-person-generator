"""Single local worker: resumable inference, export, ZIP, and relocation verification."""
import msvcrt
import ctypes
import argparse
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json,write_json,now,sha256

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/realvis500_checkpoint.json')
    args=parser.parse_args()
    config=ROOT/args.config
    target=read_json(config)['count']
    work=ROOT/'work'/config.stem
    work.mkdir(parents=True,exist_ok=True)
    with (work/'worker.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        status={'status':'running','pid':os.getpid(),'started_at':now(),'target':target}
        write_json(work/'worker_status.json',status)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            subprocess.run([sys.executable,'-u','-m','generator','resume','--config',str(config)],cwd=ROOT,check=True)
            saved=read_json(work/'state.json')
            dest=ROOT/'outputs'/saved['batch_id']
            subprocess.run([sys.executable,'-u','scripts/verify_portable.py',str(dest),'--count',str(target),
                            '--report',f'reports/{config.stem}_portability.json'],cwd=ROOT,check=True)
            if config.stem=='realvis500_checkpoint':
                subprocess.run([sys.executable,'-u','scripts/sync_checkpoint500.py'],cwd=ROOT,check=True)
            status.update({'status':'complete','completed_at':now(),'batch_id':saved['batch_id'],
                           'directory':dest.relative_to(ROOT).as_posix(),'zip_sha256':sha256(dest.with_suffix('.zip'))})
        except BaseException as error:
            status.update({'status':'failed','failed_at':now(),'error':str(error)})
            raise
        finally:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            write_json(work/'worker_status.json',status)
            lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__': main()

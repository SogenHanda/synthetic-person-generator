"""Hold system sleep only while the local worker is alive; display may sleep."""
import ctypes
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.common import read_json

def main():
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    status_path=ROOT/'work/realvis1000/worker_status.json'
    status=read_json(status_path)
    handle=kernel.OpenProcess(0x100000,False,status['pid'])
    if not handle: return
    if not kernel.SetThreadExecutionState(0x80000001):
        kernel.CloseHandle(handle)
        raise RuntimeError('Could not hold system sleep')
    try:
        while kernel.WaitForSingleObject(handle,0)==258:
            if read_json(status_path)['status'] in ('complete','failed'): break
            time.sleep(30)
    finally:
        kernel.SetThreadExecutionState(0x80000000)
        kernel.CloseHandle(handle)

if __name__=='__main__': main()

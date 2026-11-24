import argparse
import json
import shutil
import subprocess
import sys

from .common import ROOT,read_json

def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Synthetic Person Generator: local portraits, profiles, and portable datasets')
    parser.add_argument('command',choices=['doctor','faces','profiles','export','validate','package','preview','resume'])
    parser.add_argument('--config',default='configs/example.json')
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    if args.command=='doctor':
        import torch
        config=read_json(ROOT/args.config)
        print(json.dumps({'python':sys.version,'torch':torch.__version__,'cuda_available':torch.cuda.is_available(),
                          'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                          'cuda_runtime':torch.version.cuda,'free_disk_gib':round(shutil.disk_usage(ROOT).free/1024**3,2),
                          'assets_present':{'stylegan':(ROOT/config.get('stylegan',{}).get('weights','__missing__')).is_file(),
                                            'realvisxl_verified_snapshot':(ROOT/'models/realvisxl-assets.json').is_file(),
                                            'qwen':(ROOT/config.get('qwen',{}).get('model_path','__missing__')).is_file(),
                                            'llama_server':(ROOT/'tools/llama/llama-server.exe').is_file()},
                          'config':config},ensure_ascii=False,indent=2))
        subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version','--format=csv'],check=True)
        return
    from . import pipeline
    config=ROOT/args.config
    if args.command in ('faces','profiles'):
        function=pipeline.generate_faces if args.command=='faces' else pipeline.generate_profiles
        function(config,args.limit)
    elif args.command=='export':
        pipeline.export_batch(config)
    elif args.command=='validate':
        from .validation import validate_directory
        _,_,saved=pipeline.state(config)
        validate_directory(pipeline.output_path(saved))
    elif args.command=='package':
        pipeline.package(config)
    elif args.command=='preview':
        pipeline.preview(config)
    elif args.command=='resume':
        # Separate subprocesses release GPU memory before loading Qwen.
        for command in ('faces','profiles','export','validate','package','preview'):
            subprocess.run([sys.executable,'-m','generator',command,'--config',str(config)],check=True,cwd=ROOT)

if __name__=='__main__':
    main()

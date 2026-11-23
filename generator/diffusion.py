"""RealVisXL adapter. Loads only a locally verified fp16 snapshot."""
import time
from pathlib import Path
from .common import ROOT,read_json,sha256

def prompts(spec):
    if spec.get('capture_style')=='diverse-v3':
        subject=spec['presentation']
        if spec['photo_age']<18:
            subject='boy' if subject=='man' else 'girl'
        prompt=(f'{spec["face_structure"]}, {spec["nose"]}, {spec["mouth"]}, {spec["eyes"]}, '
                f'{spec["brows"]}, Japanese {subject}, {spec["photo_age"]} years old, '
                f'{spec["appearance"]}, {spec["accessory"]}, {spec["skin"]}, {spec["clothes"]}, '
                f'ID snapshot, {spec["lighting"]}, {spec["background"]} backdrop, unretouched')
        negative=('glamour, airbrushed, plastic skin, fashion model, CGI, anime, illustration, doll, '
                  'heavy makeup, HDR, watermark, text, extra face, duplicate pupils')
        if spec['accessory']=='no glasses':
            negative+=', glasses'
        return prompt,negative
    if spec.get('capture_style')=='worn-v2':
        prompt=(f'Unretouched ID snapshot, Japanese {spec["presentation"]}, {spec.get("photo_age",spec["age"])} years old, '
                f'{spec["appearance"]}, {spec["eyes"]}, {spec["skin"]}, {spec["clothes"]}, '
                f'{spec["lighting"]}, {spec["background"]} background, head and shoulders')
        negative=('anime, illustration, CGI, doll, beauty filter, airbrushed skin, glamour, fashion model, '
                  'perfect symmetry, large round eyes, heavy makeup, plastic skin, cinematic lighting, '
                  'HDR, extra face, duplicate pupils, watermark, text')
        return prompt,negative
    if spec.get('capture_style'):
        intro=(f'{spec["pose"]}, candid office headshot, shoulders angled sideways, ordinary Japanese {spec["presentation"]}, ' if spec.get('view_emphasis')=='off-angle' else
               f'ID snapshot of an ordinary Japanese {spec["presentation"]}, ')
        pose_clause='' if spec.get('view_emphasis')=='off-angle' else spec['pose']+', '
        prompt=(intro+f'{spec.get("photo_age",spec["age"])} years old, '
                f'{pose_clause}{spec["clothes"]}, {spec["skin"]}, {spec["lighting"]}, '
                f'plain {spec["background"]} backdrop, head and shoulders, closed mouth, unretouched')
        negative=('anime, illustration, CGI, doll, beauty filter, airbrushed skin, glamour, fashion editorial, '
                  'plastic skin, heavy makeup, cinematic lighting, HDR, oversharpened, '
                  'extreme side profile, extra face, malformed eyes, watermark, text')
        return prompt,negative
    age=spec['age']
    prompt=(f'Unretouched ID photograph of an ordinary Japanese {spec["presentation"]}, {age} years old, '
            f'front facing, neutral expression, closed mouth, centered head and shoulders, plain {spec["background"]} background, '
            f'flat frontal light, natural skin texture, {spec["appearance"]}, {spec["clothes"]}')
    negative=('illustration, anime, CGI, doll, plastic skin, airbrushed skin, beauty filter, glamour, fashion model, '
              'heavy makeup, cinematic lighting, harsh shadows, smile, teeth, open mouth, tilted head, '
              'side view, looking away, extra face, deformed eyes, blurry, watermark, text')
    return prompt,negative

class DiffusionAdapter:
    def __init__(self,config):
        import torch
        from diffusers import StableDiffusionXLPipeline,DPMSolverMultistepScheduler
        self.torch,self.config=torch,config
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU is required for the real-image trial')
        inventory=read_json(ROOT/'models/realvisxl-assets.json')
        if inventory['revision']!=config['revision']:
            raise ValueError('Model revision mismatch')
        for entry in inventory['assets']:
            file=ROOT/entry['path']
            if not file.is_file() or file.stat().st_size!=entry['size_bytes'] or sha256(file)!=entry['sha256']:
                raise ValueError('Model asset verification failed: '+entry['path'])
        self.pipe=StableDiffusionXLPipeline.from_pretrained(str(ROOT/config['directory']),torch_dtype=torch.float16,variant='fp16',use_safetensors=True,local_files_only=True)
        self.pipe.to(dtype=torch.float16)
        self.pipe.scheduler=DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config,algorithm_type='sde-dpmsolver++',use_karras_sigmas=True)
        self.pipe.enable_model_cpu_offload()
        self.pipe.enable_vae_tiling()
        self.pipe.set_progress_bar_config(disable=True)
        # CLIP's pooled states can be fp32 under the installed offload hooks.
        # Autocast only text encoding, preserving SDXL's fp32 VAE upcast path.
        original_encode=self.pipe.encode_prompt
        def encode_prompt(*args,**kwargs):
            with torch.autocast('cuda',dtype=torch.float16):
                outputs=original_encode(*args,**kwargs)
            return tuple(x.to(dtype=torch.float16) if isinstance(x,torch.Tensor) else x for x in outputs)
        self.pipe.encode_prompt=encode_prompt
        weights=[entry for entry in inventory['assets'] if entry['path'].endswith('.safetensors')]
        self.metadata={'model_name':config['repository'],'model_revision':config['revision'],
                       'weights_sha256':next(e['sha256'] for e in weights if '/unet/' in e['path'].replace('\\','/')),
                       'all_weights':weights,'native_image_size':config['size'],'gpu':torch.cuda.get_device_name(0),
                       'scheduler':'DPM++ SDE Karras','steps':config['steps'],'guidance_scale':config['guidance_scale'],
                       'dtype':'float16 (VAE automatic float32 upcast where required)','cpu_offload':True,
                       'clip_encoding_autocast':'cuda float16; VAE excluded',
                       'face_restoration':False,'beauty_retouching':False,
                       'limitations':['Japanese nationality is a character-design prompt, not a verified attribute.',
                                      'Appearance and backdrop require visual review. No face-ethnicity classifier is used.']}

    def generate(self,seed,destination,spec):
        torch=self.torch
        prompt,negative=prompts(spec)
        for tokenizer in (self.pipe.tokenizer,self.pipe.tokenizer_2):
            if len(tokenizer(prompt).input_ids)>tokenizer.model_max_length or len(tokenizer(negative).input_ids)>tokenizer.model_max_length:
                raise ValueError('Portrait prompt exceeds CLIP token limit; shorten before generation')
        start=time.perf_counter()
        torch.cuda.reset_peak_memory_stats()
        generator=torch.Generator(device='cpu').manual_seed(seed)
        with torch.inference_mode():
            result=self.pipe(prompt=prompt,negative_prompt=negative,height=self.config['size'],width=self.config['size'],
                             num_inference_steps=self.config['steps'],guidance_scale=spec.get('guidance_scale',self.config['guidance_scale']),generator=generator)
        image=result.images[0].convert('RGB')
        path=Path(destination)
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp')
        image.save(temp,format='PNG')
        temp.replace(path)
        torch.cuda.synchronize()
        return {'seconds':round(time.perf_counter()-start,4),'seed':seed,'sha256':sha256(path),
                'native_size':list(image.size),'prompt':prompt,'negative_prompt':negative,'character_spec':spec,
                'guidance_scale':spec.get('guidance_scale',self.config['guidance_scale']),
                'peak_torch_vram_mib':round(torch.cuda.max_memory_allocated()/1024**2,1)}

import functools
import sys
import time
from pathlib import Path

from .common import ROOT, sha256

class StyleGANAdapter:
    def __init__(self, config):
        import numpy as np
        import torch
        sys.path.insert(0,str(ROOT/config['repository']))
        import legacy
        from torch_utils.ops import bias_act, upfirdn2d, conv2d_gradfix
        # Official reference ops run on CUDA tensors; no NVCC/Visual Studio build.
        # Preserve vendor sources and record this backend in generation.json.
        if config.get('ops','reference') == 'reference':
            bias_act.bias_act = functools.partial(bias_act.bias_act,impl='ref')
            upfirdn2d.upfirdn2d = functools.partial(upfirdn2d.upfirdn2d,impl='ref')
            # Convenience functions can pass impl='cuda' explicitly. Mark the
            # optional plugin unavailable so those paths also use official ref ops.
            for module in (bias_act,upfirdn2d):
                module._inited = True
                module._plugin = None
        conv2d_gradfix.enabled = False
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU unavailable; CPU/mock generation is not substituted.')
        torch.backends.cudnn.benchmark = False
        self.torch, self.np, self.config = torch,np,config
        path = ROOT/config['weights']
        # Only load trusted official NVIDIA pickle weights recorded in assets.json.
        with path.open('rb') as f:
            self.model = legacy.load_network_pkl(f)['G_ema'].eval().requires_grad_(False).to('cuda')
        default_name='StyleGAN2 / FFHQ (official NVIDIA)' if config['weights']=='models/stylegan2/ffhq.pkl' else path.stem
        self.metadata = {'model_name':config.get('model_name',default_name),
                         'weights_sha256':sha256(path),'native_image_size':self.model.img_resolution,
                         'gpu':torch.cuda.get_device_name(0),'ops_backend':config.get('ops','reference'),
                         'force_fp32':True,'noise_mode':'const','truncation_psi':config['truncation_psi']}

    def generate(self, seed, destination, size):
        from PIL import Image
        torch,np = self.torch,self.np
        start = time.perf_counter()
        z = torch.from_numpy(np.random.RandomState(seed).randn(1,self.model.z_dim)).to('cuda')
        label = torch.zeros([1,self.model.c_dim],device='cuda')
        with torch.inference_mode():
            image = self.model(z,label,truncation_psi=self.config['truncation_psi'],noise_mode='const',force_fp32=True)
            pixels = (image.permute(0,2,3,1)*127.5+128).clamp(0,255).to(torch.uint8)[0].cpu().numpy()
        original = Image.fromarray(pixels,'RGB')
        destination = Path(destination)
        destination.parent.mkdir(parents=True,exist_ok=True)
        temp = destination.with_suffix('.tmp')
        original.save(temp,format='PNG')
        temp.replace(destination)
        torch.cuda.synchronize()
        return {'seconds':round(time.perf_counter()-start,4),'seed':seed,
                'sha256':sha256(destination),'native_size':list(original.size)}

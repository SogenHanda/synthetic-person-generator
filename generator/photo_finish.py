"""Deterministic camera/scan finishing for locally generated fictional portraits."""
from io import BytesIO
import numpy as np
from PIL import Image,ImageEnhance,ImageFilter
import hashlib

def parameters(config,person):
    settings=person.get('portrait_spec',{}).get('finish',{})
    token=f'{config["seed"]}:{person["person_id"]}:camera-finish-v1'
    seed=int(person['photo_finish_seed']) if 'photo_finish_seed' in person else int(hashlib.sha256(token.encode()).hexdigest()[:16],16)
    return settings,seed

def finish(image,settings,size,seed):
    """Return an RGB photo; source pixels are never modified in place."""
    rng=np.random.default_rng(seed)
    image=image.convert('RGB')
    angle=float(settings.get('scan_angle',0))
    if angle:
        pixels=np.asarray(image)
        color=tuple(int(v) for v in np.median(np.concatenate([pixels[:8].reshape(-1,3),pixels[-8:].reshape(-1,3)]),axis=0))
        image=image.rotate(angle,resample=Image.Resampling.BICUBIC,expand=False,fillcolor=color)
        inset=int(image.width*0.025)
        image=image.crop((inset,inset,image.width-inset,image.height-inset))
    crop=settings.get('frame_crop')
    if crop is not None:
        if not isinstance(crop,(list,tuple)) or len(crop)!=4:
            raise ValueError('frame_crop must contain left, top, right, bottom fractions')
        left,top,right,bottom=crop
        if not (0<=left<right<=1 and 0<=top<bottom<=1):
            raise ValueError('frame_crop must stay inside the source image')
        # Crop existing pixels only; never fill a shifted edge or warp the face.
        image=image.crop((round(left*image.width),round(top*image.height),
                          round(right*image.width),round(bottom*image.height)))
    effective=int(settings.get('effective_size',size))
    image=image.resize((effective,effective),Image.Resampling.LANCZOS)
    image=image.filter(ImageFilter.GaussianBlur(float(settings.get('softness',0.15))))
    image=ImageEnhance.Color(image).enhance(float(settings.get('saturation',0.95)))
    image=ImageEnhance.Contrast(image).enhance(float(settings.get('contrast',0.98)))
    image=ImageEnhance.Brightness(image).enhance(float(settings.get('brightness',1)))
    pixels=np.asarray(image,dtype=np.float32)
    pixels+=np.asarray(settings.get('color_shift',[0,0,0]),dtype=np.float32)
    pixels+=float(settings.get('black_lift',0))
    luma=rng.normal(0,float(settings.get('grain',1.4)),(effective,effective,1))
    chroma=rng.normal(0,float(settings.get('chroma_noise',0.3)),pixels.shape)
    pixels+=luma+chroma
    vignette=float(settings.get('vignette',0))
    if vignette:
        yy,xx=np.mgrid[-1:1:complex(0,effective),-1:1:complex(0,effective)]
        pixels*=1-vignette*((xx*xx+yy*yy)/2)[...,None]
    image=Image.fromarray(np.uint8(np.clip(pixels,0,255)))
    # The intermediate JPEG represents an older camera/export before ingestion.
    if settings.get('camera_jpeg_enabled',True):
        stream=BytesIO()
        image.save(stream,format='JPEG',quality=int(settings.get('camera_jpeg_quality',80)),subsampling=2)
        stream.seek(0)
        with Image.open(stream) as compressed:
            image=compressed.convert('RGB').copy()
    if image.size!=(size,size):
        image=image.resize((size,size),Image.Resampling.BICUBIC)
    return image

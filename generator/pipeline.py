import csv
import html
import importlib.metadata
import json
import platform
import random
import subprocess
import time
import uuid
import zipfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from .common import ROOT, KEYS, PUBLIC_KEYS, config_digest, now, read_json, safe_csv, sha256, write_json, photo_delivery_size

def state(config_path):
    config = read_json(config_path)
    if type(config['count']) is not int or not 1<=config['count']<=1000:
        raise ValueError('Each batch must contain 1 to 1000 people')
    if type(config['face_seed_start']) is not int or not 0<=config['face_seed_start']<2**32-config['count']:
        raise ValueError('Face seeds must fit numpy RandomState uint32 range')
    path = ROOT/'work'/Path(config_path).stem/'state.json'
    if path.exists():
        saved = read_json(path)
        if saved['config_sha256'] != config_digest(config):
            raise ValueError('Config changed. Use a new config filename for a new experiment.')
        return config,path,saved
    batch_id = 'batch_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    saved = {'batch_id':batch_id,'created_at':now(),'config':config,'config_sha256':config_digest(config),
             'people':[], 'stages':{}}
    for index in range(config['count']):
        rng = random.Random(config['seed']+index)
        reference = date.fromisoformat(config['as_of'])
        birth = reference-timedelta(days=rng.randint(20*366,85*365))
        age = reference.year-birth.year-((reference.month,reference.day)<(birth.month,birth.day))
        spec=config.get('portrait_specs',[None]*config['count'])[index]
        if spec:
            age=spec['age']
            earliest=reference.replace(year=reference.year-age-1)+timedelta(days=1)
            latest=reference.replace(year=reference.year-age)
            birth=earliest+timedelta(days=rng.randint(0,(latest-earliest).days))
        person_id='person_'+uuid.uuid5(uuid.NAMESPACE_URL,f'{batch_id}:{index}').hex if config.get('opaque_ids') else f'{batch_id}_person_{index+1:06d}'
        saved['people'].append({'person_id':person_id,
                                'face_seed':config['face_seed_start']+index,
                                'profile_seed':config['seed']+index*10,
                                'birth_date':birth.isoformat(),'age':age,
                                'face_result':None,'profile':None,**({'portrait_spec':spec} if spec else {})})
    if config.get('portrait_specs'):
        saved['age_assignment_method']='birth date derived from portrait character specification'
    write_json(path,saved)
    return config,path,saved

def generate_faces(config_path, limit=None):
    if read_json(config_path).get('diffusion'):
        return generate_diffusion_faces(config_path,limit)
    from .stylegan import StyleGANAdapter
    config,path,saved = state(config_path)
    start=time.perf_counter()
    model = StyleGANAdapter(config['stylegan'])
    previous=saved.get('face_model')
    if previous and previous['weights_sha256']!=model.metadata['weights_sha256']:
        raise ValueError('StyleGAN weights changed in an existing batch. Use a new experiment config.')
    saved['face_model']=model.metadata
    saved['face_model']['model_revision']=subprocess.check_output(['git','-C',str(ROOT/config['stylegan']['repository']),'rev-parse','HEAD'],text=True).strip()
    write_json(path,saved)
    made=0
    for i,person in enumerate(saved['people']):
        raw=path.parent/'originals'/(person['person_id']+'.png')
        if person['face_result'] and raw.exists() and sha256(raw)==person['face_result']['sha256']:
            continue
        if limit is not None and made>=limit:
            break
        print(f'Face {i+1}/{len(saved["people"])} seed={person["face_seed"]}',flush=True)
        person['face_result']=model.generate(person['face_seed'],raw,config['output_size'])
        write_json(path,saved)
        made+=1
        print(f'  saved 1024px original ({person["face_result"]["seconds"]:.2f}s)',flush=True)
    saved['stages']['faces_seconds_this_run']=round(time.perf_counter()-start,3)
    write_json(path,saved)
    print(f'Faces complete: {sum(bool(p["face_result"]) for p in saved["people"])}/{len(saved["people"])}',flush=True)

def generate_diffusion_faces(config_path,limit=None):
    from .diffusion import DiffusionAdapter
    config,path,saved=state(config_path)
    pending=[]
    for person in saved['people']:
        raw=path.parent/'originals'/(person['person_id']+'.png')
        if not (person['face_result'] and raw.exists() and sha256(raw)==person['face_result']['sha256']):
            pending.append(person)
    if not pending:
        print(f'Faces reused: {len(saved["people"])}',flush=True)
        return
    diversity=None
    if config.get('face_diversity'):
        from .face_similarity import FaceDiversity
        diversity=FaceDiversity(config['face_diversity']['threshold'])
        for cached in saved['people']:
            if cached['face_result']:
                vector=diversity.feature(path.parent/'originals'/(cached['person_id']+'.png'))
                if vector is None:
                    raise ValueError('Cached portrait has no single detectable face')
                diversity.add(cached['person_id'],vector)
    model=DiffusionAdapter(config['diffusion'])
    if diversity:
        model.metadata['face_diversity']=diversity.metadata
    if saved.get('face_model') and saved['face_model']['weights_sha256']!=model.metadata['weights_sha256']:
        raise ValueError('Model weights changed in existing batch')
    saved['face_model']=model.metadata
    write_json(path,saved)
    for person in pending[:limit] if limit is not None else pending:
        completed=sum(bool(p['face_result']) for p in saved['people'])
        print(f'Generating RealVisXL portrait {completed+1}/{len(saved["people"])}...',flush=True)
        raw=path.parent/'originals'/(person['person_id']+'.png')
        if diversity:
            attempts=person.setdefault('face_attempts',[])
            initial=person.setdefault('face_seed_initial',person['face_seed'])
            for attempt in range(len(attempts),config['face_diversity']['max_attempts']):
                candidate_seed=initial+attempt*1000003
                from .face_similarity import candidate_spec
                actual_spec=candidate_spec(person['portrait_spec'],attempt,candidate_seed)
                result=model.generate(candidate_seed,raw,actual_spec)
                decision,vector=diversity.assess(raw)
                attempts.append({'seed':candidate_seed,'seconds':result['seconds'],'prompt':result['prompt'],**decision})
                if decision['accepted']:
                    result['diversity_check']=decision
                    person['face_result']=result
                    person['face_seed']=candidate_seed
                    person['portrait_spec']=actual_spec
                    diversity.add(person['person_id'],vector)
                    break
                rejected=path.parent/'rejected'/(person['person_id']+f'_attempt_{attempt+1}.png')
                rejected.parent.mkdir(exist_ok=True)
                raw.replace(rejected)
                write_json(path,saved)
                print('  Candidate rejected:',decision,flush=True)
            else:
                raise RuntimeError('Diversity retries exhausted for '+person['person_id'])
        else:
            person['face_result']=model.generate(person['face_seed'],raw,person['portrait_spec'])
        write_json(path,saved)
        print(f'Saved original ({person["face_result"]["seconds"]:.2f}s)',flush=True)
    print(f'Faces complete: {sum(bool(p["face_result"]) for p in saved["people"])}/{len(saved["people"])}',flush=True)

def generate_profiles(config_path,limit=None):
    config=read_json(config_path)
    if config.get('profiles',{}).get('mode')=='local':
        return generate_local_profiles(config_path,limit)
    from .qwen import QwenAdapter
    config,path,saved=state(config_path)
    model_path=ROOT/config['qwen']['model_path']
    model_hash=sha256(model_path)
    if saved.get('qwen_weights_sha256') not in (None,model_hash):
        raise ValueError('Qwen weights changed in an existing batch')
    saved['qwen_weights_sha256']=model_hash
    model=QwenAdapter(config['qwen'])
    write_json(path,saved)
    names={p['profile']['name'] for p in saved['people'] if p['profile']}
    surname_pool='森岡 富永 野崎 西沢 宮坂 浅岡 松浦 矢島 岩瀬 長岡 奥山 杉浦 早川 深沢 木島 辻本 下村 本間 岡部 村瀬 安井 片岡 溝口 梅田 堀内 新田 古谷 武藤 大槻 篠原 渋谷 広瀬 福井 片山 関口 平井 宮原 米田 竹中 桑原'.split()
    made=0
    for i,person in enumerate(saved['people']):
        if person['profile']:
            continue
        if limit is not None and made>=limit:
            break
        print(f'Profile {i+1}/{len(saved["people"])} Qwen3-14B Q6_K',flush=True)
        for retry in range(3):
            hint={}
            if retry:
                unused=[s for s in surname_pool if not any(n.startswith(s+' ') for n in names)]
                if unused:
                    hint={'surname_hint':unused[(i+retry)%len(unused)]}
            profile,result=model.generate({'index':i+1,'age':person['age'],
                                          'avoid_names':sorted(names),
                                          **hint,
                                          'note':'年齢は架空人物の創作設定であり、実在者の正確な年齢ではない。'},person['profile_seed']+retry*1000000)
            if profile['name'] not in names:
                break
        else:
            raise ValueError('Duplicate name after retries')
        person['profile'],person['profile_result']=profile,result
        names.add(profile['name'])
        write_json(path,saved)
        made+=1
        print(f'  saved ({result["seconds"]:.2f}s)',flush=True)
    print(f'Profiles complete: {sum(bool(p["profile"]) for p in saved["people"])}/{len(saved["people"])}',flush=True)

def generate_local_profiles(config_path,limit=None):
    from .local_profiles import generate,validate_contacts
    from .qwen import validate_profile
    config,path,saved=state(config_path)
    if all(p['profile'] for p in saved['people']):
        print(f'Local profiles reused: {len(saved["people"])}/{len(saved["people"])}; no generation required',flush=True)
        return
    used={key:{p['profile'][key] for p in saved['people'] if p['profile'] and key in p['profile']}
          for key in ('personal_number','payment_number','bank_account_number')}
    start=time.perf_counter()
    made=0
    for person in saved['people']:
        if person['profile']:
            continue
        if limit is not None and made>=limit:
            break
        tick=time.perf_counter()
        profile=generate(person,config['seed'],used)
        validate_profile(profile,policy='real-prefecture')
        validate_contacts(profile)
        person['profile']=profile
        person['profile_result']={'seconds':round(time.perf_counter()-tick,6),'seed':config['seed'],
                                  'engine':'local dictionary/templates/random','name_source':profile['name_source']}
        made+=1
        if made%100==0:
            write_json(path,saved)
    generation_seconds=time.perf_counter()-start
    saved['profile_engine']={'name':'local structured generator v1','names':'source Qwen names reused where present; otherwise paired dictionary',
                             'address_policy':'real-prefecture-city-generated-street-v1','number_policy':'invalid-numeric-v1',
                             'generation_seconds':round(generation_seconds,6),'count_this_run':made}
    write_json(path,saved)
    print(f'Local profiles: {made} generated in {generation_seconds:.6f}s; total saved {sum(bool(p["profile"]) for p in saved["people"])}/{len(saved["people"])}',flush=True)

def output_path(saved):
    return ROOT/'outputs'/saved['batch_id']

def write_csv(path,records,keys):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,lineterminator='\n')
        writer.writeheader()
        for row in records:
            writer.writerow({key:safe_csv(row[key]) for key in keys})

def export_batch(config_path):
    config,path,saved=state(config_path)
    if not all(p['face_result'] and p['profile'] for p in saved['people']):
        raise ValueError('Both face and Qwen profile stages must finish before export.')
    dest=output_path(saved)
    if (dest/'manifest.json').exists():
        from .validation import validate_directory
        validate_directory(dest)
        print('Already exported and verified:',dest)
        return dest
    dest.mkdir(parents=True,exist_ok=True)
    (dest/'faces').mkdir(exist_ok=True)
    records,details=[],[]
    image_sizes={p['person_id']:[photo_delivery_size(config,p)]*2 for p in saved['people']}
    uniform_size=len({tuple(size) for size in image_sizes.values()})==1
    clean=config.get('profile_view')=='clean-v1'
    for i,p in enumerate(saved['people']):
        raw=path.parent/'originals'/(p['person_id']+'.png')
        if sha256(raw)!=p['face_result']['sha256']:
            raise ValueError('Original face hash mismatch')
        extension=config.get('output_format','jpg')
        face_path=f'faces/{p["person_id"]}.{extension}'
        delivery_size=photo_delivery_size(config,p)
        with Image.open(raw) as image:
            delivered=image.convert('RGB')
            quality=95
            if config.get('photo_finish'):
                from .photo_finish import finish,parameters
                settings,processing_seed=parameters(config,p)
                delivered=finish(delivered,settings,delivery_size,processing_seed)
                quality=settings.get('delivery_jpeg_quality',80)
                p['photo_processing_result']={'method':'camera-scan-finish-v1','source_sha256':p['face_result']['sha256'],
                                              'settings':settings,'seed':str(processing_seed),'delivery_size':delivery_size}
            elif delivered.size!=(delivery_size,)*2:
                delivered=delivered.resize((delivery_size,)*2,Image.Resampling.LANCZOS)
            if extension=='png':
                delivered.save(dest/face_path,format='PNG')
            else:
                delivered.save(dest/face_path,quality=quality,subsampling=2 if config.get('photo_finish') else 0)
        token=uuid.uuid5(uuid.NAMESPACE_URL,p['person_id']).hex[:16].upper()
        record=dict(zip(KEYS,[1,p['person_id'],saved['batch_id'],face_path,p['profile']['name'],p['birth_date'],
                              p['profile']['address'],p['profile'].get('personal_number','TEST-MYNUMBER-'+token),
                              p['profile'].get('payment_number','TEST-CARD-'+token),saved['created_at'],True]))
        records.append(record)
        details.append({**record,**p['profile'],'bank_account_type':p['profile'].get('bank_account_type','普通（架空）'),
                        'bank_account_number':p['profile'].get('bank_account_number','TEST-ACCOUNT-'+token),
                        'profile_age_as_of':config['as_of'],'profile_age':p['age'],
                        'face_seed':p['face_seed'],'review_status':'unreviewed',
                        'portrait_type':'prompted_realvisxl_portrait' if config.get('diffusion') else 'uncurated_ffhq','face_profile_age_matched':False,
                        'age_assignment_method':saved.get('age_assignment_method','independent_random_fictional_setting'),
                        'nationality_verified':False,'background_standardized':False})
        if clean:
            for internal_key in ('profile_age_as_of','profile_age','face_seed','review_status','portrait_type',
                                 'face_profile_age_matched','age_assignment_method','nationality_verified','background_standardized'):
                details[-1].pop(internal_key,None)
    with (dest/'people.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for record in records:
            f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
    write_csv(dest/'people.csv',records,KEYS)
    admin_stem='profiles_admin' if clean else 'profiles'
    write_csv(dest/(admin_stem+'.csv'),details,list(details[0]))
    with (dest/(admin_stem+'.jsonl')).open('w',encoding='utf-8',newline='\n') as f:
        for record in details:
            f.write(json.dumps(record,ensure_ascii=False)+'\n')
    if clean:
        public=[{key:record.get(key,'') for key in PUBLIC_KEYS} for record in details]
        write_csv(dest/'profiles.csv',public,PUBLIC_KEYS)
        with (dest/'profiles.jsonl').open('w',encoding='utf-8',newline='\n') as f:
            for record in public:
                f.write(json.dumps(record,ensure_ascii=False)+'\n')
        if config.get('portable'):
            from .portable import render
            render(dest,public)
    versions={name:importlib.metadata.version(name) for name in ('torch','numpy','Pillow','requests','jsonschema')}
    assets=read_json(ROOT/'models/assets.json') if (ROOT/'models/assets.json').exists() else {}
    qwen=config.get('qwen',{})
    qwen_name=qwen.get('repository',qwen.get('model','local dictionary'))
    quantization=qwen.get('quantization',qwen.get('model','').removesuffix('.gguf').split('-')[-1])
    profile_model=({'name':'local structured generator v1',**saved['profile_engine']} if saved.get('profile_engine') else
                   {'name':qwen_name,'quantization':quantization,'revision':config['qwen']['revision'],
                    'weights_sha256':saved['qwen_weights_sha256'],'temperature':config['qwen']['temperature'],
                    'thinking':False,'runtime':'llama.cpp','runtime_release':assets.get('llama_release')})
    metadata={'schema_version':1,'batch_id':saved['batch_id'],**saved['face_model'],
              'seed':{'face':('Per-person face_seed and face_attempts record CPU torch.Generator seeds' if config.get('face_diversity') else 'torch.Generator(cpu).manual_seed(face_seed_start+index)') if config.get('diffusion') else 'numpy.RandomState(face_seed_start+index)','face_seed_start':config['face_seed_start'],
                      'profile_seed':'SHA-256(master seed:person_id) -> Python Random' if saved.get('profile_engine') else 'seed+index*10; retry offsets recorded','seed':config['seed']},
              'image_count':len(records),'image_size':next(iter(image_sizes.values())) if uniform_size else None,
              'generated_at':saved['created_at'],'packaged_at':now(),'libraries':versions,
              'python':platform.python_version(),'platform':platform.platform(),
              'resize':f'Native {saved["face_model"].get("native_image_size",1024)}px -> '+(str(next(iter(image_sizes.values()))[0])+'px' if uniform_size else 'per-person sizes in image_sizes')+'; '+('per-person camera finishing; '+('lossless PNG delivery' if config.get('output_format')=='png' else 'JPEG delivery') if config.get('photo_finish') else 'lossless PNG' if config.get('output_format')=='png' else 'JPEG quality=95 subsampling=0'),
              'photo_finish':bool(config.get('photo_finish')),
              'profile_model':profile_model,
              'profile_reference_date':config['as_of'],
              'age_distribution':config.get('age_distribution'),
              'source_batch':saved.get('source_batch'),
              'source_profiles_batch':saved.get('source_profiles_batch'),
              'draft_adjustments':saved.get('draft_adjustments',[]),
              'public_profile_layout':'clean-v1' if clean else 'legacy',
              'address_policy':saved.get('profile_engine',{}).get('address_policy','fictional-prefix'),
              'number_policy':saved.get('profile_engine',{}).get('number_policy','test-prefix'),
              'face_inference_seconds':round(sum(p['face_result']['seconds'] for p in saved['people']),3),
              'profile_inference_seconds':round(sum(p['profile_result']['seconds'] for p in saved['people']),3),
              'timing_scope':'Sum of saved successful image/request durations; excludes downloads, setup, discarded trials and failed/repeated requests.',
              'synthetic':True,'quality_status':'unreviewed model comparison test',
              'age_assignment_method':saved.get('age_assignment_method','independent_random_fictional_setting'),
              'limitations':saved['face_model'].get('limitations',['Official FFHQ is not Japanese-specific; no ethnicity classifier used.',
                             'Background, pose and expression are not standardized.'])+[
                             'Birth dates are fictional settings. Any approximate visual age direction is unverified.',
                             'No completed manual quality review; not an accepted production dataset.',
                             'Mac import has not been tested.'],
              'people':[{k:p[k] for k in ('person_id','source_person_id','face_seed','profile_seed','face_result','profile_result','photo_processing_result','face_attempts') if k in p} for p in saved['people']]}
    if not uniform_size:
        metadata['image_sizes']=image_sizes
    write_json(dest/'generation.json',metadata)
    files=[{'path':file.relative_to(dest).as_posix(),'size_bytes':file.stat().st_size,'sha256':sha256(file)}
           for file in sorted(dest.rglob('*')) if file.is_file() and file.name!='manifest.json']
    write_json(dest/'manifest.json',{'schema_version':1,'batch_id':saved['batch_id'],'person_count':len(records),
                                    'created_at':saved['created_at'],'files':files})
    print('Exported:',dest,flush=True)
    return dest

def preview(config_path):
    config,path,saved=state(config_path)
    if config.get('portable'):
        dest=output_path(saved)
        if not (dest/'index.html').is_file():
            raise ValueError('Export the portable batch before previewing')
        print('Portable preview:',dest/'index.html')
        return dest
    from .review import render
    return render(config,path,saved)

def package(config_path):
    import tempfile
    from .validation import validate_directory,safe_extract
    _,_,saved=state(config_path)
    dest=output_path(saved)
    validate_directory(dest)
    archive=dest.with_suffix('.zip')
    if archive.exists():
        with tempfile.TemporaryDirectory() as temp:
            safe_extract(archive,Path(temp))
            validate_directory(Path(temp))
            if sha256(Path(temp)/'manifest.json') != sha256(dest/'manifest.json'):
                raise ValueError('Existing archive conflicts with this batch')
        print('Existing ZIP verified:',archive)
        return archive
    temp_zip=archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(dest.rglob('*')):
            if file.is_file():
                z.write(file,file.relative_to(dest).as_posix())
    with tempfile.TemporaryDirectory() as temp:
        safe_extract(temp_zip,Path(temp))
        validate_directory(Path(temp))
    temp_zip.replace(archive)
    print('ZIP verified:',archive,'sha256='+sha256(archive))
    return archive

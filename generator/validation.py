import csv
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

import jsonschema
from PIL import Image

from .common import ROOT, KEYS, PUBLIC_KEYS, read_json, safe_csv, sha256

def relative_path(value):
    p=PurePosixPath(value)
    if not value or '\\' in value or ':' in value or p.is_absolute() or '..' in p.parts or p.as_posix()!=value:
        raise ValueError('Unsafe or non-canonical path: '+value)
    return p

def safe_extract(archive,dest,max_bytes=1024**3,max_files=5000):
    dest=Path(dest).resolve()
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)>max_files or sum(e.file_size for e in entries)>max_bytes:
            raise ValueError('Archive exceeds limits')
        paths=set()
        for entry in entries:
            name=entry.filename.rstrip('/')
            relative_path(name)
            if name.casefold() in paths:
                raise ValueError('Duplicate ZIP path')
            paths.add(name.casefold())
            mode=entry.external_attr>>16
            if stat.S_ISLNK(mode) or not (dest/name).resolve().is_relative_to(dest):
                raise ValueError('Unsafe ZIP entry')
        z.extractall(dest)

def validate_directory(dest):
    dest=Path(dest)
    manifest=read_json(dest/'manifest.json')
    jsonschema.Draft202012Validator(read_json(ROOT/'schemas/manifest-v1.schema.json'),format_checker=jsonschema.FormatChecker()).validate(manifest)
    if type(manifest.get('schema_version')) is not int or manifest['schema_version']!=1:
        raise ValueError('Wrong manifest schema')
    if type(manifest.get('person_count')) is not int or not 1<=manifest['person_count']<=1000:
        raise ValueError('Invalid count')
    if type(manifest.get('batch_id')) is not str or not manifest['batch_id']:
        raise ValueError('Invalid batch ID')
    listed=set()
    for entry in manifest['files']:
        name=entry['path']
        relative_path(name)
        if name.casefold() in listed or name=='manifest.json':
            raise ValueError('Duplicate or circular manifest path')
        listed.add(name.casefold())
        file=dest/name
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(dest.resolve()):
            raise ValueError('Missing or unsafe file: '+name)
        if type(entry['size_bytes']) is not int or file.stat().st_size!=entry['size_bytes'] or sha256(file)!=entry['sha256']:
            raise ValueError('File hash/size mismatch: '+name)
    actual={p.relative_to(dest).as_posix().casefold() for p in dest.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if actual!=listed:
        raise ValueError('Unlisted or missing files')
    required={'people.jsonl','people.csv','generation.json'}
    if not required<=listed:
        raise ValueError('Missing required files')
    source=(dest/'people.jsonl').read_bytes()
    if source.startswith(b'\xef\xbb\xbf') or b'\r' in source or not source.endswith(b'\n'):
        raise ValueError('JSONL must be UTF-8 without BOM, LF terminated')
    records=[json.loads(line) for line in source.decode('utf-8').splitlines()]
    if len(records)!=manifest['person_count']:
        raise ValueError('Record count mismatch')
    schema=read_json(ROOT/'schemas/person-v1.schema.json')
    validator=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
    seen=set()
    face_paths=set()
    generation=read_json(dest/'generation.json')
    if generation['batch_id']!=manifest['batch_id'] or generation['image_count']!=len(records):
        raise ValueError('Generation metadata mismatch')
    sizes=generation.get('image_sizes')
    if sizes is not None:
        if not isinstance(sizes,dict) or set(sizes)!={r['person_id'] for r in records}:
            raise ValueError('Per-person image size coverage mismatch')
        if any(not isinstance(size,list) or len(size)!=2 or any(type(n) is not int or not 1<=n<=4096 for n in size) for size in sizes.values()):
            raise ValueError('Invalid per-person image dimensions')
    for record in records:
        validator.validate(record)
        from .local_profiles import mynumber_valid,luhn_valid
        if record['personal_number'].isdigit() and mynumber_valid(record['personal_number']):
            raise ValueError('Numeric personal number must fail checksum')
        if record['payment_number'].isdigit() and luhn_valid(record['payment_number']):
            raise ValueError('Numeric payment number must fail Luhn')
        if list(record)!=KEYS or record['batch_id']!=manifest['batch_id'] or record['person_id'] in seen:
            raise ValueError('Record identity/key order mismatch')
        seen.add(record['person_id'])
        name=record['face_path']
        relative_path(name)
        if name in face_paths:
            raise ValueError('Duplicate face reference')
        face_paths.add(name)
        with Image.open(dest/name) as image:
            expected_size=sizes[record['person_id']] if sizes is not None else generation['image_size']
            if image.format not in ('JPEG','PNG') or list(image.size)!=expected_size:
                raise ValueError('Invalid image format/size')
            image.load()
    actual_faces={p.relative_to(dest).as_posix() for p in (dest/'faces').rglob('*') if p.is_file()}
    if actual_faces!=face_paths:
        raise ValueError('Extra or missing face')
    with (dest/'people.csv').open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=KEYS:
            raise ValueError('CSV header mismatch')
        rows=list(reader)
    expected=[{k:str(safe_csv(v)) for k,v in row.items()} for row in records]
    if rows!=expected:
        raise ValueError('CSV and JSONL mismatch')
    if (dest/'profiles.jsonl').exists():
        from .qwen import FIELDS,PROFILE_SCHEMA,validate_profile
        clean=generation.get('public_profile_layout')=='clean-v1'
        admin_stem='profiles_admin' if clean else 'profiles'
        detail=[json.loads(line) for line in (dest/(admin_stem+'.jsonl')).read_text(encoding='utf-8').splitlines()]
        if len(detail)!=len(records):
            raise ValueError('Extended profile count mismatch')
        for base,profile in zip(records,detail):
            if any(profile[k]!=v for k,v in base.items()):
                raise ValueError('Extended profile mismatch')
            subset={k:profile[k] for k in FIELDS}
            jsonschema.validate(subset,PROFILE_SCHEMA)
            policy='real-prefecture' if generation.get('address_policy')=='real-prefecture-city-generated-street-v1' else 'fictional-prefix'
            validate_profile(subset,policy=policy)
            if 'email' in profile:
                from .local_profiles import validate_contacts
                validate_contacts(profile)
            account=profile['bank_account_number']
            if account.isdigit():
                if not re.fullmatch('[0-9]{7}',account) or profile.get('bank_routing_id')!='TEST':
                    raise ValueError('Numeric account requires 7 digits and non-routable test bank routing ID')
            elif not account.startswith('TEST-'):
                raise ValueError('Invalid test account marker')
        with (dest/(admin_stem+'.csv')).open(encoding='utf-8',newline='') as f:
            rows=list(csv.DictReader(f))
        if rows!=[{k:str(safe_csv(v)) for k,v in row.items()} for row in detail]:
            raise ValueError('Extended CSV mismatch')
        if clean:
            public=[json.loads(line) for line in (dest/'profiles.jsonl').read_text(encoding='utf-8').splitlines()]
            expected_public=[{key:row.get(key,'') for key in PUBLIC_KEYS} for row in detail]
            if public!=expected_public or any(list(row)!=PUBLIC_KEYS for row in public):
                raise ValueError('Public profile contains missing, internal, or inconsistent fields')
            with (dest/'profiles.csv').open(encoding='utf-8',newline='') as f:
                reader=csv.DictReader(f)
                if reader.fieldnames!=PUBLIC_KEYS or list(reader)!=[{k:str(safe_csv(v)) for k,v in row.items()} for row in expected_public]:
                    raise ValueError('Public CSV mismatch')
    print(f'VALID: {len(records)} people, {len(listed)} files, hashes/images/CSV/JSONL match',flush=True)
    return {'person_count':len(records),'file_count':len(listed),'batch_id':manifest['batch_id']}

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from generator.common import ROOT,read_json,sha256,write_json,safe_csv
from generator import pipeline
from generator.validation import safe_extract,validate_directory

class IntegrityTests(unittest.TestCase):
    def test_profile_rejects_mixed_bank_or_hiragana(self):
        from generator.qwen import validate_profile
        profile={'name':'架空 試験','name_kana':'カクウ シケン','address':'架空県試験市生成町1',
                 'occupation':'検証用','bank_name':'架空試験銀行','bank_branch':'生成支店','account_holder_kana':'カクウ シケン'}
        validate_profile(profile)
        with self.assertRaises(ValueError):
            validate_profile({**profile,'bank_name':'架空試験銀行 生成支店'})
        with self.assertRaises(ValueError):
            validate_profile({**profile,'name_kana':'かくう しけん'})

    def test_formula_escape(self):
        self.assertEqual(safe_csv(' =2+2'),"' =2+2")
        self.assertEqual(safe_csv(True),'true')
        self.assertEqual(safe_csv('架空 太郎'),'架空 太郎')

    def test_zip_rejects_traversal_duplicates_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            for mode in ('traversal','duplicate','symlink'):
                archive=base/(mode+'.zip')
                with zipfile.ZipFile(archive,'w') as z:
                    if mode=='traversal':
                        z.writestr('../escape','test')
                    elif mode=='duplicate':
                        z.writestr('one','a'); z.writestr('ONE','b')
                    else:
                        entry=zipfile.ZipInfo('link')
                        entry.create_system=3
                        entry.external_attr=0o120777<<16
                        z.writestr(entry,'../escape')
                with self.assertRaises(ValueError):
                    safe_extract(archive,base/'out')

    def test_fixture_export_roundtrip_and_tamper(self):
        # Explicit test fixture: solid images and no model inference. Never delivered as real generation.
        with tempfile.TemporaryDirectory() as tmp,patch.object(pipeline,'ROOT',Path(tmp)):
            temp=Path(tmp)
            config=read_json(ROOT/'configs/test100.json')
            config['count']=2
            file=temp/'fixture.json'
            write_json(file,config)
            _,state_path,saved=pipeline.state(file)
            self.assertEqual(saved['batch_id'],pipeline.state(file)[2]['batch_id'])
            for i,p in enumerate(saved['people']):
                original=state_path.parent/'originals'/(p['person_id']+'.png')
                original.parent.mkdir(exist_ok=True)
                Image.new('RGB',(1024,1024),(120+i,130,140)).save(original)
                p['face_result']={'sha256':sha256(original),'seconds':0,'seed':p['face_seed']}
                p['profile']={'name':f'架空 試験{i}','name_kana':'カクウ シケン','address':'架空県試験市生成町1',
                              'occupation':'検証用','bank_name':'架空試験銀行','bank_branch':'生成支店','account_holder_kana':'カクウ シケン'}
                p['profile_result']={'seconds':0,'seed':p['profile_seed']}
            saved['face_model']={'model_name':'TEST FIXTURE - NO INFERENCE','weights_sha256':'0'*64,'model_revision':'fixture'}
            saved['qwen_weights_sha256']='0'*64
            write_json(state_path,saved)
            dest=pipeline.export_batch(file)
            self.assertEqual(validate_directory(dest)['person_count'],2)
            archive=pipeline.package(file)
            self.assertEqual(archive,pipeline.package(file))
            (dest/'faces'/next((dest/'faces').iterdir()).name).write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                validate_directory(dest)

    def test_changed_config_refused(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pipeline,'ROOT',Path(tmp)):
            config=read_json(ROOT/'configs/test100.json')
            file=Path(tmp)/'fixture.json'
            write_json(file,config)
            pipeline.state(file)
            config['seed']+=1
            write_json(file,config)
            with self.assertRaises(ValueError):
                pipeline.state(file)

    def test_clean_public_profile_roundtrip(self):
        self._clean_roundtrip()

    def test_variable_photo_sizes_and_wrong_size_rejected(self):
        self._clean_roundtrip(variable=True)

    def test_portable_export_includes_relative_gallery_in_manifest(self):
        self._clean_roundtrip(variable=True,portable=True)

    def _clean_roundtrip(self,variable=False,portable=False):
        from generator.common import PUBLIC_KEYS
        from generator.local_profiles import generate
        with tempfile.TemporaryDirectory() as tmp,patch.object(pipeline,'ROOT',Path(tmp)):
            temp=Path(tmp)
            config=read_json(ROOT/'configs/realvis10.json')
            config['count']=2
            config['portrait_specs']=config['portrait_specs'][:2]
            if portable:
                config['portable']=True
            if variable:
                config.update({'photo_finish':True,'output_format':'jpg'})
                for i,spec in enumerate(config['portrait_specs']):
                    spec['finish']={'effective_size':128,'delivery_size':64+i*32,
                                    'camera_jpeg_enabled':False,'delivery_jpeg_quality':45+i*20}
            file=temp/'clean.json'
            write_json(file,config)
            _,path,saved=pipeline.state(file)
            for person in saved['people']:
                original=path.parent/'originals'/(person['person_id']+'.png')
                original.parent.mkdir(exist_ok=True)
                Image.new('RGB',(1024,1024),'#aabbcc').save(original)
                person['face_result']={'sha256':sha256(original),'seconds':0,'seed':person['face_seed']}
                person['profile']=generate(person,config['seed'])
                person['profile_result']={'seconds':0,'engine':'test fixture'}
            saved['face_model']={'model_name':'TEST FIXTURE - NO INFERENCE','weights_sha256':'0'*64,'model_revision':'fixture','native_image_size':1024}
            saved['profile_engine']={'name':'test fixture','address_policy':'real-prefecture-city-generated-street-v1','number_policy':'invalid-numeric-v1'}
            write_json(path,saved)
            dest=pipeline.export_batch(file)
            validate_directory(dest)
            if variable:
                metadata=read_json(dest/'generation.json')
                self.assertIsNone(metadata['image_size'])
                for i,person in enumerate(saved['people']):
                    expected=[64+i*32]*2
                    self.assertEqual(metadata['image_sizes'][person['person_id']],expected)
                    with Image.open(dest/'faces'/(person['person_id']+'.jpg')) as image:
                        self.assertEqual(list(image.size),expected)
                pipeline.package(file)
            rows=[json.loads(line) for line in (dest/'profiles.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(list(rows[0]),PUBLIC_KEYS)
            self.assertFalse({'person_id','face_seed','profile_age','synthetic'}&set(rows[0]))
            self.assertTrue((dest/'profiles_admin.jsonl').is_file())
            admin=json.loads((dest/'profiles_admin.jsonl').read_text(encoding='utf-8').splitlines()[0])
            self.assertNotIn('face_seed',admin)
            self.assertNotIn('profile_age',admin)
            review=pipeline.preview(file)
            content=(review/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('seed',content)
            self.assertNotIn('創作年齢',content)
            self.assertNotRegex(content,r'<h2>\d{3}\s')
            if portable:
                from scripts.verify_portable import References
                self.assertEqual(review,dest)
                refs=References()
                refs.feed(content)
                self.assertEqual(len(refs.images),2)
                self.assertNotIn('file:',content)
                for value in refs.images+refs.links:
                    self.assertTrue((dest/value).is_file())
                paths={entry['path'] for entry in read_json(dest/'manifest.json')['files']}
                self.assertTrue({'index.html','README.txt'}<=paths)
            if variable:
                metadata['image_sizes'][saved['people'][0]['person_id']]=[999,999]
                write_json(dest/'generation.json',metadata)
                manifest=read_json(dest/'manifest.json')
                for entry in manifest['files']:
                    if entry['path']=='generation.json':
                        entry.update({'size_bytes':(dest/'generation.json').stat().st_size,'sha256':sha256(dest/'generation.json')})
                write_json(dest/'manifest.json',manifest)
                with self.assertRaisesRegex(ValueError,'Invalid image format/size'):
                    validate_directory(dest)

if __name__=='__main__':
    unittest.main()

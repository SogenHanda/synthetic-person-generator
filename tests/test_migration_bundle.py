import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.migration_bundle import restore,relative

class MigrationTests(unittest.TestCase):
    def bundle(self,base):
        content=b'accepted synthetic original'
        entry={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
        name='work/source/originals/test.png'
        archive=base/'part001'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr(name,content)
            z.writestr('migration_manifest.json',json.dumps({'format':1,'files':{name:entry},
                'derived_originals':{'work/checkpoint/originals/renamed.png':name}}))
        manifest=base/'parts.json'
        manifest.write_text(json.dumps({'format':1,'archive_bytes':archive.stat().st_size,
            'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'parts':[{'name':archive.name,'bytes':archive.stat().st_size,
                      'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}]}))
        return manifest,content,name

    def test_roundtrip_restores_both_ids_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'target';root.mkdir()
            manifest,content,name=self.bundle(base)
            restore(manifest,root)
            self.assertEqual((root/name).read_bytes(),content)
            self.assertEqual((root/'work/checkpoint/originals/renamed.png').read_bytes(),content)
            restore(manifest,root)

    def test_checksum_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'target';root.mkdir()
            manifest,_,_=self.bundle(base)
            with (base/'part001').open('ab') as f:f.write(b'corrupt')
            with self.assertRaises(ValueError):restore(manifest,root)
            self.assertEqual(list(root.iterdir()),[])

    def test_different_existing_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'target';root.mkdir()
            manifest,_,name=self.bundle(base)
            dest=root/name;dest.parent.mkdir(parents=True);dest.write_bytes(b'previous')
            with self.assertRaises(ValueError):restore(manifest,root)
            self.assertEqual(dest.read_bytes(),b'previous')
            self.assertFalse((root/'work/checkpoint').exists())

    def test_unsafe_paths_are_rejected(self):
        for name in ('../escape','/absolute','C:/absolute','a\\b','a/../b',''):
            with self.subTest(name=name),self.assertRaises(ValueError):relative(name)

if __name__=='__main__':unittest.main()

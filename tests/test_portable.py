import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from generator.portable import render
from scripts.verify_portable import References

class PortableTests(unittest.TestCase):
    def test_offline_relative_images_and_escaped_fields_after_relocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'original'
            (folder/'faces').mkdir(parents=True)
            Image.new('RGB',(240,240),'#aabbcc').save(folder/'faces/photo.jpg')
            (folder/'profiles.csv').write_text('name,face_path\n',encoding='utf-8')
            (folder/'profiles.jsonl').write_text('',encoding='utf-8')
            render(folder,[{'name':'試験 <script>','name_kana':'シケン','birth_date':'1980-01-01',
                            'address':'東京都杉並区','face_path':'faces/photo.jpg','employer':'A&B'}])
            moved=Path(tmp)/'different'/'dataset'
            shutil.copytree(folder,moved)
            content=(moved/'index.html').read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;',content)
            self.assertIn('A&amp;B',content)
            refs=References()
            refs.feed(content)
            self.assertEqual(refs.images,['faces/photo.jpg'])
            for value in refs.images+refs.links:
                self.assertFalse(value.startswith(('file:','http:','https:','/')))
                self.assertTrue((moved/value).is_file())
            self.assertIn('loading="lazy"',content)
            self.assertNotIn('fetch(',content)

if __name__=='__main__': unittest.main()

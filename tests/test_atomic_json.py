import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generator.common import write_json,read_json

class AtomicJsonTests(unittest.TestCase):
    def test_temporary_windows_lock_retries_and_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json'
            write_json(path,{'value':'old'})
            replace=Path.replace
            calls=[]
            def intermittently_locked(source,target):
                calls.append(1)
                self.assertEqual(read_json(path),{'value':'old'})
                if len(calls)<3: raise PermissionError('simulated reader lock')
                return replace(source,target)
            with patch.object(Path,'replace',intermittently_locked),patch('generator.common.time.sleep'):
                write_json(path,{'value':'new'})
            self.assertEqual(len(calls),3)
            self.assertEqual(read_json(path),{'value':'new'})

    def test_persistent_lock_leaves_old_json_and_complete_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json'
            write_json(path,{'value':'old'})
            with patch.object(Path,'replace',side_effect=PermissionError('simulated lock')),patch('generator.common.time.sleep'):
                with self.assertRaises(PermissionError): write_json(path,{'value':'new'})
            self.assertEqual(read_json(path),{'value':'old'})
            self.assertEqual(read_json(path.with_suffix('.json.tmp')),{'value':'new'})

if __name__=='__main__': unittest.main()

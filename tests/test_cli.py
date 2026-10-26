import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, Engine, CommerceError
from commerce_core.media import compose

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/commerce-creative/scripts/commerce.py'


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_init_doctor_and_prepare_without_api_keys(self):
        r = self.cli('init', '--project', str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        req = {'operation': 'insight', 'provider': 'chanmama', 'params': {'product_name': 'Test'}}
        (self.root / 'request.json').write_text(json.dumps(req))
        r = self.cli('prepare', 'request.json', '--project', str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['state'], 'prepared')
        r = self.cli('doctor', '--project', str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('live_acceptance', json.loads(r.stdout))
        self.assertNotIn('sk-', r.stdout)

    def test_cli_reports_path_error_without_traceback(self):
        self.cli('init', '--project', str(self.root))
        r = self.cli('prepare', '../outside.json', '--project', str(self.root))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('Traceback', r.stderr)

    def test_compose_does_not_overwrite_or_escape(self):
        ws = Workspace.init(self.root)
        (self.root / 'a.mp4').write_bytes(b'synthetic')
        (self.root / 'existing.mp4').write_bytes(b'keep')
        with self.assertRaises(CommerceError):
            compose(ws, ['a.mp4'], 'existing.mp4')
        with self.assertRaises(CommerceError):
            compose(ws, ['a.mp4'], '../escape.mp4')

    def test_chinese_json_output_is_utf8_even_under_ascii_locale(self):
        self.cli('init', '--project', str(self.root))
        (self.root / 'request.json').write_text(json.dumps({'operation': 'video', 'provider': 'minimax',
            'params': {'prompt': '虚构绿豆饼', 'duration': 6}}), encoding='utf-8')
        env = {**os.environ, 'LC_ALL': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0'}
        result = subprocess.run([sys.executable, str(SCRIPT), 'prepare', 'request.json', '--project', str(self.root)],
            env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['request']['params']['prompt'], '虚构绿豆饼')


if __name__ == '__main__':
    unittest.main()

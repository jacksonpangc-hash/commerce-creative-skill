import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from commerce_core.core import Workspace, Engine, CommerceError
from commerce_core.workflow import validate_storyboard, export_requests
from commerce_core.clipcat import inspect_argv, build_clipcat_command, confirm_clipcat
from commerce_core.publishing import build_sau_command


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)
        (self.ws.root / 'product.png').write_bytes(b'synthetic')
        (self.ws.root / 'clip.mp4').write_bytes(b'synthetic')

    def story(self):
        return {'version': 1, 'product': {'name': 'Test', 'facts': ['Has a handle']},
                'sources': [{'provider': 'chanmama', 'report': 'report.md'}],
                'platform': 'douyin', 'language': 'zh', 'ratio': '9:16',
                'shots': [{'id': 's1', 'duration': 6, 'visual': 'Show handle',
                           'narration': 'A practical handle', 'subtitle': '',
                           'prompt': 'Closeup of actual product handle',
                           'assets': [{'path': 'product.png', 'role': 'first_frame'}]}]}

    def test_storyboard_exports_each_provider_without_rewriting(self):
        story = self.story()
        for provider in ['minimax', 'seedance', 'clipcat']:
            reqs = export_requests(story, provider, self.ws, model='seedance2' if provider == 'clipcat' else None, catalog_checked=True)
            self.assertEqual(reqs[0]['provider'], provider)
            self.assertIn(story['shots'][0]['prompt'], reqs[0]['params']['prompt'])
            self.assertEqual(reqs[0]['params']['duration'], 6)

    def test_empty_shots_and_duplicate_ids_rejected(self):
        s = self.story()
        s['shots'] = []
        with self.assertRaises(CommerceError):
            validate_storyboard(s)
        s = self.story()
        s['shots'].append(s['shots'][0].copy())
        with self.assertRaises(CommerceError):
            validate_storyboard(s)

    def test_long_shot_not_silently_shortened(self):
        s = self.story()
        s['shots'][0]['duration'] = 25
        with self.assertRaises(CommerceError):
            export_requests(s, 'minimax', self.ws)
        self.assertEqual(export_requests(s, 'seedance', self.ws)[0]['params']['duration'], 25)

    def test_clipcat_preserves_raw_mode_and_no_shell(self):
        req = {'operation': 'video', 'provider': 'clipcat', 'params': {
            'model': 'seedance2', 'prompt': 'literal $(do not execute)', 'duration': 6,
            'resolution': '720p', 'ratio': '9:16', 'assets': [{'path': 'product.png'}]}}
        # Command construction must not depend on a proprietary client being installed.
        with patch('commerce_core.clipcat.executable', return_value='clipcat-offline-fixture'):
            cmd = build_clipcat_command(req, self.ws)
        self.assertEqual(cmd[0], 'clipcat-offline-fixture')
        self.assertIn('generate', cmd)
        self.assertNotIn('product_video', cmd)
        self.assertIn('literal $(do not execute)', cmd)

    def test_clipcat_update_credentials_and_confirm_rejected_in_passthrough(self):
        for argv in [['update'], ['config', '--show'], ['generate', '--confirm', 'x'],
                     ['models', '--api-key', 'secret'], ['video', 'rank', '--base-url=https://evil.example']]:
            with self.assertRaises(CommerceError):
                inspect_argv(argv, self.ws)

    def test_clipcat_generic_asset_path_is_fingerprinted(self):
        files, effects = inspect_argv(['asset', 'upload', 'product.png'], self.ws)
        self.assertIn(self.ws.root / 'product.png', files)
        self.assertIn('upload', effects)

    def test_sau_uses_correct_platform_not_tiktok(self):
        p = {'platform': 'douyin', 'account': 'synthetic-account', 'title': 'Test',
             'schedule': '2026-12-01 14:00', 'assets': [{'path': 'clip.mp4', 'kind': 'video'}]}
        cmd, cwd = build_sau_command(p, self.ws)
        self.assertIn('douyin', cmd)
        self.assertIn('--schedule', cmd)
        self.assertNotIn('tiktok', cmd)
        self.assertTrue(cwd.is_relative_to(self.ws.root))

    def test_sau_account_cannot_escape(self):
        p = {'platform': 'douyin', 'account': '../../other', 'title': 'Test', 'assets': [{'path': 'clip.mp4'}]}
        with self.assertRaises(CommerceError):
            build_sau_command(p, self.ws)


if __name__ == '__main__':
    unittest.main()

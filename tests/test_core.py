import json
import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, Engine, CommerceError


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = Workspace.init(self.root)
        self.asset = self.root / 'product.png'
        self.asset.write_bytes(b'synthetic image')

    def video(self):
        return {'operation': 'video', 'provider': 'minimax', 'params': {
            'prompt': 'Show the real product', 'duration': 6,
            'resolution': '768P', 'ratio': '9:16',
            'assets': [{'path': 'product.png', 'role': 'first_frame'}]}}

    def test_prepare_never_calls_transport(self):
        calls = []
        e = Engine(self.ws, dispatch=lambda *a: calls.append(a))
        plan = e.prepare(self.video())
        self.assertEqual(calls, [])
        self.assertEqual(plan['state'], 'prepared')
        self.assertIn('upload', plan['effects'])

    def test_path_escape_and_symlink_escape_rejected(self):
        with self.assertRaises(CommerceError):
            self.ws.path('../outside')
        (self.root / 'escape').symlink_to('/etc/hosts')
        with self.assertRaises(CommerceError):
            self.ws.path('escape')

    def test_changed_asset_invalidates_confirmation(self):
        e = Engine(self.ws, dispatch=lambda p, w: {'state': 'submitted'})
        p = e.prepare(self.video())
        self.asset.write_bytes(b'changed')
        with self.assertRaisesRegex(CommerceError, 'changed'):
            e.execute(p['id'], p['id'], {'paid', 'upload', 'unknown_cost'})

    def test_changed_config_invalidates_confirmation(self):
        e = Engine(self.ws, dispatch=lambda p, w: {'state': 'submitted'})
        p = e.prepare(self.video())
        self.ws.config['defaults']['video'] = 'seedance'
        self.ws.save_config()
        with self.assertRaisesRegex(CommerceError, 'changed'):
            e.execute(p['id'], p['id'], {'paid', 'upload', 'unknown_cost'})

    def test_effect_permissions_required(self):
        e = Engine(self.ws, dispatch=lambda p, w: {'state': 'submitted'})
        p = e.prepare(self.video())
        with self.assertRaises(CommerceError):
            e.execute(p['id'], p['id'], set())
        self.assertEqual(self.ws.read_plan(p['id'])['state'], 'prepared')

    def test_dispatch_uncertainty_cannot_replay(self):
        def timeout(*_):
            raise TimeoutError('synthetic timeout')
        e = Engine(self.ws, dispatch=timeout)
        p = e.prepare(self.video())
        result = e.execute(p['id'], p['id'], {'paid', 'upload', 'unknown_cost'})
        self.assertEqual(result['state'], 'submission_unknown')
        with self.assertRaises(CommerceError):
            e.execute(p['id'], p['id'], {'paid', 'upload', 'unknown_cost'})

    def test_confirmation_id_must_match(self):
        e = Engine(self.ws, dispatch=lambda *a: {})
        p = e.prepare(self.video())
        with self.assertRaises(CommerceError):
            e.execute(p['id'], 'wrong', {'paid', 'upload', 'unknown_cost'})

    def test_success_is_not_automatically_publication(self):
        e = Engine(self.ws, dispatch=lambda p, w: {'state': 'submitted', 'remote_id': 'synthetic'})
        p = e.prepare(self.video())
        r = e.execute(p['id'], p['id'], {'paid', 'upload', 'unknown_cost'})
        self.assertEqual(r['state'], 'submitted')
        self.assertEqual(r['remote_id'], 'synthetic')


if __name__ == '__main__':
    unittest.main()

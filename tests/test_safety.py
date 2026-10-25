import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from commerce_core.core import Workspace, Engine, CommerceError
from commerce_core.http import HTTP, NoRedirect
from commerce_core.providers import parse_youcloud, refresh_job


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)

    def test_missing_key_fails_before_dispatch_claim(self):
        e = Engine(self.ws)
        p = e.prepare({'operation': 'video', 'provider': 'minimax', 'params': {'prompt': 'Test', 'duration': 6}})
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(CommerceError, 'MINIMAX_API_KEY'):
            e.execute(p['id'], p['id'], {'paid', 'unknown_cost'})
        self.assertFalse(self.ws.path('.commerce/locks/' + p['id']).exists())

    def test_credentials_not_saved_in_request(self):
        with self.assertRaises(CommerceError):
            Engine(self.ws).prepare({'operation': 'image', 'provider': 'openai',
                                    'params': {'prompt': 'Test', 'api_key': 'secret'}})

    def test_image_limit_is_not_silent_truncation(self):
        with self.assertRaises(CommerceError):
            Engine(self.ws).prepare({'operation': 'image', 'provider': 'minimax',
                'params': {'prompt': 'Test', 'assets': [{'url': 'https://example.com/a.png'},
                                                      {'url': 'https://example.com/b.png'}]}})

    def test_no_cross_provider_clipcat_asset(self):
        with self.assertRaises(CommerceError):
            Engine(self.ws).prepare({'operation': 'image', 'provider': 'openai',
                'params': {'prompt': 'Test', 'assets': [{'url': 'clipcat://assets/test'}]}})

    def test_redirect_never_forwards_authorization(self):
        with self.assertRaises(CommerceError):
            NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://other.example')

    def test_refresh_keeps_foreign_provider_id_opaque(self):
        class Fake:
            def json(inner, provider, path, **kw):
                self.assertEqual(path, '/v2/query/video_generation/a%2Fb%3Fc')
                return {'task': {'id': 'a/b?c', 'status': 'running'}}
        jid = 'c' * 32
        self.ws.save('.commerce/jobs/' + jid + '.json', {'id': jid, 'provider': 'minimax',
            'operation': 'video', 'remote_id': 'a/b?c', 'project': str(self.ws.root)})
        r = refresh_job(self.ws, jid, Fake(), {'MINIMAX_API_KEY': 'synthetic'})
        self.assertEqual(r['state'], 'running')

    def test_presigned_stage_is_explicit_not_implicit(self):
        (self.ws.root / 'v.mp4').write_bytes(b'synthetic')
        p = Engine(self.ws, dispatch=lambda *_: {}).prepare({'operation': 'stage', 'provider': 'presigned',
            'params': {'assets': [{'path': 'v.mp4', 'kind': 'video'}],
                       'put_url': 'https://example.com/signed-put',
                       'read_url': 'https://example.com/signed-get'}})
        self.assertEqual(set(p['effects']), {'network', 'upload'})

    def test_unavailable_video_data_uri_not_sent_to_ark(self):
        (self.ws.root / 'v.mp4').write_bytes(b'synthetic')
        with self.assertRaisesRegex(CommerceError, 'stage'):
            Engine(self.ws).prepare({'operation': 'video', 'provider': 'seedance',
                'params': {'prompt': 'Test', 'duration': 6,
                           'assets': [{'path': 'v.mp4', 'kind': 'video'}]}})


if __name__ == '__main__':
    unittest.main()

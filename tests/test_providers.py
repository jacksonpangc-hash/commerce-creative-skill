import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, CommerceError
from commerce_core.providers import build_video, build_image, parse_youcloud, normalize_video, dispatch


class FakeHTTP:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def json(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return next(self.responses)

    def ndjson(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return iter(next(self.responses))


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)
        (Path(self.tmp.name) / 'a.png').write_bytes(b'synthetic')

    def test_h3_uses_v2_content_and_exact_model(self):
        p = {'model': 'MiniMax-H3', 'prompt': 'Product', 'duration': 6,
             'resolution': '768P', 'ratio': '9:16',
             'assets': [{'path': 'a.png', 'role': 'first_frame'}]}
        path, body = build_video('minimax', p, self.ws)
        self.assertEqual(path, '/v2/video_generation')
        self.assertEqual(body['model'], 'MiniMax-H3')
        self.assertEqual(body['content'][1]['role'], 'first_frame')
        self.assertTrue(body['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))

    def test_ark_is_distinct_from_clipcat(self):
        path, body = build_video('seedance', {'model': 'doubao-seedance-2-5-260628',
            'prompt': 'Product', 'duration': 8, 'resolution': '720p', 'ratio': '16:9'}, self.ws)
        self.assertEqual(path, '/api/v3/contents/generations/tasks')
        self.assertEqual(body['content'][0], {'type': 'text', 'text': 'Product'})

    def test_image_reference_contracts(self):
        p = {'model': 'image-01', 'prompt': 'Product', 'n': 1, 'ratio': '1:1', 'assets': [{'path': 'a.png'}]}
        path, body = build_image('minimax', p, self.ws)
        self.assertEqual(body['subject_reference'][0]['type'], 'character')
        p['model'] = 'gpt-image-2.5-flare'
        p['size'] = '1024x1024'
        path, body = build_image('openai', p, self.ws)
        self.assertEqual(path, '/v1/images/edits')
        self.assertEqual(len(body['images']), 1)
        self.assertNotIn('subject_reference', body)

    def test_youcloud_heartbeats_and_session(self):
        lines = ['{"result":{"session_id":"synthetic-session","answer_content":""}}',
                 '{"result":{"answer_content":"A"}}',
                 '{"result":{"answer_content":""}}',
                 '{"result":{"answer_content":"B"}}']
        self.assertEqual(parse_youcloud(lines), ('AB', 'synthetic-session'))

    def test_youcloud_partial_error_is_not_success(self):
        lines = ['{"result":{"session_id":"s","answer_content":"partial"}}',
                 '{"error":{"code":13,"message":"synthetic failure"}}']
        with self.assertRaises(CommerceError):
            parse_youcloud(lines)
        with self.assertRaises(CommerceError):
            parse_youcloud(['not json'])

    def test_h3_native_query_normalization(self):
        raw = {'task': {'id': 'synthetic', 'status': 'succeeded', 'content': {'url': 'https://example.com/a.mp4'}}}
        result = normalize_video('minimax', raw)
        self.assertEqual(result['state'], 'succeeded')
        self.assertEqual(result['artifacts'][0]['url'], 'https://example.com/a.mp4')

    def test_unknown_vendor_state_stays_unknown(self):
        result = normalize_video('seedance', {'id': 'synthetic', 'status': 'unexpected'})
        self.assertEqual(result['state'], 'unknown')

    def test_changing_briefing_is_not_fabricating_gmv(self):
        h = FakeHTTP([{'code': 0, 'data': {'access_token': 'synthetic'}},
                      {'code': 0, 'data': {'briefing': 'Synthetic category insight'}}])
        plan = {'id': 'a' * 32, 'request': {'provider': 'chanmama', 'operation': 'insight', 'params': {'product_name': 'Test', 'allow_token_refresh': True}}}
        r = dispatch(plan, self.ws, http=h, env={'CHANJING_APP_ID': 'test', 'CHANJING_SECRET_KEY': 'test'})
        self.assertEqual(r['state'], 'succeeded')
        self.assertEqual(r['report_kind'], 'category_briefing')
        self.assertNotIn('gmv', r)
        self.assertNotIn('access_token', str(r))

    def test_vendor_error_code_inside_http_200(self):
        h = FakeHTTP([{'code': 10016, 'msg': 'No balance'}])
        plan = {'id': 'b' * 32, 'request': {'provider': 'chanmama', 'operation': 'insight', 'params': {'product_name': 'Test'}}}
        with self.assertRaises(CommerceError):
            dispatch(plan, self.ws, http=h, env={'CHANJING_ACCESS_TOKEN': 'synthetic'})


if __name__ == '__main__':
    unittest.main()

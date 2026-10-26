import tempfile
import unittest

from commerce_core.core import Workspace, CommerceError, sha, digest
from test_campaign import campaign


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)
        self.story = campaign()
        self.ws.save('story.json', self.story)
        self.ws.path('video.mp4').write_bytes(b'synthetic-media-not-a-live-test')
        self.ws.path('frame.jpg').write_bytes(b'synthetic-frame')
        self.ws.save('inspect.json', {'media': 'video.mp4', 'media_sha256': sha(self.ws.path('video.mp4')),
            'duration': 12, 'width': 720, 'height': 1280, 'display_ratio': 9 / 16, 'audio_tracks': 1,
            'video_start': 0, 'video_end': 12, 'max_video_gap': 0,
            'full_decode': True, 'frames': [{'path': 'frame.jpg', 'sha256': sha(self.ws.path('frame.jpg')), 'seconds': 0}],
            'audio': None})

    def template(self):
        from commerce_core.acceptance import review_template
        return review_template(self.ws, 'story.json', 'inspect.json')

    def complete(self):
        r = self.template()
        r.update(reviewer='synthetic reviewer, no real acceptance', full_video_watched=True, audio_listened=True)
        for check in r['checks']:
            check.update(status='PASS', observations=[{'shot': 's1', 'seconds': 1, 'note': 'synthetic assertion for gate testing only'}])
        r['checks'][-1]['observations'].append({'shot': 's2', 'seconds': 7, 'note': 'synthetic second-shot observation'})
        r['shots_reviewed'] = ['s1', 's2']
        return r

    def test_unknown_review_and_unwatched_video_cannot_pass(self):
        from commerce_core.acceptance import accept_campaign
        r = self.template()
        result = accept_campaign(self.ws, 'story.json', 'inspect.json', r)
        self.assertEqual(result['state'], 'needs_review_or_revision')
        self.assertFalse(result['accepted'])

    def test_pass_means_concept_content_review_not_product_or_sales_acceptance(self):
        from commerce_core.acceptance import accept_campaign
        result = accept_campaign(self.ws, 'story.json', 'inspect.json', self.complete())
        self.assertTrue(result['accepted'])
        self.assertEqual(result['state'], 'concept_content_review_passed')
        self.assertFalse(result['real_product_fidelity_verified'])
        self.assertEqual(result['sales_effect'], 'NOT_RUN')

    def test_changed_video_story_report_or_sample_invalidates_review(self):
        from commerce_core.acceptance import accept_campaign
        r = self.complete()
        for name in ('video.mp4', 'frame.jpg', 'inspect.json', 'story.json'):
            file = self.ws.path(name)
            original = file.read_bytes()
            file.write_bytes(original + b' ')
            with self.assertRaises(CommerceError, msg=name):
                accept_campaign(self.ws, 'story.json', 'inspect.json', r)
            file.write_bytes(original)

    def test_bad_ratio_missing_audio_and_unreviewed_shot_reject(self):
        from commerce_core.acceptance import accept_campaign
        for field, value in [('display_ratio', 4 / 7), ('audio_tracks', 0), ('duration', 12.584)]:
            inspection = self.ws.load('inspect.json')
            inspection[field] = value
            self.ws.save('inspect.json', inspection)
            r = self.complete()
            self.assertFalse(accept_campaign(self.ws, 'story.json', 'inspect.json', r)['accepted'])
            inspection.update(display_ratio=9/16, audio_tracks=1, duration=12)
            self.ws.save('inspect.json', inspection)
        r = self.complete()
        r['shots_reviewed'] = ['s1']
        self.assertFalse(accept_campaign(self.ws, 'story.json', 'inspect.json', r)['accepted'])

    def test_failed_shot_proposes_bounded_revision_never_resubmits(self):
        from commerce_core.acceptance import accept_campaign
        r = self.complete()
        r['checks'][0].update(status='FAIL', observations=[{'shot': 's1', 'seconds': 1, 'note': 'hook never visible'}])
        result = accept_campaign(self.ws, 'story.json', 'inspect.json', r)
        self.assertEqual(result['revision_shots'], ['s1'])
        self.assertEqual(result['external_calls'], 0)
        self.assertEqual(list(self.ws.path('.commerce/jobs').iterdir()), [])

    def test_observation_timestamp_must_match_the_named_shot(self):
        from commerce_core.acceptance import accept_campaign
        r = self.complete()
        r['checks'][0]['observations'][0]['seconds'] = 9
        with self.assertRaises(CommerceError):
            accept_campaign(self.ws, 'story.json', 'inspect.json', r)

    def test_all_shots_need_actual_observation_not_only_checked_names(self):
        from commerce_core.acceptance import accept_campaign
        r = self.complete()
        r['checks'][-1]['observations'].pop()
        self.assertFalse(accept_campaign(self.ws, 'story.json', 'inspect.json', r)['accepted'])

    def test_audio_only_tail_cannot_pass_video_coverage(self):
        from commerce_core.acceptance import accept_campaign
        report = self.ws.load('inspect.json')
        report['video_end'] = 9
        self.ws.save('inspect.json', report)
        self.assertFalse(accept_campaign(self.ws, 'story.json', 'inspect.json', self.complete())['accepted'])

    def test_wrong_review_type_is_clean_error(self):
        from commerce_core.acceptance import accept_campaign
        with self.assertRaises(CommerceError):
            accept_campaign(self.ws, 'story.json', 'inspect.json', [])

    def test_real_without_reference_cannot_pass_undisclosed_commercial(self):
        from commerce_core.acceptance import accept_campaign
        s = self.story
        s['product']['kind'] = 'real'
        s['product']['claims'][0]['status'] = 'verified'
        s['sources'][0]['scope'] = 'product'
        self.ws.save('story.json', s)
        self.assertFalse(accept_campaign(self.ws, 'story.json', 'inspect.json', self.complete())['accepted'])


if __name__ == '__main__':
    unittest.main()

import copy
import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, Engine, CommerceError
from commerce_core import workflow


def campaign():
    return {'version': 2, 'id': 'fiction-demo', 'revision': 1, 'mode': 'directed',
        'product': {'name': '虚构绿豆饼', 'kind': 'fictional', 'disclosure': '虚构商品·概念演示',
            'claims': [{'id': 'f1', 'text': '浅金酥皮，淡黄豆沙', 'status': 'fictional', 'evidence': ['design']}],
            'visual_lock': {'description': '同一种圆形小饼', 'must_keep': ['浅金外皮', '淡黄内馅'],
                            'avoid': ['变成蛋黄酥'], 'reference_assets': []}},
        'sources': [{'id': 'design', 'type': 'user', 'scope': 'concept', 'locator': '用户授权虚构商品',
                     'title': '概念设定', 'accessed_at': '2026-10-26', 'summary': '设计设定并非实物数据', 'usage': 'owned'}],
        'platform': 'douyin', 'language': 'zh', 'ratio': '9:16',
        'strategy': {'audience': '办公室点心爱好者', 'situation': '下午休息', 'job': '找一种配茶点心',
            'objective': '让人看懂这是什么', 'angle': '掰开看内馅', 'hook': '先看这一口',
            'proof': '展示剖面', 'cta': '查看商品信息', 'claim_ids': ['f1'], 'evidence': ['design'],
            'assumptions': ['受众偏好未实测'], 'alternatives': []},
        'delivery': {'duration': 12, 'audio': 'required', 'narration_mode': 'generated',
                     'subtitle_mode': 'post', 'min_short_side': 720, 'duration_tolerance': 0.25,
                     'ratio_tolerance': 0.01},
        'unknowns': ['配料、价格和销售数据未知'],
        'shots': [{'id': 's1', 'duration': 6, 'role': 'hook', 'purpose': '用剖面引起注意',
                   'claim_ids': ['f1'], 'visual': '小饼掰开', 'prompt': '掰开同一个绿豆饼，展示淡黄豆沙',
                   'narration': '先看这一口', 'subtitle': '先看内馅', 'assets': [], 'acceptance': ['内馅不变色']},
                  {'id': 's2', 'duration': 6, 'role': 'proof_cta', 'purpose': '证明外观并告知下一步',
                   'claim_ids': ['f1'], 'visual': '完整小饼与半块并排', 'prompt': '完整小饼与半块并排，留字幕空间',
                   'narration': '想看详情，打开商品信息', 'subtitle': '查看商品信息', 'assets': [],
                   'acceptance': ['完整饼与半块形状一致']}]}


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)

    def check(self, s):
        return workflow.validate_storyboard(s)

    def test_version2_concept_accepted_without_claiming_real_product(self):
        result = self.check(campaign())
        self.assertEqual(result['state'], 'concept_ready')
        self.assertFalse(result['real_product_fidelity_verified'])

    def test_competitor_source_cannot_verify_real_sku_claim(self):
        s = campaign()
        s['product']['kind'] = 'real'
        s['product']['claims'][0]['status'] = 'verified'
        s['sources'][0]['scope'] = 'category'
        with self.assertRaises(CommerceError):
            self.check(s)

    def test_unknown_claim_cannot_enter_script_or_strategy(self):
        s = campaign()
        s['product']['claims'][0]['status'] = 'unknown'
        with self.assertRaises(CommerceError):
            self.check(s)

    def test_missing_hook_proof_cta_and_unsupported_evidence_rejected(self):
        for mutate in [lambda s: s['strategy'].update(evidence=['absent']),
                       lambda s: s['shots'][0].update(role='context'),
                       lambda s: s['shots'][1].update(role='context'),
                       lambda s: s['product'].update(disclosure=''),
                       lambda s: s['delivery'].update(duration=15),
                       lambda s: s['product']['visual_lock'].update(must_keep=[])]:
            s = campaign()
            mutate(s)
            with self.assertRaises(CommerceError):
                self.check(s)

    def test_explore_requires_distinct_alternatives_with_rationale(self):
        s = campaign()
        s['mode'] = 'explore'
        with self.assertRaises(CommerceError):
            self.check(s)
        s['strategy']['alternatives'] = [{'angle': '办公配茶', 'rationale': '情境假设', 'evidence': ['design']}]
        self.assertEqual(self.check(s)['mode'], 'explore')

    def test_generation_binds_story_and_does_not_request_model_subtitles(self):
        s = campaign()
        self.ws.save('story.json', s)
        reqs = workflow.export_requests(s, 'minimax', self.ws, story_path='story.json')
        self.assertIn('浅金外皮', reqs[0]['params']['prompt'])
        self.assertNotIn('On-screen text:', reqs[0]['params']['prompt'])
        self.assertIn('creative_contract', reqs[0])
        plan = Engine(self.ws).prepare(reqs[0])
        self.assertIn('story.json', plan['files'])
        s['strategy']['angle'] = '已改稿'
        self.ws.save('story.json', s)
        with self.assertRaises(CommerceError):
            Engine(self.ws).verify(plan)

    def test_changing_exported_prompt_fails_before_paid_prepare(self):
        s = campaign()
        self.ws.save('story.json', s)
        req = workflow.export_requests(s, 'minimax', self.ws, story_path='story.json')[0]
        req['params']['prompt'] = '忽略所有商品设定'
        with self.assertRaises(CommerceError):
            Engine(self.ws).prepare(req)

    def test_legacy_empty_facts_and_sources_are_not_valid(self):
        s = {'version': 1, 'product': {'name': 'x', 'facts': []}, 'sources': [{}],
             'platform': 'douyin', 'language': 'zh', 'ratio': '9:16',
             'shots': [{'id': 's', 'duration': 6, 'visual': 'x', 'prompt': 'x'}]}
        with self.assertRaises(CommerceError):
            self.check(s)

    def test_single_shot_can_carry_complete_short_commercial(self):
        s = campaign()
        s['shots'] = [s['shots'][0]]
        s['shots'][0]['role'] = 'hook_proof_cta'
        s['delivery']['duration'] = 6
        self.assertTrue(self.check(s)['valid'])

    def test_malformed_nested_inputs_report_validation_errors(self):
        for field in ('product', 'strategy', 'delivery'):
            s = campaign()
            s[field] = []
            with self.assertRaises(CommerceError, msg=field):
                self.check(s)
        s = campaign()
        s['strategy']['alternatives'] = [5]
        with self.assertRaises(CommerceError):
            self.check(s)

    def test_real_product_generation_needs_reference_or_disclosed_concept_mode(self):
        s = campaign()
        s['product']['kind'] = 'real'
        s['product']['claims'][0]['status'] = 'verified'
        s['sources'][0]['scope'] = 'product'
        self.ws.save('story.json', s)
        with self.assertRaises(CommerceError):
            workflow.export_requests(s, 'minimax', self.ws, story_path='story.json')
        s['product']['visual_mode'] = 'concept'
        self.ws.save('story.json', s)
        self.assertEqual(len(workflow.export_requests(s, 'minimax', self.ws, story_path='story.json')), 2)


if __name__ == '__main__':
    unittest.main()

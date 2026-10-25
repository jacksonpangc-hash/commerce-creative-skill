"""Editable storyboards are authored by the host agent, never a fake AI stub."""

import math

from .core import CommerceError
from .validation import require, validate_request


def validate_storyboard(story):
    require(isinstance(story, dict) and story.get('version') == 1, 'Storyboard version must be 1')
    product = story.get('product', {})
    require(bool(product.get('name')) and isinstance(product.get('facts'), list), 'Provide product name and real facts')
    require(all(isinstance(f, str) and f.strip() for f in product['facts']), 'Product facts must be nonempty strings')
    require(isinstance(story.get('sources'), list) and bool(story['sources']), 'Record the actual source(s)')
    require(bool(story.get('platform')) and bool(story.get('language')), 'Specify platform and language')
    shots = story.get('shots')
    require(isinstance(shots, list) and bool(shots), 'Storyboard must contain shots')
    seen = set()
    for shot in shots:
        require(isinstance(shot, dict), 'Each shot must be an object')
        require(isinstance(shot.get('id'), str) and shot['id'] and shot['id'] not in seen, 'Shot ids must be unique nonempty strings')
        seen.add(shot['id'])
        duration = shot.get('duration')
        require(isinstance(duration, int) and not isinstance(duration, bool) and 1 <= duration <= 120, 'Invalid shot duration')
        require(bool(shot.get('visual')) and bool(shot.get('prompt')), 'Shot needs visual and generation prompt')
        require(isinstance(shot.get('narration', ''), str) and isinstance(shot.get('subtitle', ''), str), 'Narration/subtitle must be strings')
    return {'valid': True, 'shot_count': len(shots), 'duration': sum(s['duration'] for s in shots)}


def export_requests(story, provider, ws, model=None, catalog_checked=False):
    validate_storyboard(story)
    result = []
    for shot in story['shots']:
        prompt = shot['prompt'] + '\nLanguage: ' + story['language']
        if shot.get('narration'):
            prompt += '\nNarration: ' + shot['narration']
        if shot.get('subtitle'):
            prompt += '\nOn-screen text: ' + shot['subtitle']
        p = {'prompt': prompt, 'duration': shot['duration'], 'ratio': story.get('ratio', '9:16'),
             'assets': shot.get('assets', [])}
        if model:
            p['model'] = model
        if provider == 'clipcat':
            p['catalog_checked'] = catalog_checked
        req = {'operation': 'video', 'provider': provider, 'params': p,
               'storyboard_shot': shot['id'], 'sources': story['sources']}
        validate_request(req, ws)
        result.append(req)
    return result


def context_prompt(product, report, language='zh', platform='douyin'):
    return {'task': 'Author an editable version-1 storyboard from this evidence; do not call paid tools.',
            'product': product, 'report': report, 'language': language, 'platform': platform,
            'output_fields': ['version', 'product', 'sources', 'platform', 'language', 'ratio', 'shots'],
            'shot_fields': ['id', 'duration', 'visual', 'narration', 'subtitle', 'prompt', 'assets'],
            'instructions': 'Preserve real product facts. Distinguish vendor insights from agent proposals. '
                            'Do not invent source metrics/timecodes. Fit each shot to the selected video model; '
                            'the user reviews the storyboard before generation.'}

"""Evidence-scoped commercial briefs. Host agents author meaning; code checks contracts."""
import copy
from datetime import date

from .core import digest, sha
from .validation import require, https_url


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, allow_empty=False):
    return isinstance(value, list) and (allow_empty or bool(value)) and all(text(v) for v in value)


def concept_mode(story):
    return story['product']['kind'] == 'fictional' or story['product'].get('visual_mode') == 'concept'


def real_reference(story):
    return any(a.get('origin') == 'real_product' for a in story['product']['visual_lock']['reference_assets'])


def check_campaign(story, ws=None):
    require(isinstance(story, dict) and story.get('version') == 2, 'Commercial storyboard version must be 2')
    require(text(story.get('id')) and type(story.get('revision')) is int and story['revision'] >= 1,
            'Campaign needs id and positive revision')
    require(story.get('mode') in {'directed', 'explore', 'inspire'}, 'Choose directed/explore/inspire')
    sources = story.get('sources')
    require(isinstance(sources, list) and sources, 'Evidence register is required')
    by_source = {}
    for source in sources:
        require(isinstance(source, dict) and text(source.get('id')) and source['id'] not in by_source,
                'Source ids must be unique')
        require(source.get('scope') in {'product', 'category', 'reference', 'concept'}, 'Declare evidence scope')
        require(source.get('type') in {'web', 'vendor', 'user', 'local'}, 'Declare source type')
        require(all(text(source.get(k)) for k in ('title', 'locator', 'summary', 'accessed_at')), 'Source needs locator, title, summary and date')
        try:
            date.fromisoformat(source['accessed_at'])
        except ValueError:
            require(False, 'Source date must use YYYY-MM-DD')
        if source['type'] == 'web':
            https_url(source['locator'])
        if source['type'] in {'local', 'vendor'}:
            require(source.get('sha256') and len(source['sha256']) == 64, 'Local/vendor evidence needs SHA256')
            if ws:
                require(sha(ws.input_path(source['locator'])) == source['sha256'], 'Evidence file changed')
        require(source.get('usage') in {'owned', 'licensed', 'reference_only', 'unknown'}, 'Record source usage rights')
        by_source[source['id']] = source

    def evidence(ids):
        require(strings(ids) and all(i in by_source for i in ids), 'Evidence ids must resolve to registered sources')

    product = story.get('product', {})
    require(isinstance(product, dict), 'Product must be an object')
    require(text(product.get('name')) and product.get('kind') in {'real', 'fictional'}, 'Declare real or fictional product')
    fictional = product['kind'] == 'fictional'
    require(product.get('visual_mode', 'reference') in {'reference', 'concept'}, 'Choose reference or concept visual mode')
    if concept_mode(story):
        require(text(product.get('disclosure')), 'Fictional concepts require visible disclosure')
    claims = product.get('claims')
    require(isinstance(claims, list) and claims, 'Record product claims, including known unknowns')
    by_claim = {}
    for claim in claims:
        require(isinstance(claim, dict) and text(claim.get('id')) and claim['id'] not in by_claim, 'Claim ids must be unique')
        require(text(claim.get('text')) and claim.get('status') in {'verified', 'fictional', 'unknown'}, 'Declare claim status')
        if claim['status'] != 'unknown':
            evidence(claim.get('evidence'))
            allowed = 'concept' if claim['status'] == 'fictional' else 'product'
            require(all(by_source[i]['scope'] == allowed for i in claim['evidence']), 'Category/competitor evidence cannot verify a SKU claim')
        require(claim['status'] != 'fictional' or fictional, 'Real products cannot use fictional claims')
        require(not fictional or claim['status'] != 'verified', 'Fictional SKU claims must remain fictional')
        by_claim[claim['id']] = claim

    def used_claims(ids, allow_empty=False):
        require(strings(ids, allow_empty) and all(i in by_claim and by_claim[i]['status'] != 'unknown' for i in ids),
                'Script and strategy may only use supported claims')

    lock = product.get('visual_lock', {})
    require(isinstance(lock, dict), 'Visual lock must be an object')
    require(text(lock.get('description')) and strings(lock.get('must_keep')) and strings(lock.get('avoid')), 'Define product visual identity and exclusions')
    refs = lock.get('reference_assets')
    require(isinstance(refs, list), 'Record reference assets, or [] when unavailable')
    for asset in refs:
        require(isinstance(asset, dict), 'Product reference must be an object')
        require(asset.get('kind', 'image') in {'image', 'video'} and asset.get('rights') in {'owned', 'licensed'}, 'Product reference needs image/video and upload rights')
        require(asset.get('origin') in {'real_product', 'concept'}, 'Distinguish physical product reference from concept art')
        require(('path' in asset) != ('url' in asset), 'Reference needs one path or URL')
        if ws and 'path' in asset:
            require(ws.input_path(asset['path']).is_file(), 'Product reference file is missing')
        if 'url' in asset:
            https_url(asset['url'])
    require(text(story.get('platform')) and text(story.get('language')), 'Choose platform and language')
    require(story.get('ratio') in {'9:16', '16:9', '1:1', '4:3', '3:4'}, 'Specify a fixed delivery ratio')
    strategy = story.get('strategy', {})
    require(isinstance(strategy, dict), 'Strategy must be an object')
    require(all(text(strategy.get(k)) for k in ('audience', 'situation', 'job', 'objective', 'angle', 'hook', 'proof', 'cta')), 'Complete audience, buying task, hook, proof and CTA')
    used_claims(strategy.get('claim_ids'))
    evidence(strategy.get('evidence'))
    require(strings(strategy.get('assumptions'), True) and strings(story.get('unknowns'), True), 'Keep assumptions and unknowns explicit')
    alternatives = strategy.get('alternatives')
    require(isinstance(alternatives, list), 'Record alternative creative angles')
    if story['mode'] != 'directed':
        require(bool(alternatives), 'Exploration/inspiration needs another angle to compare')
    angles = {strategy['angle'].strip()}
    for alternative in alternatives:
        require(isinstance(alternative, dict), 'Alternative must be an object')
        require(text(alternative.get('angle')) and alternative['angle'].strip() not in angles and text(alternative.get('rationale')),
                'Alternatives need distinct angles and a rationale')
        angles.add(alternative['angle'].strip())
        evidence(alternative.get('evidence'))
    delivery = story.get('delivery', {})
    require(isinstance(delivery, dict), 'Delivery must be an object')
    require(delivery.get('audio') in {'required', 'silent'}, 'Declare whether final audio is required')
    require(delivery.get('narration_mode') in {'generated', 'external', 'none'} and delivery.get('subtitle_mode') in {'post', 'generated', 'none'}, 'Declare narration and subtitle production method')
    require(type(delivery.get('min_short_side')) is int and delivery['min_short_side'] > 0, 'Set minimum delivered short side')
    for key, maximum in [('duration_tolerance', 2), ('ratio_tolerance', 0.05)]:
        value = delivery.get(key)
        require(type(value) in (int, float) and 0 <= value <= maximum, 'Set finite bounded ' + key)
    shots = story.get('shots')
    require(isinstance(shots, list) and shots, 'Provide editable shots')
    seen, roles, warnings = set(), set(), []
    for shot in shots:
        require(isinstance(shot, dict) and text(shot.get('id')) and shot['id'] not in seen, 'Shot ids must be unique')
        seen.add(shot['id'])
        require(type(shot.get('duration')) is int and 1 <= shot['duration'] <= 120, 'Invalid shot duration')
        require(shot.get('role') in {'hook', 'proof', 'context', 'cta', 'proof_cta', 'hook_proof_cta'}, 'Declare shot role')
        roles.add(shot['role'])
        require(all(text(shot.get(k)) for k in ('purpose', 'visual', 'prompt')) and strings(shot.get('acceptance')), 'Each shot needs purpose, visual proof and observable acceptance')
        used_claims(shot.get('claim_ids'), allow_empty=shot['role'] in {'context', 'cta'})
        for key in ('narration', 'subtitle'):
            require(isinstance(shot.get(key), str), 'Narration/subtitle must be explicit strings')
        if len(shot['narration']) > shot['duration'] * 5:
            warnings.append(shot['id'] + ': narration may be too dense; listen and time it')
        require(isinstance(shot.get('assets', []), list), 'Shot assets must be a list')
    require(shots[0]['role'] in {'hook', 'hook_proof_cta'} and bool(roles & {'proof', 'proof_cta', 'hook_proof_cta'}) and
            shots[-1]['role'] in {'cta', 'proof_cta', 'hook_proof_cta'}, 'Sequence must open with a hook, show proof and end with CTA')
    total = sum(s['duration'] for s in shots)
    require(type(delivery.get('duration')) is int and delivery['duration'] == total, 'Delivery duration must equal the editable timeline')
    return {'valid': True, 'state': 'concept_ready' if concept_mode(story) else ('brief_ready' if real_reference(story) else 'brief_needs_reference'),
            'mode': story['mode'], 'shot_count': len(shots), 'duration': total, 'warnings': warnings,
            'real_product_fidelity_verified': False, 'creative_acceptance': 'NOT_RUN',
            'evidence_authenticity': 'Agent must read sources; structural validation is not fact verification',
            'missing_real_reference': not real_reference(story)}


def campaign_requests(story, provider, ws, model=None, catalog_checked=False, story_path=None):
    from .workflow import export_requests
    check_campaign(story, ws)
    require(concept_mode(story) or real_reference(story), 'Real product generation needs an authorized reference of this SKU, or explicitly disclosed visual_mode=concept')
    legacy = {'version': 1, 'product': {'name': story['product']['name'], 'facts': [c['text'] for c in story['product']['claims'] if c['status'] != 'unknown']},
              'sources': [{'provider': s['type'], 'report': s['locator']} for s in story['sources']],
              'language': story['language'], 'platform': story['platform'], 'ratio': story['ratio'], 'shots': []}
    lock = story['product']['visual_lock']
    for shot in story['shots']:
        s = copy.deepcopy(shot)
        s['prompt'] += '\nProduct identity: ' + lock['description'] + '\nKeep: ' + '; '.join(lock['must_keep']) + '\nAvoid: ' + '; '.join(lock['avoid'])
        s['prompt'] += '\nShot purpose: ' + shot['purpose'] + '\nAcceptance: ' + '; '.join(shot['acceptance'])
        if concept_mode(story):
            s['prompt'] += '\nConcept visual, not verified real-product footage. Never invent a brand, sale or certification.'
        if story['delivery']['subtitle_mode'] != 'generated':
            s['subtitle'] = ''
            s['prompt'] += '\nNo generated captions, lettering or invented logos; text will be added in post.'
        if story['delivery']['narration_mode'] != 'generated':
            s['narration'] = ''
        # Explicit shot assets override common identity references (frame mode and reference mode cannot mix).
        if not s.get('assets'):
            s['assets'] = [{k: v for k, v in a.items() if k in {'path', 'url', 'kind', 'role'}} for a in lock['reference_assets']]
        legacy['shots'].append(s)
    requests = export_requests(legacy, provider, ws, model, catalog_checked)
    if story_path:
        require(digest(ws.load(story_path)) == digest(story), 'Export the saved storyboard, not an unsaved revision')
        for request, shot in zip(requests, story['shots']):
            request['creative_contract'] = {'file': str(ws.input_path(story_path).relative_to(ws.root)),
                'digest': digest(story), 'shot': shot['id'], 'model': model, 'catalog_checked': catalog_checked}
    return requests


def contract_files(req, ws):
    contract = req['creative_contract']
    require(isinstance(contract, dict), 'Creative contract must be an object')
    require(req['operation'] == 'video', 'Creative generation contract applies to video')
    file = ws.input_path(contract['file'])
    story = ws.load(contract['file'])
    require(digest(story) == contract['digest'], 'Storyboard changed; export and review again')
    candidates = campaign_requests(story, req['provider'], ws, contract.get('model'), contract.get('catalog_checked', False))
    expected = next((r for r in candidates if r['storyboard_shot'] == contract['shot']), None)
    require(expected is not None and req['params'] == expected['params'], 'Generation differs from the reviewed storyboard; edit the storyboard and re-export')
    return [file] + [ws.input_path(s['locator']) for s in story['sources'] if s['type'] in {'local', 'vendor'}]

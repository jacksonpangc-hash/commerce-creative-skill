"""Validation runs offline and never uploads or resolves a remote asset."""

import re
from urllib.parse import urlparse

from .core import CommerceError


def require(ok, message):
    if not ok:
        raise CommerceError(message)


def https_url(value):
    u = urlparse(str(value))
    require(u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password,
            'Use an HTTPS URL without embedded credentials')
    return value


def validate_request(req, ws):
    require(isinstance(req, dict), 'Request must be an object')
    op, provider, p = req.get('operation'), req.get('provider'), req.get('params', {})
    require(isinstance(p, dict), 'params must be an object')
    allowed = {'video': {'minimax', 'seedance', 'clipcat'},
               'image': {'minimax', 'seedream', 'openai'},
               'insight': {'chanmama', 'youcloud'},
               'publish': {'clipcat', 'sau'}, 'clipcat': {'clipcat'}, 'stage': {'presigned'}}
    require(op in allowed and provider in allowed[op], 'Unsupported operation/provider')
    req['params'] = p
    common_video = {'prompt', 'model', 'duration', 'resolution', 'ratio', 'assets'}
    params_allowed = {
        ('video', 'minimax'): common_video,
        ('video', 'seedance'): common_video | {'generate_audio'},
        ('video', 'clipcat'): common_video | {'catalog_checked'},
        ('image', 'minimax'): {'prompt', 'model', 'n', 'ratio', 'assets'},
        ('image', 'seedream'): {'prompt', 'model', 'n', 'size', 'assets', 'watermark'},
        ('image', 'openai'): {'prompt', 'model', 'n', 'size', 'quality', 'background', 'assets'},
        ('insight', 'chanmama'): {'product_name', 'creative_hint', 'top_product_count', 'top_category_count', 'awemes_per_category', 'allow_token_refresh'},
        ('insight', 'youcloud'): {'input', 'chat_mode', 'session_job'},
        ('publish', 'clipcat'): {'platform', 'account', 'title', 'privacy', 'kind', 'assets', 'schedule', 'text', 'tags'},
        ('publish', 'sau'): {'platform', 'account', 'title', 'kind', 'assets', 'schedule', 'text', 'tags'},
        ('clipcat', 'clipcat'): {'argv', 'query_type'},
        ('stage', 'presigned'): {'assets', 'put_url', 'read_url'},
    }
    require(set(p) <= params_allowed[(op, provider)], 'Unsupported parameters; no inputs are silently ignored: ' + ', '.join(sorted(set(p) - params_allowed[(op, provider)])))
    files, effects = [], {'network'}
    for asset in p.get('assets', []):
        require(isinstance(asset, dict), 'Each asset must be an object')
        require(('path' in asset) != ('url' in asset), 'Asset needs exactly one path or URL')
        require(asset.get('kind', 'image') in {'image', 'video', 'audio'}, 'Unknown asset kind')
        if 'path' in asset:
            f = ws.input_path(asset['path'])
            require(f.is_file(), 'Asset not found: ' + str(asset['path']))
            require(f.stat().st_size <= 200 * 1024 * 1024, 'Asset exceeds 200 MB; split it first')
            files.append(f)
        else:
            require(not str(asset['url']).startswith('clipcat://') or provider == 'clipcat',
                    'clipcat:// references are not portable to another provider')
            if not str(asset['url']).startswith('clipcat://'):
                https_url(asset['url'])
        effects.add('upload')
    if op in {'video', 'image'}:
        effects.add('paid')
        require(isinstance(p.get('prompt'), str) and p['prompt'].strip(), 'A prompt is required')
    if op == 'video':
        duration = p.get('duration')
        require(isinstance(duration, int) and not isinstance(duration, bool), 'duration must be integer seconds')
        max_duration = 30 if provider == 'seedance' else 15
        require(4 <= duration <= max_duration, 'Duration exceeds selected model; use storyboard segments')
        p.setdefault('ratio', '9:16')
        p.setdefault('resolution', '768P' if provider == 'minimax' else '720p')
        require(p['ratio'] in {'9:16', '16:9', '1:1', '4:3', '3:4', 'adaptive'}, 'Unsupported ratio')
        if provider == 'minimax':
            p.setdefault('model', ws.config['models']['minimax_video'])
            require(p['model'] == 'MiniMax-H3', 'The approved direct MiniMax model is MiniMax-H3')
            require(p['resolution'] in {'768P', '2K'}, 'H3 resolution must be 768P or 2K')
            limits = {'image': (9, 30), 'video': (3, 50), 'audio': (3, 15)}
            require(len(p.get('prompt', '')) <= 7000, 'H3 prompt exceeds 7000 characters')
        elif provider == 'seedance':
            p.setdefault('model', ws.config['models']['seedance'])
            require(str(p['model']).startswith('doubao-seedance-2-5-'), 'Direct Seedance adapter targets the approved 2.5 series')
            require(p['resolution'] in {'480p', '720p', '1080p'}, 'Unsupported Seedance resolution')
            limits = {'image': (30, 30), 'video': (10, 200), 'audio': (10, 15)}
            require(not any('path' in a and a.get('kind') == 'video' for a in p.get('assets', [])), 'Seedance reference videos need an HTTPS URL; stage the local file first')
        else:
            require(bool(p.get('model')), 'Clipcat model must come from live clipcat models --raw')
            require(bool(p.get('catalog_checked')), 'Verify Clipcat live catalog before selecting a model')
            limits = {}
        assets = p.get('assets', [])
        roles = [a.get('role', 'reference_' + a.get('kind', 'image')) for a in assets]
        require(not (any(r in {'first_frame', 'last_frame'} for r in roles) and
                     any(r.startswith('reference_') for r in roles)), 'Frame and reference modes cannot be mixed')
        for role in roles:
            require(role in {'first_frame', 'last_frame', 'reference_image', 'reference_video', 'reference_audio'}, 'Unknown asset role')
        for role in ('first_frame', 'last_frame'):
            require(roles.count(role) <= 1, 'Only one ' + role + ' is allowed')
        for kind, (count, size) in limits.items():
            subset = [a for a in assets if a.get('kind', 'image') == kind]
            require(len(subset) <= count, 'Too many ' + kind + ' assets')
            for a in subset:
                if 'path' in a:
                    require(ws.path(a['path']).stat().st_size <= size * 1024 * 1024, 'Asset exceeds provider size limit')
        for a, role in zip(assets, roles):
            require(role.endswith(a.get('kind', 'image')) or (role in {'first_frame', 'last_frame'} and a.get('kind', 'image') == 'image'), 'Asset role does not match kind')
    elif op == 'image':
        p.setdefault('model', ws.config['models'][{'minimax': 'minimax_image', 'openai': 'openai_image', 'seedream': 'seedream'}[provider]])
        require(all(a.get('kind', 'image') == 'image' for a in p.get('assets', [])), 'Image generation only accepts image assets')
        p.setdefault('n', 1)
        require(isinstance(p['n'], int) and not isinstance(p['n'], bool) and 1 <= p['n'] <= 10, 'n must be 1..10')
        maximum = {'minimax': 1, 'openai': 16, 'seedream': 10}[provider]
        require(len(p.get('assets', [])) <= maximum, 'Too many references for selected image model')
        if provider == 'minimax':
            require(p['model'] == 'image-01', 'MiniMax image adapter targets image-01')
            p.setdefault('ratio', '1:1')
        elif provider == 'seedream':
            require(str(p['model']).startswith('doubao-seedream-5-0-pro-'), 'Seedream adapter targets 5.0 pro')
            require(p['n'] == 1, 'This Seedream 5.0 pro adapter generates one image per request')
            p.setdefault('size', '2K')
        else:
            require(str(p['model']).startswith(('gpt-image-2.5-flare', 'gpt-image-2.5-sunburst')), 'Use a supported GPT Image 2.5 model')
            p.setdefault('size', '1024x1024')
    elif op == 'insight':
        effects.add('paid')
        require(not p.get('assets'), 'Insight endpoint does not accept local media; use a documented breakdown service')
        if provider == 'chanmama':
            if p.get('allow_token_refresh'):
                effects.add('token_refresh')
            require(isinstance(p.get('product_name'), str) and 1 <= len(p['product_name']) <= 200, 'product_name must contain 1..200 characters')
            require(len(p.get('creative_hint', '')) <= 500, 'creative_hint exceeds 500 characters')
            for k, maximum in [('top_product_count', 500), ('top_category_count', 50), ('awemes_per_category', 50)]:
                if k in p:
                    require(isinstance(p[k], int) and not isinstance(p[k], bool) and 1 <= p[k] <= maximum, k + ' out of range')
        else:
            require(bool(p.get('input')), 'YouCloud requires input')
            require(p.get('chat_mode', 2) in (2, 3), 'cmclaw chat_mode must be 2 or 3')
            require('session_id' not in p, 'Resume with session_job, not a cross-project raw session_id')
            if p.get('session_job'):
                prior = ws.read_job(p['session_job'])
                require(prior['provider'] == 'youcloud' and prior.get('session_id'), 'No YouCloud session in this project job')
                require(prior.get('project') == str(ws.root), 'YouCloud session belongs to another project')
                files.append(ws.input_path('.commerce/jobs/' + p['session_job'] + '.json'))
    elif op == 'publish':
        effects.update({'upload', 'publish'})
        require(bool(p.get('account')) and bool(p.get('title')), 'Publishing requires exact account and title')
        require(p.get('platform') in ({'douyin', 'kuaishou', 'xiaohongshu'} if provider == 'sau' else {'tiktok'}), 'Wrong publication platform/provider')
        require(p.get('kind', 'video') in {'video', 'note'}, 'Publish kind must be video or note')
        require(bool(p.get('assets')), 'Publishing needs reviewed local media')
        require(all('path' in a for a in p['assets']), 'Publish from project-local reviewed files')
        if p.get('schedule'):
            require(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', p['schedule'])), 'Schedule must use YYYY-MM-DD HH:MM in Asia/Shanghai')
            effects.add('schedule')
        if provider == 'clipcat':
            require(p.get('kind', 'video') == 'video' and len(p['assets']) == 1, 'TikTok adapter accepts one video')
            require(bool(p.get('privacy')), 'Explicit TikTok privacy is required')
        else:
            require(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', p.get('account', ''))), 'Use a project-local account alias')
        require(isinstance(p.get('tags', []), list) and all(isinstance(t, str) for t in p.get('tags', [])), 'tags must be a string list')
    elif op == 'stage':
        require(len(p.get('assets', [])) == 1 and 'path' in p['assets'][0], 'Stage exactly one local asset')
        https_url(p.get('put_url'))
        https_url(p.get('read_url'))
    elif op == 'clipcat':
        from .clipcat import inspect_argv
        extra_files, extra_effects = inspect_argv(p.get('argv'), ws)
        files.extend(extra_files)
        effects.update(extra_effects)
    return list(dict.fromkeys(files)), effects

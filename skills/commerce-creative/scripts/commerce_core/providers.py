"""Documented provider adapters, with injectable HTTP for offline contracts."""

import base64
import json
import mimetypes
import os
from urllib.parse import quote

from .core import CommerceError, digest, sha
from .http import HTTP


def credential(env, name):
    value = env.get(name)
    if not value:
        raise CommerceError('Missing credential environment variable: ' + name)
    return value


def asset_ref(asset, ws):
    if 'url' in asset:
        return asset['url']
    path = ws.dispatch_path(asset['path'])
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()


def build_video(provider, p, ws):
    body = {k: p[k] for k in ('model', 'duration', 'resolution', 'ratio')}
    content = [{'type': 'text', 'text': p['prompt']}]
    for a in p.get('assets', []):
        kind = a.get('kind', 'image')
        key = kind + '_url'
        content.append({'type': key, key: {'url': asset_ref(a, ws)},
                        'role': a.get('role', 'reference_' + kind)})
    body['content'] = content
    if provider == 'seedance':
        body['generate_audio'] = p.get('generate_audio', True)
        return '/api/v3/contents/generations/tasks', body
    return '/v2/video_generation', body


def build_image(provider, p, ws):
    refs = [asset_ref(a, ws) for a in p.get('assets', [])]
    if provider == 'minimax':
        body = {'model': p['model'], 'prompt': p['prompt'], 'n': p['n'],
                'aspect_ratio': p.get('ratio', '1:1'), 'response_format': 'base64',
                'prompt_optimizer': False}
        if refs:
            body['subject_reference'] = [{'type': 'character', 'image_file': refs[0]}]
        return '/v1/image_generation', body
    if provider == 'seedream':
        body = {'model': p['model'], 'prompt': p['prompt'], 'size': p.get('size', '2K'),
                'response_format': 'b64_json', 'watermark': p.get('watermark', True)}
        if refs:
            body['image'] = refs
        return '/api/v3/images/generations', body
    body = {'model': p['model'], 'prompt': p['prompt'], 'n': p['n'],
            'size': p.get('size', '1024x1024'), 'quality': p.get('quality', 'medium')}
    if p.get('background'):
        body['background'] = p['background']
    if refs:
        body['images'] = [{'image_url': ref} for ref in refs]
        return '/v1/images/edits', body
    return '/v1/images/generations', body


def parse_youcloud(lines):
    parts, session_id = [], ''
    try:
        for line in lines:
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or item.get('error') or not isinstance(item.get('result'), dict):
                raise CommerceError('YouCloud stream incomplete or business error')
            value = item['result']
            session_id = value.get('session_id') or session_id
            parts.append(value.get('answer_content') or '')
    except Exception as e:
        error = CommerceError('YouCloud stream interrupted; partial report is not complete')
        error.session_id = session_id
        error.partial_report = ''.join(parts)
        raise error from e
    if not session_id or not ''.join(parts).strip():
        error = CommerceError('YouCloud stream ended without a complete nonempty report/session')
        error.session_id = session_id
        error.partial_report = ''.join(parts)
        raise error
    return ''.join(parts), session_id


def normalize_video(provider, raw):
    task = raw.get('task', raw)
    state = str(task.get('status', 'unknown')).lower()
    states = {'queued': 'queued', 'running': 'running', 'processing': 'running',
              'succeeded': 'succeeded', 'success': 'succeeded', 'completed': 'succeeded',
              'failed': 'failed', 'cancelled': 'cancelled', 'expired': 'expired'}
    content = task.get('content') or {}
    url = content.get('url') if provider == 'minimax' else content.get('video_url')
    return {'state': states.get(state, 'unknown'), 'remote_id': task.get('id'),
            'artifacts': [{'url': url, 'kind': 'video'}] if url else [],
            'provider_status': state, 'usage': task.get('usage'), 'error': task.get('error')}


def _report(plan, ws, text, kind, **extra):
    name = '.commerce/reports/' + plan['id'] + '.md'
    target = ws.path(name)
    if target.exists():
        raise CommerceError('Report destination already exists')
    target.write_text(text, encoding='utf-8')
    return {'state': 'succeeded', 'report': name, 'report_kind': kind, **extra}


def preflight(plan, ws, env=None):
    env = os.environ if env is None else env
    req = plan['request']
    provider, op, p = req['provider'], req['operation'], req['params']
    if provider == 'clipcat':
        from .clipcat import executable
        executable(ws)
    elif provider == 'sau':
        from .publishing import build_sau_command, interpreter_path
        cmd, cwd = build_sau_command(p, ws)
        interpreter_path(ws, verify=True)
        if not ws.path(cmd[1]).is_file():
            raise CommerceError('Project-owned SAU runtime missing; see docs/PUBLISHING.md')
    elif provider in {'minimax', 'seedance', 'seedream', 'openai', 'youcloud'}:
        credential(env, {'minimax': 'MINIMAX_API_KEY', 'seedance': 'ARK_API_KEY',
                   'seedream': 'ARK_API_KEY', 'openai': 'OPENAI_API_KEY', 'youcloud': 'YOUCLOUD_API_KEY'}[provider])
    elif provider == 'chanmama' and not env.get('CHANJING_ACCESS_TOKEN'):
        if not p.get('allow_token_refresh'):
            raise CommerceError('Set CHANJING_ACCESS_TOKEN or explicitly authorize token refresh')
        credential(env, 'CHANJING_APP_ID')
        credential(env, 'CHANJING_SECRET_KEY')


def dispatch(plan, ws, http=None, env=None):
    http, env = http or HTTP(), os.environ if env is None else env
    req = plan['request']
    op, provider, p = req['operation'], req['provider'], req['params']
    if op == 'stage':
        path = ws.dispatch_path(p['assets'][0]['path'])
        http.put_file(p['put_url'], path)
        return {'state': 'uploaded_not_generated', 'artifacts': [{'url': p['read_url'],
                'kind': p['assets'][0].get('kind', 'image'), 'sha256': sha(path)}]}
    if provider == 'clipcat':
        from .clipcat import dispatch_clipcat
        return dispatch_clipcat(plan, ws)
    if op == 'publish':
        from .publishing import dispatch_sau
        return dispatch_sau(plan, ws)
    if op in {'video', 'image'}:
        key = {'minimax': 'MINIMAX_API_KEY', 'seedance': 'ARK_API_KEY',
               'seedream': 'ARK_API_KEY', 'openai': 'OPENAI_API_KEY'}[provider]
        headers = {'Authorization': 'Bearer ' + credential(env, key)}
        path, body = (build_video if op == 'video' else build_image)(provider, p, ws)
        raw = http.json(provider, path, body, headers=headers, timeout=180)
        if raw.get('error') or raw.get('base_resp', {}).get('status_code', 0) != 0:
            raise CommerceError('Generation API returned a business error')
        if op == 'video':
            remote = raw.get('task_id') if provider == 'minimax' else raw.get('id')
            if not remote:
                raise CommerceError('No generation task id returned')
            return {'state': 'submitted', 'remote_id': str(remote), 'model': p['model']}
        artifacts = []
        if provider == 'minimax':
            encoded = raw.get('data', {}).get('image_base64', [])
            urls = raw.get('data', {}).get('image_urls', [])
        else:
            encoded = [d['b64_json'] for d in raw.get('data', []) if d.get('b64_json')]
            urls = [d['url'] for d in raw.get('data', []) if d.get('url')]
        folder = ws.path('.commerce/outputs/' + plan['id'])
        folder.mkdir(exist_ok=True)
        for i, blob in enumerate(encoded):
            data = base64.b64decode(blob, validate=True)
            filename = 'image-' + str(i) + '.png'
            if data.startswith(b'\xff\xd8'):
                filename = 'image-' + str(i) + '.jpg'
            target = folder / filename
            with target.open('xb') as f:
                f.write(data)
            artifacts.append({'path': str(target.relative_to(ws.root)), 'kind': 'image'})
        artifacts.extend({'url': u, 'kind': 'image'} for u in urls)
        if not artifacts:
            raise CommerceError('Image API returned no images')
        failed = raw.get('metadata', {}).get('failed_count')
        partial = bool(failed) or len(artifacts) < p['n']
        return {'state': 'partial_success' if partial else 'succeeded', 'artifacts': artifacts,
                'requested_count': p['n'], 'returned_count': len(artifacts), 'usage': raw.get('usage'),
                'model': p['model'], 'partial_failure': failed}
    if provider == 'chanmama':
        token = env.get('CHANJING_ACCESS_TOKEN')
        if not token:
            # Refreshing invalidates prior tokens at the vendor; opt in explicitly.
            if not p.get('allow_token_refresh'):
                raise CommerceError('Set CHANJING_ACCESS_TOKEN or explicitly allow_token_refresh')
            auth = http.json(provider, '/open/v1/access_token', {
                'app_id': credential(env, 'CHANJING_APP_ID'),
                'secret_key': credential(env, 'CHANJING_SECRET_KEY')})
            if auth.get('code') != 0:
                raise CommerceError('Chanjing token request failed')
            token = auth.get('data', {}).get('access_token')
            if not token:
                raise CommerceError('No Chanjing access token returned')
        body = {k: p[k] for k in ('product_name', 'creative_hint', 'top_product_count',
                'top_category_count', 'awemes_per_category') if k in p}
        raw = http.json(provider, '/open/v1/creative/creative_briefing', body,
                        headers={'access_token': token}, timeout=120)
        if raw.get('code') != 0:
            raise CommerceError('Chanjing business error ' + str(raw.get('code')))
        text = raw.get('data', {}).get('briefing')
        if not text or not isinstance(text, str):
            raise CommerceError('No briefing returned')
        return _report(plan, ws, text, 'category_briefing', trace_id=raw.get('trace_id'),
                       provenance={'provider': 'chanmama', 'service': 'chanjing-creative-radar'})
    if provider == 'youcloud':
        headers = {'Authorization': 'YC_API_KEY ' + credential(env, 'YOUCLOUD_API_KEY')}
        identity = http.json(provider, '/api/rpc/user/v1/user/userInfo:get', headers=headers)
        user_id, team_id = int(identity['user_id']), str(identity['team_id'])
        body = {'input': p['input'], 'user_id': user_id, 'team_id': team_id}
        if p.get('session_job'):
            prior_path = ws.dispatch_path('.commerce/jobs/' + p['session_job'] + '.json')
            previous = json.loads(prior_path.read_text(encoding='utf-8'))
            if previous.get('project') != str(ws.root):
                raise CommerceError('YouCloud session belongs to another project')
            if previous.get('identity_digest') != digest([user_id, team_id]):
                raise CommerceError('YouCloud account/team changed; start a new session')
            body['session_id'] = previous['session_id']
        else:
            body['chat_mode'] = p.get('chat_mode', 2)
        lines = http.ndjson(provider, '/api/rpc/ai/claw/v1/chat', body,
                            headers=headers, timeout=650)
        try:
            text, session_id = parse_youcloud(lines)
        except CommerceError as e:
            e.identity_digest = digest([user_id, team_id])
            raise
        return _report(plan, ws, text, 'strategy_report', session_id=session_id,
                       identity_digest=digest([user_id, team_id]))
    raise CommerceError('Unsupported dispatch')


def refresh_job(ws, job_id, http=None, env=None):
    http, env = http or HTTP(), os.environ if env is None else env
    job = ws.read_job(job_id)
    remote = job.get('remote_id')
    if not remote:
        raise CommerceError('No remote task id; inspect vendor history before any new submission')
    provider = job['provider']
    if provider in {'minimax', 'seedance'} and job['operation'] == 'video':
        key = 'MINIMAX_API_KEY' if provider == 'minimax' else 'ARK_API_KEY'
        path = ('/v2/query/video_generation/' if provider == 'minimax'
                else '/api/v3/contents/generations/tasks/') + quote(str(remote), safe='')
        raw = http.json(provider, path, headers={'Authorization': 'Bearer ' + credential(env, key)})
        update = normalize_video(provider, raw)
        update['remote_id'] = remote
        job.update(update)
    elif provider == 'clipcat':
        from .clipcat import refresh_clipcat
        job.update(refresh_clipcat(ws, job))
    else:
        raise CommerceError('No automated remote status for this operation; inspect the original service record')
    ws.save('.commerce/jobs/' + job_id + '.json', job)
    return job

"""External CLI compatibility without redistributing Clipcat's client."""

import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .core import CommerceError, Engine, redact
from .validation import require


ROOTS = {'creator', 'product', 'seller', 'video', 'live', 'find', 'prompt',
         'breakdown', 'download', 'models', 'quote', 'character', 'asset',
         'list_tasks', 'list_images', 'query_task', 'tts', 'voice', 'tiktok', 'schedule'}
FILE_FLAGS = {'--image', '--video', '--file', '--prompt-file', '--first-frame', '--last-frame',
              '--ref-video', '--ref-audio', '--audio', '--cover', '--thumbnail'}
PATH_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.mp3', '.wav', '.m4a', '.txt', '.json'}


def normalized_argv(argv):
    result = []
    for arg in argv:
        if arg.startswith('--') and '=' in arg:
            result.extend(arg.split('=', 1))
        else:
            result.append(arg)
    return result


def executable(ws):
    name = ws.config['executables'].get('clipcat', 'clipcat')
    path = shutil.which(name)
    if not path and name == 'clipcat':
        local = Path.home() / '.local/bin/clipcat'
        path = str(local) if local.is_file() else None
    if not path:
        raise CommerceError('Original Clipcat CLI not found; install it separately or set executables.clipcat')
    return path


def inspect_argv(argv, ws):
    require(isinstance(argv, list) and bool(argv) and all(isinstance(a, str) and a for a in argv), 'Clipcat argv must be a nonempty string list')
    require(argv[0] in ROOTS, 'Use the original CLI directly for configuration, installation or bundled generation')
    argv = normalized_argv(argv)
    for a in argv:
        require(not a.startswith(('--api-key', '--base-url', '--confirm', '--output')), 'Credential, endpoint and confirmation overrides are not passthrough options')
    if argv[0] == 'tiktok':
        require(len(argv) > 1 and argv[1] in {'accounts', 'creator-info', 'tasks', 'task', 'connect-status'}, 'Use dedicated publish or explicit original CLI account setup')
    files, effects = [], {'network', 'paid'}
    if argv[0] == 'asset' and len(argv) > 1 and argv[1] == 'upload':
        require(len(argv) > 2, 'asset upload needs a project file')
        path = ws.input_path(argv[2])
        require(path.is_file(), 'Asset does not exist')
        files.append(path)
        effects.add('upload')
    if argv[0] == 'schedule':
        effects.add('schedule')
    if argv[0] in {'breakdown', 'character', 'voice'}:
        effects.add('upload')
    for i, arg in enumerate(argv):
        if arg in FILE_FLAGS and i + 1 < len(argv):
            require(argv[i + 1] != '-', 'Use a frozen project file, not stdin')
            if urlparse(argv[i + 1]).scheme in {'https', 'clipcat'}:
                effects.add('upload')
                continue
            path = ws.input_path(argv[i + 1])
            require(path.is_file(), 'CLI input file not found')
            files.append(path)
            effects.add('upload')
        elif not arg.startswith('-') and not urlparse(arg).scheme and (
                Path(arg).is_absolute() or arg.startswith(('~', './', '../')) or Path(arg).suffix.lower() in PATH_SUFFIXES
                or (ws.root / arg).is_file()):
            path = ws.input_path(arg)
            require(path.is_file(), 'Positional CLI input file not found')
            files.append(path)
            effects.add('upload')
    return files, effects


def build_clipcat_command(req, ws):
    op, p = req['operation'], req['params']
    base = [executable(ws)]
    if op == 'clipcat':
        args = normalized_argv(p['argv'])
        frozen = getattr(ws, '_dispatch_files', {})
        for i, arg in enumerate(args):
            if arg.startswith('-') or urlparse(arg).scheme:
                continue
            try:
                local = ws.input_path(arg)
                name = str(local.relative_to(ws.root))
            except CommerceError:
                continue
            if name in frozen:
                args[i] = str(frozen[name])
        return base + args + ['--output', 'json']
    if op == 'video':
        args = ['generate', '--model', p['model'], '--prompt', p['prompt'],
                '--duration', str(p['duration']), '--resolution', p['resolution'], '--size', p['ratio']]
        for a in p.get('assets', []):
            kind = a.get('kind', 'image')
            role = a.get('role', 'reference_' + kind)
            if kind == 'image':
                flag = {'first_frame': '--first-frame', 'last_frame': '--last-frame'}.get(role, '--image')
                if 'url' in a:
                    flag += '-url'
            else:
                flag = '--ref-' + kind
            args += [flag, str(ws.dispatch_path(a['path'])) if 'path' in a else a['url']]
        return base + args + ['--output', 'json']
    if op == 'publish':
        caption = p['title'] + ('\n' + p['text'] if p.get('text') else '')
        if p.get('tags'):
            caption += '\n' + ' '.join('#' + t.lstrip('#') for t in p['tags'])
        args = ['tiktok', 'publish', '--open-id', p['account'], '--video', str(ws.dispatch_path(p['assets'][0]['path'])),
                '--mode', 'direct', '--privacy', p['privacy'], '--title', caption]
        if p.get('schedule'):
            date = datetime.strptime(p['schedule'], '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('Asia/Shanghai'))
            args += ['--schedule', date.isoformat()]
        return base + args + ['--output', 'json']
    raise CommerceError('Unsupported Clipcat operation')


def run_json(command, ws, runner=subprocess.run):
    result = runner(command, cwd=ws.root, capture_output=True, text=True, timeout=180, shell=False)
    if result.returncode:
        raise CommerceError('Clipcat command failed (exit ' + str(result.returncode) + '); no automatic retry')
    try:
        raw = json.loads(result.stdout)
    except ValueError as e:
        raise CommerceError('Clipcat returned non-JSON output') from e
    if raw.get('success') is False or raw.get('error') or raw.get('errorCode'):
        raise CommerceError('Clipcat returned a service error')
    return raw.get('data', raw)


def dispatch_clipcat(plan, ws):
    req = plan['request']
    if req['operation'] == 'publish':
        # This call checks current account settings; it does not publish.
        run_json([executable(ws), 'tiktok', 'creator-info', '--open-id', req['params']['account'], '--output', 'json'], ws)
    raw = run_json(build_clipcat_command(req, ws), ws)
    if raw.get('confirmationRequired') and raw.get('confirmId'):
        return {'state': 'awaiting_provider_confirmation', 'server_confirm_id': raw['confirmId'],
                'confirmation': redact(raw.get('confirmation', raw)), 'remote_id': None}
    if req['operation'] in {'video', 'publish'}:
        raise CommerceError('Clipcat did not return the required confirmation snapshot')
    remote = raw.get('taskId') or raw.get('task_id')
    return {'state': 'submitted' if remote else 'succeeded', 'remote_id': remote,
            'result': redact(raw), 'query_type': req['params'].get('query_type')}


def confirm_clipcat(ws, job_id, confirmation, permissions, runner=subprocess.run):
    plan = ws.read_plan(job_id)
    Engine(ws).verify(plan)
    job = ws.read_job(job_id)
    require(job['provider'] == 'clipcat' and job['state'] == 'awaiting_provider_confirmation', 'No pending Clipcat confirmation')
    require(confirmation == job.get('server_confirm_id'), 'Confirm the exact server snapshot shown to the user')
    require(set(plan['effects']) - {'network'} <= set(permissions), 'Missing effect authorization')
    lock = ws.path('.commerce/locks/' + job_id + '.confirm')
    try:
        lock.mkdir()
    except FileExistsError as e:
        raise CommerceError('Confirmation already sent; inspect the original task') from e
    op = plan['request']['operation']
    prefix = ['generate'] if op == 'video' else ['tiktok', 'publish']
    job['state'] = 'dispatching'
    ws.save('.commerce/jobs/' + job_id + '.json', job)
    try:
        raw = run_json([executable(ws)] + prefix + ['--confirm', confirmation, '--output', 'json'], ws, runner)
        remote = raw.get('taskId') or raw.get('task_id')
        require(bool(remote), 'No task id after Clipcat confirmation')
        job.update(state='submitted', remote_id=remote, result=redact(raw))
    except Exception as e:
        job.update(state='submission_unknown', error=redact(str(e)))
    ws.save('.commerce/jobs/' + job_id + '.json', job)
    return job


def refresh_clipcat(ws, job):
    plan = ws.read_plan(job['id'])
    if job['operation'] == 'publish':
        args = ['tiktok', 'task', '--open-id', plan['request']['params']['account'], '--task-id', str(job['remote_id'])]
    else:
        kind = job.get('query_type') or ('raw' if job['operation'] == 'video' else None)
        require(bool(kind), 'Specify params.query_type for an asynchronous original Clipcat operation')
        args = ['query_task', '--task-id', str(job['remote_id']), '--type', kind]
    raw = run_json([executable(ws)] + args + ['--output', 'json'], ws)
    state = str(raw.get('status', raw.get('state', 'unknown'))).lower()
    recognized = {'queued', 'running', 'processing', 'completed', 'failed', 'scheduled', 'published', 'succeeded'}
    artifacts = []
    for video in raw.get('videos') or []:
        if isinstance(video, dict) and video.get('videoUrl'):
            artifacts.append({'url': video['videoUrl'], 'kind': 'video',
                              'provider_status': video.get('status')})
    # Retain prior local paths/checksums when rechecking an unchanged signed URL.
    prior = {a.get('url'): a for a in job.get('artifacts', []) if a.get('url')}
    artifacts = [{**a, **prior.get(a['url'], {})} for a in artifacts]
    result = {'state': state if state in recognized else 'unknown', 'result': redact(raw)}
    if artifacts:
        result['artifacts'] = artifacts
    return result

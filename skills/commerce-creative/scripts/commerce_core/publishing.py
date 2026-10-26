"""SAU runs from a dedicated project-owned checkout, never another project's cookies."""

import re
import subprocess
import os
from pathlib import Path

from .core import CommerceError, sha
from .validation import require


def interpreter_path(ws, verify=False):
    # Executable trust differs from media input scope. A venv may link to a base interpreter.
    value = Path(os.path.abspath(ws.root / ws.config['publisher']['python']))
    require(value.is_relative_to(ws.root), 'Publisher interpreter link must live inside this project')
    if verify:
        expected = ws.config['publisher'].get('interpreter_sha256')
        require(value.is_file() and bool(expected) and sha(value) == expected,
                'Publisher interpreter missing/changed; prepare the verified project runtime first')
        venv = value.parent.parent
        require((venv / 'pyvenv.cfg').is_file(), 'Publisher runtime must be the project-owned venv')
    return value


def build_sau_command(p, ws):
    require(p.get('platform') in {'douyin', 'kuaishou', 'xiaohongshu'}, 'Unsupported domestic platform')
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', p.get('account', ''))), 'Account must be a simple project-local alias')
    checkout = ws.path(ws.config['publisher']['checkout'])
    python = interpreter_path(ws)
    script = checkout / 'sau_cli.py'
    kind = p.get('kind', 'video')
    args = [str(python), str(script), p['platform'], 'upload-video' if kind == 'video' else 'upload-note',
            '--account', p['account'], '--title', p['title']]
    if kind == 'video':
        require(len(p['assets']) == 1, 'Publish video requires exactly one reviewed file')
        args += ['--file', str(ws.dispatch_path(p['assets'][0]['path'])), '--desc', p.get('text', '')]
    else:
        args += ['--images'] + [str(ws.dispatch_path(a['path'])) for a in p['assets']]
        args += ['--note', p.get('text', '')]
    if p.get('tags'):
        args += ['--tags', ','.join(p['tags'])]
    if p.get('schedule'):
        args += ['--schedule', p['schedule']]
    return args, checkout


def dispatch_sau(plan, ws, runner=subprocess.run):
    cmd, cwd = build_sau_command(plan['request']['params'], ws)
    interpreter_path(ws, verify=True)
    require(cwd.is_dir() and ws.path(cmd[1]).is_file(),
            'Project-owned SAU checkout/runtime missing; see docs/PUBLISHING.md')
    # SAU's zero exit is submission evidence, not proof a post is publicly visible.
    env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(ws.path('.commerce/browsers'))}
    env['PYTHONIOENCODING'] = 'utf-8'
    result = runner(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', timeout=900, shell=False, env=env)
    log_path = '.commerce/outputs/' + plan['id'] + '-publisher.txt'
    from .core import redact
    ws.path(log_path).write_text(redact(result.stdout + '\n' + result.stderr), encoding='utf-8')
    if result.returncode:
        return {'state': 'submission_unknown', 'log': log_path,
                'next_action': 'Inspect the original creator-center post; do not automatically re-upload'}
    return {'state': 'submitted_unverified', 'log': log_path,
            'scheduled_requested': bool(plan['request']['params'].get('schedule')),
            'next_action': 'Verify original post/account and platform schedule; submission is not publication acceptance'}

"""Project-local snapshots, authorization and durable job state."""

import copy
import hashlib
import json
import math
import os
import re
import time
import uuid
import shutil
from pathlib import Path


class CommerceError(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def no_credentials(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if re.search(r'(^|_)(api_key|secret|secret_key|access_token|authorization|cookie|password)$', k, re.I):
                raise CommerceError('Credentials belong in environment variables, not requests/config')
            no_credentials(v)
    elif isinstance(value, list):
        for item in value:
            no_credentials(item)


def redact(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if not isinstance(v, bool) and re.search(r'api.?key|secret|access.?token|authorization|cookie|password', k, re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for k, secret in os.environ.items():
            if re.search(r'KEY|SECRET|TOKEN|PASSWORD', k) and len(secret) >= 8:
                value = value.replace(secret, '[REDACTED]')
    return value


DEFAULT_CONFIG = {
    'version': 1,
    'defaults': {'video': 'minimax', 'image': 'seedream'},
    'executables': {'clipcat': 'clipcat'},
    'publisher': {'checkout': '.commerce/tools/social-auto-upload',
                  'python': '.commerce/tools/social-auto-upload/.venv/bin/python'},
    'models': {'minimax_video': 'MiniMax-H3', 'seedance': 'doubao-seedance-2-5-260628',
               'minimax_image': 'image-01', 'seedream': 'doubao-seedream-5-0-pro-260628',
               'openai_image': 'gpt-image-2.5-flare'},
}


class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.state = self.path('.commerce')
        if not self.path('.commerce/config.json').is_file():
            raise CommerceError('Project not initialized; run init --project PATH')
        self.config = self.load('.commerce/config.json')
        no_credentials(self.config)

    @classmethod
    def init(cls, root):
        root = Path(root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        state = root / '.commerce'
        if state.is_symlink():
            raise CommerceError('Project state must not be a symlink')
        state.mkdir(mode=0o700, exist_ok=True)
        config = state / 'config.json'
        if config.is_symlink():
            raise CommerceError('Config must not be a symlink')
        if not config.exists():
            fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        ws = cls(root)
        for name in ('plans', 'jobs', 'locks', 'outputs', 'reports'):
            ws.path('.commerce/' + name).mkdir(mode=0o700, exist_ok=True)
        return ws

    def path(self, value):
        p = (self.root / str(value)).resolve()
        if not p.is_relative_to(self.root):
            raise CommerceError('Path escapes project: ' + str(value))
        return p

    def load(self, value):
        try:
            return json.loads(self.path(value).read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            raise CommerceError('Cannot read project JSON: ' + str(value)) from e

    def input_path(self, value):
        candidate = Path(os.path.abspath(self.root / str(value)))
        try:
            parts = candidate.relative_to(self.root).parts
        except ValueError as e:
            raise CommerceError('Input escapes project') from e
        cursor = self.root
        for part in parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise CommerceError('Input symlinks are not supported; select the actual project file')
        return self.path(candidate)

    def dispatch_path(self, value):
        original = self.input_path(value)
        name = str(original.relative_to(self.root))
        return getattr(self, '_dispatch_files', {}).get(name, original)

    def freeze_inputs(self, plan):
        mapping = {}
        for name, expected in plan['files'].items():
            source = self.input_path(name)
            destination = self.path('.commerce/frozen/' + plan['id'] + '/' + name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            if sha(destination) != expected:
                raise CommerceError('Input changed during snapshot; prepare again')
            mapping[name] = destination
        self._dispatch_files = mapping

    def save(self, value, data):
        target = self.path(value)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(redact(data), f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)

    def save_config(self):
        no_credentials(self.config)
        self.save('.commerce/config.json', self.config)

    @staticmethod
    def check_id(value):
        if not re.fullmatch(r'[a-f0-9]{32}', value or ''):
            raise CommerceError('Invalid local plan/job id')
        return value

    def read_plan(self, value):
        return self.load('.commerce/plans/' + self.check_id(value) + '.json')

    def read_job(self, value):
        return self.load('.commerce/jobs/' + self.check_id(value) + '.json')


class Engine:
    def __init__(self, workspace, dispatch=None):
        self.ws = workspace
        self.uses_default_dispatch = dispatch is None
        if dispatch is None:
            from .providers import dispatch as default_dispatch
            dispatch = default_dispatch
        self.dispatch = dispatch

    def prepare(self, request):
        from .validation import validate_request
        request = copy.deepcopy(request)
        no_credentials(request)
        files, effects = validate_request(request, self.ws)
        cost = request.get('cost', {})
        if cost:
            estimate = cost.get('estimate')
            if isinstance(estimate, bool) or not isinstance(estimate, (int, float)) or not math.isfinite(estimate) or estimate < 0:
                raise CommerceError('cost.estimate must be a finite nonnegative number')
            if not cost.get('currency') or not cost.get('source'):
                raise CommerceError('A cost estimate needs currency and source')
        plan = {'id': uuid.uuid4().hex, 'version': 1, 'state': 'prepared',
                'created_at': time.time(), 'project': str(self.ws.root),
                'request': request, 'effects': sorted(effects),
                'files': {str(p.relative_to(self.ws.root)): sha(p) for p in files},
                'config_digest': digest(self.ws.load('.commerce/config.json')),
                'cost_status': 'ESTIMATE' if cost else 'UNKNOWN',
                'cost_note': 'Estimate only; provider billing is authoritative. No server-side hard cap implied.'}
        plan['snapshot_digest'] = digest(plan)
        self.ws.save('.commerce/plans/' + plan['id'] + '.json', plan)
        return plan

    def verify(self, plan):
        snapshot = {k: v for k, v in plan.items() if k != 'snapshot_digest'}
        if digest(snapshot) != plan['snapshot_digest']:
            raise CommerceError('Prepared snapshot changed; prepare again')
        if plan['project'] != str(self.ws.root):
            raise CommerceError('Prepared snapshot belongs to another project')
        if digest(self.ws.load('.commerce/config.json')) != plan['config_digest']:
            raise CommerceError('Project config changed; prepare again')
        for name, expected in plan['files'].items():
            p = self.ws.input_path(name)
            if not p.is_file() or sha(p) != expected:
                raise CommerceError('Input changed; prepare again: ' + name)

    def execute(self, plan_id, confirmation, permissions):
        plan = self.ws.read_plan(plan_id)
        if confirmation != plan_id:
            raise CommerceError('Confirm the exact prepared plan id')
        self.verify(plan)
        missing = set(plan['effects']) - set(permissions) - {'network'}
        if missing:
            raise CommerceError('Explicit authorization flags missing: ' + ', '.join(sorted(missing)))
        if 'paid' in plan['effects'] and not plan['request'].get('cost') and 'unknown_cost' not in permissions:
            raise CommerceError('Cost is UNKNOWN; provide a sourced estimate or explicitly accept unknown cost')
        if self.uses_default_dispatch:
            from .providers import preflight
            preflight(plan, self.ws)
        lock = self.ws.path('.commerce/locks/' + plan_id)
        if lock.exists():
            raise CommerceError('Already dispatched or uncertain: query the existing job; do not resubmit')
        self.ws.freeze_inputs(plan)
        try:
            lock.mkdir()
        except FileExistsError as e:
            raise CommerceError('Already dispatched or uncertain: query the existing job; do not resubmit') from e
        job = {'id': plan_id, 'provider': plan['request']['provider'],
               'operation': plan['request']['operation'], 'state': 'dispatching',
               'submitted_at': time.time(), 'project': str(self.ws.root),
               'config_digest': plan['config_digest'], 'remote_id': None}
        self.ws.save('.commerce/jobs/' + plan_id + '.json', job)
        try:
            result = self.dispatch(plan, self.ws)
            if not isinstance(result, dict) or not result.get('state'):
                raise CommerceError('Provider did not return a recognized result')
            job.update(redact(result))
        except Exception as e:
            # After dispatch may have started, a missing response never proves no task exists.
            job.update(state='submission_unknown', error=redact(str(e)),
                       next_action='Inspect provider history / original post before any new submission')
            if getattr(e, 'session_id', None):
                job['session_id'] = e.session_id
            if getattr(e, 'identity_digest', None):
                job['identity_digest'] = e.identity_digest
            if getattr(e, 'partial_report', None):
                name = '.commerce/reports/' + plan_id + '-incomplete.md'
                self.ws.path(name).write_text(redact(e.partial_report), encoding='utf-8')
                job['incomplete_report'] = name
        self.ws.save('.commerce/jobs/' + plan_id + '.json', job)
        return job

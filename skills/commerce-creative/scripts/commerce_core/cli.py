"""JSON CLI. Preparing is offline; execution always names an approval snapshot."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from . import __version__
from .core import CommerceError, Engine, Workspace, redact


def permissions(args):
    return {name for name in ('paid', 'upload', 'publish', 'schedule', 'token_refresh', 'unknown_cost')
            if getattr(args, 'allow_' + name, False)}


def permission_flags(parser):
    for name in ('paid', 'upload', 'publish', 'schedule', 'token_refresh', 'unknown_cost'):
        parser.add_argument('--allow-' + name.replace('_', '-'), action='store_true')


def doctor(ws):
    names = ['MINIMAX_API_KEY', 'ARK_API_KEY', 'OPENAI_API_KEY', 'CHANJING_ACCESS_TOKEN',
             'CHANJING_APP_ID', 'CHANJING_SECRET_KEY', 'YOUCLOUD_API_KEY']
    from .clipcat import executable
    try:
        clipcat = executable(ws)
    except CommerceError:
        clipcat = None
    return {'version': __version__, 'project': str(ws.root),
            'credentials_present': {n: bool(os.environ.get(n)) for n in names},
            'tools': {'clipcat': clipcat, 'ffmpeg': shutil.which('ffmpeg'), 'ffprobe': shutil.which('ffprobe'),
                      'sau_project_checkout': ws.path(ws.config['publisher']['checkout']).is_dir()},
            'live_acceptance': 'NOT_RUN', 'note': 'Presence is not authentication, quota or feature acceptance; no network calls performed'}


def parser():
    p = argparse.ArgumentParser(description='Commerce Creative: prepare → review → execute → inspect')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('init', 'doctor', 'prepare', 'show', 'execute', 'confirm-clipcat', 'status',
                 'download', 'context', 'storyboard-check', 'storyboard-export', 'compose'):
        s = sub.add_parser(name)
        s.add_argument('--project', required=True, help='Explicit project root; no cross-project history is read')
        if name in {'prepare', 'storyboard-check', 'storyboard-export'}:
            s.add_argument('file', help='JSON file inside project')
        if name in {'show', 'execute', 'confirm-clipcat', 'status', 'download'}:
            s.add_argument('id', help='Local plan/job id')
        if name in {'execute', 'confirm-clipcat'}:
            s.add_argument('--confirm', required=True)
            permission_flags(s)
        if name == 'status':
            s.add_argument('--refresh', action='store_true', help='Query the provider; otherwise read local state only')
        if name == 'context':
            s.add_argument('--product', required=True)
            s.add_argument('--report', required=True)
            s.add_argument('--platform', default='douyin')
            s.add_argument('--language', default='zh')
        if name == 'storyboard-export':
            s.add_argument('--provider', choices=['minimax', 'seedance', 'clipcat'], default='minimax')
            s.add_argument('--model')
            s.add_argument('--catalog-checked', action='store_true', help='Clipcat only: attest that live models --raw was inspected')
            s.add_argument('--out', required=True, help='New request directory inside project')
        if name == 'compose':
            s.add_argument('--files', nargs='+', required=True)
            s.add_argument('--out', required=True)
    return p


def run(args):
    if args.command == 'init':
        ws = Workspace.init(args.project)
        return {'state': 'initialized', 'project': str(ws.root), 'network_calls': 0}
    ws = Workspace(args.project)
    if args.command == 'doctor':
        return doctor(ws)
    if args.command == 'prepare':
        return Engine(ws).prepare(ws.load(args.file))
    if args.command == 'show':
        return ws.read_plan(args.id)
    if args.command == 'execute':
        return Engine(ws).execute(args.id, args.confirm, permissions(args))
    if args.command == 'confirm-clipcat':
        from .clipcat import confirm_clipcat
        return confirm_clipcat(ws, args.id, args.confirm, permissions(args))
    if args.command == 'status':
        if args.refresh:
            from .providers import refresh_job
            return refresh_job(ws, args.id)
        return ws.read_job(args.id)
    if args.command == 'download':
        from .media import download_job
        return download_job(ws, args.id)
    if args.command == 'context':
        from .workflow import context_prompt
        report = ws.path(args.report).read_text(encoding='utf-8')
        return context_prompt(ws.load(args.product), report, args.language, args.platform)
    if args.command == 'storyboard-check':
        from .workflow import validate_storyboard
        return validate_storyboard(ws.load(args.file))
    if args.command == 'storyboard-export':
        from .workflow import export_requests
        target = ws.path(args.out)
        if target.exists():
            raise CommerceError('Output directory exists; choose a new export directory')
        reqs = export_requests(ws.load(args.file), args.provider, ws, args.model, args.catalog_checked)
        target.mkdir(parents=True)
        files = []
        for i, req in enumerate(reqs):
            name = str((target / ('shot-' + str(i + 1) + '.json')).relative_to(ws.root))
            ws.save(name, req)
            files.append(name)
        return {'state': 'exported_not_submitted', 'requests': files}
    if args.command == 'compose':
        from .media import compose
        return compose(ws, args.files, args.out)
    raise CommerceError('Unknown command')


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = run(args)
        print(json.dumps(redact(result), ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (CommerceError, OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({'state': 'error', 'error': redact(str(e))}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

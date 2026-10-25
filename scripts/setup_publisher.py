#!/usr/bin/env python3
"""Optional project-owned SAU setup. No login, browser session or publishing."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/commerce-creative/scripts'))
from commerce_core.core import Workspace, CommerceError, sha

COMMIT = '3847fff01f5434a8a32829833163cd6723cabc59'


def setup(ws, browser=False, runner=subprocess.run):
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise CommerceError('Pinned SAU requires Python 3.10–3.12')
    if not shutil.which('git'):
        raise CommerceError('Git is required')
    checkout = ws.path(ws.config['publisher']['checkout'])
    if checkout.exists():
        raise CommerceError('SAU checkout exists; preserve customizations and inspect it before updating')
    checkout.parent.mkdir(parents=True, exist_ok=True)
    run = lambda argv, **kw: runner(argv, check=True, shell=False, **kw)
    run(['git', 'clone', '--no-checkout', 'https://github.com/dreammis/social-auto-upload.git', str(checkout)])
    run(['git', '-C', str(checkout), 'checkout', '--detach', COMMIT])
    venv = checkout / '.venv'
    run([sys.executable, '-m', 'venv', str(venv)])
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    run([str(python), '-m', 'pip', 'install', '--only-binary=:all:', '-e', str(checkout)])
    config = (checkout / 'conf.example.py').read_text(encoding='utf-8')
    (checkout / 'conf.py').write_text(config.replace('DEBUG_MODE = True', 'DEBUG_MODE = False'), encoding='utf-8')
    ws.config['publisher']['python'] = str(python.relative_to(ws.root))
    ws.config['publisher']['interpreter_sha256'] = sha(python)
    ws.save_config()
    if browser:
        env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(ws.path('.commerce/browsers'))}
        run([str(python), '-m', 'patchright', 'install', 'chromium'], env=env)
    return {'state': 'runtime_prepared_accounts_not_authorized', 'commit': COMMIT,
            'checkout': str(checkout), 'browser_downloaded': browser}


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser()
    p.add_argument('--project', required=True)
    p.add_argument('--allow-download', action='store_true', required=True)
    p.add_argument('--browser', action='store_true')
    a = p.parse_args()
    try:
        print(json.dumps(setup(Workspace(a.project), a.browser), indent=2))
    except (CommerceError, OSError, subprocess.SubprocessError) as e:
        raise SystemExit(str(e))

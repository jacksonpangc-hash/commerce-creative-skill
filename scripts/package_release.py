#!/usr/bin/env python3
"""Deterministic, source-only archive; never includes workspace/credential state."""
import argparse
import hashlib
import json
import zipfile
import re
from pathlib import Path

ROOT_FILES = {'README.md', 'README_ZH.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'pyproject.toml',
              'MANIFEST.in', '.env.example', '.gitignore', 'AGENTS.md', 'CHANGELOG.md',
              'CONTRIBUTING.md', 'SECURITY.md'}
ROOT_DIRS = {'skills', 'scripts', 'tests', 'docs', 'examples', '.github'}


def source_files(root):
    entries = json.loads((root / 'release-files.json').read_text(encoding='utf-8'))
    for name in sorted(entries):
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or any(x in {'__pycache__', '.commerce', '.venv', '.git', 'cookies', 'accounts'} for x in rel.parts):
            raise ValueError('Private/escaping release entry: ' + name)
        if rel.name.startswith('.env') and rel.name != '.env.example':
            raise ValueError('Environment credentials cannot be released')
        p = root / rel
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing/linked release entry: ' + name)
        text = p.read_text(encoding='utf-8')
        if re.search(r'/(?:Users|home)/[A-Za-z0-9_.-]+/', text):
            raise ValueError('Personal absolute path in release entry: ' + name)
        if p.suffix == '.json':
            check_json_secrets(json.loads(text))
        yield p


def check_json_secrets(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if re.search(r'api.?key|secret|access.?token|cookie|password|authorization', k, re.I) and v not in ('', None, False):
                raise ValueError('Potential credential field in release JSON')
            check_json_secrets(v)
    elif isinstance(value, list):
        for v in value:
            check_json_secrets(v)


def package(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'commerce-creative-skill-0.2.0.zip'
    manifest = output / 'source-manifest.json'
    if archive.exists() or manifest.exists():
        raise FileExistsError('Choose a new output directory; release files already exist')
    hashes = {}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in source_files(root):
            name = str(p.relative_to(root)).replace('\\', '/')
            data = p.read_bytes()
            info = zipfile.ZipInfo('commerce-creative-skill/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    manifest.write_text(json.dumps({'version': '0.2.0', 'files': hashes,
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2) + '\n', encoding='utf-8')
    return archive


if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='dist/source')
    args = p.parse_args()
    print(package(Path(__file__).resolve().parents[1], args.output))

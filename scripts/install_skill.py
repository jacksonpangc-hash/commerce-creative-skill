#!/usr/bin/env python3
"""Install one self-contained Skill; preserve existing installations by default."""
import argparse
import hashlib
import json
import shutil
import sys
import uuid
import os
from pathlib import Path


def install(repo, destination):
    repo, destination = Path(repo).resolve(), Path(destination).expanduser().resolve()
    source = repo / 'skills/commerce-creative'
    target = destination / 'commerce-creative'
    if target.exists() or target.is_symlink():
        raise FileExistsError('Destination exists; compare/back up local changes before upgrading: ' + str(target))
    if not (source / 'SKILL.md').is_file():
        raise FileNotFoundError('Skill source not found')
    entries = json.loads((source / 'skill-files.json').read_text())
    files = []
    for name in entries:
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or any(x in {'.env', '.commerce', 'cookies', 'accounts', '__pycache__'} for x in rel.parts):
            raise ValueError('Private or escaping install entry')
        file = source / rel
        if file.is_symlink() or not file.resolve().is_relative_to(source.resolve()) or not file.is_file():
            raise ValueError('Install entry is missing, linked or outside source: ' + name)
        cursor = source
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError('Linked install entry refused')
        files.append((name, file))
    destination.mkdir(parents=True, exist_ok=True)
    staging = destination / ('.commerce-creative-install-' + uuid.uuid4().hex)
    staging.mkdir()
    manifest = {'version': '0.1.0', 'python': sys.executable, 'files': {}}
    try:
        for name, file in files:
            copy = staging / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, copy)
            manifest['files'][name] = hashlib.sha256(copy.read_bytes()).hexdigest()
        (staging / 'installation-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if target.exists() or target.is_symlink():
            raise FileExistsError('Destination appeared during installation')
        os.rename(staging, target)
    except Exception:
        shutil.rmtree(staging)
        raise
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--destination', default=str(Path.home() / '.codex/skills'))
    args = p.parse_args()
    target = install(Path(__file__).resolve().parents[1], args.destination)
    print(json.dumps({'installed': str(target), 'original_clipcat_changed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()

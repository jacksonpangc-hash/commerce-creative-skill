"""Local artifact download and lossless segment assembly."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .core import CommerceError, sha
from .http import HTTP


def download_job(ws, job_id, http=None):
    http = http or HTTP()
    job = ws.read_job(job_id)
    folder = ws.path('.commerce/outputs/' + job_id)
    folder.mkdir(exist_ok=True)
    for index, artifact in enumerate(job.get('artifacts', [])):
        if artifact.get('path'):
            existing = ws.path(artifact['path'])
            if not existing.is_file() or (artifact.get('sha256') and sha(existing) != artifact['sha256']):
                raise CommerceError('Existing artifact changed or missing')
            continue
        if not artifact.get('url'):
            continue
        ext = '.mp4' if artifact.get('kind') == 'video' else '.image'
        target = folder / ('artifact-' + str(index) + ext)
        if target.exists():
            raise CommerceError('Artifact destination already exists; inspect before downloading again')
        http.download(artifact['url'], target)
        artifact.update(path=str(target.relative_to(ws.root)), sha256=sha(target))
        ws.save('.commerce/jobs/' + job_id + '.json', job)
    ws.save('.commerce/jobs/' + job_id + '.json', job)
    return job


def compose(ws, inputs, output, ffmpeg=None, ffprobe=None, runner=subprocess.run):
    target = ws.path(output)
    if target.exists():
        raise CommerceError('Output already exists; choose a new filename')
    if not inputs:
        raise CommerceError('Supply at least one local segment')
    files = [ws.path(p) for p in inputs]
    if not all(p.is_file() for p in files):
        raise CommerceError('A segment is missing')
    ffmpeg, ffprobe = ffmpeg or shutil.which('ffmpeg'), ffprobe or shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise CommerceError('FFmpeg and ffprobe are required for local composition; no files changed')
    signatures = []
    for file in files:
        r = runner([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', str(file)],
                   capture_output=True, text=True, encoding='utf-8', timeout=30, shell=False)
        if r.returncode:
            raise CommerceError('Cannot inspect video segment')
        streams = json.loads(r.stdout)['streams']
        signatures.append([{k: s.get(k) for k in ('codec_type', 'codec_name', 'width', 'height',
                           'pix_fmt', 'r_frame_rate', 'time_base', 'sample_rate', 'channels')}
                           for s in streams if s.get('codec_type') in {'video', 'audio'}])
    if any(s != signatures[0] for s in signatures):
        raise CommerceError('Segments differ in codec/size/audio; normalize explicitly before lossless composition')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ws.state) as tmp:
        listing = Path(tmp) / 'segments.txt'
        listing.write_text(''.join("file '" + str(f).replace("'", "'\\''") + "'\n" for f in files), encoding='utf-8')
        r = runner([ffmpeg, '-nostdin', '-n', '-v', 'error', '-f', 'concat', '-safe', '0',
                    '-protocol_whitelist', 'file,pipe', '-i', str(listing), '-c', 'copy',
                    '-movflags', '+faststart', str(target)], capture_output=True, text=True, encoding='utf-8',
                   timeout=300, shell=False)
    if r.returncode:
        target.unlink(missing_ok=True)
        raise CommerceError('Composition failed; original segments are unchanged')
    return {'state': 'assembled_not_creatively_reviewed', 'path': str(target.relative_to(ws.root)),
            'sha256': sha(target), 'segments': len(files)}

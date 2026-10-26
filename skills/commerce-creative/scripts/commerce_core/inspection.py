"""Optional local media tools. No upload, model invocation or modification of originals."""
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .core import CommerceError, sha, digest
from .validation import require


def dependencies():
    try:
        import av
        from PIL import Image
        import imageio_ffmpeg
        return av, Image, imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise CommerceError('Local media components missing: install commerce-creative-skill[media] into this project interpreter; no system changes required') from e


def media_format(path):
    with path.open('rb') as f:
        magic = f.read(64)
    # Never pass a playlist, concat script or URL to a demuxer that can open additional inputs.
    if magic[4:8] in {b'ftyp', b'moov', b'mdat', b'wide', b'free'}:
        return 'mov'
    if magic.startswith(b'\x1aE\xdf\xa3'):
        return 'matroska'
    if magic.startswith(b'RIFF') and magic[8:12] == b'AVI ':
        return 'avi'
    raise CommerceError('Use a local MP4/MOV, WebM/MKV or AVI video, not a playlist or disguised URL')


def open_video(path):
    av, _, _ = dependencies()
    try:
        return av.open(str(path), format=media_format(path), options={'protocol_whitelist': 'file', 'enable_drefs': '0'})
    except Exception as e:
        raise CommerceError('Cannot decode the selected local video') from e


def audio_format(path):
    with path.open('rb') as f:
        magic = f.read(32)
    if magic.startswith(b'RIFF') and magic[8:12] == b'WAVE':
        return 'wav'
    if magic.startswith(b'fLaC'):
        return 'flac'
    if magic.startswith(b'OggS'):
        return 'ogg'
    if magic.startswith(b'ID3') or (len(magic) >= 2 and magic[0] == 255 and magic[1] & 224 == 224):
        return 'mp3'
    if magic[4:8] == b'ftyp':
        return 'mov'
    raise CommerceError('Use a local WAV/MP3/FLAC/Ogg/M4A audio file, not a playlist')


def metadata(path):
    with open_video(path) as container:
        require(bool(container.streams.video), 'Video track missing')
        stream = container.streams.video[0]
        duration = float(container.duration or 0) / 1000000
        require(math.isfinite(duration) and 0 < duration <= 600, 'Local media supports videos up to 600 seconds; split longer input first')
        sar = float(stream.sample_aspect_ratio or 1)
        rotation = int(stream.metadata.get('rotate', '0')) % 360
        width, height = stream.width, stream.height
        start = end = previous_end = None
        max_gap, count = 0.0, 0
        fps = float(stream.average_rate or 0)
        for frame in container.decode(video=0):
            seconds = float(frame.time) if frame.time is not None else count / max(fps, 1)
            frame_seconds = float(frame.duration * frame.time_base) if getattr(frame, 'duration', 0) else 1 / max(fps, 1)
            if start is None:
                start = seconds
                rotation = int(getattr(frame, 'rotation', rotation)) % 360
            if previous_end is not None:
                max_gap = max(max_gap, seconds - previous_end)
            previous_end = seconds + frame_seconds
            end = max(end or previous_end, previous_end)
            count += 1
            require(count <= 180000, 'Decode limit exceeded')
        require(start is not None and end is not None and rotation in {0, 90, 180, 270}, 'Video timing or orientation could not be verified')
        ratio = width * sar / height
        if rotation in {90, 270}:
            ratio = 1 / ratio
        return {'duration': duration, 'width': width, 'height': height, 'sample_aspect_ratio': sar,
                'display_ratio': ratio, 'rotation': rotation, 'fps': fps,
                'video_start': start, 'video_end': end, 'video_duration': end - start, 'max_video_gap': max_gap,
                'video_codec': stream.codec_context.name, 'audio_tracks': len(container.streams.audio)}


def ffmpeg_run(argv, cwd=None):
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=900, shell=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CommerceError('Local media process could not complete; originals retained') from e
    if result.returncode:
        # Media paths and content are private. Do not print the process stderr wholesale.
        raise CommerceError('Local media processing failed; verify the selected codecs, audio and subtitle font support')


def inspect_media(ws, file, out, sample_count=24):
    _, _, ffmpeg = dependencies()
    require(type(sample_count) is int and 2 <= sample_count <= 120, 'Use 2..120 sampled frames')
    source, folder = ws.input_path(file), ws.path(out)
    require(source.is_file() and not folder.exists(), 'Input missing or inspection directory already exists')
    original_hash = sha(source)
    meta = metadata(source)
    folder.mkdir(parents=True)
    frames, decoded, last_frame = [], 0, None
    interval = meta['duration'] / (sample_count - 1)
    next_sample = 0.0

    def save_frame(frame, seconds):
        name = 'frame-' + str(len(frames) + 1).zfill(3) + '.jpg'
        target = folder / name
        image = frame.to_image()
        if meta['sample_aspect_ratio'] != 1:
            image = image.resize((max(1, round(image.width * meta['sample_aspect_ratio'])), image.height))
        if meta['rotation']:
            image = image.rotate(meta['rotation'], expand=True)
        image.thumbnail((1280, 1280))
        image.save(target, quality=90)
        frames.append({'seconds': round(seconds, 4), 'path': str(target.relative_to(ws.root)), 'sha256': sha(target)})

    try:
        with open_video(source) as container:
            for frame in container.decode(video=0):
                seconds = float(frame.time) if frame.time is not None else decoded / max(meta['fps'], 1)
                decoded += 1
                require(decoded <= 180000, 'Decode limit exceeded')
                if seconds + 0.00001 >= next_sample and len(frames) < sample_count - 1:
                    save_frame(frame, seconds)
                    next_sample += interval
                last_frame = (frame, seconds)
        require(decoded > 0 and last_frame is not None, 'Video contains no decodable frames')
        save_frame(*last_frame)
        audio = None
        if meta['audio_tracks']:
            target = folder / 'audio.wav'
            ffmpeg_run([ffmpeg, '-nostdin', '-n', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source),
                        '-map', '0:a:0', '-vn', '-c:a', 'pcm_s16le', '-ar', '24000', '-ac', '1', str(target)])
            audio = {'path': str(target.relative_to(ws.root)), 'sha256': sha(target), 'listened': False}
        require(sha(source) == original_hash, 'Source changed while inspecting; inspect again')
        report = {**meta, 'version': 1, 'media': str(source.relative_to(ws.root)), 'media_sha256': original_hash,
                  'full_decode': True, 'decoded_frames': decoded, 'frames': frames, 'audio': audio,
                  'visual_coverage': 'SAMPLED_FRAMES_ONLY', 'audio_acceptance': 'NOT_LISTENED',
                  'creative_acceptance': 'NOT_RUN'}
        report_path = str((folder / 'inspection.json').relative_to(ws.root))
        ws.save(report_path, report)
        return {**report, 'report': report_path}
    except Exception as e:
        # Owned incomplete output is retained for diagnosis, never mistaken for a successful report.
        ws.save(str((folder / 'incomplete.json').relative_to(ws.root)), {'state': 'inspection_failed', 'original_retained': True})
        if isinstance(e, CommerceError):
            raise
        raise CommerceError('Local decode failed; inspection incomplete, original retained') from e


def srt_time(seconds):
    milliseconds = round(seconds * 1000)
    return f'{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02},{milliseconds % 1000:03}'


def subtitles(story):
    from .campaign import concept_mode
    entries, offset = [], 0
    for shot in story['shots']:
        lines = []
        if story['delivery']['subtitle_mode'] == 'post' and shot['subtitle']:
            lines.append(shot['subtitle'])
        if concept_mode(story):
            lines.append(story['product']['disclosure'])
        if lines:
            entries.append(f"{len(entries)+1}\n{srt_time(offset)} --> {srt_time(offset+shot['duration'])}\n" + '\n'.join(lines) + '\n')
        offset += shot['duration']
    return '\n'.join(entries)


def render_media(ws, story, segments, out, voiceover=None, music=None, font_file=None):
    from .campaign import check_campaign, concept_mode, real_reference
    check_campaign(story, ws)
    require(concept_mode(story) or real_reference(story), 'Undisclosed real product rendering needs an authorized reference, or visual_mode=concept with disclosure')
    _, _, ffmpeg = dependencies()
    target = ws.path(out)
    require(target.suffix.lower() == '.mp4' and not target.exists(), 'Choose a new MP4 output')
    sidecar = target.with_suffix('.render.json')
    require(not sidecar.exists(), 'Render report already exists; choose a new output')
    require(set(segments) == {s['id'] for s in story['shots']}, 'Map exactly one local segment to every shot')
    require(story['delivery']['narration_mode'] != 'external' or voiceover, 'External narration requires the reviewed local voiceover')
    sources = [ws.input_path(segments[s['id']]) for s in story['shots']]
    extras = [ws.input_path(p) for p in (voiceover, music, font_file) if p]
    require(all(p.is_file() for p in sources + extras), 'A selected local media/font input is missing')
    require(story['delivery']['audio'] != 'silent' or not (voiceover or music), 'Silent delivery cannot silently ignore selected audio files')
    audio_formats = {name: audio_format(ws.input_path(name)) for name in (voiceover, music) if name}
    originals = {str(p.relative_to(ws.root)): sha(p) for p in sources + extras}
    metas = [metadata(p) for p in sources]
    for shot, meta in zip(story['shots'], metas):
        require(meta['video_start'] <= 0.05 and meta['video_end'] + 0.05 >= shot['duration'] and meta['max_video_gap'] <= 0.1,
                'Video frames do not cover the approved shot; audio length cannot justify freezing missing pictures')
        if story['delivery']['audio'] == 'required' and not voiceover and not music:
            require(meta['audio_tracks'] > 0, 'Required audio is missing; provide an authorized audio file')
    a, b = map(int, story['ratio'].split(':'))
    scale = math.ceil(story['delivery']['min_short_side'] / min(a, b) / 2) * 2
    width, height = a * scale, b * scale
    require(width * height <= 3840 * 2160, 'Requested output is too large; reduce delivered size')
    target.parent.mkdir(parents=True, exist_ok=True)
    subtitle_text = subtitles(story)
    with tempfile.TemporaryDirectory(dir=ws.state) as temp:
        temp = Path(temp)
        for index, (shot, source, meta) in enumerate(zip(story['shots'], sources, metas)):
            argv = [ffmpeg, '-nostdin', '-n', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source)]
            if not meta['audio_tracks']:
                argv += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
            if meta['display_ratio'] >= width / height:
                fit_width, fit_height = width, max(2, int(width / meta['display_ratio'] / 2) * 2)
            else:
                fit_width, fit_height = max(2, int(height * meta['display_ratio'] / 2) * 2), height
            argv += ['-map', '0:v:0', '-map', '0:a:0' if meta['audio_tracks'] else '1:a:0',
                '-vf', f'scale={fit_width}:{fit_height},setsar=1,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps=24',
                '-af', 'aresample=48000,apad', '-t', str(shot['duration']), '-c:v', 'libx264', '-preset', 'fast',
                '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(temp / f'{index}.mp4')]
            ffmpeg_run(argv)
        (temp / 'segments.txt').write_text(''.join(f"file '{i}.mp4'\n" for i in range(len(sources))))
        argv = [ffmpeg, '-nostdin', '-n', '-v', 'error', '-f', 'concat', '-safe', '1',
                '-protocol_whitelist', 'file,pipe', '-i', 'segments.txt']
        next_index = 1
        voice_index = music_index = None
        if voiceover:
            voice_index = next_index
            argv += ['-protocol_whitelist', 'file,pipe', '-f', audio_formats[voiceover], '-i', str(ws.input_path(voiceover))]
            next_index += 1
        if music:
            music_index = next_index
            argv += ['-stream_loop', '-1', '-protocol_whitelist', 'file,pipe', '-f', audio_formats[music], '-i', str(ws.input_path(music))]
        if subtitle_text:
            (temp / 'captions.srt').write_text(subtitle_text, encoding='utf-8')
            subtitle_filter = 'subtitles=captions.srt'
            if font_file:
                fonts = temp / 'fonts'
                fonts.mkdir()
                shutil.copyfile(ws.input_path(font_file), fonts / ('custom' + ws.input_path(font_file).suffix))
                subtitle_filter += ':fontsdir=fonts'
            argv += ['-vf', subtitle_filter]
        argv += ['-map', '0:v:0']
        if story['delivery']['audio'] == 'silent':
            argv += ['-an']
        elif music_index is not None:
            audio_input = voice_index if voice_index is not None else 0
            argv += ['-filter_complex', f'[{audio_input}:a:0]apad[voice];[{music_index}:a:0]volume=0.12[music];[voice][music]amix=inputs=2:duration=longest[a]', '-map', '[a]']
        else:
            argv += ['-map', f'{voice_index if voice_index is not None else 0}:a:0', '-af', 'apad']
        argv += ['-t', str(story['delivery']['duration']), '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                 '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', 'final.mp4']
        ffmpeg_run(argv, cwd=temp)
        for name, value in originals.items():
            require(sha(ws.input_path(name)) == value, 'Input changed during render; output not accepted')
        with (temp / 'final.mp4').open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
    report = {'state': 'rendered_not_creatively_reviewed', 'path': str(target.relative_to(ws.root)), 'sha256': sha(target),
              'story_digest': digest(story),
              'inputs': originals, 'transform': 'trim to approved timeline; scale and pad without cropping; 24fps H264/AAC; optional audio mix',
              'native_provider_output': False, 'width': width, 'height': height,
              'subtitles_burned': bool(subtitle_text), 'disclosure_burned': concept_mode(story),
              'font_review': 'NOT_RUN: inspect rendered Chinese glyphs and safe areas', 'creative_acceptance': 'NOT_RUN'}
    ws.save(str(sidecar.relative_to(ws.root)), report)
    return report

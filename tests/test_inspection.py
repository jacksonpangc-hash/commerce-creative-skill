import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, CommerceError
from test_campaign import campaign

HAS_MEDIA = all(importlib.util.find_spec(n) for n in ('av', 'PIL', 'imageio_ffmpeg'))


@unittest.skipUnless(HAS_MEDIA, 'Install project [media] extra for actual media tests')
class MediaTests(unittest.TestCase):
    def setUp(self):
        import imageio_ffmpeg
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)
        self.segment = self.ws.path('synthetic.mp4')
        subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
            'testsrc2=size=160x284:rate=12:duration=6', '-f', 'lavfi', '-i',
            'sine=frequency=440:duration=6', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
            '-shortest', str(self.segment)], check=True, capture_output=True)

    def test_actual_decode_extracts_frames_audio_and_preserves_original(self):
        from commerce_core.inspection import inspect_media
        before = self.segment.read_bytes()
        result = inspect_media(self.ws, 'synthetic.mp4', 'inspection', sample_count=6)
        self.assertTrue(result['full_decode'])
        self.assertEqual(result['width'], 160)
        self.assertGreater(result['decoded_frames'], 60)
        self.assertGreaterEqual(len(result['frames']), 6)
        self.assertTrue(self.ws.path(result['audio']['path']).is_file())
        self.assertEqual(before, self.segment.read_bytes())
        with self.assertRaises(CommerceError):
            inspect_media(self.ws, 'synthetic.mp4', 'inspection')

    def test_fake_video_and_network_playlist_rejected(self):
        from commerce_core.inspection import inspect_media
        self.ws.path('fake.mp4').write_text('#EXTM3U\nhttps://example.com/private')
        with self.assertRaises(CommerceError):
            inspect_media(self.ws, 'fake.mp4', 'bad')

    def test_render_produces_real_exact_ratio_with_subtitles_and_disclosure(self):
        from commerce_core.inspection import inspect_media, render_media
        story = campaign()
        story['delivery']['min_short_side'] = 144
        result = render_media(self.ws, story, {'s1': 'synthetic.mp4', 's2': 'synthetic.mp4'}, 'final.mp4')
        self.assertEqual(result['state'], 'rendered_not_creatively_reviewed')
        inspected = inspect_media(self.ws, 'final.mp4', 'final-inspect', sample_count=5)
        self.assertAlmostEqual(inspected['display_ratio'], 9 / 16, places=3)
        self.assertAlmostEqual(inspected['duration'], 12, delta=0.1)
        self.assertTrue(result['disclosure_burned'])
        self.assertTrue(result['subtitles_burned'])
        self.assertTrue(self.segment.is_file())
        with self.assertRaises(CommerceError):
            render_media(self.ws, story, {'s1': 'synthetic.mp4', 's2': 'synthetic.mp4'}, 'final.mp4')

    def test_existing_report_does_not_create_video_before_failing(self):
        from commerce_core.inspection import render_media
        self.ws.path('final.render.json').write_text('keep')
        with self.assertRaises(CommerceError):
            render_media(self.ws, campaign(), {'s1': 'synthetic.mp4', 's2': 'synthetic.mp4'}, 'final.mp4')
        self.assertFalse(self.ws.path('final.mp4').exists())

    def test_voiceover_cannot_be_a_disguised_network_playlist(self):
        from commerce_core.inspection import render_media
        self.ws.path('voice.wav').write_text('#EXTM3U\nhttps://example.com/x')
        with self.assertRaises(CommerceError):
            render_media(self.ws, campaign(), {'s1': 'synthetic.mp4', 's2': 'synthetic.mp4'}, 'final.mp4', voiceover='voice.wav')

    def test_long_audio_does_not_make_short_video_a_complete_shot(self):
        from commerce_core.inspection import metadata, render_media
        target = self.ws.path('short-picture.mp4')
        subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
            'testsrc2=size=160x284:rate=12:duration=3', '-f', 'lavfi', '-i',
            'sine=frequency=440:duration=6', '-c:v', 'libx264', '-c:a', 'aac', str(target)],
            check=True, capture_output=True)
        meta = metadata(target)
        self.assertAlmostEqual(meta['video_end'], 3, delta=0.1)
        story = campaign()
        story['delivery']['min_short_side'] = 144
        with self.assertRaises(CommerceError):
            render_media(self.ws, story, {'s1': 'short-picture.mp4', 's2': 'short-picture.mp4'}, 'bad.mp4')

    def test_display_matrix_rotation_controls_metadata_and_sampled_frame(self):
        from commerce_core.inspection import inspect_media
        from PIL import Image
        landscape = self.ws.path('landscape.mp4')
        subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-i', str(self.segment),
            '-vf', 'scale=284:160,setsar=1', '-c:v', 'libx264', '-c:a', 'copy', str(landscape)], check=True, capture_output=True)
        rotated = self.ws.path('rotated.mp4')
        subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-display_rotation:v:0', '90', '-i',
            str(landscape), '-c', 'copy', str(rotated)], check=True, capture_output=True)
        report = inspect_media(self.ws, 'rotated.mp4', 'rotated-inspection', 3)
        self.assertAlmostEqual(report['display_ratio'], 160 / 284, places=3)
        with Image.open(self.ws.path(report['frames'][0]['path'])) as image:
            self.assertGreater(image.height, image.width)

    def test_nonsquare_pixels_keep_display_shape_when_rendered(self):
        from commerce_core.inspection import render_media, open_video
        target = self.ws.path('anamorphic.mp4')
        subprocess.run([self.ffmpeg, '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
            'color=red:size=160x160:rate=12:duration=6', '-i', str(self.segment), '-vf', 'setsar=2',
            '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-c:a', 'copy', '-shortest', str(target)], check=True, capture_output=True)
        story = campaign()
        story['ratio'] = '16:9'
        story['delivery']['min_short_side'] = 144
        render_media(self.ws, story, {'s1': 'anamorphic.mp4', 's2': 'anamorphic.mp4'}, 'shape.mp4')
        with open_video(self.ws.path('shape.mp4')) as container:
            image = next(container.decode(video=0)).to_image()
        from PIL import ImageChops
        red, green, _ = image.split()
        mask = ImageChops.multiply(red.point(lambda n: 255 if n > 128 else 0), green.point(lambda n: 255 if n < 90 else 0))
        left, top, right, bottom = mask.getbbox()
        self.assertAlmostEqual((right-left)/(bottom-top), 2, delta=0.08)


if __name__ == '__main__':
    unittest.main()

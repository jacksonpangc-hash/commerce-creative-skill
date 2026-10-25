import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from commerce_core.core import Workspace, Engine, CommerceError, redact
from commerce_core.clipcat import inspect_argv, confirm_clipcat, refresh_clipcat
from commerce_core.media import download_job
from commerce_core.providers import parse_youcloud, dispatch
from commerce_core.publishing import build_sau_command
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Workspace.init(self.tmp.name)

    def mod(self, name):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
        obj = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obj)
        return obj

    def test_symlink_inputs_rejected_before_prepare(self):
        (self.ws.root / 'a.png').write_bytes(b'a')
        try:
            (self.ws.root / 'selected.png').symlink_to('a.png')
        except OSError:
            self.skipTest('Symlink creation unavailable on this platform')
        with self.assertRaises(CommerceError):
            Engine(self.ws).prepare({'operation':'video', 'provider':'minimax', 'params': {
                'prompt':'Test', 'duration':6, 'assets':[{'path':'selected.png'}]}})

    def test_equal_form_and_positional_file_escape_rejected(self):
        for argv in [['character', 'create', '--image=/outside-project/private.png'],
                     ['voice', 'clone', '/outside-project/voice.wav']]:
            with self.assertRaises(CommerceError):
                inspect_argv(argv, self.ws)

    def test_schedule_is_a_separate_effect(self):
        (self.ws.root / 'v.mp4').write_bytes(b'synthetic')
        e = Engine(self.ws, dispatch=lambda *_: {'state':'submitted_unverified'})
        p = e.prepare({'operation':'publish','provider':'sau','params':{
            'platform':'douyin','account':'test','title':'Test','schedule':'2026-12-01 14:00',
            'assets':[{'path':'v.mp4','kind':'video'}]}})
        self.assertIn('schedule', p['effects'])
        with self.assertRaises(CommerceError):
            e.execute(p['id'],p['id'],{'publish','upload'})

    def test_youcloud_malformed_and_timeout_keep_session_and_partial(self):
        def interrupted():
            yield '{"result":{"session_id":"synthetic","answer_content":"partial"}}'
            raise TimeoutError('synthetic timeout')
        for lines in [['{"result":{"session_id":"synthetic","answer_content":"partial"}}','bad json'], interrupted()]:
            with self.assertRaises(CommerceError) as ctx:
                parse_youcloud(lines)
            self.assertEqual(ctx.exception.session_id,'synthetic')
            self.assertEqual(ctx.exception.partial_report,'partial')

    def test_interrupted_youcloud_job_keeps_identity_for_resume(self):
        class Fake:
            def json(self,*a,**k): return {'user_id':'123','team_id':'synthetic-team'}
            def ndjson(self,*a,**k): return iter(['{"result":{"session_id":"s","answer_content":"partial"}}','{"error":{"code":13}}'])
        plan={'id':'d'*32,'request':{'operation':'insight','provider':'youcloud','params':{'input':'Test'}}}
        with self.assertRaises(CommerceError) as ctx:
            dispatch(plan,self.ws,http=Fake(),env={'YOUCLOUD_API_KEY':'synthetic'})
        self.assertTrue(ctx.exception.identity_digest)

    def test_download_resumes_after_second_artifact_failure(self):
        jid='e'*32
        self.ws.save('.commerce/jobs/'+jid+'.json',{'id':jid,'state':'succeeded', 'artifacts':[
            {'url':'https://example.com/1.mp4','kind':'video'}, {'url':'https://example.com/2.mp4','kind':'video'}]})
        class Fake:
            calls=[]
            def download(inner,url,target):
                inner.calls.append(url)
                if url.endswith('2.mp4') and inner.calls.count(url)==1: raise TimeoutError('synthetic')
                target.write_bytes(b'synthetic-media')
        fake=Fake()
        with self.assertRaises(TimeoutError): download_job(self.ws,jid,fake)
        result=download_job(self.ws,jid,fake)
        self.assertEqual(fake.calls.count('https://example.com/1.mp4'),1)
        self.assertTrue(all(a.get('path') for a in result['artifacts']))

    def test_installer_does_not_copy_unknown_private_files(self):
        mod=self.mod('install_skill')
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source'; skill=source/'skills/commerce-creative'
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('public')
            (skill/'skill-files.json').write_text(json.dumps(['SKILL.md','skill-files.json']))
            (skill/'.env').write_text('DO_NOT_COPY=synthetic-private')
            target=mod.install(source,Path(d)/'target')
            self.assertFalse((target/'.env').exists())

    def test_release_uses_audited_manifest_not_all_json(self):
        mod=self.mod('package_release')
        with tempfile.TemporaryDirectory() as d:
            source=Path(d); (source/'docs').mkdir()
            (source/'README.md').write_text('public')
            (source/'docs/private-account.json').write_text('{"access_token":"synthetic-private"}')
            (source/'release-files.json').write_text(json.dumps(['README.md','release-files.json']))
            self.assertNotIn(source/'docs/private-account.json',list(mod.source_files(source)))

    def test_doctor_presence_boolean_is_not_redacted(self):
        r=redact({'credentials_present':{'MINIMAX_API_KEY':False,'ARK_API_KEY':True}})
        self.assertIs(r['credentials_present']['MINIMAX_API_KEY'],False)
        self.assertIs(r['credentials_present']['ARK_API_KEY'],True)

    def test_session_job_is_part_of_approval_snapshot(self):
        jid='f'*32
        self.ws.save('.commerce/jobs/'+jid+'.json',{'id':jid,'provider':'youcloud','project':str(self.ws.root), 'session_id':'s','identity_digest':'x'})
        e=Engine(self.ws,dispatch=lambda *_:{'state':'succeeded'})
        p=e.prepare({'operation':'insight','provider':'youcloud','params':{'input':'Test','session_job':jid}})
        self.ws.save('.commerce/jobs/'+jid+'.json',{'id':jid,'provider':'youcloud','project':str(self.ws.root), 'session_id':'changed','identity_digest':'x'})
        with self.assertRaisesRegex(CommerceError,'changed'):
            e.execute(p['id'],p['id'],{'paid','unknown_cost'})

    def test_sau_setup_records_interpreter_fingerprint(self):
        mod=self.mod('setup_publisher')
        calls=[]
        checkout=self.ws.path(self.ws.config['publisher']['checkout'])
        def fake(argv,**kw):
            calls.append(argv)
            if 'clone' in argv:
                checkout.mkdir()
                (checkout/'conf.example.py').write_text('DEBUG_MODE = True\n')
                (checkout/'sau_cli.py').write_text('')
            if 'venv' in argv:
                v=Path(argv[-1]); (v/'bin').mkdir(parents=True)
                (v/'Scripts').mkdir(exist_ok=True)
                (v/('Scripts/python.exe' if os.name=='nt' else 'bin/python')).write_bytes(b'synthetic-interpreter')
                (v/'pyvenv.cfg').write_text('home = synthetic\n')
            return SimpleNamespace(returncode=0)
        mod.setup(self.ws,runner=fake)
        venv_call=next(c for c in calls if 'venv' in c)
        self.assertNotIn('--copies',venv_call)
        self.assertEqual(len(self.ws.config['publisher']['interpreter_sha256']),64)

    def test_clipcat_server_confirmation_is_single_use_and_scheduled(self):
        self.ws.config['executables']['clipcat']=sys.executable
        self.ws.save_config()
        (self.ws.root/'v.mp4').write_bytes(b'synthetic')
        e=Engine(self.ws,dispatch=lambda *_:{'state':'awaiting_provider_confirmation','server_confirm_id':'cfm_synthetic'})
        p=e.prepare({'operation':'publish','provider':'clipcat','params':{
            'platform':'tiktok','account':'synthetic-open-id','title':'Test','privacy':'SELF_ONLY',
            'schedule':'2026-12-01 14:00','assets':[{'path':'v.mp4','kind':'video'}]}})
        e.execute(p['id'],p['id'],{'publish','upload','schedule'})
        calls=[]
        def fake(argv,**kw):
            calls.append(argv)
            return SimpleNamespace(returncode=0,stdout='{"data":{"taskId":"synthetic-task"}}')
        with self.assertRaises(CommerceError):
            confirm_clipcat(self.ws,p['id'],'cfm_synthetic',{'publish','upload'},fake)
        result=confirm_clipcat(self.ws,p['id'],'cfm_synthetic',{'publish','upload','schedule'},fake)
        self.assertEqual(result['state'],'submitted')
        self.assertEqual(len(calls),1)
        with self.assertRaises(CommerceError):
            confirm_clipcat(self.ws,p['id'],'cfm_synthetic',{'publish','upload','schedule'},fake)

    def test_dispatch_reads_frozen_approved_bytes(self):
        original=self.ws.root/'p.png'; original.write_bytes(b'approved-bytes')
        seen=[]
        def dispatch_after_edit(plan,ws):
            original.write_bytes(b'changed-after-validation')
            seen.append(ws.dispatch_path('p.png').read_bytes())
            return {'state':'submitted'}
        e=Engine(self.ws,dispatch=dispatch_after_edit)
        p=e.prepare({'operation':'video','provider':'minimax','params':{
            'prompt':'Test','duration':6,'assets':[{'path':'p.png'}]}})
        e.execute(p['id'],p['id'],{'paid','upload','unknown_cost'})
        self.assertEqual(seen,[b'approved-bytes'])

    def test_installer_rejects_manifest_symlink(self):
        mod=self.mod('install_skill')
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source'; skill=source/'skills/commerce-creative'; skill.mkdir(parents=True)
            outside=Path(d)/'private.txt'; outside.write_text('synthetic-private')
            try: (skill/'SKILL.md').symlink_to(outside)
            except OSError: self.skipTest('Symlink creation unavailable')
            (skill/'skill-files.json').write_text('["SKILL.md"]')
            with self.assertRaises(ValueError): mod.install(source,Path(d)/'target')

    def test_release_rejects_credential_even_if_listed(self):
        mod=self.mod('package_release')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'account.json').write_text('{"access_token":"synthetic-private"}')
            (root/'release-files.json').write_text('["account.json"]')
            with self.assertRaises(ValueError): list(mod.source_files(root))

    def test_empty_youcloud_report_keeps_existing_session(self):
        with self.assertRaises(CommerceError) as ctx:
            parse_youcloud(['{"result":{"session_id":"synthetic","answer_content":""}}'])
        self.assertEqual(ctx.exception.session_id, 'synthetic')
        self.assertEqual(ctx.exception.partial_report, '')

    def test_clipcat_refresh_exposes_downloadable_video(self):
        jid = '9' * 32
        self.ws.config['executables']['clipcat'] = sys.executable
        self.ws.save('.commerce/plans/' + jid + '.json', {'request': {'params': {}}})
        raw = {'status': 'completed', 'videos': [{'videoUrl': 'https://example.com/final.mp4',
                                                'status': 'completed'}]}
        with patch('commerce_core.clipcat.run_json', return_value=raw):
            result = refresh_clipcat(self.ws, {'id': jid, 'operation': 'video', 'remote_id': 'task'})
        self.assertEqual(result['artifacts'][0]['url'], 'https://example.com/final.mp4')

    def test_image_partial_success_is_explicit(self):
        class Fake:
            def json(self, *a, **k):
                return {'data': [{'url': 'https://example.com/one.png'}],
                        'metadata': {'failed_count': 1}}
        plan = {'id': '8' * 32, 'request': {'operation': 'image', 'provider': 'openai',
                 'params': {'model': 'gpt-image-2.5-flare', 'prompt': 'Test', 'n': 2}}}
        result = dispatch(plan, self.ws, http=Fake(), env={'OPENAI_API_KEY': 'synthetic'})
        self.assertEqual(result['state'], 'partial_success')
        self.assertEqual(result['requested_count'], 2)
        self.assertEqual(result['returned_count'], 1)

    def test_extensionless_existing_clipcat_input_is_fingerprinted(self):
        (self.ws.root / 'reference').write_bytes(b'synthetic')
        files, effects = inspect_argv(['breakdown', 'reference'], self.ws)
        self.assertIn(self.ws.root / 'reference', files)
        self.assertIn('upload', effects)


if __name__=='__main__': unittest.main()

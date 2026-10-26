import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_real_source_archive_handles_chinese_paths_under_non_utf8_locale(self):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, 'LC_ALL': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0'}
            result = subprocess.run([sys.executable, str(REPO / 'scripts/package_release.py'), '--output', d],
                cwd=REPO, env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(d) / 'commerce-creative-skill-0.2.0.zip').is_file())
    def module(self, name):
        spec = importlib.util.spec_from_file_location(name, REPO / 'scripts' / (name + '.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_installer_never_overwrites_existing_skill(self):
        install = self.module('install_skill')
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'commerce-creative'
            target.mkdir()
            (target / 'custom.txt').write_text('keep')
            with self.assertRaises(FileExistsError):
                install.install(REPO, Path(d))
            self.assertEqual((target / 'custom.txt').read_text(), 'keep')

    def test_installed_skill_is_self_contained(self):
        install = self.module('install_skill')
        with tempfile.TemporaryDirectory() as d:
            target = install.install(REPO, Path(d))
            self.assertTrue((target / 'SKILL.md').is_file())
            self.assertTrue((target / 'scripts/commerce_core/cli.py').is_file())
            self.assertFalse(any(target.rglob('__pycache__')))
            self.assertTrue((target / 'installation-manifest.json').is_file())

    def test_release_excludes_private_state(self):
        package = self.module('package_release')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text('public')
            (root / '.env').write_text('SECRET')
            (root / '.commerce').mkdir()
            (root / '.commerce/private.json').write_text('private')
            (root / 'skills/test').mkdir(parents=True)
            (root / 'skills/test/SKILL.md').write_text('public')
            (root / 'release-files.json').write_text('["README.md","skills/test/SKILL.md","release-files.json"]')
            files = [str(p.relative_to(root)) for p in package.source_files(root)]
            self.assertIn('README.md', files)
            self.assertNotIn('.env', files)
            self.assertNotIn('.commerce/private.json', files)

    def test_sdist_manifest_includes_skill_install_manifest(self):
        # The installer must work from the source tarball as well as the Git checkout.
        rules = (REPO / 'MANIFEST.in').read_text(encoding='utf-8').splitlines()
        entries = json.loads((REPO / 'release-files.json').read_text(encoding='utf-8'))
        for name in entries:
            self.assertIn('include ' + name, rules)

    def test_every_skill_install_file_is_public_source(self):
        public = set(json.loads((REPO / 'release-files.json').read_text(encoding='utf-8')))
        install = json.loads((REPO / 'skills/commerce-creative/skill-files.json').read_text(encoding='utf-8'))
        for name in install:
            self.assertIn('skills/commerce-creative/' + name, public)
            self.assertFalse(any(part.endswith('.egg-info') for part in Path(name).parts))


if __name__ == '__main__':
    unittest.main()

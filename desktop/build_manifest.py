"""Record the artifact identity and exact source/dependencies used for a build."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from can_relax.version import APP_NAME, VERSION


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def git_output(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    report = json.loads((ROOT / 'dist/desktop-self-test.json').read_text(encoding='utf-8'))
    if not report['ok'] or report['version'] != VERSION or report['app_name'] != APP_NAME:
        raise RuntimeError('Self-test report does not match this release.')
    installer = ROOT / f'dist/VitriFit_Setup_{VERSION}_x64.exe'
    sources = sorted([*ROOT.glob('can_relax/**/*.py'), *ROOT.glob('desktop/*.py'),
                      *ROOT.glob('desktop/*.ps1'), *ROOT.glob('desktop/*.iss'),
                      *ROOT.glob('desktop/*.spec'), ROOT / 'LICENSE'])
    manifest = {
        'name': APP_NAME, 'version': VERSION, 'git_commit_at_build': git_output('rev-parse', 'HEAD'),
        'working_tree_dirty_at_build': bool(git_output('status', '--porcelain', '--untracked-files=no')),
        'python': platform.python_version(), 'platform': platform.platform(),
        'source_sha256': {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        'dependencies': dict(sorted((d.metadata['Name'], d.version) for d in metadata.distributions())),
        'self_test': report,
        'artifacts': {},
    }
    for path in (ROOT / 'dist/VitriFit/VitriFit.exe', installer):
        if path.exists():
            manifest['artifacts'][path.name] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    (ROOT / 'dist/release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

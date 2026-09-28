"""Build a portable skill ZIP from an explicit allowlist; no virtualenv or user data."""
# SPDX-License-Identifier: Apache-2.0
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ('.meta.json', 'SKILL.md', 'requirements.txt', 'LICENSE', 'NOTICE',
              'UPSTREAM.md', 'README.md', 'README_en.md', 'CHANGELOG.md',
              'CONTRIBUTING.md', 'SECURITY.md', 'CITATION.cff')


def build(root=ROOT):
    root = Path(root)
    for name in ('scripts', 'references'):
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f'Missing or symlinked release directory: {directory}')
    files = [root / name for name in ROOT_FILES]
    files += sorted((root / 'scripts').glob('*.py'))
    files += sorted((root / 'references').glob('*.md'))
    files += [root / name for name in ('docs/PUBLISHING.md',
               'docs/source-integration-v3.8.0.md', 'docs/source-integration-v3.9.0.md')]
    # Include environment setup and build tooling so the archive is self-contained.
    files += [root / 'tools/build_release.py', root / 'tools/setup_env.py']
    for path in files:
        if not path.is_file():
            raise ValueError(f'Missing or symlinked release input: {path}')
        current = path
        while current != root:
            if current.is_symlink():
                raise ValueError(f'Symlinked release input: {current}')
            current = current.parent
    output = root / 'dist'
    if output.is_symlink():
        raise ValueError('dist must not be a symlink')
    output.mkdir(exist_ok=True)
    archive = output / 'china-market-data.zip'
    checksum = output / 'china-market-data.zip.sha256'
    if archive.is_symlink() or checksum.is_symlink():
        raise ValueError('Release outputs must not be symlinks')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            info = zipfile.ZipInfo('china-market-data/' + path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f'{digest}  {archive.name}\n')
    print(f'{archive}\n{checksum}\n{len(files)} files')
    return archive


if __name__ == '__main__':
    build()

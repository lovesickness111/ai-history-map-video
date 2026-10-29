"""Install a verified Blender portable and the OFL-licensed Vietnamese font."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def download(url,path):
    print(f'Download: {url}',flush=True)
    request=urllib.request.Request(url,headers={'User-Agent':'HanoiProceduralPipeline/1.0'})
    with urllib.request.urlopen(request,timeout=120) as source, path.open('wb') as target:
        while chunk:=source.read(1024*1024):
            target.write(chunk)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='4.5.15')
    args=parser.parse_args()
    if not re.fullmatch(r'4\.5\.\d+',args.version):
        parser.error('Use a Blender 4.5 LTS patch version')
    tools=ROOT/'tools'
    tools.mkdir(exist_ok=True)
    name=f'blender-{args.version}-windows-x64'
    binary=tools/name/'blender.exe'
    if not binary.is_file():
        archive=tools/f'{name}.zip'
        hashes=tools/f'blender-{args.version}.sha256'
        base='https://download.blender.org/release/Blender4.5/'
        download(base+hashes.name,hashes)
        entries=[line.split() for line in hashes.read_text().splitlines()]
        expected=next(parts[0] for parts in entries if parts[-1].lstrip('*')==archive.name)
        actual=None
        if archive.is_file():
            with archive.open('rb') as handle:
                actual=hashlib.file_digest(handle,'sha256').hexdigest()
        if actual!=expected:
            download(base+archive.name,archive)
        with archive.open('rb') as handle:
            actual=hashlib.file_digest(handle,'sha256').hexdigest()
        if actual!=expected:
            raise RuntimeError('Blender archive checksum mismatch')
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                resolved=(tools/item.filename).resolve()
                if not resolved.is_relative_to(tools.resolve()):
                    raise RuntimeError('Unsafe archive member')
            bundle.extractall(tools)
    font_dir=ROOT/'assets'/'fonts'
    font_dir.mkdir(parents=True,exist_ok=True)
    base='https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/'
    for filename in ('BeVietnamPro-Bold.ttf','OFL.txt'):
        path=font_dir/filename
        if not path.is_file():
            download(base+filename,path)
    print(f'Ready: {binary}',flush=True)


if __name__=='__main__':
    main()

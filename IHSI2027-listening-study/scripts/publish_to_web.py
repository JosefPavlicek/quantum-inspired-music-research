#!/usr/bin/env python3
"""Publish validated IHSI full-corpus audio to the Vite web app.

Run from anywhere. Copies or transcodes audio and writes corpus.json atomically.
No generation occurs in a browser or during a Vercel build.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
STUDY = HERE.parent.parent
CONDITIONS = ('human', 'baseline', 'guided')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--full', type=Path, default=STUDY/'experiments/full_corpus')
    p.add_argument('--web', type=Path, default=STUDY/'web')
    p.add_argument('--format', choices=('mp3', 'wav'), default='mp3')
    p.add_argument('--bitrate', default='192k')
    p.add_argument('--allow-publication', action='store_true', help='Explicit acknowledgement that excerpt distribution rights have been cleared')
    args = p.parse_args()
    if not args.allow_publication:
        p.error('Publication blocked: review HookTheory excerpt distribution rights, then explicitly pass --allow-publication. For local testing use the existing WAV files.')
    manifest_path = args.full/'manifest.json'
    if not manifest_path.is_file(): p.error(f'Missing {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    clips = manifest.get('clips', [])
    if not clips: p.error('No clips in full_corpus manifest')
    if args.format == 'mp3' and not shutil.which('ffmpeg'): p.error('ffmpeg not installed: sudo apt-get install -y ffmpeg')
    out = args.web/'public'/'audio'
    prepared = []
    for item in clips:
        cid = item['clip_id']
        if not cid.startswith('clip_') or '/' in cid or '..' in cid: p.error(f'Invalid clip ID: {cid}')
        files = {}
        for condition in CONDITIONS:
            src = args.full/cid/f'{condition}_piano.wav'
            if not src.is_file() or src.stat().st_size < 1024: p.error(f'Missing or empty audio: {src}')
            digest = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
            filename = f'{digest}.{args.format}'
            dest = out/cid/filename
            files[condition] = (src, dest, f'/audio/{cid}/{filename}')
        prepared.append((cid, files))
    published=[]
    for cid, files in prepared:
        urls={}
        for condition, (src,dest,url) in files.items():
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():
                if args.format == 'wav': shutil.copy2(src,dest)
                else:
                    temp=dest.with_name(dest.name+'.tmp.mp3')
                    try:
                        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(src),'-vn','-codec:a','libmp3lame','-b:a',args.bitrate,str(temp)],check=True)
                        temp.replace(dest)
                    finally: temp.unlink(missing_ok=True)
            urls[condition]=url
        published.append({'id':cid,'audio':urls})
        print(f'{cid}: published {len(urls)} conditions')
    public_manifest={'schema_version':1,'clips':published}
    dest=args.web/'public'/'corpus.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(public_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(dest)
    print(f'Published {len(published)} clips / {len(published)*3} files to {out}')
    print('Commit the generated public/audio and public/corpus.json files; Vercel will deploy on push after Git integration is configured.')
    return 0

if __name__=='__main__':sys.exit(main())

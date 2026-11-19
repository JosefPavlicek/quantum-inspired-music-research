#!/usr/bin/env python3
"""Render full HookTheory annotated excerpts with FluidSynth acoustic grand piano.
Run from repo root: python IHSI2027-listening-study/scripts/render_full_piano.py
Uses pilot HARMONIX JSONs after strict full-length timeline validation; does not regenerate harmony.
"""
from __future__ import annotations
import argparse, json, math, shutil, struct, subprocess, sys, tempfile, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render_variants import load_json, build_harmony
from prepare_corpus import trim

TPB = 480

def vlq(n):
    if n < 0: raise ValueError('Negative MIDI delta')
    b=[n & 127]; n >>= 7
    while n:
        b.insert(0, (n & 127) | 128); n >>= 7
    return bytes(b)

def chunk(tag, data):
    return tag + struct.pack('>I',len(data)) + data

def midi_track(events):
    # events: (absolute_tick, priority, raw_midi_event)
    events.sort(key=lambda x:(x[0],x[1]))
    out=bytearray(); last=0
    for tick,_,msg in events:
        out.extend(vlq(tick-last));out.extend(msg);last=tick
    out.extend(b'\x00\xff\x2f\x00')
    return chunk(b'MTrk',bytes(out))

def make_midi(path, melody, harmony, bpm, beats):
    if bpm <= 0: raise ValueError('Invalid BPM')
    tempo=int(round(60_000_000/bpm))
    conductor=midi_track([(0,0,b'\xff\x51\x03'+tempo.to_bytes(3,'big'))])
    tracks=[]
    for channel,program,notes in [(0,0,melody),(1,0,harmony)]:
        events=[(0,0,bytes([0xc0+channel,program]))]
        for start,end,pitch,velocity in notes:
            if not (0 <= start < end <= beats+1e-5):
                raise ValueError(f'Note outside full excerpt: {(start,end,pitch)} / {beats}')
            a=int(round(start*TPB));b=int(round(end*TPB))
            if b<=a:continue
            events.append((a,2,bytes([0x90+channel,pitch,velocity])))
            events.append((b,1,bytes([0x80+channel,pitch,0])))
        # Let the soundfont release the notes naturally; do not truncate at final beat.
        events.append((int(round((beats+3*bpm/60)*TPB)),3,b'\xff\x01\x00'))
        tracks.append(midi_track(events))
    path.write_bytes(chunk(b'MThd',struct.pack('>HHH',1,3,TPB))+conductor+b''.join(tracks))

def to_notes(melody, harmony):
    mn=[(float(n['onset']),float(n['offset']),60+int(n['pitch_class'])%12,88) for n in melody]
    hn=[]
    for h in harmony:
        root=int(h['root_pitch_class'])%12
        pcs=[root]; acc=root
        for interval in h['root_position_intervals']:
            acc+=int(interval);pcs.append(acc%12)
        mids=[48+pc for pc in pcs]
        inv=int(h.get('inversion',0))%len(mids)
        for j in range(inv):mids[j]+=12
        for pitch in mids:
            hn.append((float(h['onset']),float(h['offset']),pitch,65))
    return mn,hn

def check_timeline(segments, beats, meter=4):
    spans=[]
    for s in segments:
        a=(int(s['measure'])-1)*meter+float(s['beat'])-1
        b=a+float(s['duration'])
        spans.append((a,b))
    if not spans or abs(spans[0][0])>1e-5 or abs(spans[-1][1]-beats)>1e-5:
        raise ValueError(f'HARMONIX segments do not cover full {beats} beats: {spans[:1]} ... {spans[-1:]}')
    for (_,b),(a,_) in zip(spans,spans[1:]):
        if abs(a-b)>1e-5:raise ValueError(f'HARMONIX timeline gap/overlap at {b} -> {a}')

def check_wav(path,beats,bpm):
    with wave.open(str(path),'rb') as f:
        sec=f.getnframes()/f.getframerate()
        if f.getnframes()==0:raise ValueError('Empty WAV')
    if sec+0.01<beats*60/bpm:
        raise ValueError(f'WAV too short: {sec:.2f}s for {beats*60/bpm:.2f}s musical duration')
    return sec

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset',default='data/Hooktheory.json.gz')
    ap.add_argument('--pilot',default='IHSI2027-listening-study/experiments/pilot_corpus')
    ap.add_argument('--full',default='IHSI2027-listening-study/experiments/full_corpus')
    ap.add_argument('--sf2',default='/usr/share/sounds/sf2/FluidR3_GM.sf2')
    ap.add_argument('--rate',type=int,default=44100)
    args=ap.parse_args()
    if not shutil.which('fluidsynth'):ap.error('fluidsynth executable missing')
    if not Path(args.sf2).is_file():ap.error(f'SoundFont not found: {args.sf2}')
    dataset=load_json(args.dataset)
    pilot=Path(args.pilot);full=Path(args.full)
    pilot_manifest=load_json(pilot/'manifest.json')
    full_manifest=load_json(full/'manifest.json')
    full_by_id={x['clip_id']:x for x in full_manifest['clips']}
    completed=0
    for item in pilot_manifest['clips']:
        cid=item['clip_id'];rid=item['hooktheory_record_id']
        try:
            metadata=full_by_id[cid]
            if metadata['hooktheory_record_id']!=rid:raise ValueError('Record mismatch in full manifest')
            beats=float(metadata['full_beats']);bpm=float(item['bpm_rendered'])
            rec=dataset[rid];ann=rec['annotations']
            meter=ann['meters'][0]
            if int(meter['beats_per_bar'])!=4 or int(meter['beat_unit'])!=4:
                raise ValueError('Only 4/4 supported')
            melody=trim(ann['melody'],beats)
            reference=trim(ann['harmony'],beats)
            base=load_json(pilot/cid/'baseline_emh.json')
            guided=load_json(pilot/cid/'guided_emh.json')
            for result in (base,guided):
                if result['clip_id']!=cid or result['hooktheory_record_id']!=rid:
                    raise ValueError('Result IDs mismatch')
                check_timeline(result['segments'],beats)
                if result.get('reference_used_for_generation') is not False:
                    raise ValueError('Reference independence not verified')
            if not base.get('parity_with_emh') or not guided.get('baseline_parity') or not guided.get('zero_penalty_parity'):
                raise ValueError('Parity checks failed')
            if base['emh_baseline']!=guided['baseline_emh']:
                raise ValueError('Different baseline paths')
            conditions={
                'human':reference,
                'baseline':build_harmony(base,'emh_baseline',beats),
                'guided':build_harmony(guided,'guided_emh',beats)
            }
            folder=full/cid;folder.mkdir(parents=True,exist_ok=True)
            lengths={}
            with tempfile.TemporaryDirectory() as tmp:
                for label,harmony in conditions.items():
                    midi=Path(tmp)/f'{label}.mid'
                    mn,hn=to_notes(melody,harmony)
                    make_midi(midi,mn,hn,bpm,beats)
                    wav=folder/f'{label}_piano.wav'
                    cmd=['fluidsynth','-ni','-g','0.45','-r',str(args.rate),'-F',str(wav),str(Path(args.sf2).resolve()),str(midi)]
                    proc=subprocess.run(cmd,capture_output=True,text=True)
                    if proc.returncode!=0 or not wav.is_file():
                        raise RuntimeError(f'FluidSynth {label}: {proc.stderr[-800:]} {proc.stdout[-400:]}')
                    lengths[label]=round(check_wav(wav,beats,bpm),2)
            (folder/'piano_render_metadata.json').write_text(json.dumps({
                'clip_id':cid,'hooktheory_record_id':rid,'beats':beats,'bpm':bpm,
                'soundfont':Path(args.sf2).name,'synthesizer':'FluidSynth',
                'audio_lengths_seconds':lengths,'harmonix_source':'pilot_corpus JSON, validated full duration',
                'notes':'Normalized pitch-class melody register; soundfont and reference rights need review.'
            },indent=2)+'\n',encoding='utf8')
            print(f'{cid}: OK {beats:g} beats, HUMAN/BASELINE/GUIDED piano WAV ({lengths})')
            completed+=1
        except Exception as exc:
            print(f'{cid}: FAILED: {exc}',file=sys.stderr)
    print(f'Completed: {completed}/{len(pilot_manifest["clips"])}')
    return 0 if completed==len(pilot_manifest['clips']) else 1

if __name__=='__main__':raise SystemExit(main())

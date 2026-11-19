#!/usr/bin/env python3
"""Select deterministic HookTheory excerpts and export melody-only MusicXML + reference WAV.
No EMH output is fabricated. Review each selection and licensing before publishing.
"""
import argparse, gzip, json, random, sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_audio import render

NAMES=['C','C','D','D','E','F','F','G','G','A','A','B']
ALTER=[0,1,0,1,0,0,1,0,1,0,1,0]

def load(path):
    with (gzip.open(path,'rt',encoding='utf8') if str(path).endswith('.gz') else open(path,encoding='utf8')) as f:
        return json.load(f)

def trim(items,beats):
    result=[]
    for n in items:
        start=max(0,float(n['onset']));end=min(beats,float(n['offset']))
        if end>start+1e-6:
            x=dict(n);x['onset']=start;x['offset']=end;result.append(x)
    return sorted(result,key=lambda x:(x['onset'],x['offset']))

def xml_melody(melody,path,beats=24,divisions=480,beat_per_bar=4):
    # HookTheory octave is not calibrated here; C4..B4 normalized as in the pilot renderer.
    root=ET.Element('score-partwise',version='4.0')
    wl=ET.SubElement(root,'work');ET.SubElement(wl,'work-title').text='HookTheory research excerpt (normalized register)'
    pl=ET.SubElement(root,'part-list');sp=ET.SubElement(pl,'score-part',id='P1')
    ET.SubElement(sp,'part-name').text='Melody';ET.SubElement(sp,'part-abbreviation').text='Mel.'
    part=ET.SubElement(root,'part',id='P1')
    total=int(round(beats*divisions));bar=beat_per_bar*divisions
    events=[];cursor=0
    for n in melody:
        a=round(float(n['onset'])*divisions);b=round(float(n['offset'])*divisions)
        if a<cursor: continue # overlapping monophonic annotations excluded deterministically
        if a>cursor:events.append((cursor,a,None))
        events.append((a,b,int(n['pitch_class'])));cursor=b
    if cursor<total:events.append((cursor,total,None))
    for i in range((total+bar-1)//bar):
        measure=ET.SubElement(part,'measure',number=str(i+1))
        if i==0:
            attrs=ET.SubElement(measure,'attributes');ET.SubElement(attrs,'divisions').text=str(divisions)
            tm=ET.SubElement(attrs,'time');ET.SubElement(tm,'beats').text=str(beat_per_bar);ET.SubElement(tm,'beat-type').text='4'
            clef=ET.SubElement(attrs,'clef');ET.SubElement(clef,'sign').text='G';ET.SubElement(clef,'line').text='2'
        lo=i*bar;hi=min(total,(i+1)*bar)
        for a,b,pc in events:
            aa=max(lo,a);bb=min(hi,b)
            if bb<=aa:continue
            note=ET.SubElement(measure,'note')
            if pc is None:ET.SubElement(note,'rest')
            else:
                pitch=ET.SubElement(note,'pitch');ET.SubElement(pitch,'step').text=NAMES[pc%12]
                if ALTER[pc%12]:ET.SubElement(pitch,'alter').text='1'
                ET.SubElement(pitch,'octave').text='4'
            ET.SubElement(note,'duration').text=str(bb-aa)
            if pc is not None:
                if a<lo:ET.SubElement(note,'tie',type='stop')
                if b>hi:ET.SubElement(note,'tie',type='start')
                if a<lo or b>hi:
                    notations=ET.SubElement(note,'notations')
                    if a<lo:ET.SubElement(notations,'tied',type='stop')
                    if b>hi:ET.SubElement(notations,'tied',type='start')
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset',default='../data/Hooktheory.json.gz')
    ap.add_argument('--output',default='experiments/pilot_corpus')
    ap.add_argument('--count',type=int,default=6)
    ap.add_argument('--beats',type=int,default=24)
    ap.add_argument('--seed',type=int,default=2027)
    ap.add_argument('--bpm',type=float,default=100)
    a=ap.parse_args();data=load(a.dataset);eligible=[]
    for rid,rec in data.items():
        ann=rec.get('annotations',{});mel=ann.get('melody') or [];harm=ann.get('harmony') or []
        if not mel or not harm or len(ann.get('keys',[]))!=1 or len(ann.get('meters',[]))!=1:continue
        meter=ann['meters'][0]
        if meter.get('beats_per_bar')!=4 or meter.get('beat_unit')!=4:continue
        if ann.get('num_beats',0)<a.beats:continue
        m=trim(mel,a.beats);h=trim(harm,a.beats)
        if len(m)<14 or not 4<=len(h)<=20:continue
        if len({x['root_pitch_class'] for x in h})<3:continue
        if any(float(x['onset'])<0 for x in mel):continue
        eligible.append((rid,rec,m,h))
    rng=random.Random(a.seed);rng.shuffle(eligible)
    chosen=eligible[:a.count]
    if len(chosen)<a.count:raise SystemExit(f'Only {len(chosen)} eligible clips found')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);manifest=[]
    for idx,(rid,rec,m,h) in enumerate(chosen,1):
        cid=f'clip_{idx:02d}';folder=out/cid;folder.mkdir(exist_ok=True)
        ann=dict(rec['annotations']);ann['melody']=m;ann['harmony']=h;ann['num_beats']=a.beats
        xml_melody(m,folder/'melody.musicxml',a.beats)
        render({'annotations':ann},folder/'reference.wav',bpm=a.bpm)
        (folder/'reference_harmony.json').write_text(json.dumps(h,indent=2),encoding='utf8')
        manifest.append({'clip_id':cid,'hooktheory_record_id':rid,'artist':rec.get('hooktheory',{}).get('artist'),
            'song':rec.get('hooktheory',{}).get('song'),'split':rec.get('split'),
            'beats':a.beats,'bpm_rendered':a.bpm,'melody_events':len(m),'harmony_events':len(h),
            'melody_musicxml':f'{cid}/melody.musicxml','reference_audio':f'{cid}/reference.wav',
            'reference_harmony':f'{cid}/reference_harmony.json','baseline_emh':None,'guided_emh':None})
    (out/'manifest.json').write_text(json.dumps({'seed':a.seed,'dataset_count':len(data),'eligible_count':len(eligible),
        'warnings':['Normalized octave; not research-validated','Fixed synthetic BPM and timbre','Reference audio is not cleared for public redistribution','EMH baseline/guided outputs not yet generated'],
        'clips':manifest},indent=2,ensure_ascii=False),encoding='utf8')
    print(f'Selected {len(chosen)} of {len(eligible)} eligible excerpts; output: {out}')
    for c in manifest:print(c['clip_id'],c['hooktheory_record_id'],c['melody_events'],c['harmony_events'])

if __name__=='__main__':main()

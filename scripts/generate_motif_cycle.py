#!/usr/bin/env python3
"""A randomized six-motif SVG cycle; each motif completes an entire round."""
import argparse
import copy
import hashlib
import random
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from generate_snake_duet import TAG, build_duet, load_source

MOTIFS = [('snake','ONCE MORE'),('fireflies','AGAIN'),('robots','RESTART'),
          ('leaves','ENCORE'),('waves','REPLAY'),('comets','ONE MORE')]


def sprite(element, motif, index):
    if motif == 'snake':return
    element.tag=TAG+'svg'
    element.set('viewBox','0 0 16 16');element.set('overflow','visible')
    for key in ['rx','ry']:element.attrib.pop(key,None)
    def add(tag,**attrs):return ET.SubElement(element,TAG+tag,{k:str(v) for k,v in attrs.items()})
    if motif=='fireflies':
        add('circle',cx=8,cy=8,r=8,opacity=.12)
        add('ellipse',cx=5,cy=5,rx=3,ry=2,fill='#b9ddff',opacity=.55)
        add('ellipse',cx=11,cy=5,rx=3,ry=2,fill='#b9ddff',opacity=.55)
        add('circle',cx=8,cy=9,r=4)
        add('circle',cx=8,cy=9,r=1.5,fill='#e5f5ff')
    elif motif=='robots':
        if index==0:
            add('rect',x=1,y=3,width=14,height=10,rx=3)
            add('rect',x=3,y=5,width=10,height=5,rx=1,fill='#101b2b')
            add('rect',x=5,y=6,width=2,height=2,fill='#b9ecff')
            add('rect',x=9,y=6,width=2,height=2,fill='#b9ecff')
            add('rect',x=3,y=13,width=3,height=2,rx=1)
            add('rect',x=10,y=13,width=3,height=2,rx=1)
            add('rect',x=7,y=0,width=2,height=3)
        else:add('rect',x=6,y=6,width=4,height=4,rx=1,opacity=.65)
    elif motif=='leaves':
        add('path',d='M2 13C-1 3 8 1 15 1C15 10 10 17 2 13Z')
        add('path',d='M2 14L12 4L4 13Z',fill='#d4edff',opacity=.65)
        add('rect',x=-5,y=5,width=5,height=1,rx=.5,opacity=.35)
        add('rect',x=-3,y=9,width=4,height=1,rx=.5,opacity=.5)
    elif motif=='waves':
        add('path',d='M0 10C3 10 3 2 9 2C15 2 16 9 11 9C13 6 10 4 8 6C6 9 10 12 16 11L16 15L0 15Z')
        add('path',d='M0 12Q4 15 8 12Q12 9 16 12L16 13Q12 11 8 14Q4 16 0 14Z',fill='#d4edff',opacity=.65)
    elif motif=='comets':
        add('path',d='M-7 2L11 5L11 11L-5 16L3 8Z',opacity=.4)
        add('circle',cx=10,cy=8,r=4.5)
        add('circle',cx=11,cy=7,r=1.7,fill='#e3f5ff')


def compact_keyframes(css):
    """Drop redundant property samples, preserving hold boundaries and collisions."""
    def compact(match):
        name,body=match.groups();frames={}
        for keys,decl in re.findall(r'([^{}]+)\{([^{}]+)\}',body):
            props=dict(part.split(':',1) for part in decl.split(';') if ':' in part)
            for key in keys.split(','):frames.setdefault(float(key.strip().rstrip('%')),{}).update(props)
        output={}
        for prop in {p for f in frames.values() for p in f}:
            values=sorted((t,f[prop]) for t,f in frames.items() if prop in f)
            for i,(t,v) in enumerate(values):
                if 0<i<len(values)-1 and values[i-1][1]==v==values[i+1][1]:continue
                output.setdefault(t,{})[prop]=v
        return '@keyframes '+name+'{'+''.join(f'{t:.6f}%'+ '{'+';'.join(f'{k}:{v}' for k,v in sorted(props.items()))+'}' for t,props in sorted(output.items()))+'}'
    return re.sub(r'@keyframes ([\w-]+)\{((?:[^{}]*\{[^{}]*\})+)\}',compact,css)


def compose(sources,seed,route_cache=None):
    route_cache={} if route_cache is None else route_cache
    rng=random.Random(seed);order=list(MOTIFS);rng.shuffle(order)
    rounds=[(motif,phrase,ET.fromstring(build_duet(sources,seed=seed,phrase=phrase,route_cache=route_cache))) for motif,phrase in order]
    gaps=[rng.randint(1200,4200) for _ in rounds]
    duration=max(float(root.get('data-cycle-ms'))+gap for (_,_,root),gap in zip(rounds,gaps))+100
    total=duration*len(rounds)
    first=rounds[0][2]
    width,height=first.get('width'),first.get('height')
    result=ET.Element(TAG+'svg',{'width':width,'height':height,'viewBox':f'0 0 {width} {height}',
        'role':'img','aria-label':'Contributions: snakes, fireflies, robots, wind and leaves, waves, and comets',
        'data-motif-order':','.join(m for m,_,_ in rounds),'data-round-ms':f'{duration:.3f}',
        'data-cycle-ms':f'{total:.3f}','data-seed':str(seed)})
    ET.SubElement(result,TAG+'title').text='A little world, once more'
    gates=[]
    for i,((motif,phrase,root),gap) in enumerate(zip(rounds,gaps)):
        scene=f'scene-{i}';base=float(root.get('data-cycle-ms'));css=root.find(TAG+'style').text
        names=set(re.findall(r'@keyframes ([\w-]+)',css));mapping={n:scene+'-'+n for n in names}
        for el in root.iter():
            if el.get('class'):el.set('class',' '.join(mapping.get(c,c) for c in el.get('class').split()))
            if el.get('id'):el.set('id',scene+'-'+el.get('id'))
            for k,v in list(el.attrib.items()):
                if 'url(#' in v:el.set(k,v.replace('url(#','url(#'+scene+'-'))
        for old,new in sorted(mapping.items(),key=lambda x:-len(x[0])):css=re.sub(r'(?<![\w-])'+re.escape(old)+r'(?![\w-])',new,css)
        css=css.replace('url(#','url(#'+scene+'-').replace(':root','#'+scene)
        # Scope style selectors; nested SVG style sheets otherwise leak between rounds.
        css=re.sub(r'(?<=\})([^@{}][^{}]*)\{',lambda m:','.join('#'+scene+' '+x.strip() for x in m[1].split(','))+'{' if '%' not in m[1] and not m[1].strip().startswith('@') else m[0],css)
        css=re.sub(r'(?<![\d.])([\d.]+)%',lambda m:f'{(float(m[1])*base/100+gap)/duration*100:.7f}%',css)
        css=css.replace(f'{base:.3f}ms',f'{duration:.3f}ms')
        # Keep initial values fixed during the randomized inter-round wait.
        # Percent zero is shifted by the gap, so CSS also holds the first keyframe before it.
        root.find(TAG+'style').text=compact_keyframes(css)
        for group in root.findall(TAG+'g'):
            cls=group.get('class','')
            if cls in ('duet-red','duet-blue'):
                for actor in group:
                    for index,element in enumerate(actor):sprite(element,motif,index)
            elif cls=='forming-snakes':
                for element in group:sprite(element,motif,int(element.get('data-morph-slot')))
        root.set('id',scene);root.set('x','0');root.set('y','0');root.set('data-motif',motif)
        root.set('data-phrase',phrase);root.set('data-entry-gap-ms',str(gap))
        root.set('aria-label',f'{motif}: collect, {phrase}, restore, depart')
        for group in root.findall(TAG+'g'):
            if group.get('class')=='forming-snakes':group.set('aria-label',f'{motif} gradually forming')
        wrapper=ET.SubElement(result,TAG+'g',{'class':'round-'+str(i)})
        wrapper.append(root)
        start=i/len(rounds)*100;end=(i+1)/len(rounds)*100
        # No all-round flicker at the super-cycle boundary.
        frames=('0%{opacity:1}' if i==0 else f'0%,{start-.000001:.7f}%{{opacity:0}}{start:.7f}%{{opacity:1}}')
        frames+=f'{end-.000001:.7f}%{{opacity:1}}{end:.7f}%,100%{{opacity:0}}' if i<len(rounds)-1 else '100%{opacity:1}'
        gates.append(f'.round-{i}'+'{'+f'opacity:{1 if i==0 else 0};animation:gate-{i} {total:.3f}ms steps(1,end) infinite'+'}'+f'@keyframes gate-{i}'+'{'+frames+'}')
    ET.SubElement(result,TAG+'style').text='\n'.join(gates)+'@media(prefers-reduced-motion:reduce){'+''.join(f'.round-{i}'+'{animation:none;opacity:'+('1' if i==0 else '0')+'}' for i in range(len(rounds)))+'}'
    return ET.tostring(result,encoding='unicode')+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',default='ryouy/ryouy');parser.add_argument('--source-light',type=Path);parser.add_argument('--source-dark',type=Path)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'assets')
    parser.add_argument('--seed',type=int)
    args=parser.parse_args()
    seed=args.seed if args.seed is not None else int(hashlib.sha256(date.today().isoformat().encode()).hexdigest()[:12],16)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    route_cache={}
    for dark,path in [(False,args.source_light),(True,args.source_dark)]:
        output=args.output_dir/('motif-cycle-dark.svg' if dark else 'motif-cycle.svg')
        svg=compose(load_source(path,args.repository,dark),seed,route_cache)
        output.write_text(svg);print(output.name,len(svg.encode()),'bytes')
if __name__=='__main__':main()

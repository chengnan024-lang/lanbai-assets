# Verifier's independent parity check (own C# parser, own expectations): LanbaiGradeData.cs + LanbaiExposure.cs
# vs art/grades_final.json, art/calib_final.json §C, ART_BIBLE appendix B (B1 rows parsed from the markdown, B2, B3).
# Fix pass (B1): the kit now ships the ENGINE numbers (Tools~/inputs/grades_engine.json). The seven colour parameters
# of each scene are compared with that file; B1 (the look definition) is compared with its ppv2_lookdef record;
# everything else (postExposure, bloom, helpers) still with art/grades_final.json. B3 = bible v2.1.
import re, json, hashlib, sys
import os
K=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT=os.path.normpath(os.path.join(K,'..','..'))
cs=open(K+'/Editor/LanbaiGradeData.cs',encoding='utf-8').read()
G=json.load(open(ROOT+'/art/grades_final.json',encoding='utf-8'))
GE=json.load(open(K+'/Tools~/inputs/grades_engine.json',encoding='utf-8'))
COLOUR=('temperature','tint','saturation','contrast','lift','gamma','gain')
CAL=json.load(open(ROOT+'/art/calib_final.json',encoding='utf-8'))
bible=open(ROOT+'/art/ART_BIBLE.md',encoding='utf-8').read()
fails=[]
def fail(m): fails.append(m); print('FAIL',m)
# sha
for name,path in [('grades',ROOT+'/art/grades_final.json'),('calib',ROOT+'/art/calib_final.json'),('engine',K+'/Tools~/inputs/grades_engine.json')]:
    h=hashlib.sha256(open(path,'rb').read()).hexdigest()
    if h not in cs: fail('sha256 of %s not in C# header'%name)
# split entries
blocks=re.findall(r'new LanbaiGradeEntry\s*\{(.*?)\n\s*\},',cs,re.S)
ents={}
for b in blocks:
    d={}
    for m in re.finditer(r'^\s*(\w+)\s*=\s*(.+?),\s*$',b,re.M):
        k,v=m.group(1),m.group(2).strip()
        if v.startswith('new float[]'):
            d[k]=[float(x.rstrip('f')) for x in re.findall(r'-?[\d.]+f',v)]
        elif v.startswith('new string[]'):
            d[k]=re.findall(r'"(#[0-9A-F]{6})"',v)
        elif v.startswith('"'): d[k]=json.loads(v)
        elif v in('true','false'): d[k]=(v=='true')
        elif v.startswith('LanbaiGradeKind.'): d[k]=v.split('.')[1]
        else: d[k]=float(v.rstrip('f'))
    ents[d['id']]=d
print('entries',len(ents),list(ents))
def eq(a,b,tag):
    if (isinstance(a,list) and a and isinstance(a[0],str)) or (isinstance(b,list) and b and isinstance(b[0],str)):
        if a is None or b is None or [x.upper() for x in a]!=[x.upper() for x in b]: fail('%s: cs %r json %r'%(tag,a,b))
    elif isinstance(a,list) or isinstance(b,list):
        if a is None or b is None or len(a)!=len(b) or any(abs(float(x)-float(y))>1e-6 for x,y in zip(a,b)): fail('%s: cs %r json %r'%(tag,a,b))
    elif isinstance(a,str) or isinstance(b,str):
        if (a or '').upper()!=(b or '').upper(): fail('%s: cs %r json %r'%(tag,a,b))
    elif isinstance(a,bool) or isinstance(b,bool):
        if a!=b: fail('%s: cs %r json %r'%(tag,a,b))
    else:
        if a is None or b is None or abs(float(a)-float(b))>1e-6: fail('%s: cs %r json %r'%(tag,a,b))
com=G['common']
scene_keys=['hdrNeutral','postExposure','temperature','tint','colorFilter','hueShift','saturation','contrast','lift','gamma','gain','bloomIntensity','bloomThreshold','bloomSoftKnee','bloomClamp','bloomDiffusion','bloomAnamorphicRatio','bloomColor','bloomFastMode','vignetteIntensity','grainIntensity']
n=0
prio_order=sorted(G['profiles'],key=lambda k:G['profiles'][k]['priority'])
for sid,p in G['profiles'].items():
    e=ents.get(sid)
    if not e: fail('missing '+sid); continue
    pp=dict(p['ppv2']); b=pp['bloom']
    for k in COLOUR: pp[k]=GE['profiles'][sid]['ppv2'][k]          # engine numbers
    eq(e.get('channelMixer'),GE['profiles'][sid]['ppv2']['mixer'],sid+'.channelMixer'); n+=1
    for k in COLOUR: eq(GE['profiles'][sid]['ppv2_lookdef'][k],p['ppv2'][k],sid+'.lookdef.'+k)
    exp={'hdrNeutral':True,'postExposure':pp['postExposure'],'temperature':pp['temperature'],'tint':pp['tint'],'colorFilter':com['colorFilter'],'hueShift':com['hueShift'],
         'saturation':pp['saturation'],'contrast':pp['contrast'],'lift':pp['lift'],'gamma':pp['gamma'],'gain':pp['gain'],'bloomIntensity':b['intensity'],'bloomThreshold':b['threshold'],
         'bloomSoftKnee':b['softKnee'],'bloomClamp':com['bloom']['clamp'],'bloomDiffusion':b['diffusion'],'bloomAnamorphicRatio':com['bloom']['anamorphicRatio'],'bloomColor':b['color'],
         'bloomFastMode':com['bloom']['fastMode'],'vignetteIntensity':com['vignette']['intensity'],'grainIntensity':com['grain']['intensity'],'priority':p['priority'],'bloomT0':p['bloom_T0_scene_linear']}
    for k,v in exp.items(): eq(e.get(k),v,sid+'.'+k); n+=1
    # extra override keys present?
    extra=[k for k in e if k.startswith(('vignette','grain')) and k not in ('vignetteIntensity','grainIntensity')]
    if extra: fail(sid+' extra lens keys '+str(extra))
    eq(e.get('expectedTestCard'),CAL['ramp'][sid],sid+'.testcard'); n+=1
    eq(e.get('initialWeight'), 1.0 if sid==prio_order[0] else 0.0, sid+'.initialWeight')
    if e.get('kind')!='Scene' or e.get('group')!='Scenes': fail(sid+' kind/group')
H=G['helpers']
for hid in ['EXPO_UP','EXPO_DOWN','WHITE_SAT','WHITE_BLOOM','LENS_CLEAN','LENS_ARCHIVE']:
    e=ents.get(hid); h=H[hid]
    if not e: fail('missing '+hid); continue
    eq(e.get('priority'),h['priority'],hid+'.priority'); n+=1
    keys=set(k for k in e if k not in('id','shortName','displayName','kind','group','priority','initialWeight','desktopOnly','weightRule','bloomColorCompensated'))
    if 'bloomColor' in e:   # PPv2 double sRGB decode of the bloom tint (verify.md m1): raw = sRGB-encode(hex/255)
        enc=lambda v: 12.92*v if v<=0.0031308 else 1.055*v**(1/2.4)-0.055
        eq(e.get('bloomColorCompensated'),[round(enc(int(e['bloomColor'][i:i+2],16)/255),6) for i in (1,3,5)],hid+'.bloomColorCompensated')
    if 'ppv2' in h:
        pv=h['ppv2']
        want={}
        if 'postExposure' in pv: want['postExposure']=pv['postExposure']
        if 'saturation' in pv: want['saturation']=pv['saturation']
        if 'bloom' in pv:
            bb=pv['bloom']; want.update({'bloomIntensity':bb['intensity'],'bloomThreshold':bb['threshold'],'bloomSoftKnee':bb['softKnee'],'bloomDiffusion':bb['diffusion'],'bloomColor':bb['color']})
        for k,v in want.items(): eq(e.get(k),v,hid+'.'+k); n+=1
        if keys!=set(want): fail('%s override keys %s != %s'%(hid,sorted(keys),sorted(want)))
    else:
        v=h['vignette']; g=h['grain']
        want={'vignetteIntensity':v['intensity'],'vignetteSmoothness':v['smoothness'],'vignetteColor':v['color'],'grainIntensity':g['intensity'],'grainSize':g['size'],'grainLumContrib':g['lumContrib'],'grainColored':g['colored']}
        for k,vv in want.items(): eq(e.get(k),vv,hid+'.'+k); n+=1
        extra=keys-set(want)
        print(hid,'extra (defaults) keys:',{k:e[k] for k in sorted(extra)})
    eq(e.get('initialWeight'), 1.0 if hid=='LENS_CLEAN' else 0.0, hid+'.initialWeight')
print('value comparisons',n)
# ---- bible appendix B table B1
rows=re.findall(r'^\| (\*\*)?(S\d+\w?)[^|]*\| (\d+) \| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\|',bible,re.M)
NIGHT=[0.9875,0.9905,1,0.008]
def num(s):
    s=s.replace('*','').replace('−','-').replace('+','').strip()
    return float(s)
def vec(s):
    s=s.replace('*','').strip()
    if s=='夜间': return NIGHT
    return [float(x) for x in s.strip('()').split(',')]
b1=0
for r in rows:
    sid=r[1]; e=ents[sid]; ld=GE['profiles'][sid]['ppv2_lookdef']
    eq(e['priority'],float(r[2]),'B1 '+sid+' prio'); eq(e['postExposure'],num(r[3]),'B1 '+sid+' pe'); eq(ld['temperature'],num(r[4]),'B1 '+sid+' temp')
    eq(ld['tint'],num(r[5]),'B1 '+sid+' tint'); eq(ld['saturation'],num(r[6]),'B1 '+sid+' sat'); eq(ld['contrast'],num(r[7]),'B1 '+sid+' con')
    eq(ld['lift'],vec(r[8]),'B1 '+sid+' lift'); eq(ld['gamma'],vec(r[9]),'B1 '+sid+' gamma'); eq(ld['gain'],vec(r[10]),'B1 '+sid+' gain')
    bl=[x.strip().strip('*').strip('`').strip('*').strip('`') for x in r[11].split('/')]
    eq(e['bloomIntensity'],float(bl[0].strip('*')),'B1 '+sid+' bI'); eq(e['bloomThreshold'],float(bl[1]),'B1 '+sid+' bT'); eq(e['bloomSoftKnee'],float(bl[2]),'B1 '+sid+' bK')
    eq(e['bloomDiffusion'],float(bl[3]),'B1 '+sid+' bD'); eq(e['bloomColor'],bl[4].strip('*`'),'B1 '+sid+' bC')
    t0=r[12].strip()
    if t0!='—': eq(round(e['bloomT0'],2),float(t0),'B1 '+sid+' T0')
    b1+=1
print('B1 rows',b1)
# B2
if not re.search(r'`EXPO_UP` \| 100 \| postExposure \*\*\+4\.0\*\*',bible): fail('B2 EXPO_UP row')
if not re.search(r'`EXPO_DOWN` \| 99 \| postExposure \*\*−4\.0\*\*',bible): fail('B2 EXPO_DOWN row')
if not re.search(r'`WHITE_SAT` \| 96 \| saturation −30',bible): fail('B2 WHITE_SAT')
if not re.search(r'`WHITE_BLOOM` \| 96 \| bloom 12 / 0\.8 / 0\.8 / 9 / `#EEF4F8`',bible): fail('B2 WHITE_BLOOM')
if not re.search(r'`LENS_CLEAN` \| 199 \| 暗角 0\.20 / 0\.40 / `#02040A`；颗粒 0\.06 / 0\.8 / 单色',bible): fail('B2 LENS_CLEAN')
if not re.search(r'`LENS_ARCHIVE` \| 200 \| 暗角 0\.26 / 0\.45；颗粒 0\.20 / 1\.0 / 亮度贡献 0\.85 / 单色',bible): fail('B2 LENS_ARCHIVE')
# ---- bloom T0 recompute: GammaToLinearSpaceExact(threshold)*(1-knee)
def g2l(v):
    if v<=0.04045: return v/12.92
    if v<1: return ((v+0.055)/1.055)**2.4
    return v**2.2
for sid,e in ents.items():
    if e.get('kind')=='Scene':
        t0=g2l(e['bloomThreshold'])*(1-e['bloomSoftKnee'])
        if abs(t0-e['bloomT0'])>0.002: fail('T0 %s recomputed %.4f vs %.4f'%(sid,t0,e['bloomT0']))
# ---- U# region
ux=open(K+'/Runtime/LanbaiExposure.cs',encoding='utf-8').read()
ids=re.findall(r'case (\d+): return "(S\w+)";',ux)
if [i for _,i in ids]!=prio_order: fail('U# SceneId order %s'%ids)
pes=re.findall(r'case (\d+): return (-?[\d.]+)f; // (S\w+)',ux)
for i,v,sid in pes:
    if prio_order[int(i)]!=sid or abs(float(v)-G['profiles'][sid]['ppv2']['postExposure'])>1e-6: fail('U# pe %s %s %s'%(i,v,sid))
if len(pes)!=15: fail('U# pe count')
for sid in prio_order:
    if not re.search(r'if \(id == "%s"\) return %d;'%(sid,prio_order.index(sid)),ux): fail('U# SceneIndex '+sid)
if 'ExpoUpTarget = 4f' not in ux or 'ExpoDownTarget = -4f' not in ux: fail('U# targets')
if 'grades_engine.json" sha256="%s"'%hashlib.sha256(open(K+'/Tools~/inputs/grades_engine.json','rb').read()).hexdigest() not in ux: fail('U# sha')
# ---- B3 weights
def wu(d,b): return d/(4-b)
def wd(d,b): return -d/(b+4)
B3=[(-0.9,0.5,0.102),(-0.85,0.3,0.062),(-0.9,1.5,0.306),(-0.75,-0.5,0.154),(-0.8,-0.5,0.156),(-0.4,-2.43,0.68),(-0.5,0.5,0.11),(0.3,0.35,0.095),(0.3,1.0,0.270),(0.3,2.4,0.649),(-0.15,1.0,0.241),(0.0,0.8,0.200)]
for b,d,w in B3:   # bible v2.1 table B3
    ww=wu(d,b) if d>0 else wd(d,b)
    if abs(ww-w)>0.006: fail('B3 %s %s -> %.4f vs %s'%(b,d,ww,w))
print('RESULT', 'PASS' if not fails else 'FAIL %d'%len(fails))

"""第 3 幕破云 U6k：125 -> 135 s 的天（只有天）和整帧模型的对数平均亮度曲线（Sky/Docs~/u6k/README_u6k.md）。写 curves.json 到当前目录。"""
import sys, os, json, numpy as np
R='/home/user/lanbai-assets'; sys.path.insert(0, R+'/Sky/Tools~/render')
import sky_cpu as S, grade as G, test_sequence as TS, make_presets as MP
from shader_cpu import camera_dirs
P,_=TS.load()
d=camera_dirs(320,180,90,0,0).astype(np.float32)
S.renderer().tex.clear(); S.set_cube('_CubeA', S.load_hdr(MP.P['overcast_rain_night']['hdri_file']))
T0=129.1
def sky_log(t,fade):
    a,b=P['overcast_rain_night'],P['moon_night']
    if t<T0: g=TS.globs_of(a)
    elif fade>0 and t<T0+fade:
        x=(t-T0)/fade; g=TS.blend(a,b,x*x*(3-2*x))[0]
        g=dict(g)
        if TS.blend(a,b,0.5)[3]: pass
    else: g=TS.globs_of(b)
    c=np.clip(G.grade(S.render(d,{},dict(g)).reshape(180,320,3),'S3'),0,255)
    lin=np.where(c/255<=0.04045,(c/255)/12.92,((c/255+0.055)/1.055)**2.4)@[0.2126,0.7152,0.0722]
    return float(np.log2(np.maximum(lin,1e-5)).mean())
def expo(t):   # EXPO_UP +0.5 EV: 0.6 s rise (smoothstep), 3 s linear decay (bible §6·3c)
    if t<T0: return 0.0
    if t<T0+0.6: x=(t-T0)/0.6; return 0.5*x*x*(3-2*x)
    return max(0.0,0.5*(1-(t-T0-0.6)/3.0))
def law(ev,dt=0.1):
    out={}
    for win,lim in ((0.25,0.5),(1.0,1.0),(2.0,1.8)):
        n=int(round(win/dt)); out[win]=round(max(ev[i+n]-ev[i] for i in range(len(ev)-n)),3)
    return out
ts=np.round(np.arange(125.0,135.0+1e-6,0.1),2)
res={}
for fade in (0.0,2.5,3.5):
    sky=np.array([sky_log(t,fade) for t in ts]); k=1.008/1.633   # sky share of the whole frame (Unity step / CPU sky step)
    whole=sky[0]+k*(sky-sky[0])+np.array([expo(t) for t in ts])
    res[fade]=dict(sky=sky.round(4).tolist(),whole=whole.round(4).tolist(),law_sky=law(sky),law_whole=law(whole))
    print('fade %.1f s  sky-only ramp %s   whole-frame model (sky x %.2f + EXPO_UP) ramp %s'%(fade,law(sky),k,law(whole)))
json.dump(dict(t=ts.tolist(),runs={str(k):v for k,v in res.items()}),open('curves.json','w'))

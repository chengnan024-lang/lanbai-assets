"""D-49 #4 / D-34 #5: where the hall door sits at F7 from the main eye (0.55, 1.70, 2.05) for the three ways to get it off
the PAZ centre post -- B / B' (the bus path moved right by s) and C (the bus steers right into the stop, F6 -> F7) --
through the bus package's viewcheck grid (Bus/Docs~/viewcheck/hero_occlusion.npz). Report: Docs~/7b_F7殿门三个做法.md.

  ~/bpy/bin/python Act07_Sea/Tools~/f7_door_options.py
"""
import json, math, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); import act07_motion as M
z=np.load(os.path.join(REPO,'Bus','Docs~','viewcheck','hero_occlusion.npz'),allow_pickle=True); ids=z['ids']; AZ=z['az']; EL=z['el']
wins=json.loads(str(z['windows'])); parts=json.loads(str(z['parts']))
def lab(a,e):
    i=int(np.argmin(abs(EL-e))); j=int(np.argmin(abs(AZ-a))); k=int(ids[i,j])
    return 'open' if k==-1 else (wins[-k-2] if k<0 else parts[k])
F=json.load(open(os.path.join(REPO,'Act07_Sea','PalaceFrame_约定.json'),encoding='utf-8'))
H=F['hall']; dx0=H['door_x']; dw,dh=H['door_size']; plat=H['platform']['height_m']; zd=H['front_z']
L=M.L; zs=M.fwd(L['F7']); car=np.array([0.0,F['frame']['bus_origin_y_stop'],zs]); EYE=np.array([0.55,1.70,2.05])
def rot(p,th):  # rotate palace point about bus origin by th deg (Unity yaw, + clockwise from above)
    a=math.radians(th); q=p-car; return car+np.array([q[0]*math.cos(a)+q[2]*math.sin(a),q[1],-q[0]*math.sin(a)+q[2]*math.cos(a)])
def door(s=0.0,th=0.0):
    e=car+EYE; out={}
    pts={'L':(dx0-dw/2,plat+dh/2),'R':(dx0+dw/2,plat+dh/2),'C':(dx0,plat+dh/2),'TL':(dx0-dw/2,plat+dh),'TR':(dx0+dw/2,plat+dh),'BL':(dx0-dw/2,plat),'BR':(dx0+dw/2,plat)}
    for k,(x,y) in pts.items():
        p=rot(np.array([x-s,y,zd]),th); d=p-e
        out[k]=(math.degrees(math.atan2(d[0],d[2])), math.degrees(math.atan2(d[1],math.hypot(d[0],d[2]))))
    labs=set()
    for a in np.linspace(out['BL'][0],out['BR'][0],12):
        for el in np.linspace(out['BL'][1],out['TL'][1],12): labs.add(lab(a,el))
    # pillar right margin: nearest non-window cell to the right of the door's right edge, over the door's el range
    marg=[]
    for el in np.linspace(out['BR'][1],out['TR'][1],8):
        a=out['R'][0]
        while lab(a,el)=='WindscreenL' and a<0: a+=0.25
        marg.append(a-out['R'][0])
    return out,labs,min(marg),np.linalg.norm(rot(np.array([dx0-s,plat+dh/2,zd]),th)-e)
def solve_s(target):
    lo,hi=-5,30
    for _ in range(60):
        m=(lo+hi)/2; c=door(s=m)[0]['C'][0]
        if c>target: lo=m
        else: hi=m
    return m
def solve_th(target):
    lo,hi=-40,40
    for _ in range(60):
        m=(lo+hi)/2; c=door(th=m)[0]['C'][0]
        if c>target: lo=m
        else: hi=m
    return m

# ---- C: the bus steers right into the stop: heading psi(t) = PSI * smoothstep((t - t0) / (F7 - t0)); it moves along its
# heading (v from act07_motion), so it drifts sideways x(t) = integral v sin(psi); the palace frame is what moves in Unity
def smooth(u):
    u=min(max(u,0.0),1.0); return u*u*(3-2*u)
def c_path(PSI, t0=None, t1=None, dt=0.02):
    t0=L['F6'] if t0 is None else t0; t1=L['F7'] if t1 is None else t1
    x=0.0; zc=M.fwd(t0); t=t0; out=[]
    while t<t1-1e-9:
        tm=t+dt/2; psi=math.radians(PSI*smooth((tm-t0)/(t1-t0))); ds=M.fwd(t+dt)-M.fwd(t)
        x+=ds*math.sin(psi); zc+=ds*math.cos(psi); t+=dt; out.append((t,x,zc,math.degrees(psi)))
    return out
def door_c(PSI):
    p=c_path(PSI); t,x,zc,psi=p[-1]
    e0=np.array([x,F['frame']['bus_origin_y_stop'],zc])
    a=math.radians(psi); R=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
    e=e0+R@EYE; res={}
    for k,(xx,y) in {'L':(dx0-dw/2,plat+dh/2),'R':(dx0+dw/2,plat+dh/2),'C':(dx0,plat+dh/2),'TL':(dx0-dw/2,plat+dh),'BL':(dx0-dw/2,plat),'TR':(dx0+dw/2,plat+dh),'BR':(dx0+dw/2,plat)}.items():
        d=R.T@(np.array([xx,y,zd])-e)
        res[k]=(math.degrees(math.atan2(d[0],d[2])), math.degrees(math.atan2(d[1],math.hypot(d[0],d[2]))))
    return res, dict(x_drift=x, z_stop=zc, psi=psi, eye=e, dist=float(np.linalg.norm(np.array([dx0,plat+dh/2,zd])-e)))


def report():
    def show(nm, o, extra=''):
        labs=set()
        for a in np.linspace(o['BL'][0],o['BR'][0],12):
            for el in np.linspace(o['BL'][1],o['TL'][1],12): labs.add(lab(a,el))
        mg=[]
        for el in np.linspace(o['BR'][1],o['TR'][1],8):
            a=o['R'][0]
            while lab(a,el)=='WindscreenL' and a<0: a+=0.25
            mg.append(a-o['R'][0])
        print('%-10s door L %.1f R %.1f (centre %.1f) | el %.1f..%.1f | through %s | to the post %.1f deg %s'%(nm,o['L'][0],o['R'][0],o['C'][0],o['BL'][1],o['TL'][1],sorted(labs),min(mg),extra))
    show('now', door()[0])
    for nm,s_ in (('B',9.35),("B'",solve_s(-35))):
        show(nm, door(s=s_)[0], '| path +%.2f m, near lamp column %.2f m from the eye'%(s_, -F['avenue']['columns_x'][0]+s_+EYE[0]))
    lo,hi=0,30
    for _ in range(50):
        m=(lo+hi)/2
        if door_c(m)[0]['C'][0]>-40: lo=m
        else: hi=m
    o,info=door_c(m); p=c_path(m)
    rate=max((p[i+1][3]-p[i][3])/0.02 for i in range(len(p)-1))
    show('C', o, '| steer %.2f deg over F6 -> F7 (%.1f s), max %.2f deg/s, drift %.2f m'%(m,L['F7']-L['F6'],rate,info['x_drift']))

    # as built: act07_motion.TURN_DEG / heading / drift (the contract's bus_turn, the driver's PalaceTurn)
    pb=lambda q: M.palace_to_bus(np.array(q,float),L['F7'],F['frame']['bus_origin_y_stop'])
    res={}
    for k,(xx,y) in {'L':(dx0-dw/2,plat+dh/2),'R':(dx0+dw/2,plat+dh/2),'C':(dx0,plat+dh/2),'TL':(dx0-dw/2,plat+dh),'BL':(dx0-dw/2,plat),'TR':(dx0+dw/2,plat+dh),'BR':(dx0+dw/2,plat)}.items():
        d=pb((xx,y,zd))-EYE; res[k]=(math.degrees(math.atan2(d[0],d[2])), math.degrees(math.atan2(d[1],math.hypot(d[0],d[2]))))
    show('C built', res, '| TURN_DEG %.2f, max %.2f deg/s, drift %.3f m'%(M.TURN_DEG, 1.5*M.TURN_DEG/(L['F7']-L['F6']), M.drift(L['F7'])[0]))


if __name__=='__main__':
    report()

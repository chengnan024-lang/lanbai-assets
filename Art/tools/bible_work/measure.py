import numpy as np, glob, os, json
def lch(a):
    lin=np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4)
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    X=lin@M.T/np.array([0.95047,1,1.08883])
    f=np.where(X>0.008856,np.cbrt(X),7.787*X+16/116)
    L=116*f[...,1]-16; A=500*(f[...,0]-f[...,1]); B=200*(f[...,1]-f[...,2])
    return L,np.hypot(A,B),(np.degrees(np.arctan2(B,A))+360)%360
out={}
for p in sorted(glob.glob('cache/after_*.npy')):
    k=os.path.basename(p)[6:-4]; a=np.clip(np.load(p).astype(float),0,1)
    L,C,H=lch(a); luma=(a@[0.2126,0.7152,0.0722])*255
    r=dict(APL=round(luma.mean(),1), dark12=round((luma<12).mean()*100,1),
           violet15=round(((H>=290)&(H<=325)&(C>15)).mean()*100,1), violet30=round(((H>=290)&(H<=320)&(C>30)).mean()*100,1),
           lav12=round(((H>=285)&(H<=330)&(C>12)).mean()*100,1), teal=round(((H>=195)&(H<=250)&(C>12)&(L>8)).mean()*100,1))
    out[k]=r; print(k.ljust(4), r)
json.dump(out,open('cache/metrics.json','w'),indent=1)

import numpy as np
def lab(hx):
    h=hx.lstrip('#'); c=np.array([int(h[i:i+2],16)/255 for i in (0,2,4)])
    lin=np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    X,Y,Z=M@lin/np.array([0.95047,1,1.08883])
    f=lambda t: t**(1/3) if t>0.008856 else 7.787*t+16/116
    L=116*f(Y)-16; a=500*(f(X)-f(Y)); b=200*(f(Y)-f(Z))
    return L, float(np.hypot(a,b)), float((np.degrees(np.arctan2(b,a))+360)%360)
def luma(hx):
    h=hx.lstrip('#'); c=[int(h[i:i+2],16) for i in (0,2,4)]
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
if __name__=='__main__':
    import sys
    for hx in sys.argv[1:]:
        L,C,H=lab(hx); v='  VIOLET' if 290<=H<=325 and C>15 else ''
        print(f'{hx} L*{L:5.1f} C*{C:5.1f} h{H:5.0f} luma{luma(hx):5.0f}{v}')

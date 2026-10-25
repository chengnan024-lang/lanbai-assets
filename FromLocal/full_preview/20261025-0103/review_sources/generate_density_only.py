from pathlib import Path
import numpy as np
import sys
root=Path(sys.argv[1])  # Pass the intended LocalIntegration directory explicitly.
size=128
rng=np.random.default_rng(20261025)
def noise(n):
    grid=rng.random((n,n,n),dtype=np.float32)
    coord=np.arange(size,dtype=np.float32)*n/size
    idx=coord.astype(int);u=coord-idx;u=u*u*(3-2*u)
    out=np.zeros((size,size,size),np.float32)
    for x in range(2):
      for y in range(2):
       for z in range(2):
        wx=u if x else 1-u;wy=u if y else 1-u;wz=u if z else 1-u
        out+=grid[(idx[:,None,None]+x)%n,(idx[None,:,None]+y)%n,(idx[None,None,:]+z)%n]*wx[:,None,None]*wy[None,:,None]*wz[None,None,:]
    return out
a=noise(4);b=noise(8);c=noise(16);d=noise(32)
rgba=np.empty((size,size,size,4),np.uint8)
rgba[...,0]=np.clip((a*.55+b*.30+c*.15)*255,0,255)
rgba[...,1]=np.clip((c*.7+d*.3)*255,0,255)
rgba[...,2]=np.clip(a*255,0,255);rgba[...,3]=255
folder=root/'Textures';folder.mkdir(parents=True,exist_ok=True)
(folder/'CloudDensity128.bytes').write_bytes(rgba.tobytes())

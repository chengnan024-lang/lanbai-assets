import sys, json, numpy as np
sys.path.insert(0,'../lens_cine')
import ppv2
G=json.load(open('../lens_cine/grades.json'))
P={k:v['ppv2'] for k,v in G['profiles'].items()}
def disp(lin,prof): return ppv2.srgb_to_hex(ppv2.display_of(np.asarray(lin,float),prof))
for K in [4000,4500,5000,5600,6500,7500]:
    print(K, ppv2.kelvin_hex(K))
print('neutral(1.0)=',ppv2.neutral_tonemap(1.0), 'sRGB', ppv2.lin_to_srgb(ppv2.neutral_tonemap(1.0))*255)
alb_field=ppv2.hex_to_lin('#EBF6F7'); ink=ppv2.hex_to_lin('#1D3E66')
for light in ['#CFEAF0','#DDEFF2','#E6F2F2','#EAF2FF','#FFF5E5','#F6E7C0']:
    L=ppv2.hex_to_lin(light)
    for prof in ['S1','S2']:
        for T in [-6,-3,0]:
            p=dict(P[prof]); p['temperature']=T
            for E in [0.35,0.5,0.7]:
                pass
            E=0.5
            print(light,prof,'T',T,'field',disp(alb_field*L*E,p),'ink',disp(ink*L*E,p),'white0.8',disp(0.8*L*E,p),'grey',disp(0.18*L*E*2,p), 'oxblood', disp(ppv2.hex_to_lin('#5A2126')*L*E*1.2,p))

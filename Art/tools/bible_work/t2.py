import sys, json, numpy as np
sys.path.insert(0,'../lens_cine')
import ppv2
G=json.load(open('../lens_cine/grades.json'))
P={k:v['ppv2'] for k,v in G['profiles'].items()}
def disp(lin,prof): return ppv2.srgb_to_hex(ppv2.display_of(np.asarray(lin,float),prof))
field=ppv2.hex_to_lin('#EBF6F7'); ink=ppv2.hex_to_lin('#1D3E66')
for light in ['#E4F1F3','#E0F0F2','#EAF3F2']:
  L=ppv2.hex_to_lin(light)
  for T in [-4,-3]:
    p=dict(P['S1']); p['temperature']=T
    for E in [1.0,1.3,1.6,2.0]:
        print(light,'T',T,'E',E,'field',disp(field*L*E,p),'ink',disp(ink*L*E,p),'grey',disp(0.18*L*E,p),'wetroad(0.035,+spec)',disp(0.035*L*E,p))
# cabin under S2 with tubes
L=ppv2.hex_to_lin('#E4F1F3')
p=dict(P['S2']); p['temperature']=-4
for E in [0.55,0.8,1.0,1.3]:
    print('cabin E',E,'ceiling #E2DDCF',disp(ppv2.hex_to_lin('#E2DDCF')*L*E*1.2,p),'seat',disp(ppv2.hex_to_lin('#5A2126')*L*E,p),'grey',disp(0.18*L*E,p),'floor',disp(ppv2.hex_to_lin('#2E3230')*L*E*0.6,p), 'curtain', disp(ppv2.hex_to_lin('#A9BCCB')*L*E*0.8,p))
# sodium sweep
S=ppv2.hex_to_lin(ppv2.kelvin_hex(2050)); print('sodium hex',ppv2.kelvin_hex(2050))
for E in [0.6,0.9,1.2]:
    print('sweep E',E,'seat',disp(ppv2.hex_to_lin('#5A2126')*(S*E+L*0.8),p),'grey',disp(0.18*(S*E+L*0.8),p))

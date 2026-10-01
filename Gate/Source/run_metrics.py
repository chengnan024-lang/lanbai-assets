"""round 3: metrics on the finals (U7, key, U8fwd) -> final/<name>_metrics.json + final/metrics_summary.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_metrics as GM  # noqa
F = os.path.join(HERE, 'final')
out = {}
for shot, name in (('U7', 'U7_engelein'), ('key', 'keyart_239'), ('U8fwd', 'U8_forward')):
    png = os.path.join(F, name + '.png')
    idn = os.path.join(F, name + '_id.npy')
    if not (os.path.exists(png) and os.path.exists(idn)):
        print('skip', name)
        continue
    r = GM.run(shot, png, idn, os.path.join(F, name + '_metrics.json'))
    r3 = r['round3']
    out[name] = dict(APL=r['APL'], APL_glass=r['APL_through_glass'], luma_lt12=r['luma_lt12_pct'],
                     violet=r['strong_violet_pct'], L_pillars=(r['pillars'] or {}).get('L_median'),
                     L_mid_crowns=(r['mid_crowns'] or {}).get('L_median'),
                     L_colossus_crowns=(r['colossus_crowns'] or {}).get('L_median'),
                     L_haze=(r['haze_behind'] or {}).get('L_median'), steps=r['layer_steps'],
                     cloud=r['cloud'], lavender_out25=r['lavender_outside_25deg_pct'], L85_out=r['L85_outside_wound_pct'],
                     area=r['area_pct'], dL_ring=r3['dL_ring'], tide=r3['tide'], top10=r3.get('top10_sky_L'),
                     top25=r3.get('top25_sky_L'), frac_L15_40=r3['frac_L15_40_pct'], mirror_IoU=r3.get('mirror_IoU'),
                     tear_x=r3.get('tear_centroid_x_pct'), sil_gt10=r3['silhouettes_gt10pct_above_horizon'],
                     deck_sigma=r3['deck_sigma_L'], near_deck_L=r3['near_deck_L'], halo_C_0_1=r3.get('halo_C_0_1deg'),
                     halo_C_1_3=r3.get('halo_C_1_3deg'), halo_L_1_3=r3.get('halo_L_1_3deg'),
                     per_instance=r3['per_instance'])
json.dump(out, open(os.path.join(F, 'metrics_summary.json'), 'w'), indent=1)
for k, v in out.items():
    print('==', k)
    for kk, vv in v.items():
        if kk != 'per_instance':
            print('  ', kk, vv)

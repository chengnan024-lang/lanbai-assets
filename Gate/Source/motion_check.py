"""own angular speed (deg/s) of every arm's visible points from its own animation (rise / lean / track / close; the
bus's motion excluded: both samples from the same eye), max over U6 - 60 s .. U9 + 2 s; and the near-arm / bus
clearance + |v_rel| / (1.05 d) with the full relative velocity. Writes wip/motion_check.json.
Limits (round 2): colossi / pillars / Engel <= 0.5 deg/s, mid ring <= 1.0 (documented deviation), rear <= 1.0."""
import json
import os
import numpy as np
import gate_layout as G

LIMIT = dict(colossus=0.5, colossus_bg=0.5, mid=1.0, rear=1.0, surge=1.0, near=None)   # round 4: 'surge' = the multitude
# (150 3D arms rising U7 - 5 .. U7b, crown <= ~1 deg/s: the mid-layer convention, a documented deviation, README §12)

if __name__ == '__main__':
    lay = G.build_layout()
    rows = []
    for it in lay:
        if it['layer'] == 'near':
            continue
        # only while it can be seen: from its first non-zero _Reveal (round 3; GateRoot is active from U6 - 20)
        ks = it.get('reveal')
        t_vis = max(G.CUE['U6'] - 20.0, float(ks[0][0]) if ks else -1e9)
        v, t, u = G.own_speed(it, t_vis, G.CUE['U9'] + 2.0, dt=0.25, step=8)
        lim = LIMIT.get(it['layer'])
        rows.append(dict(id=it['id'], layer=it['layer'], role=it.get('role'), max_deg_s=round(v, 2),
                         at_t=None if t is None else round(t, 2), at_u=None if u is None else round(u, 2),
                         limit=lim, ok=(lim is None or v <= lim + 0.02)))
    near = []
    for it in lay:
        if it['layer'] in ('near', 'mid', 'colossus'):
            c = G.near_check(it, G.CUE['U7'], G.CUE['U9'] + 0.4, step=0.2)
            if c['min_d'] < 150:
                near.append(dict(id=it['id'], min_skin_to_shell_m=round(c['min_d'], 1), t=c['t_min'],
                                 worst_v_over_1_05d=round(c['worst_ratio'], 2), eye_deg_s=round(c['eye_deg_s'], 1)))
    # round 3 (tech M5): eye angular speed of every vertex sample INCLUDING the world's motion past the bus, for the
    # hero eye and the rear eye, U8 .. U9 + 1 (limit 60 deg/s), and the min distance of every non-near arm to the
    # shell box (limit 62 m)
    eyes = dict(main=G.EYE_SEATED, rear=G.EYE_STAND_REAR)
    omega = []
    for it in lay:
        if it['layer'] == 'near':
            continue
        worst = dict(id=it['id'], max_eye_deg_s=0.0, eye=None, t=None, min_shell_m=1e9)
        for t in np.arange(G.CUE['U8'], G.CUE['U9'] + 1.0, 0.25):
            W1, _ = G.world_centreline(it, t, 6)
            W2, _ = G.world_centreline(it, t + 0.05, 6)
            vis = W1[:, 2] > -5.0
            if not vis.any():
                continue
            b = G.bus_to_cf(np.array([0.0, 1.58, 0.0]), t)
            d = W1 - b
            dd = np.sqrt(np.maximum(np.abs(d[:, 0]) - G.BUS_BOX[0], 0) ** 2 + np.maximum(np.abs(d[:, 1]) - G.BUS_BOX[1], 0) ** 2
                         + np.maximum(np.abs(d[:, 2]) - G.BUS_BOX[2], 0) ** 2)
            worst['min_shell_m'] = min(worst['min_shell_m'], float(dd[vis].min()))
            for en, ev in eyes.items():
                e1, e2 = G.eye_cf(t, ev), G.eye_cf(t + 0.05, ev)
                a1 = W1[vis] - e1
                a2 = W2[vis] - e2
                c = np.sum(a1 * a2, 1) / np.linalg.norm(a1, axis=1) / np.linalg.norm(a2, axis=1)
                w = float(np.degrees(np.arccos(np.clip(c, -1, 1))).max() / 0.05)
                if w > worst['max_eye_deg_s']:
                    worst.update(max_eye_deg_s=round(w, 1), eye=en, t=round(float(t), 2))
        worst['min_shell_m'] = round(worst['min_shell_m'], 1)
        worst['ok'] = worst['max_eye_deg_s'] <= 60.0 and worst['min_shell_m'] >= 62.0
        omega.append(worst)
    for r in sorted(rows, key=lambda r: (r['layer'], -r['max_deg_s'])):
        print('%-12s %-16s %5.2f deg/s at t %s (u %s)  limit %s %s' % (r['layer'], r['id'], r['max_deg_s'], r['at_t'],
                                                                       r['at_u'], r['limit'], '' if r['ok'] else 'OVER'))
    for n in near:
        print('near', n)
    for o in sorted(omega, key=lambda o: -o['max_eye_deg_s'])[:8]:
        print('eye', o)
    tide_rows = []
    import json as _j
    cells = None      # round 4: build_tide always uses the v3 cells (the v2.1 atlas json is in deliver/Tentacles/_superseded~)
    for td in G.build_tide(cells):     # tide rise: the crest's own elevation speed from the U7b eye (limit ~0.3)
        a = td['anim'][0]
        e = G.E_HERO
        ts = np.linspace(a['t0'], a['t1'], 29)
        el = [np.degrees(np.arctan2(G.tide_root_at(td, t)[2] + td['size'] * td['cell']['cell_height_in_lengths'] *
                                    np.cos(np.radians(td['lean'])) - e[2], td['dist'])) for t in ts]
        tide_rows.append(float(np.max(np.abs(np.diff(el)) / np.diff(ts))))
    print('tide crest speed deg/s: median %.2f max %.2f' % (np.median(tide_rows), np.max(tide_rows)))
    json.dump(dict(own_motion=rows, clearance=near, eye_speed_U8_U9=omega,
                   tide_crest_deg_s=dict(median=round(float(np.median(tide_rows)), 3), max=round(float(np.max(tide_rows)), 3))),
              open(os.path.join(G.WIP, 'motion_check.json'), 'w'), indent=1)

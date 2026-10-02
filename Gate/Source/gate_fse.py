"""Transparent overdraw budget at U8 / U8 + 7 s (tech M11; bible 1.9: <= 4.0 full-screen equivalents). Round 8: the
lens depth prepass counted as its own line (the other Tear materials' prepass is culled in the vertex stage, v6), the
halo x its distance fade (renderer off at 0), the foot skyline + light lane added, the foot clouds retired.
Projects every transparent card of the gate from the hero eye (U8fwd framing: yaw 0, pitch 0, hFOV 90, 16:9) and sums
each card's screen coverage (overlapping cards of one part counted separately). The cabin glass (0.7) and the cloud
sea (0.9) are the critique's own estimates (their geometry is the Unity side's). Writes final/fse_U8.json."""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_layout as G  # noqa
sys.path.insert(0, os.path.join(G.LAN, 'tear', 'v2'))
import kit_mesh as K  # noqa
import tear_def as T  # noqa

W, H = 480, 270


def cam_proj(t, yaw=0.0, pitch=0.0, hfov=90.0):
    e = G.eye_cf(t)
    y, p = math.radians(yaw), math.radians(pitch)
    f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    r = np.array([math.cos(y), -math.sin(y), 0.0])
    u = np.cross(r, f)
    fl = (W / 2) / math.tan(math.radians(hfov / 2))

    def proj(P):
        d = np.asarray(P, float) - e
        z = d @ f
        return np.stack([W / 2 + fl * (d @ r) / np.maximum(z, 1e-3), H / 2 - fl * (d @ u) / np.maximum(z, 1e-3)], -1), z
    return proj


def cover(polys):
    tot = 0.0
    for poly in polys:
        im = Image.new('L', (W, H), 0)
        ImageDraw.Draw(im).polygon([tuple(p) for p in poly], fill=255)
        tot += (np.asarray(im) > 0).mean()
    return tot


def card_polys(proj, quads, znear=1.0):
    """round 4 (tech M2): every quad is CLIPPED against the near plane (Sutherland-Hodgman on the camera depth) instead
    of being dropped when one vertex is behind the eye (the 2.2 km CloudGlow quad passes under the bus after U8)."""
    out = []
    for q in quads:
        q = np.asarray(q, float)
        _, z = proj(q)
        if (z > znear).all():
            out.append(proj(q)[0])
            continue
        if (z <= znear).all():
            continue
        poly = []
        n = len(q)
        for i in range(n):
            a, b = q[i], q[(i + 1) % n]
            za, zb = z[i], z[(i + 1) % n]
            if za > znear:
                poly.append(a)
            if (za > znear) != (zb > znear):
                f = (znear - za) / (zb - za)
                poly.append(a + (b - a) * f)
        if len(poly) >= 3:
            xy, _ = proj(np.array(poly))
            out.append(np.clip(xy, -50 * W, 50 * W))
    return out


def cloudglow_add(t):
    """round 4: the ADDITIVE CloudGlow pass fades out (G.CLOUDGLOW_ADD; the bus is above the pool, the white fills the
    view); the multiply pass (CloudGlow_Lit, dst x (1 + glow)) stays. Unity: Tear_CloudGlow _Intensity keys (JSON)."""
    return G.key_at(G.CLOUDGLOW_ADD, t)


def fse_at(t):
    proj = cam_proj(t)
    S = G.tear_H(t) / T.H
    open01 = T.tear_open_param(0.18 + 0.12 * G.tear_open(t))
    e = G.eye_cf(t)
    cam_kit = e / S
    res = {}
    for p in K.all_parts():
        if p['name'].startswith(('Tear_Flap', 'Tear_FootCloud')) or p['name'] == 'Tear_Shafts':
            continue          # flaps: alpha-to-coverage cutout (opaque cost); the kit's 12-card shaft fan is NOT used
                              # at the gate (the 2 gate beams below replace it)
        V = K.deform(p, open01, cam_kit) * S
        if p['name'] == 'Tear_LightLane':       # round 8: Udon scales its x so the half width = LANE_HALF_K x D
            xc_ = 0.5 * float(T.path(np.array([0.0]))[0]) * S
            Df = float(np.linalg.norm(e[:2] - np.array([xc_, 0.0])))
            kx = float(np.clip(G.LANE_HALF_K * Df / (S * K.LANE_HALF), 0.15, 1.0))
            V = V.copy()
            V[:, 0] = xc_ + (V[:, 0] - xc_) * kx
        quads = [V[list(f)] for f in p['F']]
        if p['name'] == 'Tear_Halo':
            # round 8 (tech r4 M4): the whole halo x smoothstep(250, 1200, D); the renderer is OFF once that is ~0
            nq = len(quads)
            D = abs(float(e[1]))                     # eye -> tear plane (the tear plane is y = 0 in this frame)
            hk = max((float(G.ss((D - 250.0) / 950.0)) - 0.25) / 0.75, 0.0)    # = gate_scene.halo_dist (off < 0.05)
            hk = hk if hk >= 0.05 else 0.0
            per = max(nq // 3, 1)
            parts = [cover(card_polys(proj, quads[i * per:(i + 1) * per])) for i in range(3)]
            res['Tear_Halo (fade %.2f)' % hk] = round((parts[0] + parts[1] + parts[2]) * (1.0 if hk > 0.01 else 0.0), 3)
        elif p['name'] == 'Tear_SkyFolds':
            res[p['name']] = round(cover(card_polys(proj, quads)) * (1.0 if G.key_at(G.SKYFOLDS_FADE, t) > 0 else 0.0), 3)
        elif p['name'] == 'Tear_CloudGlow':     # two materials on one quad: CloudGlow (additive) + CloudGlow_Lit (multiply)
            c = cover(card_polys(proj, quads))
            res['Tear_CloudGlow (Lit + additive while on)'] = round(c * (1.0 + (1.0 if cloudglow_add(t) > 0 else 0.0)), 3)
        elif p['name'] == 'Tear_FootSkyline':   # round 8: only the part above the cloud tops is drawn over the sea
            q2 = []
            for q in quads:
                q = np.asarray(q, float).copy()
                q[:, 2] = np.maximum(q[:, 2], 0.0)
                q2.append(q)
            res[p['name']] = round(cover(card_polys(proj, q2)), 3)
        elif p['name'] == 'Tear_LightLane':     # round 8: on the cloud tops, DstColor One; off when its keys reach 0
            im = Image.new('L', (W, H), 0)
            dr = ImageDraw.Draw(im)
            for xy in card_polys(proj, quads):
                dr.polygon([tuple(a) for a in xy], fill=255)
            res[p['name']] = round(float((np.asarray(im) > 0).mean()) * (1.0 if G.key_at(G.LANE_FADE, t) > 0 else 0.0), 3)
        elif p['name'] == 'Tear_Lens':          # round 8 (tech r4 M5): the transparent pass + its depth prepass
            im = Image.new('L', (W, H), 0)
            dr = ImageDraw.Draw(im)
            for xy in card_polys(proj, quads):
                dr.polygon([tuple(a) for a in xy], fill=255)
            c = round(float((np.asarray(im) > 0).mean()), 3)
            res['Tear_Lens'] = c
            res['Tear_Lens depth prepass'] = c
        else:
            im = Image.new('L', (W, H), 0)
            dr = ImageDraw.Draw(im)
            for xy in card_polys(proj, quads):
                dr.polygon([tuple(a) for a in xy], fill=255)
            res[p['name']] = round(float((np.asarray(im) > 0).mean()), 3)
    lay = G.build_layout()
    tw = []
    for spc in G.tower_specs(lay):
        loc = spc['loc']
        d = loc - e
        d[2] = 0
        d /= np.linalg.norm(d)
        rt = np.array([d[1], -d[0], 0.0])
        w, h = spc['width'], spc['width']
        tw.append(np.array([loc - rt * w / 2, loc + rt * w / 2, loc + rt * w / 2 + [0, 0, h], loc - rt * w / 2 + [0, 0, h]]))
    al = [float(np.interp(t, [k[0] for k in spc['alpha']], [k[1] for k in spc['alpha']])) for spc in G.tower_specs(lay)]
    # round 4: the towers SINK (only the part above the deck counts)
    tw = []
    for spc in G.tower_specs(lay):
        loc = np.asarray(spc['loc'], float).copy()
        if spc.get('sink'):
            loc[2] += float(np.interp(t, [k[0] for k in spc['sink']], [k[1] for k in spc['sink']]))
        d = loc - e
        d[2] = 0
        d /= np.linalg.norm(d)
        rt = np.array([d[1], -d[0], 0.0])
        w = spc['width']
        hv = max(spc['width'] * 0.81 + loc[2] - 12.0, 0.0)
        z0 = 12.0
        tw.append(np.array([[*(loc - rt * w / 2)[:2], z0], [*(loc + rt * w / 2)[:2], z0], [*(loc + rt * w / 2)[:2], z0 + hv],
                            [*(loc - rt * w / 2)[:2], z0 + hv]]))
    res['Towers'] = round(cover([pp for pp, a_ in zip(card_polys(proj, tw), al) if a_ > 0.0]), 3)
    # run 6: the horizon relief cloud cards (opaque body, alpha-blended edges; counted as full quads)
    meta = json.load(open(os.path.join(G.LAN, 'deliver', 'Clouds', 'clouds_meta.json')))
    rq = []
    for spc in G.mist_positions(G.horizon_relief()) + G.mist_positions(G.FAR_CLOUDS):
        sz = meta[spc['card']]['size']
        w = spc['width']
        h = w * sz[1] / sz[0]
        loc = np.asarray(spc['loc'], float) - [0, 0, meta[spc['card']]['cloud_base_v'] * h]
        d = loc - e
        d[2] = 0
        d /= np.linalg.norm(d)
        rt = np.array([d[1], -d[0], 0.0])
        rq.append(np.array([loc - rt * w / 2, loc + rt * w / 2, loc + rt * w / 2 + [0, 0, h], loc - rt * w / 2 + [0, 0, h]]))
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    for xy in card_polys(proj, rq):
        dr.polygon([tuple(a) for a in xy], fill=255)
    res['Far clouds + horizon relief'] = round(float((np.asarray(im) > 0).mean()), 3)
    beams, wedges = G.build_shafts()
    bq = []
    for sb in beams:
        k = S if sb.get('kit_space') else 1.0
        p0 = np.asarray(sb['start']) * k
        p1 = p0 + np.asarray(sb['axis']) * sb['length'] * k
        side = np.cross(np.asarray(sb['axis']), e - p0)
        side /= np.linalg.norm(side)
        hw0, hw1 = sb['half_width'] * k, sb['half_width'] * k * sb.get('widen', 2.2)
        bq.append(np.array([p0 - side * hw0, p0 + side * hw0, p1 + side * hw1, p1 - side * hw1]))
    res['Gate beams (2)'] = round(cover(card_polys(proj, bq)), 3)
    cells = None      # round 4: build_tide always uses the v3 cells (the v2.1 atlas json is in deliver/Tentacles/_superseded~)
    tq = []
    for td in G.build_tide(cells):
        r0 = G.tide_root_at(td, t)
        Hq = td['size'] * td['cell']['cell_height_in_lengths']
        d = r0 - e
        d[2] = 0
        d /= np.linalg.norm(d)
        rt = np.array([d[1], -d[0], 0.0])
        tq.append(np.array([r0 - rt * Hq / 4, r0 + rt * Hq / 4, r0 + rt * Hq / 4 + [0, 0, Hq], r0 - rt * Hq / 4 + [0, 0, Hq]]))
    im = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(im)
    for xy in card_polys(proj, tq):
        dr.polygon([tuple(a) for a in xy], fill=255)
    # the tide's renderer is off once its material _Reveal reaches 0 (U8 + 1: the wave has receded into the haze)
    res['Tide'] = round(float((np.asarray(im) > 0).mean()), 3) if G.tide_reveal(t) > 0.0 else 0.0
    # round 8: the v5 foot clouds are retired (Tear_FootSkyline above replaces them)

    res['CabinGlass (critique estimate)'] = 0.7
    res['CloudSea cards (critique estimate)'] = 0.9
    res['TOTAL'] = round(sum(v for k, v in res.items() if k != 'TOTAL'), 2)
    return res


if __name__ == '__main__':
    out = {}
    for name, t in (('U8', G.CUE['U8']), ('U8+3.5', G.CUE['U8'] + 3.5), ('U8+7', G.CUE['U8'] + 7.0)):
        out[name] = fse_at(t)
        print(name, out[name])
    os.makedirs(os.path.join(HERE, 'final'), exist_ok=True)
    json.dump(dict(limit=4.0, note=__doc__, frames=out), open(os.path.join(HERE, 'final', 'fse_U8.json'), 'w'), indent=1)

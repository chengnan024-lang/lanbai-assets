"""Transparent overdraw budget at U8 / U8 + 7 s (tech M11; bible 1.9: <= 4.0 full-screen equivalents).
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


def card_polys(proj, quads):
    out = []
    for q in quads:
        xy, z = proj(q)
        if (z > 1.0).all():
            out.append(xy)
    return out


def fse_at(t):
    proj = cam_proj(t)
    S = G.tear_H(t) / T.H
    open01 = T.tear_open_param(0.18 + 0.12 * G.tear_open(t))
    e = G.eye_cf(t)
    cam_kit = e / S
    res = {}
    for p in K.all_parts():
        if p['name'].startswith('Tear_Flap') or p['name'] == 'Tear_Shafts':
            continue          # flaps: alpha-to-coverage cutout (opaque cost); the kit's 12-card shaft fan is NOT used
                              # at the gate (the 2 gate beams below replace it)
        V = K.deform(p, open01, cam_kit) * S
        quads = [V[list(f)] for f in p['F']]
        if p['name'] == 'Tear_Halo':
            # each card separately; the widest card (the last 2 faces' worth) fades out U8 .. U8 + 4 (bible 1.9 order)
            nq = len(quads)
            k_w = float(np.clip((G.CUE['U8'] + 4.0 - t) / 4.0, 0.0, 1.0)) if t > G.CUE['U8'] else 1.0
            per = max(nq // 3, 1)
            parts = [cover(card_polys(proj, quads[i * per:(i + 1) * per])) for i in range(3)]
            res['Tear_Halo'] = round(parts[0] + parts[1] + parts[2] * k_w, 3)
        elif p['name'] in ('Tear_SkyFolds', 'Tear_CloudGlow'):
            res[p['name']] = round(cover(card_polys(proj, quads)), 3)
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
    cells = json.load(open(os.path.join(G.LAN, 'deliver', 'Tentacles', 'Textures', 'TentacleTide_Atlas.json')))['cells']
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

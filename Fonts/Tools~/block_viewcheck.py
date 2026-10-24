# -*- coding: utf-8 -*-
"""D-33 #5: every poem block, every player, against the REAL bus (pkg/bus Bus/Source build_bus + viewcheck).

A block is the rectangle layout[player].block gives (azimuth left..right, elevation bottom..top, degrees from the main
seat's eye). Rays are cast from the eye over that rectangle every STEP degrees, the way the bus's viewcheck.py does
(walk through glass, stop at the first opaque part). A block passes when no ray inside it hits an opaque part.
The clearance is the smallest ring (0.25° steps, up to MAX_CLEAR) around the block in which a ray hits something
opaque, and which part that is (A pillar, radio, door stack ...).

Two ways (build_fonts.py picks the first that exists):
  * run_lookup(layouts, bus_dir): the bus's own table (pkg/bus 147be7c+: Bus/Docs~/viewcheck/hero_occlusion.npz +
    Bus/Source/occlusion_lookup.py, numpy only, 0.25° grid of rays from the eye against the real mesh; glass is not an
    occluder). A block passes when occ.rect(block) has blocked == 0. The bus's note: parts thinner than 0.25° can slip
    through the grid; for that, the ray mode below.
  * run(layouts, bus_dir): rays cast here with the bpy python (build_bus.build() + viewcheck.cast), 0.5° inside the block.
Both return {poem: {player: {ok, hits[], clearance_deg, clear_hit, ...}}}.
bus_dir = a checkout (or `git archive`) of pkg/bus.
"""
import math
import os
import sys

STEP = 0.5          # degrees between rays inside the block (the bus's viewcheck grid step)
RING = 0.25         # ring step for the clearance
MAX_CLEAR = 4.0     # look this far around the block for the nearest opaque part
OK_HIT = ('Glass_',)


def _load(bus_dir):
    src = os.path.join(bus_dir, 'Bus', 'Source')
    if not os.path.exists(os.path.join(src, 'viewcheck.py')):
        raise FileNotFoundError('pkg/bus checkout not found at %s (need Bus/Source/viewcheck.py)' % bus_dir)
    if src not in sys.path:
        sys.path.insert(0, src)
    import build_bus
    import bus_spec
    import viewcheck
    build_bus.build()
    bvh, owner = viewcheck.scene_bvh()
    return bus_spec, viewcheck, bvh, owner


def _hit(VC, B, bvh, owner, eb, az, el):
    passed, opq = VC.cast(bvh, owner, eb, VC.U2B(B.dir_az_el(az, el)))
    return opq


def check_block(VC, B, bvh, owner, eb, az0, az1, el0, el1):
    hits, rays = set(), 0
    n_az = max(1, int(math.ceil((az1 - az0) / STEP)))
    n_el = max(1, int(math.ceil((el1 - el0) / STEP)))
    for i in range(n_el + 1):
        el = el0 + (el1 - el0) * i / n_el
        for j in range(n_az + 1):
            az = az0 + (az1 - az0) * j / n_az
            rays += 1
            h = _hit(VC, B, bvh, owner, eb, az, el)
            if h:
                hits.add(h)
    clear, clear_hit = None, None
    if not hits:
        r = RING
        while r <= MAX_CLEAR + 1e-6 and clear is None:
            # the ring's four edges at distance r (rays every STEP along each edge)
            for az, el in _ring(az0 - r, az1 + r, el0 - r, el1 + r):
                h = _hit(VC, B, bvh, owner, eb, az, el)
                if h:
                    clear, clear_hit = r, h
                    break
            r += RING
    return dict(ok=not hits, hits=sorted(hits), rays=rays,
                clearance_deg=(round(clear - RING, 2) if clear is not None else '>= %.1f' % MAX_CLEAR),
                clear_hit=clear_hit)


def _ring(a0, a1, e0, e1):
    n_a = max(1, int(math.ceil((a1 - a0) / STEP)))
    n_e = max(1, int(math.ceil((e1 - e0) / STEP)))
    for j in range(n_a + 1):
        a = a0 + (a1 - a0) * j / n_a
        yield a, e0
        yield a, e1
    for i in range(1, n_e):
        e = e0 + (e1 - e0) * i / n_e
        yield a0, e
        yield a1, e


def run(layouts, bus_dir):
    B, VC, bvh, owner = _load(bus_dir)
    eb = VC.U2B(B.EYE)
    out = {}
    for pid, per in layouts.items():
        for pl, lay in per.items():
            b = lay['block']
            out.setdefault(pid, {})[pl] = check_block(VC, B, bvh, owner, eb, b['az'][0], b['az'][1], b['el'][0], b['el'][1])
    return out


def lookup_available(bus_dir):
    return os.path.exists(os.path.join(bus_dir, 'Bus', 'Docs~', 'viewcheck', 'hero_occlusion.npz')) and \
        os.path.exists(os.path.join(bus_dir, 'Bus', 'Source', 'occlusion_lookup.py'))


def run_lookup(layouts, bus_dir):
    src = os.path.join(bus_dir, 'Bus', 'Source')
    if src not in sys.path:
        sys.path.insert(0, src)
    import occlusion_lookup
    occ = occlusion_lookup.Occlusion(os.path.join(bus_dir, 'Bus', 'Docs~', 'viewcheck', 'hero_occlusion.npz'))
    out = {}
    for pid, per in layouts.items():
        for pl, lay in per.items():
            b = lay['block']
            a0, a1, e0, e1 = b['az'][0], b['az'][1], b['el'][0], b['el'][1]
            r = occ.rect(a0, a1, e0, e1)
            clear, clear_hit = None, None
            if r['blocked'] == 0:
                ring = RING
                while ring <= MAX_CLEAR + 1e-6 and clear is None:
                    big = occ.rect(a0 - ring, a1 + ring, e0 - ring, e1 + ring)
                    if big['blocked'] > 0:
                        clear, clear_hit = ring, max(big['by'], key=big['by'].get)
                    ring += RING
            out.setdefault(pid, {})[pl] = dict(
                ok=r['blocked'] == 0, hits=sorted(r['by']), blocked=r['blocked'], by=r['by'], window=r['window'],
                clearance_deg=(round(clear - RING, 2) if clear is not None else '>= %.1f' % MAX_CLEAR), clear_hit=clear_hit)
    return out

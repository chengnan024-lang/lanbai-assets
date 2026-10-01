# ---------------------------------------------------------------------------------------------------- v4 (round 3)
# Director's notes, round 3 (critique_awe_r2 / critique_tech_r2). ONE image; everything that does not serve it is cut.
# Few huge things and many tiny ones, nothing medium:
#   1. RIGHT GATE PILLAR close and dominant (0.5 km at az +30 at U7b, GateRoot local (+262, -1005)): it breaches as a
#      hump, leaves the cloud leaning in over the road and arches over it; its crown is always beyond the frame top.
#      LEFT PILLAR far (0.85 km, az -40, local (-546, -792)): only its whip comes into the key frame from the top left.
#   2. TWO HAND BUNDLES, unequal (left 600-700 m, nearer; right 450-550 m): braided forearms (3 fingers winding 0.6
#      turn, touching) rooted 250-400 m in front of the lens, leaving the cloud leaning ~40 deg toward the wound; the
#      upper third curls over and DOWN and the fingertips HOOK the flaps (left curl at 15-25 % H, right peel at
#      35-60 % H) at the tear plane, so the grip is physical (it survives the approach and VR parallax).
#   3. THE ENGEL: 2.2 km long, rooted 2.7 km away at az +24 in the band, leaning over the wound toward you; its crest
#      leaves the frame top, its last quarter hangs IN FRONT of the lens (local z -100) over the upper third / right lip.
#   4. Colossus 2 takes the moon (custom, its round side to the camera); colossus 1 behind the Rilke line;
#      6 background giants whose bodies stay inside the band (el <= 13 deg).
#   5. The SURGE RING: 22 small arms (200-350 m) at 2.5-4 km in the band (az +-8..+-55), all leaning toward the wound.
# No flame bundles, no side ring, no forks beyond 300 m (only the near arms keep the library's forked tips).
# Reveal (critique B8 / tech B1): GateRoot is switched on under the white cloud (U6 - 20 s); the giants are already
# standing, hidden inside towering cumulus (gate_layout.TOWERS) and by _Reveal = 0; the band brightens with S4
# (U6 -> U6 + 30 s smoothstep). Hands rise crown-first after a dome; the surge ring and the tide rise from U7.
T_HERO = CUE['U7b']
LAYOUT_CACHE = os.path.join(WIP, 'layout_v4.pkl')
E_HERO = eye_cf(T_HERO)


def at_az(az, d, z=0.0, eye=None):
    e = E_HERO if eye is None else eye
    a = math.radians(az)
    return np.array([e[0] + d * math.sin(a), e[1] + d * math.cos(a), z])


def tear_foot_cf():
    return np.zeros(3)


def tear_core_cf(t):
    """the white's centre: widest point of the lens (40 % of the height), a little behind the cloth."""
    S = tear_H(t) / TD.H
    return TD.P(TD.T_W, float(TD.path(np.array([TD.T_W]))[0]), 60.0)[()] * S


def tear_half_width(t):
    return 0.5 * (0.18 + 0.12 * tear_open(t)) * tear_H(t)


def lip_point(t, zf, side, out=0.0, y=-20.0):
    """a point on the left (side -1) / right (+1) lip at height fraction zf of H, pushed `out` m outward."""
    S = tear_H(t) / TD.H
    w = TD.width_mul(tear_open(t))
    tt = zf * TD.T_TOP
    aL, aR = TD.lips(np.array([tt]))
    a = float((aR[0] if side > 0 else aL[0]) * w) + side * out / S
    p = TD.P(tt, a, 0.0)[()] * S
    p[1] = y
    return p


def world_pts(key, root, R, scale, step=10):
    P, u = cl_points(key, step)
    return np.asarray(root) + scale * (P @ R.T), u


def height_of(key, R, scale):
    P = BL.centreline(key)['P']
    return float(scale * (P @ R.T)[:, 2].max())


def _lean_axis(root, to=(0.0, 0.0)):
    return unit(np.cross(np.array([0, 0, 1.0]), unit(np.array([to[0] - root[0], to[1] - root[1], 0.0]) + 1e-9)))


def _hero_to_final(it, R_hero, lean):
    """lean = (t0, t1, deg[, axis]): the arm bends toward the wound by deg over t0..t1; R_hero is its pose at
    T_HERO; the stored R is the FINAL pose."""
    t0, t1, deg = lean[:3]
    ax = lean[3] if len(lean) > 3 else _lean_axis(it['root'])
    a = dict(type='lean', t0=t0, t1=t1, deg=deg, axis=np.asarray(ax, float), prof='ss')
    s = anim_s(a, T_HERO)
    it['R'] = rodrigues(a['axis'], math.radians(deg * (1 - s))) @ R_hero
    it['anim'].append(a)
    return it


def own_speed(it, t0, t1, dt=0.25, step=10):
    """max own angular speed (deg/s) of the arm's visible points (the bus's motion excluded: both samples from the
    same eye) over t0..t1: (speed, t, u)."""
    best, bt, bu = 0.0, None, None
    for t in np.arange(t0, t1, dt):
        e = eye_cf(t)
        A, u = world_centreline(it, t, step)
        B, _ = world_centreline(it, t + dt, step)
        vis = (A[:, 2] > 0) & (B[:, 2] > 0)
        if not vis.any():
            continue
        a1, e1 = azel_of(A[vis] - e)
        a2, e2 = azel_of(B[vis] - e)
        v = np.hypot((a2 - a1) * np.cos(np.radians(e1)), e2 - e1) / dt
        k = int(np.argmax(v))
        if v[k] > best:
            best, bt, bu = float(v[k]), float(t), float(u[vis][k])
    return best, bt, bu


def fit_rise(it, t0, vmax, depth, prof_='trap', ease=0.2, t1_min=None, t1_max=None, direction=None):
    """add a rise starting at t0: the SHORTEST duration whose own angular speed peaks at <= vmax. direction: the
    unit vector the arm slides out along (v4: its own axis at the cloud; default straight up)."""
    a = dict(type='rise', t0=t0, t1=t0 + 10.0, depth=depth, prof=prof_, ease=ease)
    if direction is not None:
        a['dir'] = [float(x) for x in unit(np.asarray(direction, float))]
    it['anim'].insert(0, a)
    best = None
    for T in np.arange(4.0, 120.0, 1.0):
        a['t1'] = t0 + T
        if t1_max is not None and a['t1'] > t1_max + 1e-6:
            break
        v, _, _ = own_speed(it, t0, min(t0 + T, CUE['U9'] + 2.0), dt=0.35, step=14)
        if best is None or v < best[1]:
            best = (T, v)
        if v <= vmax:
            best = (T, v)
            break
    a['t1'] = t0 + best[0]
    if t1_min is not None and a['t1'] < t1_min:
        a['t1'] = t1_min
    if t1_max is not None and a['t1'] > t1_max:
        a['t1'] = t1_max
    it['rise_vmax'] = round(float(own_speed(it, t0, min(a['t1'], CUE['U9'] + 2.0), dt=0.3, step=10)[0]), 2)
    return it


# ---------------------------------------------------------------------------------------------------- moon
def _score_moon(W, u, e, urange=(0.30, 0.55)):
    az, el = azel_of(W - e)
    if W[-1, 2] < 40:
        return -1e9
    k = int(np.argmax(el))
    sec = (u > urange[0]) & (u < urange[1])
    dm = np.hypot((az[sec] - MOON_AZ) * math.cos(math.radians(8)), el[sec] - MOON_EL)
    s = -20.0 * max(dm.min() - 0.05, 0.0)
    s -= 1.0 * max(0.0, (MOON_EL + 3.0) - el[k])
    s -= 0.6 * max(0.0, el[k] - (MOON_EL + 6.0))
    s += 0.2 * min(az[-1] - MOON_AZ, 6.0)
    return s


def moon_coverage(it, t, n=41):
    """fraction of the 1.2 deg moon disc hidden by the arm at time t (skin radius from arm_radius)."""
    m = L_MOON
    e1 = np.cross(m, [0, 0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(e1, m)
    g = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(g, g)
    k = (X ** 2 + Y ** 2) <= 1
    ang = math.radians(0.6)
    D = m[None] + ang * (X[k][:, None] * e1[None] + Y[k][:, None] * e2[None])
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    e = eye_cf(t)
    W, u = world_centreline(it, t, 2)
    r = arm_radius(it, u)
    vis = W[:, 2] > 0
    if not vis.any():
        return 0.0
    V = W[vis] - e
    dist = np.linalg.norm(V, axis=1)
    Vn = V / dist[:, None]
    angr = np.arcsin(np.clip(r[vis] / dist, 0, 1))
    ca = np.arccos(np.clip(D @ Vn.T, -1, 1))
    return float((ca < angr[None]).any(1).mean())


def refine_moon(it, t0, t1, n=3):
    """small rotations of the HERO pose so the moon disc is covered as fully as possible over t0..t1."""
    best = np.mean([moon_coverage(it, t, 25) for t in np.linspace(t0, t1, n)])
    R0 = it['R'].copy()
    for sp in (1.0, 0.5, 0.25, 0.12):
        improved = True
        while improved:
            improved = False
            for ax in np.eye(3):
                for sg in (-1, 1):
                    it['R'] = rodrigues(ax, math.radians(sg * sp)) @ R0
                    c = np.mean([moon_coverage(it, t, 25) for t in np.linspace(t0, t1, n)])
                    if c > best + 1e-4:
                        best, R0, improved = c, it['R'].copy(), True
    it['R'] = R0
    return best


def track_moon(it, t_from, t_to, dt=1.5, vmax=0.45, u_sec=0.42):
    """'track' keys (rotation vectors about the root, applied after rise / lean) that keep the occluding section on
    the moon ray as the bus approaches, each step limited so the own motion stays <= vmax."""
    keys = [(t_from, np.zeros(3))]
    it['anim'].append(dict(type='track', keys=keys))
    P, u = cl_points(it['variant'], 2)
    k_sec = int(np.argmin(np.abs(u - u_sec)))
    for t in np.arange(t_from + dt, t_to + 1e-6, dt):
        rv_prev = keys[-1][1]
        keys.append((float(t), rv_prev.copy()))
        root, _ = pose_at(it, t)
        W, _ = world_centreline(it, t, 2)
        e = eye_cf(t)
        Ps = W[k_sec]
        m = L_MOON
        Q = e + float((Ps - e) @ m) * m
        a, b_ = Ps - root, Q - root
        ax = np.cross(a, b_)
        if np.linalg.norm(ax) < 1e-9:
            continue
        ang = math.atan2(np.linalg.norm(ax), float(a @ b_))
        dist = np.linalg.norm(Ps - e)
        far = np.max(np.linalg.norm(W - root, axis=1))
        amax = math.radians(vmax) * dt * dist / max(far, 1.0)
        ang = min(ang, amax)
        rv_new = rv_prev + (ax / np.linalg.norm(ax)) * ang
        keys[-1] = (float(t), rv_new)
    it['anim'][-1]['keys'] = [(k, list(map(float, v))) for k, v in keys]
    return it


def track_points(it, targets, t_from, t_to, dt=1.0, vmax=0.8, u_tip=0.97):
    """'track' keys (rotation vectors about the root) that keep the arm's point at u_tip on a moving target
    targets(t) -> CF point (the hands' fingertips riding the flaps as the tear grows and opens), each step limited
    to vmax deg/s of own motion."""
    keys = [(t_from, np.zeros(3))]
    it['anim'].append(dict(type='track', keys=keys))
    P, u = cl_points(it['variant'], 2)
    k_tip = int(np.argmin(np.abs(u - u_tip)))
    for t in np.arange(t_from + dt, t_to + 1e-6, dt):
        rv_prev = np.asarray(keys[-1][1], float)
        keys.append((float(t), rv_prev.copy()))
        root, _ = pose_at(it, t)
        W, _ = world_centreline(it, t, 2)
        a, b_ = W[k_tip] - root, np.asarray(targets(t), float) - root
        ax = np.cross(a, b_)
        if np.linalg.norm(ax) < 1e-9:
            continue
        ang = math.atan2(np.linalg.norm(ax), float(a @ b_))
        dist = np.linalg.norm(W[k_tip] - eye_cf(t))
        amax = math.radians(vmax) * dt * dist / max(np.linalg.norm(a), 1.0)
        ang = min(ang, amax)
        keys[-1] = (float(t), rv_prev + (ax / np.linalg.norm(ax)) * ang)
    it['anim'][-1]['keys'] = [(k, list(map(float, v))) for k, v in keys]
    return it


# ---------------------------------------------------------------------------------------------------- the grip
# the tear v4 flaps (kit metres, H 1000, full opening; tear_def.FLAPS v4): the left CURL at 15-25 % H (120 m) and
# the right PEEL at 35-60 % H (300 m); the fingertips hook their rolled lips
FLAP_LEN = {-1: 120.0, +1: 300.0}
GRIPS = {-1: [(0.165, 0.60, 0.30), (0.205, 0.66, 0.34), (0.245, 0.55, 0.30)],
         +1: [(0.40, 0.58, 0.36), (0.475, 0.62, 0.38), (0.55, 0.56, 0.35)]}


def grip_cf(t, side, k):
    zf, of, bf = GRIPS[side][k]
    S = tear_H(t) / TD.H
    L = FLAP_LEN[side] * S
    return lip_point(t, zf, side, out=of * L, y=-bf * L)


def _along(p0, p1, f):
    return np.asarray(p0, float) + (np.asarray(p1, float) - np.asarray(p0, float)) * f


# ---------------------------------------------------------------------------------------------------- hero arms
FOG_PILLAR = 0.05         # LanbaiFog density scale (the only true blacks)
FOG_HAND = 0.30           # hands: a dark volume in the band (body L* 15-18 against 30-34; critique B1)
FOG_ENGEL = 0.80          # 'a pale shape leans out of the haze' (body band - 8..10; its hand dark against the glow)
FOG_BG = 1.0              # background giants: band - 8 (cap 0.92 beyond 1.3 km, x height falloff)
FOG_SURGE = 1.0
FOG_COL = 0.55            # colossus 1
FOG_C2 = 0.12             # colossus 2: a black notch in the moon's aureole (L* <= 12)


def _hero(id_, layer, role, key, P, R_root, note, thick=1.0, lod=0, lods=((40, 210), (24, 120), (12, 48))):
    rng = np.random.default_rng(zlib.crc32(id_.encode()))
    root = A4.register(key, P, R_root, float(rng.random()), lods=lods, thick=thick, vofs=float(rng.uniform(0, 1)))
    it = inst(id_, layer, key, root, np.eye(3), 1.0, lod=lod, note=note)
    it['role'] = role
    return it


def pillar_R_ctrl():
    """breaches as a hump (front right), dives, leaves the cloud at (262, -1005) leaning 38 deg in over the road and
    arches over it at ~700 m; the whip falls on the far side of the road (always beyond the frame top)."""
    return [(560, -700, -90), (500, -760, 60), (445, -830, 165), (395, -900, 120), (350, -955, -10),
            (305, -990, -95), (262, -1005, 0), (212, -1035, 150), (162, -1060, 330), (115, -1070, 505),
            (60, -1055, 640), (0, -1020, 705), (-60, -985, 690), (-100, -960, 620)]


def pillar_L_ctrl():
    return [(-640, -820, -110), (-590, -805, 0), (-530, -785, 200), (-480, -765, 400), (-440, -745, 560),
            (-395, -720, 650), (-345, -700, 640), (-310, -690, 580), (-290, -684, 510)]


def engel_ctrl():
    """root 2.7 km away at az +24 (local (1130, 1040)); rises leaning over the wound toward the bus; crest at el ~27
    from the U7b eye (leaving the key frame top); the last quarter hangs in front of the lens (local z ~-100) over its
    upper third and right lip; the tip curls at el ~14 (60 % H), a quarter of the lens width right of the axis."""
    return [(1150, 1060, -140), (1110, 1020, 0), (1010, 900, 280), (870, 730, 600), (700, 520, 860),
            (520, 320, 985), (360, 150, 960), (230, 20, 840), (140, -60, 690), (85, -100, 545), (45, -112, 440)]


def hand_ctrl(side):
    """(axis ctrl, [(R_root, finger ctrl beyond the wrist)]) of a bundle."""
    g = lambda k: grip_cf(T_HERO, side, k)
    if side < 0:      # LEFT: bigger, nearer (~680 m), leaves the cloud leaning 41 deg toward the wound
        axis = [(-190, -385, -80), (-150, -322, 0), (-122, -268, 110), (-104, -228, 205)]
        f = [(17.0, [(-96, -170, 300), (-97, -118, 335), (-103, -80, 290), _along(g(0), (-110, -70, 200), 0.45),
                     g(0)]),
             (15.5, [(-82, -182, 285), (-80, -128, 312), (-86, -86, 268), _along(g(1), (-92, -70, 210), 0.45),
                     g(1)]),
             (14.0, [(-118, -176, 290), (-114, -120, 318), (-104, -78, 290), _along(g(2), (-100, -66, 230), 0.4),
                     g(2)])]
    else:             # RIGHT: smaller (~520 m), more fogged
        axis = [(262, -345, -80), (225, -287, 0), (207, -240, 100), (197, -205, 175)]
        f = [(14.0, [(196, -158, 300), (200, -122, 368), (206, -96, 350), _along(g(0), (205, -90, 300), 0.4),
                     g(0)]),
             (12.5, [(212, -165, 310), (218, -126, 392), (222, -100, 380), _along(g(1), (220, -92, 335), 0.4),
                     g(1)]),
             (11.5, [(184, -150, 320), (188, -115, 412), (196, -92, 405), _along(g(2), (204, -88, 372), 0.4),
                     g(2)])]
    return axis, f


def build_heroes():
    U6, U7, U7b, U8 = CUE['U6'], CUE['U7'], CUE['U7b'], CUE['U8']
    out = []
    # --- gate pillars (standing at activation; revealed from their towers U7 - 2 .. U7b + 6)
    P = A4.curve(A4.hook_end(pillar_R_ctrl(), 30.0, 110.0, (-0.3, 0.6, -1.0)))
    it = _hero('Pillar_R', 'colossus', 'pillar', 'PR', P, 42.0, 'right gate pillar: hump, leans in, arches over the road',
               thick=1.25)
    it['fog'] = FOG_PILLAR
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b + 6.0, 1.0)]
    out.append(it)
    P = A4.curve(A4.hook_end(pillar_L_ctrl(), 24.0, 100.0, (0.5, -0.3, -1.0)))
    it = _hero('Pillar_L', 'colossus', 'pillar', 'PL', P, 36.0, 'left gate pillar: far; only its whip in the key frame',
               thick=1.2)
    it['fog'] = FOG_PILLAR
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b + 6.0, 1.0)]
    out.append(it)
    # --- the Engel (bows in U7 - 1 .. U8 by 3 deg about its root)
    P = A4.curve(A4.hook_end(engel_ctrl(), 28.0, 130.0, (-0.6, 0.2, 0.4)))
    it = _hero('Colossus_3', 'colossus', 'engel', 'ENG', P, 82.0, "'der Engel': leans over the wound; its hand hangs "
               "in front of the lens", thick=1.15)
    it['fog'] = FOG_ENGEL
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b + 4.0, 1.0)]
    _hero_to_final(it, np.eye(3), (U7 - 1.0, U8, 3.0, _lean_axis(it['root'], (0.0, 0.0))))
    out.append(it)
    # --- hands: braided bundles, crowns break the deck after a dome, slide out along their axis, then the fingertips
    # ride the flaps as the tear grows (track keys)
    for side, name in ((-1, 'L'), (1, 'R')):
        axis, fingers = hand_ctrl(side)
        Ps = A4.braid(axis, fingers, turns=0.62 if side < 0 else 0.55, phase0=0.4 if side < 0 else 2.1)
        cls = []
        for k, ((R0, _), P) in enumerate(zip(fingers, Ps)):
            P = A4.curve(A4.hook_end([P[i] for i in np.linspace(0, len(P) - 1, 26).astype(int)], 9.0 * R0 / 15.0,
                                     95.0, (0.0, 1.0, -0.8) if side < 0 else (0.0, 1.0, -0.6)), smooth=1.5)
            it = _hero('Hand_%s%d' % (name, k), 'mid', 'hand', 'H%s%d' % (name, k), P, R0,
                       'hand bundle %s, finger %d: hooks the %s' % (name, k, 'left curl' if side < 0 else 'right peel'))
            it['bundle'] = 'Hand_' + name
            it['fog'] = FOG_HAND * (1.0 if side < 0 else 1.25)
            cls.append(it)
        # the rise: along the forearm's axis at the cloud (crown first), U6 + 10 -> ~U7b (fitted <= 1.0 deg/s)
        ax0 = unit(np.asarray(axis[1], float) - np.asarray(axis[0], float))
        for it in cls:
            Wc, _ = world_centreline(it, T_HERO, 4)
            depth = float((Wc[:, 2].max() + 25.0) / max(ax0[2], 0.3))
            it['anim'].append(dict(type='dome', t0=U6 + 4.0, t1=U6 + 11.0, centre=[float(axis[1][0]), float(axis[1][1])],
                                   radius=float(1.6 * 2 * fingers[0][0]), height=45.0))
            it['anim'].insert(0, dict(type='rise', t0=U6 + 10.0, t1=U7b - 0.5, depth=depth, prof='trap', ease=0.3,
                                      dir=[float(x) for x in ax0]))
            it['rise_vmax'] = round(float(own_speed(it, U6 + 10.0, U7b, dt=0.3, step=10)[0]), 2)
            k = int(it['id'][-1])
            track_points(it, lambda tt, s_=side, k_=k: grip_cf(tt, s_, k_), U7b, CUE['U9'] - 1.0, dt=1.0, vmax=0.6)
            out.append(it)
    return out


# ---------------------------------------------------------------------------------------------------- smaller arms
def _proc_arm(rng, e_cf, L, lean_deg, to_xy=(0.0, 0.0), curl=1.0):
    """a procedural arm in the v4 form language: leaves the cloud at e_cf leaning lean_deg toward to_xy, rises,
    crests at ~60 % of its length and curls over and down toward the wound (tip 15-25 % of L below the crest)."""
    e = np.asarray(e_cf, float)
    h = unit(np.array([to_xy[0] - e[0], to_xy[1] - e[1], 0.0]))
    pp = np.cross(np.array([0, 0, 1.0]), h)
    sl = math.tan(math.radians(lean_deg))
    w = rng.uniform(-0.06, 0.06) * L
    pts2 = [(-0.10 * sl, -0.13), (0.0, 0.0), (0.16 * sl + 0.03, 0.26), (0.30 * sl + 0.10, 0.46),
            (0.48 * sl + 0.20, 0.58), (0.62 * sl + 0.30, 0.56), (0.70 * sl + 0.36, 0.46 - 0.04 * curl),
            (0.74 * sl + 0.40, 0.36 - 0.06 * curl)]
    out = []
    for i, (hh, zz) in enumerate(pts2):
        lat = w * math.sin(math.pi * i / (len(pts2) - 1)) * (1 if i % 2 else 0.6)
        out.append(e + h * hh * L + pp * lat + np.array([0, 0, zz * L]))
    return A4.hook_end(out, 0.035 * L, rng.uniform(70, 120), h * 0.3 - np.array([0, 0, 1.0]))


SURGE_SEED = 41
BACKGROUND = [   # (az from the U7b eye, distance m, length m): bodies inside the band (crest el <= 13 deg)
    (-24.0, 3600.0, 760.0), (-36.0, 3300.0, 820.0), (-50.0, 3800.0, 900.0),
    (21.0, 4100.0, 860.0), (38.0, 3400.0, 780.0), (52.0, 3900.0, 920.0),
]


def build_others():
    U6, U7, U7b = CUE['U6'], CUE['U7'], CUE['U7b']
    rng = np.random.default_rng(SURGE_SEED)
    e = E_HERO
    out = []
    # --- background giants (standing; inside the band; revealed by their towers / _Reveal U7 - 2 .. U7b + 6)
    for i, (az, d, L) in enumerate(BACKGROUND):
        ep = at_az(az, d, 0.0)
        P = A4.curve(_proc_arm(rng, ep, L, rng.uniform(28, 40)))
        it = _hero('Colossus_bg_%02d' % i, 'colossus_bg', 'background', 'BG%d' % i, P, L / 22.0, 'background giant',
                   lod=1, lods=((28, 140), (18, 80), (10, 36)))
        it['fog'] = FOG_BG
        it['reveal'] = [(U7 - 2.0, 0.0), (U7b + 6.0, 1.0)]
        out.append(it)
    # --- colossus 1 (behind the Rilke line, az +24, 3.2 km at U7b): rises from U6 + 10 at <= 0.3 deg/s
    ep = at_az(24.5, 3200.0, 0.0)
    P = A4.curve(_proc_arm(rng, ep, 460.0, 30.0))
    it = _hero('Colossus_1', 'colossus', 'rilke', 'C1', P, 460.0 / 20.0, 'rises behind the Rilke line', lod=1,
               lods=((28, 140), (18, 80), (10, 36)))
    it['fog'] = FOG_COL
    h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
    fit_rise(it, U6 + 10.0, 0.3, h + 40.0, prof_='beta', ease=3.5)
    out.append(it)
    # --- colossus 2 (takes the moon on '...abweisen'): custom, its round side toward the camera
    M = e + 2520.0 * L_MOON
    ctrl = [(-800, 1150, -110), (-772, 1130, 0), (-700, 1085, 180), (-615, 1035, 320), M + np.array([0, 0, 0]),
            (-420, 925, 470), (-330, 875, 525), (-240, 830, 520), (-170, 800, 470), (-130, 785, 405)]
    P = A4.curve(A4.hook_end(ctrl, 26.0, 110.0, (0.2, -0.2, -1.0)))
    it = _hero('Colossus_2', 'colossus', 'moon', 'C2', P, 55.0, "takes the moon on '...abweisen'", thick=1.1)
    it['fog'] = FOG_C2
    ax_bow = unit(np.cross(unit(np.array([L_MOON[0], L_MOON[1], 0.0])), np.array([0, 0, 1.0])))
    _hero_to_final(it, np.eye(3), (U7b - 3.0, U7b + 1.0, -2.0, ax_bow))
    h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
    fit_rise(it, U6 + 8.0, 0.5, h + 80.0, prof_='beta', ease=3.5)
    it['moon_cover_hero'] = round(refine_moon(it, U7b - 0.3, U7b + 1.0), 3)
    track_moon(it, U7b + 1.0, CUE['U9'], dt=1.0, vmax=0.35, u_sec=0.36)
    out.append(it)
    # --- the surge ring: 22 small arms at 2.5-4 km in the band, az +-8..+-55, leaning toward the wound; they break the
    # deck crowns first from U7 (bible: 12 -> 30 in 12 s), <= 0.5 deg/s
    azs = []
    while len(azs) < 22:
        a = float(rng.uniform(-56, 56))
        if abs(a) < 7.5 or (-15.5 < a < -8.5) or any(abs(a - b) < 3.2 for b in azs):
            continue
        azs.append(a)
    for i, az in enumerate(sorted(azs)):
        d = float(rng.uniform(2500, 4000))
        L = float(rng.uniform(200, 350))
        ep = at_az(az, d, 0.0)
        P = A4.curve(_proc_arm(rng, ep, L, rng.uniform(22, 40)))
        it = _hero('Surge_%02d' % i, 'surge', 'surge', 'SG%02d' % i, P, L / 18.0, 'surge ring', lod=1,
                   lods=((20, 90), (12, 48), (8, 24)))
        it['fog'] = FOG_SURGE
        h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
        t0 = U7 + 1.0 * rng.random() + 2.5 * (1.0 - abs(az) / 56.0)
        fit_rise(it, t0, 0.5, h + 30.0, prof_='trap', ease=0.25)
        out.append(it)
    return out

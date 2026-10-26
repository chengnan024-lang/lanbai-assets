# -*- coding: utf-8 -*-
"""D-40 #1 切片终审图：切片三件（Seat_SeatR0、Window_R1 + Glass_WinR1、Pole_R0）在第 2 幕（夜路、管灯亮）的
Lanbai/Cabin 近似着色下，从 bus_slice.json 的六台近景机位看，再加主座位眼位的两张整车里的图；另一个模式跑六台的闪烁。

    ~/bpy/bin/python -B Bus/Docs~/slice/slice_final.py [--samples 48] [--threads 2] [--grade S2|none]
                                                       [--only seat_05m,ctx_window] [--out Bus/Docs~/slice/终审]
    ~/bpy/bin/python -B Bus/Docs~/slice/slice_final.py --sheet-only          # 只重拼 contact_sheet.png
    ~/bpy/bin/python -B Bus/Docs~/slice/slice_final.py --flicker /tmp/bus/slice_flicker [--frames 90]
        # 对六台跑 qa.py --mode flicker --view slice:<名>（DIR 里已有 JSON 的跳过），写 <out>/flicker.json，
        # 最差两台的 shimmer 热图（2 × 2 取最大缩一半）拷进 <out>

只读：/tmp/bus/bus_final_ext.blend 先拷一份到临时文件夹再从拷贝里读（前后 md5 记进 renders.json），不存 .blend；
Bus/Textures、Bus/Models 只读。

着色：直接用 Bus/Docs~/lookdev/scene_acts.py 的 build()（第 2 幕：act_material 给 Cabin_Static / Seat_* / Window_* /
Pole_* 上 反照率 ×（_CabinTubeLM.rgb × 管灯 + 环境色 × AO），座椅用零件图集；管灯罩自发光；天只给相机看）。场景
由渲染标准台（Engineering/render_harness/lbh/scene.py）起：Cycles CPU、OIDN 降噪。这里另加三条，让漫射只来自光照图
（Lanbai/Cabin 就是这样）：管灯罩对漫射光线隐身（不再在漫射上照一遍）、车厢材质的自发光不当光源采样、漫射反弹 0。
光泽反射照常追（金属、乙烯的高光里看得到亮着的车厢和管灯，代替 Unity 的车厢反射探针）。
调色：--grade S2（默认）= 标准台的 PPv2 模拟（lbh/grade.py，第 2 幕 S2，VR：不加镜头层，bloom 开）；none = Standard
视图直出。

机位：六台近景照 bus_slice.json（Bus/Source/parts/qa.py 的 SLICE_CAMS / SLICE_CROP / SLICE_PPD / look_rotation /
place_camera / ppd_size / bounds_center，和 qa.py --view slice:<名> 一样的算法）：看切片物体（Slice_SideWindow 含玻璃）
包围盒中心，朝主座位的眼退 0.5 / 1.0 m，40 × 30°、20 px/° = 834 × 614，不加头部微动。包围盒取导出的 .blend 里的
物体（= Bus.fbx），不是 qa.py 从源码现搭的那几件。近景的画面里只有切片三件（和 LanbaiBusSliceBuilder 搭的切片场景
一样），车厢别的东西只给光泽光线看（金属的光照图 E 是 0，不这样钢管是黑的；Unity 的切片场景里没有车厢探针）。
两张整车里的（主座位眼 (0.55, 1.70, 2.05)，960 × 720）：ctx_window = 偏航 61°、俯 10°、水平 90°（朝 WinR1 前半，
和 lm_seam_check.py 的 hero_window_yaw61 同一个方向）；ctx_cushion = 偏航 −30°、俯 70°、水平 80°，往左下看主座位
自己的座垫。

出：<out>/<机位>.png（每张 < 400 KB）、<out>/contact_sheet.png（带标签）、<out>/renders.json（机位、用时、md5）。
没在 Unity 里编译、导入、运行过；这是 Blender 里的近似。
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'Engineering', 'render_harness'))
sys.path.insert(0, os.path.join(ROOT, 'Bus', 'Docs~', 'lookdev'))
sys.path.insert(0, os.path.join(ROOT, 'Bus', 'Source', 'parts'))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from lbh import grade as G  # noqa: E402
from lbh import scene as S  # noqa: E402
import qa as QA  # noqa: E402        (Bus/Source/parts/qa.py: the slice cameras of bus_slice.json)
import scene_acts as SA  # noqa: E402

HERO = (0.55, 1.70, 2.05)
PIECES = {'seat': ['Seat_SeatR0'], 'window': ['Window_R1', 'Glass_WinR1'], 'pillar': ['Pole_R0']}
SLICE_OBJS = [n for v in PIECES.values() for n in v]
ORDER = ['seat_05m', 'seat_10m', 'window_05m', 'window_10m', 'pillar_05m', 'pillar_10m']
# what to look at (contact sheet + README)
LOOK = {
    'seat_05m': '从主座位的眼往下看自己的座垫和靠背：乙烯、滚边、裂纹；光照图有没有黑点、接缝',
    'seat_10m': '离 1 m 从上往下看整把座椅；左上黑色 T 形件是靠墙的固定板（整车里藏在墙和轮罩之间）',
    'window_05m': '画面里只有玻璃（窗中心，外面是夜）：窗框、窗扣、胶条都不在这台机位里',
    'window_10m': '只拍到推拉窗中间的横框和竖框（铝）；其余是玻璃',
    'pillar_05m': '立柱钢管（反射车厢）、停车按钮盒背面、按钮盒上的箍',
    'pillar_10m': '立柱稍远和按钮盒；测试的闪烁项 pillar_micro 用这台',
    'ctx_window': '整车里：主座位往右前看 WinR1 前半：窗柱、横框、窗台、胶条、扶杆',
    'ctx_cushion': '整车里：主座位往左下看自己的座垫：座垫左沿、过道；下边是靠背上沿',
}
CONTEXT = {
    'ctx_window': dict(eye=list(HERO), yaw_deg=61.0, pitch_deg=-10.0, hfov_deg=90.0, res=[960, 720]),
    'ctx_cushion': dict(eye=list(HERO), yaw_deg=-30.0, pitch_deg=-70.0, hfov_deg=80.0, res=[960, 720]),
}
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
MAX_PNG = 390 * 1024


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save_capped(im, path, limit=MAX_PNG):
    """PNG under the limit: optimised RGB, else a 256-colour palette (no dither), else smaller."""
    im.save(path, optimize=True)
    if os.path.getsize(path) <= limit:
        return 'rgb'
    q = im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(path, optimize=True)
    k = 1.0
    while os.path.getsize(path) > limit:
        k *= 0.9
        im2 = im.resize((int(im.width * k), int(im.height * k)), Image.Resampling.LANCZOS)
        im2.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
    return 'palette256' + ('' if k == 1.0 else ' x%.2f' % k)


def lanbai_cabin_only_lightmap(objs):
    """keep the diffuse on the lightmap term only (Lanbai/Cabin): tube diffusers invisible to diffuse rays, no emissive
    material sampled as a light, no diffuse bounce, no world light. Glossy rays still see everything (probe stand-in)."""
    sc = bpy.context.scene
    sc.cycles.diffuse_bounces = 0
    try:
        sc.world.cycles.sampling_method = 'NONE'
    except Exception:  # noqa: BLE001
        pass
    for m in bpy.data.materials:
        if m.name != 'TubeGlow':
            m.cycles.emission_sampling = 'NONE'
    t = objs.get('Cabin_Tubes')
    if t is not None:
        t.visible_diffuse = False
        t.visible_shadow = False


def slice_only_frame(base_hide):
    """the slice cameras see only the three pieces (the slice scene); the rest of the bus stays in the render for glossy
    rays only - the metals and the vinyl reflect the lit cabin and the tubes, a stand-in for Unity's cabin reflection
    probe (without it the steel, whose lightmap E is 0 like every metal, would be black on the night sky)."""
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE'):
            continue
        if o.name in SLICE_OBJS:
            o.hide_render = False
            continue
        o.hide_render = base_hide.get(o.name, False) or o.name == 'Ground'
        o.visible_camera = False
        o.visible_transmission = False                   # through the glass: the night sky, as in the slice scene
        o.visible_shadow = False
        o.visible_diffuse = False


def whole_bus(base_hide):
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE'):
            continue
        o.hide_render = base_hide.get(o.name, False)
        o.visible_camera = o.visible_transmission = o.visible_shadow = True
        o.visible_diffuse = o.name != 'Cabin_Tubes'
    t = bpy.data.objects.get('Cabin_Tubes')
    if t is not None:
        t.visible_shadow = False


def to_png(lin, grade):
    if grade == 'none':
        return QA.lin_to_srgb8(lin)
    codes, _, _ = G.grade(lin, {grade: 1.0}, bloom=True, lens=False)
    return G.to_u8(codes)


def slice_cams(objs):
    """bus_slice.json cameras exactly as qa.py --view slice:<id> computes them (LanbaiTestCapture 83-105), on the
    exported pieces."""
    bpy.context.view_layer.update()                       # matrix_world of the appended objects (else identity)
    out = {}
    for cid in ORDER:
        piece, dist = QA.SLICE_CAMS[cid]
        _, lo, hi = QA.bounds_center([objs[n] for n in PIECES[piece] if n in objs])
        target = QA.slice_target(cid, lo, hi)                # look_at_anchor (main 90bf00c): the window cameras
        d = np.asarray(HERO, float) - target
        eye = target + d / np.linalg.norm(d) * dist
        out[cid] = dict(piece=piece, distance=dist, target=target, eye=eye, rot=QA.look_rotation(target - eye),
                        bounds_min=lo, bounds_max=hi)
    return out


def label_font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def wrap(dr, text, font, width):
    """split text into lines that fit width px (character by character: Chinese has no spaces)."""
    lines, cur = [], ''
    for ch in text:
        if dr.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def contact_sheet(tiles, path, tw=480):
    """tiles: [(PIL image, title, line2)], 2 columns, a label band under each tile."""
    th_img = int(tw * 0.75)
    band = 62
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    W, H = tw * cols + 6 * (cols + 1), (th_img + band) * rows + 6 * (rows + 1) + 30
    sheet = Image.new('RGB', (W, H), (18, 18, 20))
    dr = ImageDraw.Draw(sheet)
    f1, f2, f0 = label_font(15), label_font(12), label_font(14)
    dr.text((8, 7), '车 · 切片终审（D-40 #1）· 第 2 幕夜路、管灯亮 · Blender 近似（Cycles），不是 Unity 截图', fill=(230, 230, 230), font=f0)
    for i, (img, t1, t2) in enumerate(tiles):
        x = 6 + (i % cols) * (tw + 6)
        y = 30 + 6 + (i // cols) * (th_img + band + 6)
        im = img.copy()
        im.thumbnail((tw, th_img), Image.Resampling.LANCZOS)
        sheet.paste(im, (x + (tw - im.width) // 2, y + (th_img - im.height) // 2))
        dr.text((x + 2, y + th_img + 4), t1, fill=(255, 255, 255), font=f1)
        for k, ln in enumerate(wrap(dr, t2, f2, tw - 6)[:2]):
            dr.text((x + 2, y + th_img + 24 + 16 * k), ln, fill=(190, 190, 190), font=f2)
    return save_capped(sheet, path)


def build_sheet(out):
    tiles = []
    for vid in ORDER + list(CONTEXT):
        p = os.path.join(out, vid + '.png')
        if not os.path.exists(p):
            continue
        if vid in QA.SLICE_CAMS:
            t1 = '%s · %.1f m · 40×30° · 只有切片三件' % (vid, QA.SLICE_CAMS[vid][1])
        else:
            sp = CONTEXT[vid]
            t1 = '%s · 主座位眼 · 偏航 %g° 俯仰 %g° · 整车' % (vid, sp['yaw_deg'], sp['pitch_deg'])
        tiles.append((Image.open(p).convert('RGB'), t1, '看：' + LOOK[vid]))
    sp = os.path.join(out, 'contact_sheet.png')
    mode = contact_sheet(tiles, sp)
    return dict(png='contact_sheet.png', mode=mode, kb=round(os.path.getsize(sp) / 1024))


FLICKER_PART = {'seat': 'seat', 'window': 'window', 'pillar': 'poles'}       # qa.py --part (only names the files)
FLICKER_KEYS = ('shimmer_mean', 'shimmer_p99', 'shimmer_frac', 'motion_std_mean', 'motion_std_p99', 'hf_raw_mean',
                'hf_raw_p99', 'hf_raw_frac', 'apl_min', 'apl_max', 'apl_max_step')


def flicker(fdir, out, frames):
    """qa.py --mode flicker --view slice:<id> for the six cameras (EEVEE, Render Samples 1, reference 4x), collected."""
    import subprocess
    os.makedirs(fdir, exist_ok=True)
    qa_py = os.path.join(ROOT, 'Bus', 'Source', 'parts', 'qa.py')
    runs = {}
    for cid in ORDER:
        part = FLICKER_PART[QA.SLICE_CAMS[cid][0]]
        js = os.path.join(fdir, '%s_slice-%s_flicker.json' % (part, cid))
        cmd = [sys.executable, '-B', qa_py, '--mode', 'flicker', '--part', part, '--view', 'slice:' + cid,
               '--frames', str(frames), '--out', fdir]
        if not os.path.exists(js):
            print('[slice_final] running', ' '.join(cmd), flush=True)
            subprocess.run(cmd, cwd=ROOT, check=True)
        runs[cid] = (js, ' '.join(['~/bpy/bin/python -B Bus/Source/parts/qa.py'] + cmd[3:-2]))
    views = {}
    for cid, (js, cmd) in runs.items():
        r = json.load(open(js, encoding='utf-8'))
        views[cid] = dict(**{k: r.get(k) for k in FLICKER_KEYS}, frames=r.get('frames'), fps=r.get('fps'),
                          size=[r.get('w'), r.get('h')], reference_ss=r.get('reference_ss'), engine=r.get('engine'),
                          eye=r.get('eye'), bounds_center=r.get('camera', {}).get('bounds_center'),
                          unity_sequence=r.get('unity_sequence'), unity_check=r.get('unity_check'),
                          seconds=r.get('seconds'), sources_commit=r.get('sources_commit'), command=cmd)
    worst = sorted(views, key=lambda c: -(views[c]['shimmer_frac'] or 0))[:2]
    heats = {}
    for cid in worst:
        part = FLICKER_PART[QA.SLICE_CAMS[cid][0]]
        src = os.path.join(fdir, '%s_slice-%s_flicker_heat_shimmer.png' % (part, cid))
        a = np.asarray(Image.open(src).convert('RGB'))
        h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2       # 2 x 2 max-pool: half size, hot pixels kept
        a = a[:h, :w].reshape(h // 2, 2, w // 2, 2, 3).max(axis=(1, 3))
        dst = os.path.join(out, 'flicker_heat_shimmer_%s.png' % cid)
        save_capped(Image.fromarray(a), dst, 200 * 1024)
        heats[cid] = os.path.basename(dst)
    rec = dict(
        what='qa.py --mode flicker 在 bus_slice.json 的六台近景机位上（--view slice:<名>）',
        layer='Blender 离线（近似）：EEVEE，Render Samples 1，参考图 4 倍同一姿态再缩回；量法照抄 LanbaiTestCapture 的 '
              'micro_motion（shimmer = 逐像素“测的图 − 参考图”亮度差随时间的标准差，shimmer_frac = 大于 4 的像素占比）',
        unity='不是 Unity 的数。Unity 层的数以总工程师的测试工具（bus_slice.json 的 sequences：seat_micro、window_micro、'
              'pillar_micro，都在 1.0 m 机位）出的为准；测试里 pillar_shimmer / window_shimmer ≤ 0.005，gate false（初值）。',
        differences='qa.py 现搭切片三件（Bus/Source 的 seat.py / window.py / poles.py，不是导出的减面网格）、MAT_TABLE 的'
                    '平色材质（没有零件图集）、管灯是 EEVEE 实时面光（不是 _CabinTubeLM）、没有 Lanbai/Cabin 的几何高光抗锯齿'
                    '（金属上的数应当比 Unity 大）、切片机位不加反射探针、没有 PPv2。',
        views=views, worst_two=worst, heat_images=heats,
        heat_note='热图 = qa.py 的 heat_shimmer（颜色 0 → 12 级亮度），这里 2 × 2 取最大缩成一半（亮点不丢）')
    with open(os.path.join(out, 'flicker.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    for cid in ORDER:
        v = views[cid]
        print('[slice_final] flicker %-10s shimmer_mean %.3f p99 %.2f frac %.5f' % (cid, v['shimmer_mean'], v['shimmer_p99'],
                                                                                   v['shimmer_frac']))
    print('[slice_final] worst two:', worst)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', default='/tmp/bus/bus_final_ext.blend')
    ap.add_argument('--out', default=os.path.join(HERE, '终审'))
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--grade', default='S2', help="harness grade key for act 2 (S2), or 'none' (Standard view)")
    ap.add_argument('--only', default='', help='comma list of view ids (default: all eight)')
    ap.add_argument('--no-sheet', action='store_true')
    ap.add_argument('--sheet-only', action='store_true', help='only rebuild contact_sheet.png from the PNGs in --out')
    ap.add_argument('--flicker', default='', metavar='DIR',
                    help='instead of rendering: run qa.py --mode flicker on the six slice cameras into DIR (skipping '
                         'views that already have a JSON there), then write <out>/flicker.json and the worst two heat maps')
    ap.add_argument('--frames', type=int, default=90, help='--flicker: frames per view (qa.py default 90)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.sheet_only:
        print('[slice_final] contact sheet:', build_sheet(a.out))
        return
    if a.flicker:
        flicker(a.flicker, a.out, a.frames)
        return
    only = [s for s in a.only.split(',') if s]
    md5_before = md5(a.blend)
    tmp = tempfile.mkdtemp(prefix='slice_final_')
    work = os.path.join(tmp, 'bus_final_ext_copy.blend')
    shutil.copyfile(a.blend, work)                         # read the copy, never the original

    S.new_scene(samples=a.samples, res=(834, 614), denoise=True, threads=a.threads)
    sc = bpy.context.scene
    ctx = dict(t=30.0, cam=S.camera_spec('hero'), eye=list(HERO), act='02', args={'act': '2', 'blend': work},
               U2B=S.U2B, lbh_scene=S, quality='final')
    info = SA.build(ctx)
    objs = {o.name: o for o in bpy.data.objects}
    lanbai_cabin_only_lightmap(objs)
    base_hide = {o.name: o.hide_render for o in bpy.data.objects}
    rec = dict(views={}, scene=info, blend=a.blend, blend_md5_before=md5_before, samples=a.samples, threads=a.threads,
               grade=a.grade if a.grade == 'none' else '%s (lbh/grade.py, bloom on, no lens layer = VR)' % a.grade,
               denoise='OpenImageDenoise', engine='Cycles CPU',
               shading='scene_acts.build(act 2) + diffuse from the lightmap only (tube diffusers hidden from diffuse '
                       'rays, emissive materials not sampled as lights, diffuse bounces 0); glossy rays traced')
    cams = slice_cams(objs)

    # ---- the six test cameras: the three pieces alone (as in the slice scene)
    cd = bpy.data.cameras.new('SliceCam')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(QA.SLICE_CROP[1])
    cd.clip_start, cd.clip_end = 0.02, 200.0
    cam = bpy.data.objects.new('SliceCam', cd)
    sc.collection.objects.link(cam)
    w_, h_ = QA.ppd_size(QA.SLICE_CROP[0], QA.SLICE_CROP[1], QA.SLICE_PPD)
    pngs = {}
    for cid in ORDER:
        if only and cid not in only:
            continue
        c = cams[cid]
        slice_only_frame(base_hide)
        sc.camera = cam
        QA.place_camera(cam, c['eye'], c['rot'])
        sc.render.resolution_x, sc.render.resolution_y = w_, h_
        t0 = time.time()
        lin = S.render_linear(os.path.join(tmp, cid + '.exr'))
        px = to_png(lin, a.grade)
        p = os.path.join(a.out, cid + '.png')
        how = save_capped(Image.fromarray(px), p)
        pngs[cid] = p
        rec['views'][cid] = dict(kind='bus_slice.json camera', look_at_object=c['piece'], distance_m=c['distance'],
                                 eye=[round(float(v), 4) for v in c['eye']], target=[round(float(v), 4) for v in c['target']],
                                 bounds_min=[round(float(v), 4) for v in c['bounds_min']],
                                 bounds_max=[round(float(v), 4) for v in c['bounds_max']],
                                 crop_deg=list(QA.SLICE_CROP), ppd=QA.SLICE_PPD, res=[w_, h_], scene='the three pieces only',
                                 seconds=round(time.time() - t0, 1), png=os.path.basename(p), png_kb=round(os.path.getsize(p) / 1024),
                                 png_mode=how, mean_srgb=round(float(px.mean()), 1), look_at=LOOK[cid])
        print('[slice_final] %s %.0f s -> %s' % (cid, time.time() - t0, p), flush=True)

    # ---- two views from the hero eye in the whole bus
    whole_bus(base_hide)
    for vid, spec in CONTEXT.items():
        if only and vid not in only:
            continue
        cobj = S.add_camera(dict(spec), name='Cam_' + vid)
        t0 = time.time()
        lin = S.render_linear(os.path.join(tmp, vid + '.exr'))
        px = to_png(lin, a.grade)
        p = os.path.join(a.out, vid + '.png')
        how = save_capped(Image.fromarray(px), p)
        pngs[vid] = p
        rec['views'][vid] = dict(kind='hero eye, whole bus', **spec, scene='the whole bus (scene_acts act 2)',
                                 seconds=round(time.time() - t0, 1), png=os.path.basename(p),
                                 png_kb=round(os.path.getsize(p) / 1024), png_mode=how, mean_srgb=round(float(px.mean()), 1),
                                 look_at=LOOK[vid])
        cobj.hide_render = True
        print('[slice_final] %s %.0f s -> %s' % (vid, time.time() - t0, p), flush=True)

    # ---- contact sheet (from whatever PNGs are in the folder, so --only re-renders keep the sheet whole)
    if not a.no_sheet:
        rec['contact_sheet'] = build_sheet(a.out)
    rec['blend_md5_after'] = md5(a.blend)
    rec['blend_untouched'] = rec['blend_md5_after'] == md5_before
    rec['note'] = ('Blender 里的近似（Cycles、scene_acts 的第 2 幕着色），不是 Unity 截图；没在 Unity 里编译、导入、运行过。'
                   '近景只有切片三件（和切片场景一样），整车两张是整辆车。')
    rj = os.path.join(a.out, 'renders.json')
    old = {}
    if only and os.path.exists(rj):
        try:
            old = json.load(open(rj, encoding='utf-8')).get('views', {})
        except Exception:  # noqa: BLE001
            old = {}
    rec['views'] = {**old, **rec['views']}
    with open(rj, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    print('[slice_final] blend untouched: %s -> %s' % (rec['blend_untouched'], rj))


if __name__ == '__main__':
    main()

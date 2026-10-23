# -*- coding: utf-8 -*-
"""渲染标准台 · 一条命令：搭场景 → 机位 → （车壳）→ Cycles 渲染 → PPv2 模拟调色 → 量数 → 存档。

  ~/bpy/bin/python Engineering/render_harness/lbh_render.py --scene <你的脚本.py> --cam hero --grade S4 \
        --act 04 --t 155.10 --out /tmp/<包>/r01 [--bus bible_v2|local_v1|none|fbx:<路径>] [--glass]
        [--quality preview|final] [--samples N] [--res 960x540] [--lens clean|archive|none] [--vr]
        [--set k=v ...]

--scene 脚本里写一个函数  build(ctx)  ：ctx 是 dict（t、cam、eye、act、args、U2B、lbh 模块），在里面往当前 bpy
场景里加东西（导入 FBX、摆卡、灯、天空的世界节点……）。build 可以返回一个 dict，会原样写进 metrics.json 的 scene 栏。
输出（--out 目录）：linear.exr（场景线性）、linear.npy（float16，给 lbh_grade 重调色）、graded.png（调色后）、
metrics.json（量的数 + 目标 APL + 用了的机位 / 调色状态）、stranger/（640 px 匿名缩略图 + 提问）。"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from lbh import grade as G  # noqa: E402
from lbh import measure as M  # noqa: E402
from lbh import sheets as SH  # noqa: E402


def grade_spec(args):
    spec = {}
    for part in args.grade.split('+'):
        if '=' in part:
            k, w = part.split('=')
            spec[k] = float(w)
        else:
            spec[part] = 1.0
    if args.lens == 'clean':
        spec['LENS_CLEAN'] = 1.0
    elif args.lens == 'archive':
        spec['LENS_CLEAN'] = 1.0
        spec['LENS_ARCHIVE'] = 1.0
    if args.dev:
        st = G.blend({k: v for k, v in spec.items() if not k.startswith(('EXPO', 'LENS'))})
        k, w = G.expo_weight(args.dev, st['postExposure'])
        spec[k] = w
    return spec


def finish(lin, args, cam, out, scene_info=None, t_render=None):
    """grade + measure + write; shared by lbh_render and lbh_grade."""
    G.BLOOM_TINT_MODE = args.bloom_tint
    spec = grade_spec(args)
    codes, st, bl = G.grade(lin, spec, bloom=not args.no_bloom, lens=(args.lens != 'none' and not args.vr))
    u8 = G.to_u8(codes)
    png = os.path.join(out, 'graded.png')
    Image.fromarray(u8).save(png)
    m = M.measure(u8, act=args.act, cam=cam)
    rec = dict(metrics=m, cam=cam, grade_spec=spec, grade_state=st,
               bloom_share_of_APL=round(float(m['APL'] - M.measure(G.to_u8(G.grade(lin, spec, bloom=False, lens=(args.lens != 'none' and not args.vr))[0]))['APL']), 2) if not args.no_bloom else 0.0)
    if args.t is not None:
        rec['t'] = args.t
        rec['target'] = M.apl_target(args.t)
    if scene_info:
        rec['scene'] = scene_info
    if t_render is not None:
        rec['render_seconds'] = round(t_render, 1)
    rec['lens'] = args.lens
    rec['bloom_tint'] = args.bloom_tint
    rec['note'] = args.note or ''
    json.dump(rec, open(os.path.join(out, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.note:
        open(os.path.join(out, 'note.txt'), 'w', encoding='utf-8').write(args.note + '\n')
    SH.stranger_thumb(png, os.path.join(out, 'stranger'))
    return rec


def common_args(ap):
    ap.add_argument('--grade', default='S10', help='profile 键（S1..S12、S4c、S7a…），可叠：S3+S4=0.4+EXPO_UP=0.1')
    ap.add_argument('--dev', type=float, default=None, help='这一帧的曝光事件 ΔEV（自动解 EXPO_UP / EXPO_DOWN 的权重）')
    ap.add_argument('--lens', default='none', choices=['none', 'clean', 'archive'], help='桌面镜头层（暗角；颗粒不模拟）。和本地桌面截图比时用 clean')
    ap.add_argument('--vr', action='store_true', help='VR：不加任何镜头层')
    ap.add_argument('--no-bloom', action='store_true')
    ap.add_argument('--bloom-tint', default='single', choices=['single', 'double'],
                    help='single（默认）= 设计的颜色 = Unity 里 Grading 默认做了补偿以后的样子；double = 没补偿的 PPv2（颜色被线性化两次）')
    ap.add_argument('--act', default=None, help='色板键：01 02 03 04 04c 05 06 07a 07b 08 08b 09 10 11 12')
    ap.add_argument('--t', type=float, default=None, help='时间轴秒（只用来查圣经 §2 的目标 APL；场景脚本自己用 ctx["t"]）')
    ap.add_argument('--note', default=None, help='这一轮的一句话（写进 note.txt，迭代总览会用）')
    ap.add_argument('--out', required=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scene', required=True)
    ap.add_argument('--cam', default='hero')
    ap.add_argument('--yaw', type=float, default=None)
    ap.add_argument('--pitch', type=float, default=None)
    ap.add_argument('--hfov', type=float, default=None)
    ap.add_argument('--res', default=None, help='例如 960x540；默认取机位的 res（preview 质量时减半）')
    ap.add_argument('--bus', default='bible_v2', help='bible_v2 | local_v1 | none | fbx:<路径>')
    ap.add_argument('--glass', action='store_true', help='车窗上加一层薄玻璃（4%% 菲涅尔反射）')
    ap.add_argument('--interior-ambient', default=None, help='车厢内壁的环境色（线性 r,g,b），例如 0.02,0.024,0.035')
    ap.add_argument('--quality', default='preview', choices=['preview', 'final'])
    ap.add_argument('--samples', type=int, default=None)
    ap.add_argument('--set', action='append', default=[], help='传给场景脚本的 k=v（ctx["args"]）')
    ap.add_argument('--fse', action='store_true', help='另外量透明叠绘 FSE（物体上设自定义属性 lb_fse = 层名，或用 --fse-pattern）')
    ap.add_argument('--fse-pattern', action='append', default=[], help='物体名的正则，匹配到的算透明层')
    ap.add_argument('--fse-res', default='480x270')
    common_args(ap)
    args = ap.parse_args()

    from lbh import scene as S
    cam = S.camera_spec(args.cam, yaw_deg=args.yaw, pitch_deg=args.pitch, hfov_deg=args.hfov)
    cam['name'] = args.cam
    if args.res:
        w, h = (int(x) for x in args.res.lower().split('x'))
        cam['res'] = [w, h]
    elif args.quality == 'preview':
        cam['res'] = [cam['res'][0] // 2, cam['res'][1] // 2]
    samples = args.samples or (48 if args.quality == 'preview' else 384)
    S.new_scene(samples=samples, res=tuple(cam['res']))
    if args.t is None and 't' in cam:
        args.t = cam['t']
    ctx = dict(t=args.t, cam=cam, eye=cam['eye'], act=args.act, args=dict(kv.split('=', 1) for kv in args.set),
               U2B=S.U2B, lbh_scene=S, quality=args.quality)
    spec = importlib.util.spec_from_file_location('lbh_user_scene', os.path.abspath(args.scene))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    info = mod.build(ctx) or {}
    if args.bus.startswith('fbx:'):
        S.import_unity_fbx(args.bus[4:])
    elif args.bus != 'none':
        amb = tuple(float(x) for x in args.interior_ambient.split(',')) if args.interior_ambient else None
        S.bus_shell(args.bus, glass=args.glass, interior_ambient=amb)
    S.add_camera(cam)
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    lin = S.render_linear(os.path.join(args.out, 'linear.exr'))
    dt = time.time() - t0
    np.save(os.path.join(args.out, 'linear.npy'), lin.astype(np.float16))
    info.update(dict(bus=args.bus, glass=args.glass, samples=samples, res=cam['res']))
    if args.fse or args.fse_pattern:
        from lbh import fse as F
        fw, fh = (int(x) for x in args.fse_res.lower().split('x'))
        info['fse'] = F.measure(args.out, res=(fw, fh), patterns=args.fse_pattern)
    rec = finish(lin, args, cam, args.out, info, dt)
    m = rec['metrics']
    tgt = rec.get('target')
    if 'fse' in info:
        print('[lbh] FSE total %.3f  layers %s  max layers/pixel %s' % (info['fse'].get('total', 0), info['fse'].get('layers'), info['fse'].get('max_layers_per_pixel')))
    print('[lbh] %s  APL %.1f%s  purple %.2f%%  brightest at %s  (%0.0f s render)' % (
        args.out, m['APL'], (' (target %.0f, %s)' % (tgt['APL'], tgt['phase'])) if tgt else '', m['purple_pct'],
        m['brightest'].get('centroid_az_el', m['brightest']['centroid']), dt))


if __name__ == '__main__':
    main()

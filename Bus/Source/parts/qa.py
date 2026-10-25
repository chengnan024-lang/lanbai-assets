# -*- coding: utf-8 -*-
"""D-40 / D-40a 的 Blender 层检查（车的零件：seat / window / poles，零件和机位都来自 parts/preview.py）。

    ~/bpy/bin/python Bus/Source/parts/qa.py --mode neutral --part poles [--views a,b] [--samples 64] [--res-pct 100]
    ~/bpy/bin/python Bus/Source/parts/qa.py --mode flicker --part poles [--view aisle_2m | --view slice:pillar_10m]
                                           [--frames 90] [--fps 90] [--crop 32,24] [--ppd 20] [--engine eevee]

别的会话正在改 seat.py / common.py / materials.py / build_bus.py 的时候，这些文件可能一时 import 不了。那就先把
提交过的源码拷一份，用 LANBAI_BUS_SRC 指过去（qa.py 自己照常从工作区跑）：
    git archive HEAD Bus/Source Bus/Textures | tar -x -C /tmp/snap
    LANBAI_BUS_SRC=/tmp/snap/Bus/Source ~/bpy/bin/python Bus/Source/parts/qa.py --mode ...

--mode neutral（D-40 #2 中性光）：只留零件自己的物体，放在一块 18% 灰的地上；均匀的白环境光（一个常数颜色的
    “HDRI”，没有车厢管灯、没有太阳），Standard 视图变换、Look None（不调色）。机位和 preview.PARTS 的完全一样
    （1280 × 720、水平 64° = 20 px/°）。每个机位的左下角放一张 18% 灰卡和一张 90% 白卡（只给相机看，不投影、不进
    反射，所以不挡零件的光），先用一张只渲灰卡那一小块的低采样图量灰卡，把曝光（EV）定到灰卡读 sRGB 118，再渲正图。
    出 /tmp/bus/parts/<part>_<view>_neutral.png 和 <part>_neutral.json（每张的 EV、灰卡 / 白卡实际读数）。
    材质用定稿的那套（materials.apply_details，和 preview 一样）。这张图要回答：不靠灯光，认不认得出
    乙烯、搪瓷漆、阳极铝、橡胶、漆过的钢管。认不出就是材质的问题（D-40 #2：不许靠灯光救）。
    渲染器 Cycles（CPU、降噪）。

--mode flicker（D-40a #5 头部微动，总导演 10-25 改：不用 Workbench）：EEVEE（'BLENDER_EEVEE'），
    Render Samples = 1（scene.eevee.taa_render_samples = 1：不做 TAA 累积，一帧就是一次光栅化、一个像素一个
    采样点，最接近 Unity 不开 MSAA 的一帧；实测 1 个采样时 filter_size 1.5 和 0 出的图逐像素相同，采样点在像素
    中心）。90 帧、90 fps，头部按总工程师 Unity 工具同一条运动走（±2 cm、±1°，两个正弦叠加，平滑、每次跑都一样）。
    像素密度 20 px/°：在 preview 的机位上，以 target 为中心裁 32 × 24°（按 Unity 工具的 ppd 公式 = 657 × 487）；
    或者用 --view slice:<seat_05m|seat_10m|window_05m|window_10m|pillar_05m|pillar_10m>，照 bus_slice.json 的机位
    （看切片物体包围盒中心，朝主座位的眼退 distance，40 × 30°，834 × 614）。
    材质：Lanbai/Cabin 的数（圣经 §4.2 = build_bus.MAT_TABLE、Cabin/README.md §2）：Principled 的 Roughness =
    1 − 光滑度（Unity Standard 的 perceptual roughness，两边都是 α = r²），Metallic 照表，底色照表；立柱 / 顶杆
    （Steel）加 Lanbai/Cabin 的 _HeightSmooth 握手带（y 1.62–2.42 光滑度 0.80，两头 5 cm smoothstep，
    LanbaiCabin.shader 第 261–262 行）。法线：几何法线；--detail-normals vinyl（默认）给乙烯加 Unity 同一张
    皮纹法线（Cabin_SeatLeather_N_0.30m，0.35，30 cm 一格，LanbaiBusBuild 的 Detail()），none = 一张都不加。
    不用 materials.apply_details（那套程序化旧化在 Unity 里是烘好的贴图，这里只比光滑度和金属度）。
    光：车厢的 10 根管灯，照 bake_lightmap.add_tubes 烘 _CabinTubeLM 时的样子摆（真位置、0.12 × (长 − 0.06) m 的
    面光、冷白 #E4F1F3、朝上一盏 12% 的副灯），功率取烘焙标定出来的那个（bake_report.json 的 watts_per_tube：
    7 个中段座垫平均 E = 0.60）。面光的漫射只有直射（Unity 的光照图还带反弹，所以这里的暗处更暗）；高光按比例
    缩到“管灯在金属里的亮度 = Unity 管灯罩的自发光”（LanbaiBusBuild TubeDiffuser 的 _EmissionColor，亮度 1.94；
    Blender 面光的辐亮度 = P / (π A)，实测 EEVEE 12.47、Cycles 12.71 对 12.73）。面光的高光就是“管灯在立柱上拉出
    的长竖高光”，正是要看闪不闪的东西。preview 机位再加一个 EEVEE 球形反射探针（过道中间、1.70 m、256 / 面，
    圣经的车内立方图），金属里映出亮着的车厢，而不是黑的夜；切片机位不加（Unity 的切片场景里也没有车厢探针）。
    阴影默认关：Unity 里管灯是烘好的光照图、没有实时阴影；EEVEE 的软阴影是随机追踪的，1 个采样时每帧是噪点，
    会被 hf 当成闪烁（实测：关掉以后头不动，连续 4 帧逐像素相同，hf = 0）。夜路：世界只有一点暗蓝灰
    （#30343A × 0.03），没有太阳。
    量数照抄 Engineering/UnityTest/Editor/LanbaiTestCapture.cs（origin/pkg/engineering ee337a1）：
      Luma = 0.2126 R + 0.7152 G + 0.0722 B（8 位 sRGB，float，第 711 行）；
      逐像素累加 sum、sum²、二阶时间差分 dd = y − 2·p1 + p2 的平方（第 511–517 行），APL = 每帧平均亮度（第 518 行）；
      std = √max(0, sum²/n − m²)（第 533 行）；hf = √(Σdd² / (n − 2) / 6)（第 534 行：白噪声时二阶差分的方差是 6σ²，
      ÷6 后和 std 同一尺度，平滑的运动几乎不算，来回跳的闪烁 / 爬动才算）；
      std_mean、std_p99、hf_mean、hf_p99、hf_frac（hf > 阈值 6 的像素占比）、apl_min / apl_max / apl_max_step
      （相邻两帧 APL 的最大跳变）（第 537–548 行）；平均 Avg（第 577 行）；百分位 Pct = 排序后取第 (int)(q·(N−1)) 个
      （第 578–583 行）；热图 Img.Heat（第 773–791 行）；
      头部运动 W() 和位置 = 眼 + rot·off、朝向 = rot·q（第 498–508、573–576 行）；超采样 1、不开 MSAA（第 464、255 行）；
      ppd 定尺寸（第 130–138 行）；look_at_object + toward + distance 的机位（第 83–105 行）。
    出 /tmp/bus/parts/<part>_<view>_flicker.json、..._flicker_heat.png（hf 热图）、..._flicker_heat_std.png（std 热图）、
    ..._flicker_f000.png（第一帧）。
    **这是 Blender 里的近似，不是 Unity 的测量；Unity 层的结果以总工程师测试工具（LanbaiTestCapture）出的为准**
    （D-40a #4：三层分开记）。和 Unity 不同的地方：没有 Lanbai/Cabin 的几何高光抗锯齿（D-40 #4，Blender 的节点
    拿不到 ddx / ddy，所以金属上的数应当比 Unity 的差）；没有零件图集的法线 / 遮罩、mip 和贴图压缩；管灯的漫射
    在 Unity 里是烘好的 _CabinTubeLM（带反弹和 AO），这里是 EEVEE 的实时面光（只有直射、没有阴影）；Unity 的高光
    来自反射探针（和主光），这里来自缩过的面光高光加一个球形探针；没有 PPv2 调色。
    --engine workbench：旧的 Workbench 路线，**不看高光**（没有 PBR 高光，看不出高光闪烁），只能看几何边缘的爬动，
    默认不用。--engine cycles_point：没有 libEGL 时的备用（Cycles 1 spp、像素中心点采样、只有直射的点光和太阳，
    同样不抗锯齿），数和 EEVEE 的不能直接比。JSON 里写明用的是哪个。

EEVEE / Workbench 在没有显示器的机器上要 libEGL（Mesa llvmpipe 就行；EGL_BAD_MATCH 的警告不碍事，第一帧编译
shader 约 20 s）。系统里没有 libEGL.so.1 时：装 libegl1 + libegl-mesa0，或者把这两个 deb 解到一个文件夹，
传 --egl-dir（或设 LANBAI_EGL_DIR），脚本会从那里预载。都没有就报错退出（退出码 3），或者 --allow-fallback 改用
cycles_point。

退出码：0 成功；2 参数不对；3 没有 EGL；4 零件 / 场景搭不起来（多半是别的会话正在改 seat.py 等，用 LANBAI_BUS_SRC）。
没有在 Unity 里编译、运行过；Blender 层的数只代表 Blender 层。
"""
import argparse
import ctypes
import json
import math
import os
import shutil
import sys
import tempfile
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.environ.get('LANBAI_BUS_SRC') or os.path.dirname(HERE))
sys.path.insert(0, SRC)

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from PIL import Image  # noqa: E402

try:
    import build_bus as BB  # noqa: E402
    import bus_spec as B  # noqa: E402
    from parts import preview as PV  # noqa: E402
except Exception:                                    # the lead may be mid-edit in seat.py / common.py / build_bus.py
    traceback.print_exc()
    print('[qa] ERROR: the bus sources in %s do not import. If another session is editing them, snapshot the committed\n'
          '     ones and point LANBAI_BUS_SRC at the copy:\n'
          '       git archive HEAD Bus/Source Bus/Textures | tar -x -C /tmp/snap\n'
          '       LANBAI_BUS_SRC=/tmp/snap/Bus/Source ~/bpy/bin/python Bus/Source/parts/qa.py ...' % SRC)
    sys.exit(4)

CAPTURE_CS = 'origin/pkg/engineering:Engineering/UnityTest/Editor/LanbaiTestCapture.cs (ee337a1)'
TARGET_GREY = 118.0          # 18% 灰卡在 sRGB 里的读数
GREY_ALBEDO, WHITE_ALBEDO, FLOOR_ALBEDO = 0.18, 0.90, 0.18

# 总工程师 bus_slice.json 的六台机位（origin/pkg/engineering:Engineering/UnityTest/tests/bus_slice.json）：
# 看切片物体的包围盒中心，朝主座位的眼退 distance，裁 40 × 30°，20 px/°。切片物体 = 车里真位置上的那一件
# （Bus/Editor/LanbaiBusSliceBuilder.cs：Slice_Seat = SeatR0 主座位，Slice_SideWindow = WinR1，Slice_Pillar = PoleR0）。
SLICE_CAMS = {
    'seat_05m': ('seat', 0.5), 'seat_10m': ('seat', 1.0),
    'window_05m': ('window', 0.5), 'window_10m': ('window', 1.0),
    'pillar_05m': ('pillar', 0.5), 'pillar_10m': ('pillar', 1.0),
}
SLICE_CROP, SLICE_PPD = (40.0, 30.0), 20.0

# Lanbai/Cabin _HeightSmooth on the stanchions (LanbaiBusBuild.cs 'Steel'; LanbaiCabin.shader 261-262)
STEEL_BAND = (1.62, 2.42, 0.80)
# the tube lights exactly as bake_lightmap.add_tubes makes them for _CabinTubeLM (#E4F1F3, 0.12 x (length - 0.06) m at
# CEIL_Y - 0.05, an up-facing twin at 12 %), at the power its calibration found (bake_report.json watts_per_tube: mean
# of 7 mid-cabin cushions E = 0.60). Their specular is scaled so the tube reflects as bright as Unity's tube diffuser
# (LanbaiBusBuild 'TubeDiffuser' _EmissionColor (1.632, 2.024, 2.042), luma 1.95): that is what the cabin cubemap gives
# the metals in Unity. Blender area light radiance = P / (pi A) (measured: EEVEE 12.47, Cycles 12.71 vs 12.73).
TUBE_LIN = (0.776, 0.882, 0.894)
TUBE_EMISSION_LUMA = 0.2126 * 1.632 + 0.7152 * 2.024 + 0.0722 * 2.042
TUBE_WATTS_DEFAULT = 9.01


def tube_watts():
    """watts per tube from the lightmap bake's report (the one next to these sources, else the repo's), else 9.01."""
    for d in (os.path.join(SRC, '..', 'Docs~'), os.path.join(HERE, '..', '..', 'Docs~')):
        try:
            return float(json.load(open(os.path.join(d, 'bake_report.json')))['watts_per_tube']), os.path.normpath(d)
        except Exception:
            continue
    return TUBE_WATTS_DEFAULT, 'default'


# ------------------------------------------------------------------------------------------------ small helpers
def srgb_to_lin(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def luma8(a):
    """LanbaiTestCapture.cs 711: Img.Luma, on 8-bit sRGB values (float32, same order of operations)."""
    a = a.astype(np.float32)
    return np.float32(0.2126) * a[..., 0] + np.float32(0.7152) * a[..., 1] + np.float32(0.0722) * a[..., 2]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    BB.MATS.clear()
    BB.COLL.clear()


def out_path(out, part, view, suffix):
    return os.path.join(out, '%s_%s_%s' % (part, view.replace(':', '-'), suffix))


def diffuse_mat(name, albedo):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    d = nt.nodes.new('ShaderNodeBsdfDiffuse')
    d.inputs['Color'].default_value = (albedo, albedo, albedo, 1.0)
    d.inputs['Roughness'].default_value = 0.0
    nt.links.new(d.outputs['BSDF'], nt.nodes['Material Output'].inputs['Surface'])
    m.diffuse_color = (albedo, albedo, albedo, 1.0)
    return m


def quad(name, pts, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], [], [(0, 1, 2, 3)])
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def tan_half(cam):
    """(tan(hfov/2), tan(vfov/2)) of a Blender camera at the scene's resolution."""
    sc = bpy.context.scene
    W, H = sc.render.resolution_x, sc.render.resolution_y
    cd = cam.data
    fit = cd.sensor_fit
    if fit == 'AUTO':
        fit = 'HORIZONTAL' if W >= H else 'VERTICAL'
    if fit == 'HORIZONTAL':
        tx = cd.sensor_width / (2 * cd.lens)
        return tx, tx * H / W
    ty = cd.sensor_height / (2 * cd.lens)
    return ty * W / H, ty


def build_part(P):
    """the part's builder, with a clear message when the sources are mid-edit."""
    try:
        return P['build']()
    except Exception:
        traceback.print_exc()
        print('[qa] ERROR: the part did not build from %s (another session editing it?). Use a HEAD snapshot: '
              'LANBAI_BUS_SRC=<snap>/Bus/Source (see the docstring).' % SRC)
        return None


# ------------------------------------------------------------------------------------------------ neutral (D-40 #2)
CARD_U = ((0.015, 0.065), (0.072, 0.122))      # grey, white: image-x ranges (0 = left)
CARD_V0 = 0.03                                  # bottom margin (0 = bottom)


def card_rects(W, H):
    """pixel rects (x0, y0, x1, y1; y from the top) + (u0, u1, v0, v1) of the grey and the white card."""
    out = []
    for u0, u1 in CARD_U:
        s = (u1 - u0) * W / H                   # square cards
        v0, v1 = CARD_V0, CARD_V0 + s
        out.append((u0 * W, (1 - v1) * H, u1 * W, (1 - v0) * H, u0, u1, v0, v1))
    return out


def add_cards(cam, depth=0.05):
    """the grey and the white card in the bottom-left corner, in the camera's image plane, seen by the camera only."""
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    tx, ty = tan_half(cam)
    M = cam.matrix_world
    obs = []
    for k, (r, alb) in enumerate(zip(card_rects(sc.render.resolution_x, sc.render.resolution_y), (GREY_ALBEDO, WHITE_ALBEDO))):
        u0, u1, v0, v1 = r[4:]
        loc = [((2 * u - 1) * tx * depth, (2 * v - 1) * ty * depth, -depth) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        ob = quad('QA_Card%d' % k, [M @ Vector(p) for p in loc], diffuse_mat('QA_Card%d' % k, alb))
        for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
            setattr(ob, attr, False)
        obs.append(ob)
    return obs


def read_cards(png):
    """mean sRGB (8-bit) of the inner half of the grey and the white card -> [(r, g, b, luma), ...]."""
    a = np.asarray(Image.open(png).convert('RGB')).astype(np.float64)
    H, W = a.shape[:2]
    out = []
    for x0, y0, x1, y1, *_ in card_rects(W, H):
        mx, my = (x1 - x0) * 0.25, (y1 - y0) * 0.25
        p = a[int(round(y0 + my)):int(round(y1 - my)), int(round(x0 + mx)):int(round(x1 - mx))].reshape(-1, 3).mean(0)
        out.append([round(float(c), 2) for c in p] + [round(float(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]), 2)])
    return out


def studio(env=1.0):
    """uniform white environment + an 18% grey floor under the part (0.5 mm below the bus floor level)."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('QA_Studio')
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs[1].default_value = env
    w.color = (0.18, 0.18, 0.18)
    sc.world = w
    y = B.FLOOR_Y - 0.0005
    h = 15.0
    return quad('QA_Floor', [BB.U2B(p) for p in ((-h, y, -h), (-h, y, h), (h, y, h), (h, y, -h))],
                diffuse_mat('QA_Floor', FLOOR_ALBEDO))


def material_census(objs):
    """{material name: number of objects} on the part (which surfaces the neutral picture has to identify)."""
    out = {}
    for o in objs:
        if o.type == 'MESH':
            for ms in o.data.materials:
                if ms is not None:
                    out[ms.name] = out.get(ms.name, 0) + 1
    return dict(sorted(out.items()))


def mode_neutral(a):
    P = PV.PARTS[a.part]
    reset()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    objs = build_part(P)
    if objs is None:
        return 4
    keep = set(objs)
    dropped = 0
    for o in list(bpy.data.objects):             # the bus shell, ceiling, floor, glass, lights...: only the part stays
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
            dropped += 1
    if not a.flat:
        from parts import materials as MATS
        MATS.apply_details(objs)
    census = material_census(objs)
    studio(a.env)
    res = (int(round(1280 * a.res_pct / 100)), int(round(720 * a.res_pct / 100)))
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='qa_neutral_')
    views = [v for v in P['views'] if not a.views or v in a.views.split(',')]
    if not views:
        print('[qa neutral] ERROR: %s has no view among %s (%s)' % (a.part, a.views, ', '.join(P['views'])))
        return 2
    rec = []
    for v in views:
        t0 = time.time()
        eye, tgt = P['views'][v]
        cam = PV.camera(eye, tgt, res=res)
        cards = add_cards(cam)
        # 1) the grey-card exposure: render only the cards' corner, low samples, measure, set EV
        r = card_rects(*res)
        sc.render.use_border, sc.render.use_crop_to_border = True, False
        sc.render.border_min_x, sc.render.border_max_x = max(0.0, r[0][4] - 0.01), min(1.0, r[1][5] + 0.01)
        sc.render.border_min_y, sc.render.border_max_y = max(0.0, r[0][6] - 0.01), min(1.0, r[0][7] + 0.01)
        sc.view_settings.exposure = 0.0
        sc.cycles.samples = a.cal_samples
        sc.render.filepath = os.path.join(tmp, 'cal.png')
        bpy.ops.render.render(write_still=True)
        g0 = read_cards(sc.render.filepath)[0][3]
        ev = float(np.clip(math.log2(float(srgb_to_lin(TARGET_GREY / 255.0)) / max(float(srgb_to_lin(g0 / 255.0)), 1e-6)), -8, 8))
        sc.view_settings.exposure = ev
        # 2) the picture
        sc.render.use_border = False
        sc.cycles.samples = a.samples
        sc.render.filepath = out_path(a.out, a.part, v, 'neutral.png')
        bpy.ops.render.render(write_still=True)
        grey, white = read_cards(sc.render.filepath)
        rec.append(dict(view=v, file=sc.render.filepath, eye=list(eye), target=list(tgt), exposure_ev=round(ev, 3),
                        grey_card_uncal_luma=g0, grey_card_rgb_luma=grey, white_card_rgb_luma=white,
                        seconds=round(time.time() - t0, 1)))
        print('[qa neutral] %s %s: EV %+.2f, grey card %.1f (target %d), white card %.1f, %.0f s'
              % (a.part, v, ev, grey[3], TARGET_GREY, white[3], time.time() - t0))
        for o in cards + [cam]:
            bpy.data.objects.remove(o, do_unlink=True)
    shutil.rmtree(tmp, ignore_errors=True)
    js = os.path.join(a.out, '%s_neutral.json' % a.part)
    json.dump(dict(
        part=a.part, mode='neutral', ruling='D-40 #2', sources=SRC, resolution=list(res),
        px_per_deg=round(res[0] / 64.0, 2), engine='CYCLES (CPU)', samples=a.samples, calibration_samples=a.cal_samples,
        denoise=True,
        light=dict(environment='uniform white, strength %.2f (no HDRI image: a constant colour)' % a.env,
                   floor='Diffuse %.2f grey plane at FLOOR_Y' % FLOOR_ALBEDO, cabin_tube_lights=False, sun=False),
        colour=dict(view_transform='Standard', look='None', exposure='per view from the grey card', grading=False),
        cards=dict(grey_albedo=GREY_ALBEDO, white_albedo=WHITE_ALBEDO, target_grey_srgb=TARGET_GREY,
                   where='bottom-left corner, 5 cm in front of the lens, camera-visible only (no shadow, no reflection)'),
        materials='flat MAT_TABLE' if a.flat else 'parts/materials.apply_details (the final ones)',
        part_materials=census, scene_objects_removed=dropped, views=rec,
        note='Blender 离线层（D-40a #4）；没有在 Unity 里编译或运行过。认不认得出材质由人看图判，这个 JSON 只记条件。'),
        open(js, 'w'), ensure_ascii=False, indent=1)
    print('[qa neutral] %s: %d views -> %s' % (a.part, len(rec), js))
    return 0


# ------------------------------------------------------------------------------------------------ flicker (D-40a #5)
def W_(s, f1, p1, f2, p2):
    """LanbaiTestCapture.cs 573-576 (float32 in Unity; the sum of two sines, |W| <= 1)."""
    return 0.6 * math.sin(2 * math.pi * f1 * s + p1) + 0.4 * math.sin(2 * math.pi * f2 * s + p2)


def look_rotation(fwd, up=(0.0, 1.0, 0.0)):
    """Unity Quaternion.LookRotation as a 3x3 (columns = right, up, forward), Unity coordinates."""
    z = np.asarray(fwd, float)
    z = z / np.linalg.norm(z)
    x = np.cross(up, z)
    x = x / np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def unity_euler(xd, yd, zd):
    """Unity Quaternion.Euler(x, y, z): z first, then x, then y (R = Ry Rx Rz)."""
    x, y, z = (math.radians(v) for v in (xd, yd, zd))
    Rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def head_pose(s, eye, rot, amp_m, amp_deg):
    """LanbaiTestCapture.cs 498-508: off / q from W(), position = eye + rot * off, rotation = rot * q."""
    off = np.array([W_(s, 0.83, 0.3, 2.1, 1.7), W_(s, 0.61, 2.2, 1.7, 0.4), W_(s, 0.47, 1.1, 1.3, 2.9)]) * amp_m
    q = unity_euler(W_(s, 0.53, 0.2, 1.6, 2.0) * amp_deg, W_(s, 0.71, 0.9, 1.9, 2.4) * amp_deg,
                    W_(s, 0.37, 1.4, 1.1, 0.6) * amp_deg * 0.5)
    return np.asarray(eye, float) + rot @ off, rot @ q


def place_camera(cam, eye_u, R_u):
    """a Unity camera pose (eye, columns right/up/forward in Unity coords) onto a Blender camera (looks down -Z)."""
    S = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float)          # U2B: (x, y, z) -> (x, z, y)
    r, u, f = S @ R_u[:, 0], S @ R_u[:, 1], S @ R_u[:, 2]
    m3 = Matrix(np.column_stack([r, u, -f]).tolist())
    cam.matrix_world = Matrix.Translation(BB.U2B(tuple(eye_u))) @ m3.to_4x4()


def ppd_size(hfov, vfov, ppd):
    """LanbaiTestCapture.cs 130-138: centre density ppd px/deg (Mathf.RoundToInt = round half to even)."""
    k = ppd * 180.0 / math.pi
    return int(round(2 * math.tan(math.radians(hfov) / 2) * k)), int(round(2 * math.tan(math.radians(vfov) / 2) * k))


def bounds_center(objs):
    """Unity Renderer.bounds of all the pieces, encapsulated -> centre (Unity coords)."""
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for o in objs:
        if o.type != 'MESH':
            continue
        M = o.matrix_world
        for v in o.data.vertices:
            w = M @ v.co
            p = np.array((w.x, w.z, w.y))
            lo, hi = np.minimum(lo, p), np.maximum(hi, p)
    return (lo + hi) / 2, lo, hi


def slice_scene():
    """the three slice pieces at their places in the bus, nothing else (as LanbaiBusSliceBuilder puts them)."""
    from parts import poles as PL
    from parts import seat as SEAT
    from parts import window as WIN
    pieces = {}
    pieces['seat'] = SEAT.seat_module('SeatR0', B.SEAT_R_X[0], B.SEAT_R_X[1], B.RIGHT_ROWS[0], cushion_y=1.00 + 0.04,
                                      wall_side=1, on_box=True, wall_x=B.X_IN_R)
    pieces['window'] = WIN.side_window('R', 1, *B.WIN_R[0])
    pieces['pillar'] = PL.pole('PoleR0', 0.29, B.RIGHT_ROWS[1] - 0.03, B.FLOOR_Y, BB.ceil_y(0.29), button=True)
    return pieces


def egl_ready(egl_dir=None):
    """EEVEE and Workbench need an EGL context here. 'system', 'private:<dir>' or None."""
    try:
        ctypes.CDLL('libEGL.so.1')
        return 'system'
    except OSError:
        pass
    d = egl_dir or os.environ.get('LANBAI_EGL_DIR')
    if not d:
        return None
    for lib in (os.path.join(d, 'usr', 'lib', 'x86_64-linux-gnu'), os.path.join(d, 'lib'), d):
        if os.path.exists(os.path.join(lib, 'libEGL.so.1')):
            vend = os.path.join(d, 'usr', 'share', 'glvnd', 'egl_vendor.d')
            if os.path.isdir(vend):
                os.environ['__EGL_VENDOR_LIBRARY_DIRS'] = vend
            try:
                if os.path.exists(os.path.join(lib, 'libEGL_mesa.so.0')):
                    ctypes.CDLL(os.path.join(lib, 'libEGL_mesa.so.0'), mode=ctypes.RTLD_GLOBAL)
                ctypes.CDLL(os.path.join(lib, 'libEGL.so.1'), mode=ctypes.RTLD_GLOBAL)
                return 'private:' + d
            except OSError:
                return None
    return None


def mat_key(m):
    return m.name.replace('M_Bus_', '').split('.')[0]


def _steel_band(m):
    """Lanbai/Cabin _HeightSmooth on a flat MAT_TABLE material: smoothness lerps to 0.80 inside y 1.62-2.42 (Unity y =
    Blender world z), with 5 cm smoothsteps at both ends (LanbaiCabin.shader 261-262). Roughness = 1 - smoothness."""
    nt = m.node_tree
    bs = nt.nodes.get('Principled BSDF')
    y0, y1, s_band = STEEL_BAND
    s_base = BB.MAT_TABLE['Steel'][1]
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    ramps = []
    for lo, hi, to0, to1 in ((y0 - 0.05, y0, 0.0, 1.0), (y1, y1 + 0.05, 1.0, 0.0)):
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.interpolation_type = 'SMOOTHSTEP'
        mr.clamp = True
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = lo, hi
        mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = to0, to1
        ramps.append(mr)
    hb = nt.nodes.new('ShaderNodeMath')
    hb.operation = 'MULTIPLY'
    nt.links.new(ramps[0].outputs['Result'], hb.inputs[0])
    nt.links.new(ramps[1].outputs['Result'], hb.inputs[1])
    rough = nt.nodes.new('ShaderNodeMath')
    rough.operation = 'MULTIPLY_ADD'                     # (1 - s_base) - (s_band - s_base) * hb
    nt.links.new(hb.outputs['Value'], rough.inputs[0])
    rough.inputs[1].default_value = -(s_band - s_base)
    rough.inputs[2].default_value = 1.0 - s_base
    nt.links.new(rough.outputs['Value'], bs.inputs['Roughness'])


def flicker_materials(detail_normals):
    """every MAT_TABLE material as Lanbai/Cabin shades it: base colour, Roughness = 1 - smoothness, Metallic (Glass
    stays as build_bus makes it); Steel gets the hand-height band; Vinyl the scanned grain if asked. Returns a record."""
    rec = {}
    for m in list(bpy.data.materials):
        key = mat_key(m)
        if key not in BB.MAT_TABLE or not m.use_nodes or m.node_tree is None:
            continue
        bs = m.node_tree.nodes.get('Principled BSDF')
        if bs is None:
            continue
        hexc, smooth, metal = BB.MAT_TABLE[key]
        note = dict(albedo=hexc, smoothness=smooth, roughness=round(1.0 - smooth, 3), metallic=float(metal))
        if key != 'Glass':
            for l in list(bs.inputs['Base Color'].links) + list(bs.inputs['Roughness'].links) + list(bs.inputs['Metallic'].links):
                m.node_tree.links.remove(l)
            bs.inputs['Base Color'].default_value = (*BB.srgb2lin(hexc), 1.0)
            bs.inputs['Roughness'].default_value = 1.0 - smooth
            bs.inputs['Metallic'].default_value = float(metal)
        else:
            note['glass'] = 'as build_bus.mat makes it (transmission 1, IOR 1, roughness 0.03)'
        if key == 'Steel':
            _steel_band(m)
            note['height_band'] = dict(y0=STEEL_BAND[0], y1=STEEL_BAND[1], smoothness=STEEL_BAND[2], edge_m=0.05)
        if key == 'Vinyl' and detail_normals == 'vinyl':
            PV.detail_normal(m, 'Cabin_SeatLeather_N_0.30m.jpg', 0.30, 0.35)
            note['detail_normal'] = 'Cabin_SeatLeather_N_0.30m.jpg, 0.35, 0.30 m tile (box projection, object space)'
        rec[m.name] = note
    return rec


def night_cabin_light(world_strength, spec=None):
    """the cabin's 10 tube lights as bake_lightmap.add_tubes puts them (real places, bake power), a dim night world,
    no sun. spec None = scale the specular so a tube reflects at Unity's diffuser brightness (see TUBE_EMISSION_LUMA)."""
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o, do_unlink=True)
    watts, wsrc = tube_watts()
    luma = 0.2126 * TUBE_LIN[0] + 0.7152 * TUBE_LIN[1] + 0.0722 * TUBE_LIN[2]
    n, rad = 0, None
    for side, x, zl in (('L', B.TUBE_X[0], B.TUBE_Z_L), ('R', B.TUBE_X[1], B.TUBE_Z)):
        for i, (z0, z1) in enumerate(zl):
            for up in (False, True):
                ld = bpy.data.lights.new('QA_Tube%s%d%s' % (side, i, '_up' if up else ''), 'AREA')
                ld.shape = 'RECTANGLE'
                ld.size, ld.size_y = (0.14 if up else 0.12), (z1 - z0) - 0.06
                ld.color = TUBE_LIN
                ld.energy = watts * (0.12 if up else 1.0)
                if not up:
                    rad = watts / (math.pi * 0.12 * ld.size_y)          # its radiance (W m^-2 sr^-1 = pixel units)
                k = spec if spec is not None else TUBE_EMISSION_LUMA / (rad * luma if rad else 1.0)
                ld.specular_factor = k
                lo = bpy.data.objects.new(ld.name, ld)
                lo.location = (x, (z0 + z1) / 2, B.CEIL_Y - (0.04 if up else 0.05))   # Blender coords, as add_tubes
                if up:
                    lo.rotation_euler = (math.pi, 0, 0)
                sc.collection.objects.link(lo)
                n += 1
    w = bpy.data.worlds.new('QA_Night')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (*BB.srgb2lin('#30343A'), 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = world_strength
    w.color = (0.05, 0.05, 0.05)
    sc.world = w
    k = spec if spec is not None else TUBE_EMISSION_LUMA / (rad * luma)
    return dict(tubes=n // 2, up_twins=n // 2, watts_per_tube=round(watts, 3), watts_from=wsrc, colour_linear=list(TUBE_LIN),
                tube_radiance_luma=round(rad * luma, 3), specular_factor=round(k, 4),
                reflected_tube_luma=round(rad * luma * k, 3), unity_tube_emission_luma=round(TUBE_EMISSION_LUMA, 3),
                diffuse_factor=1.0, world='#30343A x %.3f' % world_strength, sun=False,
                note='bake_lightmap.add_tubes layout and power; specular scaled to the Unity diffuser brightness')


def cabin_probe(target_u, res='256'):
    """an EEVEE sphere probe in the aisle at head height (the bible's cabin cubemap, 256 per face): the metals reflect
    the lit cabin as Unity's reflection probe makes them, not the black night world. Captured at render time from a
    fixed place, so it does not change with the head."""
    sc = bpy.context.scene
    pd = bpy.data.lightprobes.new('QA_CabinProbe', 'SPHERE')
    pd.influence_distance = 6.0
    pd.clip_start = 0.05
    po = bpy.data.objects.new('QA_CabinProbe', pd)
    loc = (B.XC, 1.70, float(target_u[2]))
    po.location = BB.U2B(loc)
    sc.collection.objects.link(po)
    sc.eevee.gi_cubemap_resolution = res
    return dict(sphere_probe=list(loc), influence_m=6.0, cubemap_res=res)


def setup_eevee(sc, shadows=False):
    """EEVEE, 1 render sample. Shadows off by default: in Unity the tube light is the baked _CabinTubeLM (no real-time
    shadow), and EEVEE's soft shadows are traced stochastically - at 1 sample that is per-frame noise, which the
    hf metric would count as flicker. With them off, a still camera gives identical frames (hf = 0)."""
    sc.render.engine = 'BLENDER_EEVEE'
    e = sc.eevee
    e.taa_render_samples = 1                     # no TAA accumulation: one raster pass, one sample per pixel
    e.use_shadows = shadows
    e.use_raytracing = False                     # no screen-space tracing: lights + world probe, like a forward path
    sc.render.use_motion_blur = False
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.data.use_shadow = shadows
    return dict(engine='BLENDER_EEVEE', taa_render_samples=1, shadows=shadows, raytracing=False, motion_blur=False,
                film_filter_px=round(sc.render.filter_size, 2),
                note='1 sample: the sample sits at the pixel centre (checked: filter 1.5 and 0 give identical pixels)')


def setup_workbench(sc):
    """NOT FOR HIGHLIGHTS: Workbench has no PBR specular. Kept for geometric edge crawl only."""
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.render_aa = 'OFF'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.use_world_space_lighting = True
    sh.show_specular_highlight = True
    sh.color_type = 'MATERIAL'
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_object_outline = False
    sh.show_backface_culling = False
    for m in bpy.data.materials:                 # Workbench reads the material's viewport colour / metallic / roughness
        key = mat_key(m)
        if key in BB.MAT_TABLE:
            hexc, smooth, metal = BB.MAT_TABLE[key]
            m.diffuse_color = (*BB.srgb2lin(hexc), 1.0)
            m.roughness = 1.0 - smooth
            m.metallic = float(metal)
    return dict(engine='BLENDER_WORKBENCH', render_aa='OFF', light='STUDIO', world_space_lighting=True,
                specular_highlight='Workbench studio only (no PBR)', color_type='MATERIAL (MAT_TABLE)',
                warning='不看高光：Workbench 没有 PBR 高光，只能看几何边缘的爬动')


def setup_cycles_point(sc):
    """the no-EGL fallback: Cycles at 1 spp, a 0.01 px box filter (= the pixel centre), direct light from delta lights
    only (no environment, no bounces): deterministic per pixel and aliased like a rasteriser without MSAA."""
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'
    c.samples = 1
    c.use_adaptive_sampling = False
    c.use_denoising = False
    c.seed = 0
    c.use_animated_seed = False
    c.pixel_filter_type = 'BOX'
    c.filter_width = 0.01
    c.max_bounces = c.diffuse_bounces = c.glossy_bounces = c.transmission_bounces = 0
    c.transparent_max_bounces = 0
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o, do_unlink=True)
    if sc.world:
        sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.0
    for kind, loc, rot, energy in (('SUN', None, (0.9, 0.0, 2.2), 3.0), ('POINT', (0.0, 2.45, 1.0), None, 60.0),
                                   ('POINT', (0.4, 2.45, -0.6), None, 40.0)):
        ld = bpy.data.lights.new('QA_' + kind, kind)
        ld.energy = energy
        if kind == 'SUN':
            ld.angle = 0.0
        else:
            ld.shadow_soft_size = 0.0
        lo = bpy.data.objects.new(ld.name, ld)
        if loc:
            lo.location = BB.U2B(loc)
        if rot:
            lo.rotation_euler = rot
        sc.collection.objects.link(lo)
    return dict(engine='CYCLES (point-sampled fallback)', samples=1, pixel_filter='BOX 0.01 px', bounces=0,
                lights='sun + 2 points, delta', environment=0,
                warning='没有 EGL 时的备用；光和 EEVEE 的不一样，数不能直接比')


def heat(v, mean, scale):
    """LanbaiTestCapture.cs 773-791 (Img.Heat; Color32.Lerp truncates to bytes)."""
    ramp = np.array([(0, 0, 4), (87, 16, 110), (188, 55, 84), (249, 142, 9), (252, 255, 164)], np.float32)
    x = np.clip(v / np.float32(max(1e-3, scale)), 0.0, 1.0).astype(np.float32)
    f = x * np.float32(len(ramp) - 1)
    k = np.minimum(len(ramp) - 2, f.astype(np.int32))
    t = (f - k)[..., None]
    c = ramp[k] + (ramp[k + 1] - ramp[k]) * t
    out = np.floor(c).astype(np.uint8)
    g = (mean * np.float32(0.35)).astype(np.uint8)
    low = x < np.float32(0.04)
    out[low] = np.stack([g, g, g], -1)[low]
    return out


def pct(a, q):
    """LanbaiTestCapture.cs 578-583."""
    b = np.sort(a, axis=None)
    return float(b[min(b.size - 1, int(q * (b.size - 1)))])


class Acc:
    """the per-pixel accumulation of LanbaiTestCapture.cs 511-518 and the numbers of 528-548."""

    def __init__(self, w, h):
        self.n, self.N = 0, w * h
        self.S1 = np.zeros((h, w), np.float64)
        self.S2 = np.zeros((h, w), np.float64)
        self.HF2 = np.zeros((h, w), np.float64)
        self.p1 = np.zeros((h, w), np.float32)
        self.p2 = np.zeros((h, w), np.float32)
        self.apl = []

    def add(self, y):
        """y: float32 luma of one frame (0-255)."""
        self.S1 += y
        self.S2 += y.astype(np.float64) * y
        if self.n >= 2:
            dd = (y - np.float32(2) * self.p1 + self.p2).astype(np.float64)     # float math, then double (516)
            self.HF2 += dd * dd
        self.apl.append(float(y.astype(np.float64).sum() / self.N))
        self.p2, self.p1 = self.p1, y
        self.n += 1

    def metrics(self, thr):
        n = self.n
        m = self.S1 / n
        std = np.sqrt(np.maximum(0.0, self.S2 / n - m * m)).astype(np.float32)          # 533
        hf = np.sqrt(self.HF2 / (n - 2) / 6.0).astype(np.float32)                        # 534
        mean = m.astype(np.float32)
        steps = [abs(self.apl[i] - self.apl[i - 1]) for i in range(1, len(self.apl))]
        met = dict(std_mean=float(std.mean(dtype=np.float64)), std_p99=pct(std, 0.99),
                   hf_mean=float(hf.mean(dtype=np.float64)), hf_p99=pct(hf, 0.99),
                   hf_frac=float((hf > np.float32(thr)).sum()) / self.N,
                   apl_min=min(self.apl), apl_max=max(self.apl), apl_max_step=max(steps) if steps else 0.0)
        return std, hf, mean, met


def mode_flicker(a):
    P = PV.PARTS[a.part]
    eng = a.engine
    egl = None
    if eng in ('eevee', 'workbench'):
        egl = egl_ready(a.egl_dir)
        if egl is None:
            if not a.allow_fallback:
                print('[qa flicker] ERROR: no libEGL.so.1, %s cannot render here. Install libegl1 + libegl-mesa0, or '
                      'unpack them and pass --egl-dir / set LANBAI_EGL_DIR; or --allow-fallback / --engine cycles_point '
                      '(a different stand-in, numbers not comparable).' % eng)
                return 3
            eng = 'cycles_point'
    n, fps = a.frames, float(a.fps)
    if n < 3:
        print('[qa flicker] ERROR: at least 3 frames (LanbaiTestCapture.cs 479)')
        return 2
    reset()
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = a.exposure
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.film_transparent = False
    view = a.view or next(iter(P['views']))
    if view.startswith('slice:'):
        cid = view.split(':', 1)[1]
        if cid not in SLICE_CAMS:
            print('[qa flicker] ERROR: unknown slice camera %s (%s)' % (cid, ', '.join(SLICE_CAMS)))
            return 2
        piece, dist = SLICE_CAMS[cid]
        try:
            pieces = slice_scene()
        except Exception:
            traceback.print_exc()
            print('[qa flicker] ERROR: the slice pieces did not build from %s; use a HEAD snapshot (LANBAI_BUS_SRC)' % SRC)
            return 4
        target, lo, hi = bounds_center(pieces[piece])
        d = np.asarray(B.EYE, float) - target                      # LanbaiTestCapture.cs 95-105: back off toward 'toward'
        eye = target + d / np.linalg.norm(d) * dist
        crop = SLICE_CROP
        ppd = SLICE_PPD
        cam_info = dict(slice_cam=cid, look_at_object=piece, bounds_center=[round(float(v), 4) for v in target],
                        bounds_min=[round(float(v), 4) for v in lo], bounds_max=[round(float(v), 4) for v in hi],
                        toward=list(B.EYE), distance=dist, scene='the three slice pieces only (LanbaiBusSliceBuilder)')
    else:
        if view not in P['views']:
            print('[qa flicker] ERROR: %s has no view %s (%s)' % (a.part, view, ', '.join(P['views'])))
            return 2
        if build_part(P) is None:
            return 4
        PV.stage(P['wall'], day=False, shell=P.get('shell', False))   # the preview's surroundings; its lights go below
        eye, target = (np.asarray(p, float) for p in P['views'][view])
        crop = tuple(float(v) for v in a.crop.split(','))
        ppd = a.ppd
        cam_info = dict(preview_view=view, target=[float(v) for v in target],
                        scene='parts/preview.py %s scene (%s)' % (a.part, 'bus shell' if P.get('shell') else 'floor + wall'))
    light = night_cabin_light(a.world, a.tube_spec)
    if eng == 'eevee' and a.probe and not view.startswith('slice:'):
        light['reflection'] = cabin_probe(target)
    else:
        light['reflection'] = 'the night world only (no probe)'
    mats = flicker_materials(a.detail_normals) if eng == 'eevee' else {}
    rot = look_rotation(target - eye)
    w_, h_ = ppd_size(crop[0], crop[1], ppd)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w_, h_, 100
    cd = bpy.data.cameras.new('QA_Cam')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(crop[1])
    cd.clip_start, cd.clip_end = 0.02, 200.0
    cam = bpy.data.objects.new('QA_Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    if eng == 'eevee':
        eng_rec = setup_eevee(sc, a.shadows)
    elif eng == 'workbench':
        eng_rec = setup_workbench(sc)
        light = dict(note='Workbench studio light (scene lights unused)')
    else:
        eng_rec = setup_cycles_point(sc)
        light = dict(note='cycles_point: sun + 2 point lights, see engine_settings')
    amp_m, amp_deg = a.amp_cm * 0.01, a.amp_deg
    ref_n = a.ref_samples if eng == 'eevee' else 0
    acc, ref = Acc(w_, h_), (Acc(w_, h_) if ref_n > 0 else None)
    tag = '%s_%s' % (a.part, view.replace(':', '-'))
    keep = os.path.join(a.out, tag + '_flicker_frames') if a.save_frames else None
    tmp = keep or tempfile.mkdtemp(prefix='qa_flicker_')
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    for i in range(n):
        s = i / fps
        e, R = head_pose(s, eye, rot, amp_m, amp_deg)
        place_camera(cam, e, R)
        sc.render.filepath = os.path.join(tmp, '%04d.png' % i)
        bpy.ops.render.render(write_still=True)
        acc.add(luma8(np.asarray(Image.open(sc.render.filepath).convert('RGB'))))
        if ref is not None:                      # the same pose, antialiased (N samples): the smooth signal
            sc.eevee.taa_render_samples = ref_n
            sc.render.filepath = os.path.join(tmp, 'ref_%04d.png' % i)
            bpy.ops.render.render(write_still=True)
            ref.add(luma8(np.asarray(Image.open(sc.render.filepath).convert('RGB'))))
            sc.eevee.taa_render_samples = 1
        if i == 0:
            shutil.copy(os.path.join(tmp, '0000.png'), os.path.join(a.out, tag + '_flicker_f000.png'))
            print('[qa flicker] frame 0 in %.0f s (shader compile)' % (time.time() - t0))
    secs = time.time() - t0
    std, hf, mean, met = acc.metrics(a.hf_threshold)
    apl = acc.apl
    Image.fromarray(heat(hf, mean, a.heat_scale)).save(os.path.join(a.out, tag + '_flicker_heat.png'))
    Image.fromarray(heat(std, mean, a.heat_scale)).save(os.path.join(a.out, tag + '_flicker_heat_std.png'))
    extra = {}
    if ref is not None:
        _, hf_r, _, met_r = ref.metrics(a.hf_threshold)
        ex = np.maximum(np.float32(0), hf - hf_r)
        Image.fromarray(heat(ex, mean, a.heat_scale)).save(os.path.join(a.out, tag + '_flicker_heat_excess.png'))
        extra = dict(blender_only=dict(
            what='不是 Unity 工具的量，只在这里有（D-40a #5 的辅助）：同一条运动再渲一遍 %d 个采样（抗锯齿）当“平滑的信号”，'
                 'excess = max(0, hf − hf_ref)。快速扫过的边两遍都有、被减掉；剩下的近似是锯齿和高光闪烁本身。' % ref_n,
            ref_samples=ref_n, hf_ref_mean=met_r['hf_mean'], hf_ref_p99=met_r['hf_p99'], hf_ref_frac=met_r['hf_frac'],
            excess_mean=float(ex.mean(dtype=np.float64)), excess_p99=pct(ex, 0.99),
            excess_frac=float((ex > np.float32(a.hf_threshold)).sum()) / ex.size,
            heat_excess=os.path.join(a.out, tag + '_flicker_heat_excess.png')))
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
    rec = dict(
        id=tag, part=a.part, view=view, kind='micro_motion', ruling='D-40a #5', layer='Blender 离线（近似）',
        engine=eng, egl=egl, engine_settings=eng_rec, light=light, materials=mats,
        detail_normals=a.detail_normals if eng == 'eevee' else 'n/a',
        colour=dict(view_transform='Standard', look='None', exposure_ev=a.exposure, grading=False),
        sources=SRC, fps=fps, frames=n, w=w_, h=h_, ss=1, crop_deg=list(crop), ppd=ppd, amp_cm=a.amp_cm,
        amp_deg=amp_deg, eye_offset_mm=0.0, eye=[round(float(v), 4) for v in eye], camera=cam_info,
        hf_threshold=a.hf_threshold, heat_scale=a.heat_scale, **met, **extra, apl_per_frame=[round(v, 3) for v in apl],
        heat_flicker=os.path.join(a.out, tag + '_flicker_heat.png'),
        heat_std=os.path.join(a.out, tag + '_flicker_heat_std.png'),
        frame0=os.path.join(a.out, tag + '_flicker_f000.png'), frames_dir=keep, seconds=round(secs, 1),
        definitions='照抄 %s：Luma 711；累加 511-518；std 533；hf 534；量数 537-548；Avg 577；Pct 578-583；Heat 773-791；'
                    '运动 498-508 / W 573-576；ss 1、无 MSAA 464 / 255；ppd 尺寸 130-138；机位 83-105' % CAPTURE_CS,
        note='Blender 层的近似（%s 代替 Unity 渲的），不是 Unity 的测量；Unity 层的结果以总工程师的测试工具为准。'
             '这里没有 Lanbai/Cabin 的几何高光抗锯齿（D-40 #4）、零件图集的法线 / 遮罩、mip、贴图压缩、烘好的管灯光照图和'
             '反射探针、PPv2 调色。没有在 Unity 里编译或运行过。热图颜色 0 → %g（亮度 0–255），底下是平均画面的暗灰。'
             % (eng, a.heat_scale))
    js = os.path.join(a.out, tag + '_flicker.json')
    json.dump(rec, open(js, 'w'), ensure_ascii=False, indent=1)
    print('[qa flicker] %s %s (%s, %dx%d, %d frames, %.0f s): std_mean %.3f std_p99 %.2f hf_mean %.3f hf_p99 %.2f '
          'hf_frac %.5f (hf > %g) APL %.1f..%.1f max step %.2f -> %s'
          % (a.part, view, eng, w_, h_, n, secs, met['std_mean'], met['std_p99'], met['hf_mean'], met['hf_p99'],
             met['hf_frac'], a.hf_threshold, met['apl_min'], met['apl_max'], met['apl_max_step'], js))
    if extra:
        x = extra['blender_only']
        print('[qa flicker] reference %d samples: hf_ref_mean %.3f hf_ref_frac %.5f; excess_mean %.3f excess_p99 %.2f '
              'excess_frac %.5f (Blender-only aid, not a Unity metric)'
              % (ref_n, x['hf_ref_mean'], x['hf_ref_frac'], x['excess_mean'], x['excess_p99'], x['excess_frac']))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='D-40 / D-40a Blender-layer QA for the bus parts (an approximation; the '
                                             'Unity layer is the engineering test tool)')
    ap.add_argument('--mode', required=True, choices=['neutral', 'flicker'])
    ap.add_argument('--part', default='seat', choices=sorted(PV.PARTS))
    ap.add_argument('--out', default='/tmp/bus/parts')
    # neutral
    ap.add_argument('--views', default='', help='neutral: comma list of preview views (default all)')
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--cal-samples', type=int, default=24, help='samples of the grey-card exposure render')
    ap.add_argument('--res-pct', type=float, default=100.0, help='of 1280x720 (100 = 20 px/deg at 64 deg)')
    ap.add_argument('--env', type=float, default=1.0, help='uniform environment strength (exposure follows the card)')
    ap.add_argument('--flat', action='store_true', help='neutral: MAT_TABLE colours only (no detail materials)')
    # flicker
    ap.add_argument('--view', default='', help='flicker: a preview view, or slice:<seat_05m|seat_10m|window_..|pillar_..>')
    ap.add_argument('--frames', type=int, default=90)
    ap.add_argument('--fps', type=float, default=90.0)
    ap.add_argument('--amp-cm', type=float, default=2.0)
    ap.add_argument('--amp-deg', type=float, default=1.0)
    ap.add_argument('--crop', default='32,24', help='flicker on a preview view: crop deg (h,v) around the target')
    ap.add_argument('--ppd', type=float, default=20.0)
    ap.add_argument('--hf-threshold', type=float, default=6.0)
    ap.add_argument('--heat-scale', type=float, default=24.0)
    ap.add_argument('--engine', default='eevee', choices=['eevee', 'workbench', 'cycles_point'],
                    help='eevee (default, 1 sample); workbench = NOT for highlights; cycles_point = no-EGL fallback')
    ap.add_argument('--detail-normals', default='vinyl', choices=['vinyl', 'none'],
                    help='eevee: the scanned leather normal on Vinyl as Unity has it (vinyl) or geometry normals only')
    ap.add_argument('--shadows', action='store_true', help='eevee: real-time shadows on (stochastic: per-frame noise at 1 sample)')
    ap.add_argument('--tube-spec', type=float, default=None,
                    help='eevee: tube light specular factor (default: reflected tube = Unity diffuser luma 1.95)')
    ap.add_argument('--no-probe', dest='probe', action='store_false',
                    help='eevee: no cabin sphere probe (metals then reflect the night world only)')
    ap.add_argument('--ref-samples', type=int, default=0,
                    help='eevee: also render each pose with N samples and report hf minus that (a Blender-only aid; 0 = off)')
    ap.add_argument('--world', type=float, default=0.03, help='flicker: night world strength (#30343A)')
    ap.add_argument('--exposure', type=float, default=0.0, help='flicker: EV (fixed for all frames)')
    ap.add_argument('--allow-fallback', action='store_true', help='no EGL: use cycles_point instead of exiting 3')
    ap.add_argument('--egl-dir', default='', help='a folder with libEGL.so.1 + libEGL_mesa.so.0 (unpacked debs)')
    ap.add_argument('--save-frames', action='store_true')
    a = ap.parse_args(argv)
    return mode_neutral(a) if a.mode == 'neutral' else mode_flicker(a)


if __name__ == '__main__':
    sys.exit(main())

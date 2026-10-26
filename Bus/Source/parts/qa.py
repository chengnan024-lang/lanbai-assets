# -*- coding: utf-8 -*-
"""D-40 / D-40a 的 Blender 层检查（车的零件：seat / window / poles，零件和机位都来自 parts/preview.py）。

    ~/bpy/bin/python Bus/Source/parts/qa.py --mode neutral --part poles [--views a,b] [--samples 64] [--res-pct 100]
    ~/bpy/bin/python Bus/Source/parts/qa.py --mode flicker --part poles [--view aisle_2m | --view slice:pillar_10m]
                                           [--frames 90] [--fps 90] [--crop 32,24] [--ppd 20] [--reference-ss 4]

别的会话正在改 seat.py / common.py / materials.py / build_bus.py 的时候，这些文件可能一时 import 不了。那就先把
提交过的源码拷一份，用 LANBAI_BUS_SRC 指过去（qa.py 自己照常从工作区跑）：
    mkdir -p /tmp/snap && git archive HEAD Bus/Source Bus/Textures Bus/Docs~/bake_report.json | tar -x -C /tmp/snap
    LANBAI_BUS_SRC=/tmp/snap/Bus/Source ~/bpy/bin/python Bus/Source/parts/qa.py --mode ...
设了 LANBAI_BUS_SRC 时，管灯功率只从快照里的 Bus/Docs~/bake_report.json 读；快照里没有就报错退出（退出码 4），
不去读工作区那份（那份可能是别的会话还没提交的烘焙）。也可以用 --tube-watts 直接给。

--mode neutral（D-40 #2 中性光，灰色影棚）：只留零件自己的物体。
    光：均匀的白环境（一个常数颜色，强度 --env，默认 1；没有 HDRI 图、没有车厢管灯、没有太阳），零件上的漫射和光泽
    光线看到的都是它。相机直接看到的背景（和隔着玻璃直接看到的）是 18% 灰（世界节点里 Light Path 的 Is Camera Ray /
    Is Transmission Ray），所以背景读 sRGB 约 118，不削顶。地是一块 18% 灰的平面：相机、光泽、透射光线看得见（给
    金属一条地平线，零件在地上有接触阴影），漫射和阴影光线看不见（不挡环境光，灰卡在每个机位受的光都一样）。
    不调色：Standard 视图变换、Look None、不加抖动（dither 0）。
    机位和 preview.PARTS 完全一样，连各机位自己的水平视角也一样（view_hfov / hfov，默认 64°）：1280 × 720 在 64° 时
    平均约 20 px/°（画面中心按测试工具的公式约 18 px/°）；JSON 里每个机位记自己的两个数。
    灰卡（18%）和白卡（90%）放在画面的一个角上，底下垫一块深色的板（卡和板只给相机看：不投影、不进反射）。先用
    1 个采样渲一张零件的遮罩，在左下、右下、左上、右上里挑第一个不压着零件的角；四个角都压着时，卡片不进画面，
    另渲一条只有卡片的窄条（同一个相机、同一个曝光，零件只是对相机隐身，照样挡光）接在图的下面。
    曝光：每个机位只渲卡片那一小块（低采样），量灰卡，算出让灰卡读 sRGB 118 的 EV；一个零件只用一个 EV = 各机位
    标定值的中位数，同一种材质在每张图里一样亮，可以跨机位比反照率（地对漫射光线不可见，各机位的标定值本来就差不多）。
    出 /tmp/bus/parts/<part>_<view>_neutral.png 和 <part>_neutral.json（每个机位：标定的 EV、用的 EV、灰卡 / 白卡读数、
    卡片放在哪、零件像素里削顶（任一通道 ≥ 254）的占比、背景读数）。
    材质用定稿的那套（materials.apply_details，和 preview 一样；--flat 只用 MAT_TABLE 的底色）。这张图要回答：不靠灯光，
    认不认得出乙烯、搪瓷漆、阳极铝、橡胶、漆过的钢管（D-40 #2：不许靠灯光救）。认不认得出由人看图判。
    渲染器 Cycles（CPU、降噪）。

--mode flicker（D-40a #5 头部微动，总导演 10-25 改：不用 Workbench）：EEVEE（'BLENDER_EEVEE'），
    Render Samples = 1（scene.eevee.taa_render_samples = 1：不做 TAA 累积，一帧就是一次光栅化、一个像素一个
    采样点，最接近 Unity 不开 MSAA 的一帧；实测 1 个采样时 filter_size 1.5 和 0 出的图逐像素相同，采样点在像素
    中心）。90 帧、90 fps，头部按总工程师 Unity 工具同一条运动走（±2 cm、±1°，两个正弦叠加，平滑、每次跑都一样）。
    像素密度 20 px/°：在 preview 的机位上，以 target 为中心裁 32 × 24°（按 Unity 工具的 ppd 公式 = 657 × 487）；
    或者用 --view slice:<seat_05m|seat_10m|window_05m|window_10m|pillar_05m|pillar_10m>，照 bus_slice.json 的机位
    （看切片物体包围盒中心，朝主座位的眼退 distance，40 × 30°，834 × 614）。
    闪烁的主量是 shimmer（测试工具 33f9a60 起）：每一帧同一个姿态再渲一张 reference_ss 倍（默认 4，0 = 不渲）分辨率、
    同样 1 个采样的参考图，照 Unity 的 Graphics.Blit(big, small) 缩回来（双线性：每个输出像素在中心取一次样，4× 时
    样点正好落在四个 texel 中间 = 离中心最近的 2 × 2 个 texel 在线性空间的平均，不是 4 × 4 的方框平均），再转 sRGB
    8 位。shimmer = 逐像素“测的图 − 参考图”的亮度差随时间的标准差：真实运动两张图一起挪，差里没有；剩下的是采样
    不足带来的锯齿、高光闪烁、爬动和摩尔纹。Blender 里先渲完全部测的帧、再渲全部参考帧（姿态是确定的，和 Unity
    一帧一帧交替渲的结果一样）。帧都先存成线性的 EXR，再自己转 sRGB 8 位（和 Blender Standard 视图出的 PNG 实测
    最多差 1 级、只在 0.01% 的像素上），这样测的图和参考图走同一条路。
    材质：Lanbai/Cabin 的数（圣经 §4.2 = build_bus.MAT_TABLE、Cabin/README.md §2）：Principled 的 Roughness =
    1 − 光滑度（Unity Standard 的 perceptual roughness，两边都是 α = r²），Metallic 照表，底色照表；立柱 / 顶杆
    （Steel）加 Lanbai/Cabin 的 _HeightSmooth 握手带（y 1.62–2.42 光滑度 0.80，两头 5 cm smoothstep：
    LanbaiCabin.shader @27145d8 第 263–264 行 hb = smoothstep(_HeightSmooth.x − 0.05, _HeightSmooth.x, P.y) ×
    (1 − smoothstep(_HeightSmooth.y, _HeightSmooth.y + 0.05, P.y))）。法线：几何法线；--detail-normals vinyl（默认）
    给乙烯加 Unity 同一张皮纹法线（Cabin_SeatLeather_N_0.30m，0.35，30 cm 一格，LanbaiBusBuild 的 Detail()），
    none = 一张都不加。不用 materials.apply_details（那套程序化旧化在 Unity 里是烘好的贴图，这里只比光滑度和金属度）。
    光：车厢的 10 根管灯，照 bake_lightmap.add_tubes 烘 _CabinTubeLM 时的样子摆（真位置、0.12 × (长 − 0.06) m 的
    面光、冷白 #E4F1F3、朝上一盏 12% 的副灯），功率取烘焙标定出来的那个（bake_report.json 的 watts_per_tube：
    7 个中段座垫平均 E = 0.60；读的是哪个文件记在 JSON 的 light.watts_from 里）。面光的漫射只有直射（Unity 的光照图
    还带反弹，所以这里的暗处更暗）；高光按比例缩到“管灯在金属里的亮度 = Unity 管灯罩的自发光”（LanbaiBusBuild
    TubeDiffuser 的 _EmissionColor，亮度 1.94；Blender 面光的辐亮度 = P / (π A)，实测 EEVEE 12.47、Cycles 12.71 对
    12.73）。面光的高光就是“管灯在立柱上拉出的长竖高光”，正是要看闪不闪的东西。preview 机位再加一个 EEVEE 球形
    反射探针（过道中间、1.70 m、256 / 面，圣经的车内立方图），金属里映出亮着的车厢，而不是黑的夜；切片机位不加
    （Unity 的切片场景里也没有车厢探针）。阴影默认关：Unity 里管灯是烘好的光照图、没有实时阴影；EEVEE 的软阴影是
    随机追踪的，1 个采样时每帧是噪点，会被当成闪烁（关掉以后头不动，连续 4 帧逐像素相同）。夜路：世界只有一点
    暗蓝灰（#30343A × 0.03），没有太阳。
    量数照抄 origin/pkg/engineering:Engineering/UnityTest/Editor/LanbaiTestCapture.cs @ ec0b071（micro_motion 这一段
    和 33f9a60 一字不差；中间只改了贴图压缩那几行，682 行以后的行号往后挪了 6 行）：
      Luma = 0.2126 R + 0.7152 G + 0.0722 B（8 位 sRGB，float，第 756 行）；
      逐像素累加 sum、sum²、二阶时间差分 dd = y − 2·p1 + p2 的平方，和 df = y − Luma(参考) 的 dsum、dsum²
      （第 527–533 行），APL = 每帧平均亮度（第 535 行）；
      motion_std = √max(0, sum²/n − m²)（第 551 行）；hf_raw = √(Σdd² / (n − 2) / 6)（第 552 行）；
      shimmer = (float)√max(0, dsum²/n − (dsum/n)²)（第 553 行）；
      shimmer_mean / shimmer_p99 / shimmer_frac（> shimmer_threshold 4）、motion_std_mean / motion_std_p99、
      hf_raw_mean / hf_raw_p99 / hf_raw_frac（> hf_threshold 6）、apl_min / apl_max / apl_max_step（第 555–573 行）；
      热图 heat_motion_std、heat_hf_raw（0 → heat_scale 24）和 heat_shimmer（0 → max(1, heat_scale / 2)）（第 574–581 行，
      Img.Heat 第 818–836 行）；记录的字段（第 582–591 行）；平均 Avg（第 609 行）；百分位 Pct = 排序后取第
      (int)(q·(N−1)) 个（第 610–615 行）；参考图只在 reference_ss > ss 时渲（第 470、495 行）；
      头部运动 W() 和位置 = 眼 + rot·off、朝向 = rot·q（第 510–517、605–608 行），参考相机同一个姿态（第 520–525 行）；
      超采样 1（第 464 行）、渲进 HDR 线性目标、不开 MSAA、Graphics.Blit 双线性缩到 sRGB 8 位（第 255–265 行）；
      ppd 定尺寸（第 130–138 行）；look_at_object 包围盒 + toward + distance 的机位（第 83–105 行）；至少 3 帧（第 485 行）。
    出 /tmp/bus/parts/<part>_<view>_flicker.json、..._flicker_heat_shimmer.png、..._flicker_heat_motion_std.png、
    ..._flicker_heat_hf_raw.png、..._flicker_f000.png（第一帧）、..._flicker_ref000.png（第一帧的参考图）。
    **这是 Blender 里的近似，不是 Unity 的测量；Unity 层的结果以总工程师测试工具（LanbaiTestCapture）出的为准**
    （D-40a #4：三层分开记）。和 Unity 不同的地方：没有 Lanbai/Cabin 的几何高光抗锯齿（D-40 #4，Blender 的节点
    拿不到 ddx / ddy；Unity 里测的图和参考图都有它，这里都没有，所以金属上的 shimmer 应当比 Unity 的大）；没有零件
    图集的法线 / 遮罩、mip 和贴图压缩；管灯的漫射在 Unity 里是烘好的 _CabinTubeLM（带反弹和 AO），这里是 EEVEE 的
    实时面光（只有直射、没有阴影）；Unity 的高光来自反射探针（和主光），这里来自缩过的面光高光加一个球形探针；
    没有 PPv2 调色。
    --engine workbench：旧的 Workbench 路线，**不看高光**（没有 PBR 高光，看不出高光闪烁），只能看几何边缘的爬动，
    默认不用。--engine cycles_point：没有 libEGL 时的备用（Cycles 1 spp、像素中心点采样、只有直射的点光和太阳，
    同样不抗锯齿），数和 EEVEE 的不能直接比。JSON 里写明用的是哪个。

EEVEE / Workbench 在没有显示器的机器上要 libEGL（Mesa llvmpipe 就行；EGL_BAD_MATCH 的警告不碍事，第一帧编译
shader 约 20 s）。系统里没有 libEGL.so.1 时：装 libegl1 + libegl-mesa0，或者把这两个 deb 解到一个文件夹，
传 --egl-dir（或设 LANBAI_EGL_DIR），脚本会从那里预载。都没有就报错退出（退出码 3），或者 --allow-fallback 改用
cycles_point。

退出码：0 成功；2 参数不对；3 没有 EGL；4 零件 / 场景搭不起来（多半是别的会话正在改 seat.py 等，用 LANBAI_BUS_SRC），
或者快照里没有 bake_report.json。
没有在 Unity 里编译、运行过；Blender 层的数只代表 Blender 层。
"""
import argparse
import ctypes
import json
import math
import os
import shutil
import subprocess
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

SNAP_RECIPE = ('mkdir -p /tmp/snap && git archive HEAD Bus/Source Bus/Textures Bus/Docs~/bake_report.json '
               '| tar -x -C /tmp/snap\n       LANBAI_BUS_SRC=/tmp/snap/Bus/Source ~/bpy/bin/python Bus/Source/parts/qa.py ...')
try:
    import build_bus as BB  # noqa: E402
    import bus_spec as B  # noqa: E402
    from parts import preview as PV  # noqa: E402
except Exception:                                    # the lead may be mid-edit in seat.py / common.py / build_bus.py
    traceback.print_exc()
    print('[qa] ERROR: the bus sources in %s do not import. If another session is editing them, snapshot the committed\n'
          '     ones and point LANBAI_BUS_SRC at the copy:\n       %s' % (SRC, SNAP_RECIPE))
    sys.exit(4)

CAPTURE_CS = ('origin/pkg/engineering:Engineering/UnityTest/Editor/LanbaiTestCapture.cs @ ec0b071 '
              '(micro_motion identical to 33f9a60)')
TARGET_GREY = 118.0          # 18% 灰卡在 sRGB 里的读数
GREY_ALBEDO, WHITE_ALBEDO, FLOOR_ALBEDO = 0.18, 0.90, 0.18
BACKDROP = 0.18              # what camera rays (and rays straight through glass) see, x env: reads ~118 at EV 0
PLATE_ALBEDO = 0.04          # the dark plate under the cards (the grey card would vanish on the grey backdrop)
CLIP_LEVEL = 254             # a pixel is clipped when any channel reaches this

# 总工程师 bus_slice.json 的六台机位（origin/pkg/engineering:Engineering/UnityTest/tests/bus_slice.json @ ec0b071，
# 侧窗两台 main 90bf00c）：看切片物体的包围盒中心（侧窗两台看 SLICE_ANCHOR），朝主座位的眼退 distance，裁 40 × 30°，20 px/°。切片物体 = 车里真位置上的那一件
# （Bus/Editor/LanbaiBusSliceBuilder.cs：Slice_Seat = SeatR0 主座位，Slice_SideWindow = WinR1，Slice_Pillar = PoleR0）。
SLICE_CAMS = {
    'seat_05m': ('seat', 0.5), 'seat_10m': ('seat', 1.0),
    'window_05m': ('window', 0.5), 'window_10m': ('window', 1.0),
    'pillar_05m': ('pillar', 0.5), 'pillar_10m': ('pillar', 1.0),
}
SLICE_CROP, SLICE_PPD = (40.0, 30.0), 20.0
# look_at_anchor（main 90bf00c，测试工具 1.2.2，LanbaiTestCapture 93-97）：两台侧窗机位不再对着包围盒中心（只拍到玻璃），
# 对着包围盒里的一点，每轴 0 = min、1 = max：window_05m 窗扣、window_10m 窗框的后上角
SLICE_ANCHOR = {'window_05m': (0.5, 0.785, 0.5), 'window_10m': (0.5, 0.785, 0.774)}
# bus_slice.json 'sequences' (cam -> sequence id) and its shimmer checks (gate false: an initial value, set after the
# slice's first Unity run). Listed so the Blender number can be found next to the Unity one; it is not that check.
SLICE_SEQ = {'pillar_10m': 'pillar_micro', 'window_10m': 'window_micro', 'seat_10m': 'seat_micro'}
UNITY_CHECKS = {'pillar_micro': dict(id='pillar_shimmer', metric='seq.pillar_micro.shimmer_frac', op='<=', value=0.005,
                                     gate=False),
                'window_micro': dict(id='window_shimmer', metric='seq.window_micro.shimmer_frac', op='<=', value=0.005,
                                     gate=False)}

# Lanbai/Cabin _HeightSmooth on the stanchions (LanbaiBusBuild.cs 'Steel'; LanbaiCabin.shader @27145d8 263-264)
STEEL_BAND = (1.62, 2.42, 0.80)
# the tube lights exactly as bake_lightmap.add_tubes makes them for _CabinTubeLM (#E4F1F3, 0.12 x (length - 0.06) m at
# CEIL_Y - 0.05, an up-facing twin at 12 %), at the power its calibration found (bake_report.json watts_per_tube: mean
# of 7 mid-cabin cushions E = 0.60). Their specular is scaled so the tube reflects as bright as Unity's tube diffuser
# (LanbaiBusBuild 'TubeDiffuser' _EmissionColor (1.632, 2.024, 2.042), luma 1.95): that is what the cabin cubemap gives
# the metals in Unity. Blender area light radiance = P / (pi A) (measured: EEVEE 12.47, Cycles 12.71 vs 12.73).
TUBE_LIN = (0.776, 0.882, 0.894)
TUBE_EMISSION_LUMA = 0.2126 * 1.632 + 0.7152 * 2.024 + 0.0722 * 2.042
TUBE_WATTS_DEFAULT = 9.01


def tube_watts(override=None):
    """watts per tube: --tube-watts, else the lightmap bake's report next to the sources (SRC/../Docs~). With
    LANBAI_BUS_SRC (a snapshot) the snapshot must carry its own report - never the working tree's, which may hold
    another session's uncommitted bake - so a missing one exits 4. Without a snapshot: warn and use 9.01."""
    if override:
        return float(override), '--tube-watts'
    p = os.path.normpath(os.path.join(SRC, '..', 'Docs~', 'bake_report.json'))
    try:
        with open(p, encoding='utf-8') as f:
            return float(json.load(f)['watts_per_tube']), p
    except Exception as e:  # noqa: BLE001
        if os.environ.get('LANBAI_BUS_SRC'):
            print('[qa] ERROR: %s is not readable (%s). The snapshot needs its own bake report:\n       %s\n'
                  '     or pass --tube-watts.' % (p, e, SNAP_RECIPE))
            raise SystemExit(4) from e
        print('[qa] WARNING: %s is not readable (%s): using the default %.2f W per tube' % (p, e, TUBE_WATTS_DEFAULT))
        return TUBE_WATTS_DEFAULT, 'default (no bake_report.json)'


def repo_head():
    """the commit of the sources the run used: the working tree's HEAD (+ 'dirty' when Bus/Source differs), or
    'snapshot' when LANBAI_BUS_SRC points elsewhere (the caller wrote down which commit it archived)."""
    if os.environ.get('LANBAI_BUS_SRC'):
        return 'snapshot at %s' % SRC
    try:
        root = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
        h = subprocess.run(['git', '-C', root, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                           timeout=10).stdout.strip()
        dirty = subprocess.run(['git', '-C', root, 'status', '--porcelain', '--', 'Bus/Source'], capture_output=True,
                               text=True, timeout=10).stdout.strip()
        return h + (' + uncommitted Bus/Source changes' if dirty else '')
    except Exception:  # noqa: BLE001
        return 'unknown'


# ------------------------------------------------------------------------------------------------ small helpers
def srgb_to_lin(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def lin_to_srgb8(lin, ev=0.0):
    """scene-linear RGB -> 8-bit sRGB: x 2^EV, clip to 1, piecewise sRGB, round to nearest. This is Blender's Standard
    view on an sRGB display (checked against Blender's own PNG with dither 0: at most 1 level, on 0.01 % of pixels) and
    Unity's write of an HDR target into an sRGB ARGB32 one (LanbaiTestCapture.cs 255-265)."""
    v = np.clip(np.asarray(lin, np.float32) * np.float32(2.0 ** ev), 0.0, 1.0)
    s = np.where(v <= np.float32(0.0031308), v * np.float32(12.92),
                 np.float32(1.055) * np.power(v, np.float32(1 / 2.4)) - np.float32(0.055))
    return np.floor(s * np.float32(255.0) + np.float32(0.5)).astype(np.uint8)


def luma8(a):
    """LanbaiTestCapture.cs 756: Img.Luma, on 8-bit sRGB values (float32, same order of operations)."""
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


def camera_only(ob):
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, attr, False)


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


def build_part(P, quality='low'):
    """the part's builder (with preview's quality for the parts that have one), with a clear message when the sources
    are mid-edit."""
    try:
        return P['build'](quality) if P.get('quality') else P['build']()
    except Exception:
        traceback.print_exc()
        print('[qa] ERROR: the part did not build from %s (another session editing it?). Use a HEAD snapshot:\n'
              '       %s' % (SRC, SNAP_RECIPE))
        return None


# ------------------------------------------------------------------------------------------------ neutral (D-40 #2)
CARD_U = ((0.015, 0.065), (0.072, 0.122))      # grey, white: image-x ranges from the corner's side (0 = that edge)
CARD_V0 = 0.03                                  # margin from the corner's top / bottom edge
PLATE_M = 0.008                                 # the plate's margin round the cards (fraction of the width)
CORNERS = ('bl', 'br', 'tl', 'tr')
CORNER_NAME = {'bl': '左下', 'br': '右下', 'tl': '左上', 'tr': '右上', 'strip': '图下面接的窄条'}


def card_rects(W, H, corner='bl'):
    """pixel rects (x0, y0, x1, y1; y from the top) + (u0, u1, v0, v1; v from the bottom) of the grey and the white
    card in a corner ('bl', 'br', 'tl', 'tr')."""
    out = []
    for u0, u1 in CARD_U:
        s = (u1 - u0) * W / H                   # square cards
        v0, v1 = CARD_V0, CARD_V0 + s
        if corner[1] == 'r':
            u0, u1 = 1 - u1, 1 - u0
        if corner[0] == 't':
            v0, v1 = 1 - v1, 1 - v0
        out.append((u0 * W, (1 - v1) * H, u1 * W, (1 - v0) * H, u0, u1, v0, v1))
    return out


def plate_rect(W, H, corner='bl'):
    """(u0, u1, v0, v1) of the dark plate under both cards."""
    r = card_rects(W, H, corner)
    mv = PLATE_M * W / H
    return (max(0.0, min(c[4] for c in r) - PLATE_M), min(1.0, max(c[5] for c in r) + PLATE_M),
            max(0.0, min(c[6] for c in r) - mv), min(1.0, max(c[7] for c in r) + mv))


def plate_px(W, H, corner, pad=2):
    """the plate as a pixel slice (y0, y1, x0, x1), padded."""
    u0, u1, v0, v1 = plate_rect(W, H, corner)
    return (max(0, int((1 - v1) * H) - pad), min(H, int(math.ceil((1 - v0) * H)) + pad),
            max(0, int(u0 * W) - pad), min(W, int(math.ceil(u1 * W)) + pad))


def add_cards(cam, corner='bl', depth=0.05):
    """the grey and the white card on a dark plate in a corner, in the camera's image plane, seen by the camera only."""
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    tx, ty = tan_half(cam)
    M = cam.matrix_world
    W, H = sc.render.resolution_x, sc.render.resolution_y

    def plane(name, u0, u1, v0, v1, dep, alb):
        loc = [((2 * u - 1) * tx * dep, (2 * v - 1) * ty * dep, -dep) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        ob = quad(name, [M @ Vector(p) for p in loc], diffuse_mat(name, alb))
        camera_only(ob)
        return ob

    obs = [plane('QA_Card%d' % k, *r[4:], depth, alb)
           for k, (r, alb) in enumerate(zip(card_rects(W, H, corner), (GREY_ALBEDO, WHITE_ALBEDO)))]
    obs.append(plane('QA_CardPlate', *plate_rect(W, H, corner), depth * 1.02, PLATE_ALBEDO))
    return obs


def read_cards(a, rects, y_off=0):
    """mean sRGB (8-bit) of the inner half of the grey and the white card -> [(r, g, b, luma), ...]. a: HxWx3 uint8;
    y_off: the image's first row in frame rows (a strip under the frame)."""
    a = a.astype(np.float64)
    out = []
    for x0, y0, x1, y1, *_ in rects:
        y0, y1 = y0 - y_off, y1 - y_off
        mx, my = (x1 - x0) * 0.25, (y1 - y0) * 0.25
        p = a[int(round(y0 + my)):int(round(y1 - my)), int(round(x0 + mx)):int(round(x1 - mx))].reshape(-1, 3).mean(0)
        out.append([round(float(c), 2) for c in p] + [round(float(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]), 2)])
    return out


def load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB'))


def studio(env=1.0):
    """the grey studio. World: uniform white (strength env) for every ray but the camera's: camera rays and rays
    straight through glass see BACKDROP grey. Floor: an 18% grey plane at FLOOR_Y seen by camera, glossy and
    transmission rays (a horizon for the metals; it still receives the part's contact shadow), not by diffuse or
    shadow rays (it does not block the environment, so the cards get the same light in every view)."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new('QA_Studio')
    w.use_nodes = True
    nt = w.node_tree
    lit = nt.nodes['Background']
    lit.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    lit.inputs[1].default_value = env
    back = nt.nodes.new('ShaderNodeBackground')
    back.inputs[0].default_value = (BACKDROP, BACKDROP, BACKDROP, 1.0)
    back.inputs[1].default_value = env
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(lp.outputs['Is Transmission Ray'], mx.inputs[1])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mx.outputs['Value'], mix.inputs[0])
    nt.links.new(lit.outputs['Background'], mix.inputs[1])
    nt.links.new(back.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], nt.nodes['World Output'].inputs['Surface'])
    w.color = (BACKDROP, BACKDROP, BACKDROP)
    sc.world = w
    y = B.FLOOR_Y - 0.0005
    h = 15.0
    fl = quad('QA_Floor', [BB.U2B(p) for p in ((-h, y, -h), (-h, y, h), (h, y, h), (h, y, -h))],
              diffuse_mat('QA_Floor', FLOOR_ALBEDO))
    fl.visible_diffuse = False
    fl.visible_shadow = False
    return fl


def material_census(objs):
    """{material name: number of objects} on the part (which surfaces the neutral picture has to identify)."""
    out = {}
    for o in objs:
        if o.type == 'MESH':
            for ms in o.data.materials:
                if ms is not None:
                    out[ms.name] = out.get(ms.name, 0) + 1
    return dict(sorted(out.items()))


def part_mask(floor, tmp):
    """which pixels are the part: one sample, no bounces, transparent film, floor off -> alpha > 0.5 (glass counts)."""
    sc = bpy.context.scene
    c, ims = sc.cycles, sc.render.image_settings
    keep = (sc.render.film_transparent, c.samples, c.use_denoising, c.max_bounces, ims.color_mode, sc.render.use_border)
    floor.hide_render = True
    sc.render.film_transparent, c.samples, c.use_denoising, c.max_bounces = True, 1, False, 0
    ims.color_mode, sc.render.use_border = 'RGBA', False
    sc.render.filepath = os.path.join(tmp, 'mask.png')
    try:
        bpy.ops.render.render(write_still=True)
        m = np.asarray(Image.open(sc.render.filepath).convert('RGBA'))[..., 3] > 127
    finally:
        floor.hide_render = False
        (sc.render.film_transparent, c.samples, c.use_denoising, c.max_bounces, ims.color_mode,
         sc.render.use_border) = keep
    return m


def pick_corner(mask):
    """the first corner whose plate covers no part pixel -> (corner or 'strip', {corner: part pixels under it})."""
    H, W = mask.shape
    over = {}
    for c in CORNERS:
        y0, y1, x0, x1 = plate_px(W, H, c)
        over[c] = int(mask[y0:y1, x0:x1].sum())
        if over[c] == 0:
            return c, over
    return 'strip', over


def render_border(path, u0, u1, v0, v1, crop):
    sc = bpy.context.scene
    sc.render.use_border, sc.render.use_crop_to_border = True, crop
    sc.render.border_min_x, sc.render.border_max_x = max(0.0, u0), min(1.0, u1)
    sc.render.border_min_y, sc.render.border_max_y = max(0.0, v0), min(1.0, v1)
    sc.render.filepath = path
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        sc.render.use_border, sc.render.use_crop_to_border = False, False


def card_strip(cam, part_objs, floor, tmp):
    """the cards alone under the frame (no free corner): same camera and exposure, the part and the floor hidden from
    the camera only (they still block light as in the picture). -> (strip image HxWx3, card rects, y offset)."""
    sc = bpy.context.scene
    W, H = sc.render.resolution_x, sc.render.resolution_y
    cards = add_cards(cam, 'bl')
    hid = [o for o in list(part_objs) + [floor] if o.type == 'MESH' and o.visible_camera]
    for o in hid:
        o.visible_camera = False
    try:
        v1 = plate_rect(W, H, 'bl')[3]
        render_border(os.path.join(tmp, 'strip.png'), 0.0, 1.0, 0.0, min(1.0, v1 + 0.01), True)
        a = load_rgb(os.path.join(tmp, 'strip.png'))
    finally:
        for o in hid:
            o.visible_camera = True
        for o in cards:
            bpy.data.objects.remove(o, do_unlink=True)
    return a, card_rects(W, H, 'bl'), H - a.shape[0]


def neutral_view_cam(P, v, res):
    eye, tgt = P['views'][v]
    hfov = float(P.get('view_hfov', {}).get(v, P.get('hfov', 64.0)))
    return PV.camera(eye, tgt, hfov=hfov, res=res), eye, tgt, hfov


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
    sc.render.dither_intensity = 0.0
    sc.render.film_transparent = False
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    objs = build_part(P, a.quality)
    if objs is None:
        return 4
    keep = set(objs)
    dropped = 0
    for o in list(bpy.data.objects):             # the bus shell, ceiling, floor, glass, lights...: only the part stays
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
            dropped += 1
    objs = [o for o in objs if o.name in bpy.data.objects]
    if not a.flat:
        from parts import materials as MATS
        MATS.apply_details(objs)
    census = material_census(objs)
    floor = studio(a.env)
    res = (int(round(1280 * a.res_pct / 100)), int(round(720 * a.res_pct / 100)))
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='qa_neutral_')
    views = [v for v in P['views'] if not a.views or v in a.views.split(',')]
    if not views:
        print('[qa neutral] ERROR: %s has no view among %s (%s)' % (a.part, a.views, ', '.join(P['views'])))
        return 2
    t_all = time.time()
    # 1) per view: the part mask (where may the cards go), then the grey-card calibration of that view
    cal = {}
    for v in views:
        t0 = time.time()
        cam, eye, tgt, hfov = neutral_view_cam(P, v, res)
        mask = part_mask(floor, tmp)
        corner, over = pick_corner(mask)
        cc = corner if corner != 'strip' else 'bl'
        cards = add_cards(cam, cc)
        sc.view_settings.exposure = 0.0
        sc.cycles.samples = a.cal_samples
        u0, u1, v0, v1 = plate_rect(*res, cc)
        render_border(os.path.join(tmp, 'cal.png'), u0 - 0.01, u1 + 0.01, v0 - 0.01, v1 + 0.01, False)
        g0 = read_cards(load_rgb(os.path.join(tmp, 'cal.png')), card_rects(*res, cc))[0][3]
        ev = float(np.clip(math.log2(float(srgb_to_lin(TARGET_GREY / 255.0)) / max(float(srgb_to_lin(g0 / 255.0)), 1e-6)),
                           -8, 8))
        cal[v] = dict(mask=mask, corner=corner, over=over, ev=ev, g0=g0, hfov=hfov, eye=eye, tgt=tgt,
                      seconds=time.time() - t0)
        print('[qa neutral] %s %s: cards %s (part px under each corner %s), card alone %.1f -> EV %+.2f'
              % (a.part, v, corner, over, g0, ev))
        for o in cards + [cam]:
            bpy.data.objects.remove(o, do_unlink=True)
    ev_part = float(np.median([c['ev'] for c in cal.values()]))
    print('[qa neutral] %s: one EV for the part = median of %d views = %+.3f' % (a.part, len(cal), ev_part))
    # 2) the pictures, all at the part's EV
    rec = []
    for v in views:
        t0 = time.time()
        c = cal[v]
        cam, eye, tgt, hfov = neutral_view_cam(P, v, res)
        cards = add_cards(cam, c['corner']) if c['corner'] != 'strip' else []
        sc.view_settings.exposure = ev_part
        sc.cycles.samples = a.samples
        path = out_path(a.out, a.part, v, 'neutral.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = load_rgb(path)
        if c['corner'] != 'strip':
            grey, white = read_cards(img, card_rects(*res, c['corner']))
            y0, y1, x0, x1 = plate_px(res[0], res[1], c['corner'])
            free = np.ones(c['mask'].shape, bool)
            free[y0:y1, x0:x1] = False
        else:
            strip, rects, y_off = card_strip(cam, objs, floor, tmp)
            grey, white = read_cards(strip, rects, y_off)
            Image.fromarray(np.concatenate([img, strip], 0)).save(path)
            free = np.ones(c['mask'].shape, bool)
        m = c['mask']
        clip = img.max(-1) >= CLIP_LEVEL
        npart = int(m.sum())
        bd = ~m & free
        ylum = luma8(img)
        rec.append(dict(
            view=v, file=path, eye=list(eye), target=list(tgt), hfov_deg=c['hfov'],
            px_per_deg_mean=round(res[0] / c['hfov'], 2),
            px_per_deg_centre=round(res[0] / (2 * math.tan(math.radians(c['hfov']) / 2) * 180 / math.pi), 2),
            exposure_ev_calibrated=round(c['ev'], 3), exposure_ev_used=round(ev_part, 3),
            grey_card_alone_luma_ev0=c['g0'], grey_card_rgb_luma=grey, white_card_rgb_luma=white,
            cards=dict(where=c['corner'], where_zh=CORNER_NAME[c['corner']], part_px_under_each_corner=c['over']),
            part_px_pct=round(100.0 * npart / m.size, 2),
            part_clip_pct=round(100.0 * float((clip & m).sum()) / max(1, npart), 3),
            frame_clip_pct=round(100.0 * float(clip[:m.shape[0]].mean()), 3),
            backdrop_luma_median=round(float(np.median(ylum[:m.shape[0]][bd])), 1) if bd.any() else None,
            seconds=round(c['seconds'] + time.time() - t0, 1)))
        print('[qa neutral] %s %s: hfov %g, EV %+.2f, grey card %.1f (target %d), white card %.1f, part %.1f%% of the '
              'frame, clipped %.2f%% of the part, backdrop %s, %.0f s'
              % (a.part, v, c['hfov'], ev_part, grey[3], TARGET_GREY, white[3], rec[-1]['part_px_pct'],
                 rec[-1]['part_clip_pct'], rec[-1]['backdrop_luma_median'], time.time() - t0))
        for o in cards + [cam]:
            bpy.data.objects.remove(o, do_unlink=True)
    shutil.rmtree(tmp, ignore_errors=True)
    js = os.path.join(a.out, '%s_neutral.json' % a.part)
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(dict(
            part=a.part, mode='neutral', ruling='D-40 #2', sources=SRC, sources_commit=repo_head(), resolution=list(res),
            engine='CYCLES (CPU)', samples=a.samples, calibration_samples=a.cal_samples, denoise=True,
            quality=a.quality if P.get('quality') else None,
            light=dict(environment='uniform white, strength %.2f, for diffuse and glossy rays (a constant colour, no '
                                   'HDRI image)' % a.env,
                       backdrop='camera rays and rays straight through glass see %.2f grey x %.2f (Light Path Is '
                                'Camera Ray / Is Transmission Ray): ~sRGB 118 at EV 0' % (BACKDROP, a.env),
                       floor='Diffuse %.2f grey plane at FLOOR_Y, visible to camera, glossy and transmission rays only '
                             '(not diffuse, not shadow)' % FLOOR_ALBEDO,
                       cabin_tube_lights=False, sun=False),
            colour=dict(view_transform='Standard', look='None', dither=0.0, grading=False,
                        exposure='one EV for the part = the median of the per-view grey-card calibrations',
                        exposure_ev=round(ev_part, 3)),
            cards=dict(grey_albedo=GREY_ALBEDO, white_albedo=WHITE_ALBEDO, plate_albedo=PLATE_ALBEDO,
                       target_grey_srgb=TARGET_GREY,
                       where='the first corner (bl, br, tl, tr) whose plate covers no part pixel (1-sample mask); none '
                             'free: a strip of the cards alone under the picture. 5 cm in front of the lens, '
                             'camera-visible only (no shadow, no reflection)'),
            clip=dict(level=CLIP_LEVEL, rule='any channel >= %d' % CLIP_LEVEL,
                      part_mask='1 sample, no bounces, transparent film, floor hidden: alpha > 0.5'),
            materials='flat MAT_TABLE' if a.flat else 'parts/materials.apply_details (the final ones)',
            part_materials=census, scene_objects_removed=dropped, views=rec, seconds=round(time.time() - t_all, 1),
            note='Blender 离线层（D-40a #4）；没有在 Unity 里编译或运行过。认不认得出材质由人看图判，这个 JSON 只记条件和读数。'),
            f, ensure_ascii=False, indent=1)
    print('[qa neutral] %s: %d views -> %s' % (a.part, len(rec), js))
    return 0


# ------------------------------------------------------------------------------------------------ flicker (D-40a #5)
def W_(s, f1, p1, f2, p2):
    """LanbaiTestCapture.cs 605-608 (float32 in Unity; the sum of two sines, |W| <= 1)."""
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
    """LanbaiTestCapture.cs 510-517: off / q from W(), position = eye + rot * off, rotation = rot * q."""
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


def slice_target(cid, lo, hi):
    """the point a slice camera looks at: the bounds centre, or its look_at_anchor inside the bounds."""
    an = SLICE_ANCHOR.get(cid)
    return (lo + hi) / 2 if an is None else lo + np.asarray(an, float) * (hi - lo)


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
    Blender world z), with 5 cm smoothsteps at both ends (LanbaiCabin.shader @27145d8 263-264: hb =
    smoothstep(x - 0.05, x, P.y) * (1 - smoothstep(y, y + 0.05, P.y))). Roughness = 1 - smoothness."""
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
            for lk in list(bs.inputs['Base Color'].links) + list(bs.inputs['Roughness'].links) + \
                    list(bs.inputs['Metallic'].links):
                m.node_tree.links.remove(lk)
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


def night_cabin_light(world_strength, spec=None, watts_override=None):
    """the cabin's 10 tube lights as bake_lightmap.add_tubes puts them (real places, bake power), a dim night world,
    no sun. spec None = scale the specular so a tube reflects at Unity's diffuser brightness (see TUBE_EMISSION_LUMA)."""
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o, do_unlink=True)
    watts, wsrc = tube_watts(watts_override)
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
    metrics would count as flicker. With them off, a still camera gives identical frames."""
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


def render_linear(path):
    """render the scene to a half-float EXR and read it back: scene-linear RGB, HxWx3 float32, top row first."""
    sc = bpy.context.scene
    ims = sc.render.image_settings
    ims.file_format, ims.color_mode, ims.color_depth, ims.exr_codec = 'OPEN_EXR', 'RGB', '16', 'NONE'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size
        px = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px)
    finally:
        bpy.data.images.remove(img)
    os.remove(path)
    return np.ascontiguousarray(px.reshape(h, w, 4)[::-1, :, :3])


def blit_down(big, k):
    """Unity Graphics.Blit(big, small) with FilterMode.Bilinear from a k-times target (LanbaiTestCapture.cs 255-265):
    one bilinear tap at each output pixel centre, in linear (the HDR source), before the sRGB 8-bit write. The tap is at
    big texel coordinate (x + 0.5) k: for k = 4 it falls between texels 4x+1 and 4x+2, i.e. the mean of the 2 x 2 texels
    nearest the centre (not a 4 x 4 box); for odd k it is the centre texel. Symmetric within a block, so top-down rows
    give the same result as Unity's bottom-up ones."""
    H, W = big.shape[0] // k, big.shape[1] // k

    def taps(n):
        u = (np.arange(n) + 0.5) * k - 0.5
        j0 = np.floor(u).astype(np.int64)
        f = (u - j0).astype(np.float32)
        return np.clip(j0, 0, n * k - 1), np.clip(j0 + 1, 0, n * k - 1), f

    x0, x1, fx = taps(W)
    y0, y1, fy = taps(H)
    fx, fy = fx[None, :, None], fy[:, None, None]
    r0, r1 = big[y0], big[y1]
    top = r0[:, x0] * (1 - fx) + r0[:, x1] * fx
    bot = r1[:, x0] * (1 - fx) + r1[:, x1] * fx
    return top * (1 - fy) + bot * fy


def heat(v, mean, scale):
    """LanbaiTestCapture.cs 818-836 (Img.Heat; Color32.Lerp truncates to bytes)."""
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


def avg(a):
    """LanbaiTestCapture.cs 609: the double sum of the floats / length."""
    return float(np.sum(a, dtype=np.float64) / a.size)


def pct(a, q):
    """LanbaiTestCapture.cs 610-615."""
    b = np.sort(a, axis=None)
    return float(b[min(b.size - 1, int(q * (b.size - 1)))])


class Acc:
    """the per-pixel sums of LanbaiTestCapture.cs 492-535 and the numbers of 545-573."""

    def __init__(self, w, h, with_ref):
        self.n, self.N = 0, w * h
        self.S1 = np.zeros((h, w), np.float64)
        self.S2 = np.zeros((h, w), np.float64)
        self.HF2 = np.zeros((h, w), np.float64)
        self.D1 = np.zeros((h, w), np.float64) if with_ref else None
        self.D2 = np.zeros((h, w), np.float64) if with_ref else None
        self.nd = 0
        self.p1 = np.zeros((h, w), np.float32)
        self.p2 = np.zeros((h, w), np.float32)
        self.apl = []

    def add(self, y):
        """y: float32 luma of one measured frame (0-255): 529-535."""
        self.S1 += y
        self.S2 += y.astype(np.float64) * y
        if self.n >= 2:
            dd = (y - np.float32(2) * self.p1 + self.p2).astype(np.float64)     # float math, then double (532)
            self.HF2 += dd * dd
        self.apl.append(float(y.astype(np.float64).sum() / self.N))
        self.p2, self.p1 = self.p1, y
        self.n += 1

    def add_ref(self, y, yr):
        """y: that frame's luma again, yr: the luma of its reference (533: double df = y - Luma(rpx))."""
        df = (y - yr).astype(np.float64)
        self.D1 += df
        self.D2 += df * df
        self.nd += 1

    def metrics(self, thr, sh_thr):
        n = self.n
        m = self.S1 / n
        mean = m.astype(np.float32)
        std = np.sqrt(np.maximum(0.0, self.S2 / n - m * m)).astype(np.float32)          # 551
        hf = np.sqrt(self.HF2 / (n - 2) / 6.0).astype(np.float32)                        # 552
        sh = None
        met = dict(frames=n)
        if self.D1 is not None and self.nd == n:
            dm = self.D1 / n
            sh = np.sqrt(np.maximum(0.0, self.D2 / n - dm * dm)).astype(np.float32)     # 553
            met.update(shimmer_mean=avg(sh), shimmer_p99=pct(sh, 0.99),
                       shimmer_frac=float((sh > np.float32(sh_thr)).sum()) / self.N)
        steps = [abs(self.apl[i] - self.apl[i - 1]) for i in range(1, len(self.apl))]
        met.update(motion_std_mean=avg(std), motion_std_p99=pct(std, 0.99),
                   hf_raw_mean=avg(hf), hf_raw_p99=pct(hf, 0.99),
                   hf_raw_frac=float((hf > np.float32(thr)).sum()) / self.N,
                   apl_min=min(self.apl), apl_max=max(self.apl), apl_max_step=max(steps) if steps else 0.0)
        return dict(std=std, hf=hf, sh=sh, mean=mean), met


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
        print('[qa flicker] ERROR: at least 3 frames (LanbaiTestCapture.cs 485)')
        return 2
    reset()
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'     # the frames are converted from linear EXR by lin_to_srgb8,
    sc.view_settings.look = 'None'                   # which is this view (and the Unity sRGB target write)
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.dither_intensity = 0.0
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    view = a.view or next(iter(P['views']))
    seq_id = None
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
            print('[qa flicker] ERROR: the slice pieces did not build from %s; use a HEAD snapshot:\n       %s'
                  % (SRC, SNAP_RECIPE))
            return 4
        _, lo, hi = bounds_center(pieces[piece])
        target = slice_target(cid, lo, hi)
        d = np.asarray(B.EYE, float) - target                      # LanbaiTestCapture.cs 95-105: back off toward 'toward'
        eye = target + d / np.linalg.norm(d) * dist
        crop = SLICE_CROP
        ppd = SLICE_PPD
        seq_id = SLICE_SEQ.get(cid)
        cam_info = dict(slice_cam=cid, look_at_object=piece, bounds_center=[round(float(v), 4) for v in (lo + hi) / 2],
                        look_at_anchor=SLICE_ANCHOR.get(cid), look_at=[round(float(v), 4) for v in target],
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
    light = night_cabin_light(a.world, a.tube_spec, a.tube_watts)
    if eng == 'eevee' and a.probe and not view.startswith('slice:'):
        light['reflection'] = cabin_probe(target)
    else:
        light['reflection'] = 'the night world only (no probe)'
    mats = flicker_materials(a.detail_normals) if eng == 'eevee' else {}
    rot = look_rotation(target - eye)
    w_, h_ = ppd_size(crop[0], crop[1], ppd)
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
    ss = 1                                                       # LanbaiTestCapture.cs 464 (a sequence's ss: 1)
    ref_k = a.reference_ss if a.reference_ss > ss else 0         # 470 / 495: a reference only when reference_ss > ss
    acc = Acc(w_, h_, ref_k > 0)
    ys = [] if ref_k else None
    tag = '%s_%s' % (a.part, view.replace(':', '-'))
    keep = os.path.join(a.out, tag + '_flicker_frames') if a.save_frames else None
    tmp = tempfile.mkdtemp(prefix='qa_flicker_')
    if keep:
        os.makedirs(keep, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    # pass 1: the measured frames (ss 1)
    sc.render.resolution_x, sc.render.resolution_y = w_, h_
    for i in range(n):
        e, R = head_pose(i / fps, eye, rot, amp_m, amp_deg)
        place_camera(cam, e, R)
        px = lin_to_srgb8(render_linear(os.path.join(tmp, 'f.exr')), a.exposure)
        y = luma8(px)
        acc.add(y)
        if ys is not None:
            ys.append(y)
        if keep:
            Image.fromarray(px).save(os.path.join(keep, '%04d.png' % i))
        if i == 0:
            Image.fromarray(px).save(os.path.join(a.out, tag + '_flicker_f000.png'))
            print('[qa flicker] frame 0 in %.0f s (shader compile)' % (time.time() - t0))
        elif i % 15 == 0:
            print('[qa flicker] frame %d / %d, %.0f s' % (i, n, time.time() - t0))
    t1 = time.time()
    # pass 2: the same poses at reference_ss x the size, 1 sample, blitted down (the poses are deterministic, so this is
    # the same as rendering the two alternately as the Unity tool does)
    if ref_k:
        sc.render.resolution_x, sc.render.resolution_y = w_ * ref_k, h_ * ref_k
        for i in range(n):
            e, R = head_pose(i / fps, eye, rot, amp_m, amp_deg)
            place_camera(cam, e, R)
            pr = lin_to_srgb8(blit_down(render_linear(os.path.join(tmp, 'r.exr')), ref_k), a.exposure)
            acc.add_ref(ys[i], luma8(pr))
            if i == 0:
                Image.fromarray(pr).save(os.path.join(a.out, tag + '_flicker_ref000.png'))
                print('[qa flicker] reference frame 0 (%dx%d) in %.0f s' % (w_ * ref_k, h_ * ref_k, time.time() - t1))
            elif i % 15 == 0:
                print('[qa flicker] reference %d / %d, %.0f s' % (i, n, time.time() - t1))
        sc.render.resolution_x, sc.render.resolution_y = w_, h_
    secs = time.time() - t0
    shutil.rmtree(tmp, ignore_errors=True)
    arr, met = acc.metrics(a.hf_threshold, a.shimmer_threshold)
    met.pop('frames', None)                                      # the record has its own 'frames' (= n)
    heats = {}
    for key, v, scale in (('heat_motion_std', arr['std'], a.heat_scale), ('heat_hf_raw', arr['hf'], a.heat_scale),
                          ('heat_shimmer', arr['sh'], max(1.0, a.heat_scale / 2.0))):
        if v is None:
            heats[key] = None
            continue
        heats[key] = os.path.join(a.out, '%s_flicker_%s.png' % (tag, key))
        Image.fromarray(heat(v, arr['mean'], scale)).save(heats[key])
    rec = dict(
        id=tag, part=a.part, view=view, kind='micro_motion', ruling='D-40a #5', layer='Blender 离线（近似）',
        unity_sequence=seq_id, unity_check=UNITY_CHECKS.get(seq_id),
        engine=eng, egl=egl, engine_settings=eng_rec, light=light, materials=mats,
        detail_normals=a.detail_normals if eng == 'eevee' else 'n/a',
        colour=dict(view_transform='Standard (applied by lin_to_srgb8 to linear EXR frames)', look='None',
                    exposure_ev=a.exposure, grading=False, dither=0.0),
        sources=SRC, sources_commit=repo_head(),
        fps=fps, frames=n, w=w_, h=h_, ss=ss, crop_deg=list(crop), ppd=ppd, amp_cm=a.amp_cm, amp_deg=amp_deg,
        eye_offset_mm=0.0, t0=None, t1=None, advance_time=False, eye=[round(float(v), 4) for v in eye], camera=cam_info,
        heat_scale=a.heat_scale, hf_threshold=a.hf_threshold, reference_ss=ref_k, shimmer_threshold=a.shimmer_threshold,
        reference='%d x size, 1 sample, bilinear blit down (2 x 2 nearest texels, linear), then sRGB 8-bit' % ref_k
                  if ref_k else 'off (no shimmer)',
        **met, apl_per_frame=[round(v, 3) for v in acc.apl], **heats,
        frame0=os.path.join(a.out, tag + '_flicker_f000.png'),
        reference0=os.path.join(a.out, tag + '_flicker_ref000.png') if ref_k else None,
        frames_dir=keep, seconds=round(secs, 1), seconds_reference=round(time.time() - t1, 1) if ref_k else 0.0,
        definitions='照抄 %s：Luma 756；累加 527-535；motion_std 551；hf_raw 552；shimmer 553；量数 555-573；热图 574-581'
                    '（Heat 818-836，shimmer 的热图 0 → max(1, heat_scale/2)）；记录 582-591；Avg 609；Pct 610-615；'
                    '参考图 reference_ss > ss 才渲 470 / 495、同一姿态 520-525；运动 510-517 / W 605-608；ss 1 464；'
                    'HDR 目标、无 MSAA、Blit 双线性 255-265；ppd 尺寸 130-138；机位 83-105' % CAPTURE_CS,
        note='Blender 层的近似（%s 代替 Unity 渲的），不是 Unity 的测量；Unity 层的结果以总工程师的测试工具为准。'
             '这里没有 Lanbai/Cabin 的几何高光抗锯齿（D-40 #4；测的图和参考图都没有）、零件图集的法线 / 遮罩、mip、贴图压缩、'
             '烘好的管灯光照图和反射探针、PPv2 调色。没有在 Unity 里编译或运行过。热图颜色 0 → %g（shimmer 0 → %g；'
             '亮度 0–255），底下是平均画面的暗灰。' % (eng, a.heat_scale, max(1.0, a.heat_scale / 2.0)))
    js = os.path.join(a.out, tag + '_flicker.json')
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    sh_txt = ('shimmer_mean %.3f shimmer_p99 %.2f shimmer_frac %.5f (> %g); '
              % (met['shimmer_mean'], met['shimmer_p99'], met['shimmer_frac'], a.shimmer_threshold)
              if 'shimmer_mean' in met else 'no reference (no shimmer); ')
    print('[qa flicker] %s %s (%s, %dx%d, %d frames, reference %s, %.0f s): %smotion_std_mean %.3f motion_std_p99 %.2f '
          'hf_raw_mean %.3f hf_raw_p99 %.2f hf_raw_frac %.5f (> %g); APL %.1f..%.1f max step %.2f -> %s'
          % (a.part, view, eng, w_, h_, n, ('%dx' % ref_k) if ref_k else 'off', secs, sh_txt, met['motion_std_mean'],
             met['motion_std_p99'], met['hf_raw_mean'], met['hf_raw_p99'], met['hf_raw_frac'], a.hf_threshold,
             met['apl_min'], met['apl_max'], met['apl_max_step'], js))
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
    ap.add_argument('--res-pct', type=float, default=100.0, help='of 1280x720 (at 64 deg: ~20 px/deg mean, ~18 centre)')
    ap.add_argument('--env', type=float, default=1.0, help='uniform environment strength (exposure follows the card)')
    ap.add_argument('--flat', action='store_true', help='neutral: MAT_TABLE colours only (no detail materials)')
    ap.add_argument('--quality', default='low', choices=['low', 'high'], help="neutral: preview's --quality (seat)")
    # flicker
    ap.add_argument('--view', default='', help='flicker: a preview view, or slice:<seat_05m|seat_10m|window_..|pillar_..>')
    ap.add_argument('--frames', type=int, default=90)
    ap.add_argument('--fps', type=float, default=90.0)
    ap.add_argument('--amp-cm', type=float, default=2.0)
    ap.add_argument('--amp-deg', type=float, default=1.0)
    ap.add_argument('--crop', default='32,24', help='flicker on a preview view: crop deg (h,v) around the target')
    ap.add_argument('--ppd', type=float, default=20.0)
    ap.add_argument('--reference-ss', type=int, default=4,
                    help='flicker: the shimmer reference at N x the size, 1 sample, blitted down (0 or 1 = off)')
    ap.add_argument('--shimmer-threshold', type=float, default=4.0)
    ap.add_argument('--hf-threshold', type=float, default=6.0)
    ap.add_argument('--heat-scale', type=float, default=24.0)
    ap.add_argument('--engine', default='eevee', choices=['eevee', 'workbench', 'cycles_point'],
                    help='eevee (default, 1 sample); workbench = NOT for highlights; cycles_point = no-EGL fallback')
    ap.add_argument('--detail-normals', default='vinyl', choices=['vinyl', 'none'],
                    help='eevee: the scanned leather normal on Vinyl as Unity has it (vinyl) or geometry normals only')
    ap.add_argument('--shadows', action='store_true', help='eevee: real-time shadows on (stochastic: per-frame noise at 1 sample)')
    ap.add_argument('--tube-spec', type=float, default=None,
                    help='eevee: tube light specular factor (default: reflected tube = Unity diffuser luma 1.95)')
    ap.add_argument('--tube-watts', type=float, default=None,
                    help='flicker: watts per tube (default: bake_report.json next to the sources)')
    ap.add_argument('--no-probe', dest='probe', action='store_false',
                    help='eevee: no cabin sphere probe (metals then reflect the night world only)')
    ap.add_argument('--world', type=float, default=0.03, help='flicker: night world strength (#30343A)')
    ap.add_argument('--exposure', type=float, default=0.0, help='flicker: EV (fixed for all frames)')
    ap.add_argument('--allow-fallback', action='store_true', help='no EGL: use cycles_point instead of exiting 3')
    ap.add_argument('--egl-dir', default='', help='a folder with libEGL.so.1 + libEGL_mesa.so.0 (unpacked debs)')
    ap.add_argument('--save-frames', action='store_true')
    a = ap.parse_args(argv)
    return mode_neutral(a) if a.mode == 'neutral' else mode_flicker(a)


if __name__ == '__main__':
    sys.exit(main())

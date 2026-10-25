# -*- coding: utf-8 -*-
"""Reference board (phase 1): the problem (user frame 1277 s), the two existing trees, three candidate forms."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
F = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')
SK = sys.argv[1]
OUT = sys.argv[2]
f1, f2, f3 = ImageFont.truetype(F, 44), ImageFont.truetype(F, 26), ImageFont.truetype(F, 21)
W = 2400
im = Image.new('RGB', (W, 2700), (18, 19, 22))
d = ImageDraw.Draw(im)
d.text((50, 30), '蓝白 · 样板树 · 参考板与树形草图（第一阶段，供总导演选形）', font=f1, fill=(232, 241, 245))
d.text((50, 96), '全部程序化生成（自己的代码 + numpy 贴图，不用任何外部素材 → 可按 CC0 公开）。云端到 Poly Haven / ambientCG 的网络不通，所以也没有可下载的 CC0 树。', font=f3, fill=(150, 158, 168))
# row 1: problem
y = 150
d.text((50, y), '① 问题：现在的树', font=f2, fill=(200, 208, 218)); y += 44
u = Image.open(os.path.join(REPO, 'FromLocal', 'visual_feedback', '20261025-0206', '03_user_tree_and_console_1277s.png')).convert('RGB')
u = u.crop((480, 115, 1940, 840)).resize((760, 377))
p = Image.open(os.path.join(REPO, 'FromLocal', 'trees', 'poplar_right.jpg')).resize((760, 427))
l = Image.open(os.path.join(REPO, 'FromLocal', 'trees', 'linluo_right.jpg')).resize((760, 427))
im.paste(u, (50, y)); im.paste(p, (830, y)); im.paste(l, (1610, y))
for x, t in ((50, '小楠的截图（1277 s，第 11 幕）：左边一排树是平的绿团，没有枝、没有空隙'), (830, '本地杨树：轮廓像一根绿色的柱，贴着灯是亮绿的'), (1610, '临落树（Standard 材质）：夜里发绿发亮，叶是均匀的一层')):
    d.text((x, y + 440), t, font=f3, fill=(170, 178, 188))
y += 500
d.text((50, y), '要改的：①轮廓要有枝、有团、有天空的空隙（法线贴图给不了轮廓）；②钠灯下叶子不能发绿发亮——湿叶反照率低、暗面透一点光、只在迎灯一侧亮；③15–40 m 外读作剪影（显示 3–6，圣经 §6·1）。', font=f3, fill=(220, 200, 160)); y += 60
# row 2: candidates
d.text((50, y), '② 三个候选形（上：灰天下看形；下：雨夜、钠灯在左前 7 m、S2 调色）', font=f2, fill=(200, 208, 218)); y += 50
names = [('A_old_broadleaf', 'A · 老的路边阔叶树（槐 / 榆一类的形）', '短干、3–5 根斜伸的大枝、枝端一团团的叶云，团与团之间露天。羽状小叶。\n最“无名”、到处都有；在钠灯下迎灯的一团亮、其余是剪影。推荐。'),
         ('B_weeping', 'B · 垂枝型（柳一类，水田边）', '几根向上的大枝，枝端垂下 2–4 m 的细枝帘。水田边、雨里最有气氛，\n但一眼就是“柳”，比 A 更有地方感；适合点缀 1–2 棵。'),
         ('C_columnar', 'C · 柱形（杨树一类，改好的版本）', '本地杨树的形，但冠是碎的、有空隙、主干分叉。\n成排种时节奏好；单棵看最平淡。')]
for i, (k, t, desc) in enumerate(names):
    x = 50 + i * 780
    a = Image.open(os.path.join(SK, k + '_clay.png')).resize((360, 480))
    b = Image.open(os.path.join(SK, k + '_night.png')).resize((360, 480))
    im.paste(a, (x, y)); im.paste(b, (x + 380, y + 0))
    d.text((x, y + 495), t, font=f2, fill=(232, 241, 245))
    d.multiline_text((x, y + 535), desc, font=f3, fill=(170, 178, 188), spacing=8)
y += 640
d.text((50, y), '③ 接下来（选形以后）', font=f2, fill=(200, 208, 218)); y += 44
plan = ['• 树形精修：高 10–13 m（现在的草图偏小），主枝 / 次枝 / 细枝三级，叶云团 5–8 个，树冠里留 3–5 个天空洞。',
        '• 叶：羽状小叶簇卡（2×2 图集，alpha-to-coverage 阈值 0.5）、透光、湿叶光滑度 0.55–0.65；树皮：湿 ×0.6、0.45（圣经 §1.6，走 _Udon_Wetness）。',
        '• LOD0 ≤ 12k 三角（草图现在 12–26k，正式版会把叶卡合并、细枝换成卡上的画）、LOD1 ≈ 4k、LOD2 = 交叉的剪影卡（≈ 200）；顶点风（顶点色 R = 柔度、G = 相位、B = 叶）。',
        '• 比较：FromLocal/trees 的三个机位（overview / right / left）与杨树、临落树并排；再加主座位往窗外看的近景（20 px/°，D-40b）。',
        '• 交付：Blender 源文件 + 渲染、FBX、贴图、Unity 预制体说明（Lanbai/Tree shader：LampKit 的湿润数学 + 透光 + 风）、Engineering/UnityTest 的测试定义。']
for t in plan:
    d.text((50, y), t, font=f3, fill=(170, 178, 188)); y += 38
im = im.crop((0, 0, W, y + 30))
im.save(OUT, optimize=True)
print(OUT, im.size)

# -*- coding: utf-8 -*-
"""Final board for the sample tree (D-44 #6): the four trees x 3 LODs, the three local comparison cameras
(poplar | Linluo | new, same framing), the main-seat close-up at 20 px/deg and the flicker proxy.
usage: python lt_board_final.py <lineup.png> <cmp_dir> <hero.png> <shim_dir> <info.json> <out.png>"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
F = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')
lineup, cmpd, hero, shimd, infof, out = sys.argv[1:7]
f1, f2, f3 = ImageFont.truetype(F, 44), ImageFont.truetype(F, 26), ImageFont.truetype(F, 20)
info = json.load(open(infof))
W = 2400
im = Image.new('RGB', (W, 5200), (18, 19, 22))
d = ImageDraw.Draw(im)
d.text((50, 30), '蓝白 · 样板树 · 正式版（A 为主、B 点缀）', font=f1, fill=(232, 241, 245))
d.text((50, 96), '全部程序化（自己的代码 + numpy 贴图，可按 CC0 公开）。LOD0 / LOD1 叶簇卡、LOD2 两张交叉的剪影卡；alpha-to-coverage；湿润走 _Udon_Wetness；顶点风。', font=f3, fill=(150, 158, 168))
y = 150
d.text((50, y), '① 四棵树、三档 LOD（灰天，看形）：从左到右 A1 · A2 · A3 · B1；上 LOD0、中 LOD1、下 LOD2', font=f2, fill=(200, 208, 218)); y += 44
L = Image.open(lineup)
L = L.resize((W - 100, int(L.height * (W - 100) / L.width)))
im.paste(L, (50, y)); y += L.height + 10
row = '   '.join('%s：%.1f m，%d / %d / %d 三角' % (k, v['height_m'], v['tris_lod0'], v['tris_lod1'], v['tris_lod2']) for k, v in info.items())
d.text((50, y), row, font=f3, fill=(170, 178, 188)); y += 50
d.text((50, y), '② 和本地的两种树并排（FromLocal/trees 的同样三个机位：Unity 世界，垂直 55°，1600×900）', font=f2, fill=(200, 208, 218)); y += 40
d.text((50, y), '左：本地杨树　中：临落树（原样 Standard）　右：新的样板树（Blender Cycles，第 1 幕 S1 调色、雾 0.009、灯包的钠灯在 (6.3, 11)；没有车、雨、站牌——只比树）', font=f3, fill=(150, 158, 168)); y += 38
tw = (W - 100 - 40) // 3
th = int(tw * 900 / 1600)
for cam in ('overview', 'right', 'left'):
    imgs = [Image.open(os.path.join(REPO, 'FromLocal', 'trees', 'poplar_%s.jpg' % cam)), Image.open(os.path.join(REPO, 'FromLocal', 'trees', 'linluo_%s.jpg' % cam)),
            Image.open(os.path.join(cmpd, '%s.png' % cam))]
    for i, a in enumerate(imgs):
        im.paste(a.convert('RGB').resize((tw, th), Image.LANCZOS), (50 + i * (tw + 20), y))
    m = json.load(open(os.path.join(cmpd, '%s_m.json' % cam)))
    d.text((50, y + th + 6), '%s　（新：APL %.1f；本地的图亮度不可比：Night profile + 更亮的灯 + 车）' % (cam, m['APL']), font=f3, fill=(150, 158, 168))
    y += th + 44
y += 10
d.text((50, y), '③ 主座位往外看（D-40b：眼 (0.55, 1.70, 2.05)，20 px/°，40° × 30° = 800 × 600），看右手第一棵树（A1）与路灯', font=f2, fill=(200, 208, 218)); y += 44
H = Image.open(hero)
im.paste(H, (50, y))
sh = json.load(open(os.path.join(shimd, 'hero_shimmer.json')))
heat = Image.open(os.path.join(shimd, 'hero_shimmer_heat.png'))
im.paste(heat, (50 + H.width + 30, y))
tx = 50 + H.width + 30
d.text((tx, y + heat.height + 10), '闪烁代理（头部 ±2 cm / ±1° 微动 12 帧；4× 有序超采样 ≈ MSAA 4× 的 alpha-to-coverage，对 16× 参考）', font=f3, fill=(170, 178, 188))
d.text((tx, y + heat.height + 40), 'shimmer 均值 %.2f · p99 %.1f · >4 的像素 %.2f %% · 只看叶缘像素的均值 %.2f（0–255）' %
       (sh['shimmer_mean'], sh['shimmer_p99'], 100 * sh['shimmer_frac_gt4'], sh['shimmer_mean_on_edges']), font=f3, fill=(220, 200, 160))
d.text((tx, y + heat.height + 70), '热图：黑 0 → 红 → 黄 ≥ 16。真正的判定是 Unity 测试 tree_sample 的 hero_micro 序列（门槛初值 p99 ≤ 12、>4 的 ≤ 2 %）和头显。', font=f3, fill=(150, 158, 168))
y += max(H.height, heat.height + 110) + 30
notes = ['总导演四条：① 剪影先于细节——叶云团之间露天，15–40 m 外比背后的天暗一档（显示约 3–15，天 ~18–22）；② 叶簇卡 1.25 m（LOD0）、2.5 m 叶团（LOD1）、远处剪影卡（LOD2），',
         '　图集开 Mip Maps Preserve Coverage；③ A 三个变体（种子、10.9 / 12.2 / 13.0 m、偏冠方向不同）；④ 湿树皮 ×0.6 / 0.45，湿叶 0.60，透光；钠灯下叶是暗橄榄，不发绿发亮。',
         '已知：Blender 里路灯投影，灯旁树的下层叶团被上层挡住，比 Unity（路灯烘焙）暗一点；远处的球形“树线”只是舞台。']
for t in notes:
    d.text((50, y), t, font=f3, fill=(170, 178, 188)); y += 34
im = im.crop((0, 0, W, y + 30))
im.save(out, optimize=True)
print(out, im.size)

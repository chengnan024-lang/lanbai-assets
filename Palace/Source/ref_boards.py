# -*- coding: utf-8 -*-
"""D-31 #2：考据按区做参考板（屋顶、门阙、纹样、器物、颜色），每板注明出处。图只用 CC0 的实物照片（Docs~/实物参考_汉代器物/）
和我们自己的渲染 / 贴图；没有开放授权照片的（阙、长信宫灯）只写出处、不放图。"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', 'Docs~')
REF = os.path.join(D, '实物参考_汉代器物')
OUT = os.path.join(D, 'ref_boards')


def font(px):
    try:
        return ImageFont.truetype('/home/user/lanbai-assets/Fonts/Originals~/SourceHanSerifCN-Regular.otf', px)
    except Exception:
        pass
    for p in glob.glob('/home/user/lanbai-assets/Fonts/**/*.otf', recursive=True):
        if 'Sans' in p and ('Regular' in p or 'Medium' in p):
            try:
                return ImageFont.truetype(p, px)
            except Exception:
                pass
    return ImageFont.load_default()


def board(name, title, items, notes):
    """items: [(图路径, (左, 上, 右, 下) 或 None, 说明)]"""
    th = 420
    tiles = []
    for p, box, cap in items:
        im = Image.open(p).convert('RGB')
        if box:
            im = im.crop(box)
        im = im.resize((int(im.width * th / im.height), th), Image.LANCZOS)
        tiles.append((im, cap))
    W = max(1400, sum(t[0].width + 16 for t in tiles) + 32)
    H = 90 + th + 70 + 28 * len(notes) + 30
    b = Image.new('RGB', (W, H), (18, 20, 24))
    d = ImageDraw.Draw(b)
    d.text((24, 22), title, font=font(30), fill=(232, 238, 242))
    x = 24
    for im, cap in tiles:
        b.paste(im, (x, 80))
        d.text((x, 80 + th + 8), cap, font=font(16), fill=(170, 178, 188))
        x += im.width + 16
    y = 80 + th + 52
    for n in notes:
        d.text((24, y), n, font=font(18), fill=(206, 212, 218))
        y += 28
    b.save(os.path.join(OUT, name + '.png'), optimize=True)
    print('wrote', name)


def main():
    os.makedirs(OUT, exist_ok=True)
    R = lambda f: os.path.join(REF, f)
    board('01_roof', '屋顶 · 直坡四阿、腰檐、平座、插拱（东汉陶楼明器）', [
        (R('Met_49519.jpg'), (300, 100, 2700, 2300), 'Met 49519 东汉绿釉陶望楼：直坡四阿、插拱、斜格窗'),
        (R('Met_49520.jpg'), (300, 100, 2700, 2000), 'Met 49520 多层望楼：腰檐、平座、屋脊两端'),
        (R('CMA_1989.71.jpg'), (600, 0, 2600, 2100), 'CMA 1989.71 水盆中的楼：直坡、筒瓦垄'),
    ], ['做法：屋面直坡（26–30°），檐口平直、转角不起翘，只在檐口最外 1/5 折缓一点（“反宇”的意思，班固《西都赋》）。',
        '正脊两端只起翘 + 很克制的鱼尾（D-29）；陶楼上屋脊两端立的是鸟，不是鸱尾。',
        '腰檐（重檐）的根据：陶楼的层层腰檐；大殿用两层，上层殿身压低（第 2 轮）。'])
    board('02_pattern', '纹样 · 楚汉漆器的云气纹、联珠、黑地朱绘', [
        (R('CMA_1969.129.jpg'), (150, 250, 1650, 2100), 'CMA 1969.129 乐浪漆盘残片（新莽 9 CE）：朱地刻云纹、联珠带'),
        (R('CMA_1969.129.jpg'), (1600, 700, 3000, 2300), '同上，中心纹饰：卷云'),
        (R('CMA_1991.7.jpg'), (300, 700, 3100, 1500), 'CMA 1991.7 西汉漆耳杯：黑漆地上的云纹与叶纹'),
    ], ['朱漆贴图 T_07b_Lacquer_* 直接取自 1969.129 内面（去光、无缝、均值校到圣经 #A3201E）。',
        '梁枋带 T_07b_LacquerBand_*：黑地朱绘卷云，按 1991.7 的笔意程序生成（耳杯的纹样带是弯的，这一窗没拉直，留作下一步）。',
        '瓦当只做无字的卷云（考据 §6）：汉代瓦当多有“长乐未央”等字，圣经不许放字。'])
    board('03_colour', '颜色 · 朱与靛（圣经 §6·7b 色板）', [
        ('/home/user/lanbai-assets/Art/palettes/Palette_07b_the_deep_the_palace.png', None, '圣经色板 07b'),
        (os.path.join(HERE, '..', 'Textures', 'T_07b_Lacquer_Albedo.png'), (0, 0, 1024, 1024), '朱漆（照片取材）'),
        (os.path.join(HERE, '..', 'Textures', 'T_07b_Cowrie_Albedo.png'), (0, 0, 1024, 1024), '紫贝 #5B2A4E / 背斑 #B89AB0'),
        (os.path.join(HERE, '..', 'Textures', 'T_07b_FishScale_Albedo.png'), (0, 0, 1024, 1024), '鱼鳞瓦（珍珠母）'),
    ], ['陶楼的绿是铅釉，不是建筑的颜色：只借结构和比例，不借颜色（实物参考 README）。',
        '青铜 #BA926A（D-29），暗处按电介质；D-21 紫护栏：渲染图里 h 290–330、C* > 8、L* > 40 的像素为 0。'])


if __name__ == '__main__':
    main()

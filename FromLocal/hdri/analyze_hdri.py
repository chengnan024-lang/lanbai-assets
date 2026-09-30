"""挑晨 / 暮 HDRI：太阳仰角、动态范围、背日 20–40° 的天色相（CIE Lab h_ab）、背日地平线的地影带 / 金星带、天顶色相。输出 json + 缩略图总览。"""
import os, glob, json, math
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

def srgb(x): x = np.clip(x, 0, None); return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
def lab_from_linear(rgb):
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = rgb @ M.T; wp = np.array([0.95047, 1.0, 1.08883]); t = xyz / wp
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16; a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b
def hue_chroma(rgb_lin):
    L, a, b = lab_from_linear(rgb_lin)
    return float(L), float((math.degrees(math.atan2(b, a)) + 360) % 360), float(math.hypot(a, b))

out = {}
for p in sorted(glob.glob('*_1k.hdr')):
    k = p.replace('_1k.hdr', '')
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float64)    # RGB 线性
    H, W, _ = img.shape
    lum = img @ np.array([0.2126, 0.7152, 0.0722])
    # 太阳：最亮点（先稍微模糊）
    bl = cv2.GaussianBlur(lum.astype(np.float32), (5, 5), 0)
    y, x = np.unravel_index(np.argmax(bl), bl.shape)
    el = 90 - (y + 0.5) / H * 180; az = (x + 0.5) / W * 360        # az：图像 u 方向的度数
    sky = lum[: H // 2]
    med = float(np.median(sky)); mx = float(lum.max())
    # 背日方向
    aaz = (az + 180) % 360
    def band(el0, el1, daz=20, center=None):
        c = aaz if center is None else center
        ys = slice(int((90 - el1) / 180 * H), int((90 - el0) / 180 * H))
        xs = [int(((c + d) % 360) / 360 * W) for d in np.arange(-daz, daz + 0.1, 360 / W)]
        return img[ys][:, xs].reshape(-1, 3).mean(0)
    anti_2040 = band(20, 40); anti_0_6 = band(0.5, 6); anti_8_20 = band(8, 20)
    zen = img[: int(H * 0.04)].reshape(-1, 3).mean(0)
    sun_side_hor = band(0.5, 6, 25, center=az)
    # 归一：让背日 20–40° 的亮度到 sRGB ~0.6（只影响 L，色相几乎不变）
    s = 0.3 / max(anti_2040 @ np.array([0.2126, 0.7152, 0.0722]), 1e-6)
    r = {}
    for name, c in [('anti_20_40', anti_2040), ('anti_hor_0_6', anti_0_6), ('anti_8_20', anti_8_20), ('zenith', zen), ('sun_side_hor', sun_side_hor)]:
        L, h, C = hue_chroma(c * s)
        r[name] = dict(h_ab=round(h, 1), C=round(C, 1), L=round(L, 1), srgb='#%02X%02X%02X' % tuple(int(round(v * 255)) for v in np.clip(srgb(c * s), 0, 1)))
    out[k] = dict(sun_el=round(float(el), 2), sun_az_u=round(float(az), 1), max_over_median=round(mx / max(med, 1e-9)), max=round(mx, 1), **r)
    # 缩略图（上半球，简单曝光 + Reinhard）
    e = img * (0.18 / max(med, 1e-6)); tm = e / (1 + e)
    th = (np.clip(srgb(tm), 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(th).resize((512, 256), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    sx, sy = az / 360 * 512, (90 - el) / 180 * 256
    d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], outline=(255, 0, 0), width=2)
    ax = aaz / 360 * 512
    d.line([ax, (90 - 40) / 180 * 256, ax, (90 - 20) / 180 * 256], fill=(0, 255, 255), width=2)
    d.line([0, 128, 512, 128], fill=(90, 90, 90), width=1)
    im.save(k + '_thumb.png')
print(json.dumps(out, indent=1, ensure_ascii=False))
json.dump(out, open('hdri_measure.json', 'w'), indent=1)

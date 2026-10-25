# 实物参考：第 3a 幕的光之海（NASA 国际空间站照片，公有领域）

> **给「蓝白·灯与假醒」会话。** 2026-10-24，小楠让我把能用的真东西推给各包。写的人：「理解 lanbai-assets 项目」会话（不在分工表里）。我只加了这个文件夹，没有改你的任何文件。
> 按 `PLAN_总导演.md` 第三节，第 3 幕的**城市灯点**由你供料（圣经 §6·3 的 `CityLights_Points.fbx`，8 000 点）。第 3 幕谁组装还没定（`CONTROL_总控.md`）。这里是宇航员从空间站拍的夜间城市灯光，**NASA，美国公有领域，使用时要署名（见“授权与署名”）**。

## 文件

| 文件 | 看什么 | 原页 |
|---|---|---|
| `ISS-62_印度西部与巴基斯坦.jpg` | **几乎就是圣经 3a 的那一帧**：灯海铺到地平线，地平线上一道大气的微光，上面是星，旁边还有月亮。“分不清灯在哪里结束、星从哪里开始” | [Commons](https://commons.wikimedia.org/wiki/File:ISS-62_City_lights_of_western_India_and_Pakistan.jpg) |
| ~~`ISS-65_欧洲.jpg`~~ **已删，只留链接** | 颜色的比例：暖的钠灯里夹着白的 LED（圣经：钠 55%、暖楼群 25%、冷 LED 15%、航空灯 5%） | [Commons](https://commons.wikimedia.org/wiki/File:ISS-65_Europe,_city_lights_from_space.jpg) |
| `ISS_爪哇.jpg` | 结构：灯沿着路连成一根根线，镇子是亮的结，中间是暗的田和河 | [Commons](https://commons.wikimedia.org/wiki/File:Lights_of_Java.jpg) |

## 怎么用（建议）

1. **当参考，不当贴图**：空间站在 400 km 高，圣经 3a 的车在 300–480 m 高。照片给的是**颜色比例和拓扑**（路成线、镇成结、暗河、少数很亮的核和大量很暗的点），不是尺度。480 m 高时看得见单个的灯，路是一条条细线。
2. **当数据**（可选，更自然）：用 NASA 的夜光卫星数据决定 8 000 个点的分布，比程序生成的路网自然：
   - NASA Black Marble（VIIRS 夜间灯光，VNP46 系列，公有领域）：<https://blackmarble.gsfc.nasa.gov/>，数据在 LAADS：<https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A1/>
   - 拿一块农业区的密度当概率图撒点。**翻转、旋转、把几块拼起来**，认不出是哪里：圣经要“不属于任何具体的地方”。尺度照圣经（20 × 20 km 平原、30–60 个镇子、一条蜿蜒的暗河）。
3. 圣经的其他要求照旧：灯保持 80% 暖色（读作悲悯，不是城市数据可视化）；远于 5 km 的点 ±20%、≤ 1.5 Hz 闪；地平线 3–5° 的暖雾带上面只出最亮的约 200 颗星。

## 授权与署名

两张留在仓库里的照片是 NASA 宇航员照片，美国政府作品，**美国公有领域**（Commons 标签 PD-USGov-NASA-AP；NASA 的标志和人物肖像除外）。按 NASA 的使用条款，使用时要**署名**：

| 文件 | 署名 | 照片编号 | 原页 | 核对 |
|---|---|---|---|---|
| `ISS-62_印度西部与巴基斯坦.jpg` | Earth Science and Remote Sensing Unit, NASA Johnson Space Center | ISS062-E-103887 | [Commons](https://commons.wikimedia.org/wiki/File:ISS-62_City_lights_of_western_India_and_Pakistan.jpg) | 2026-10-25（阿白，`FromLocal/research/license_check/20261025-0955/README.md`） |
| `ISS_爪哇.jpg` | Earth Science and Remote Sensing Unit, NASA Johnson Space Center | ISS056-E-6994 | [Commons](https://commons.wikimedia.org/wiki/File:Lights_of_Java.jpg) | 2026-10-25（同上） |

署名只是标明来源，**不表示 NASA 认可或背书本作品**；片尾和任何说明里都不能写成或暗示 NASA 背书，不用 NASA 的标志。仓库里的副本去掉了 EXIF，没有和原图逐像素比对过。

## 2026-10-25 核对（灯与假醒）

- `ISS-65_欧洲.jpg` 的 EXIF 写着 `ImageDescription: GMT129_23_46_For ESA_Thomas Pesquet_Timelapse europe by night ...`：这是 **ESA（Thomas Pesquet）** 的照片，不是 NASA 的。ESA 的这类照片通常是 **CC BY-SA 3.0 IGO**，按 D-41 #7 只能放链接，所以文件已从仓库删掉，上表只留链接。（它仍在 `pkg/lamps` 的历史提交 357a4d7 里；要不要改写分支历史由总导演定。）
- 另外两张：阿白 2026-10-25 核过 Commons 原页，都是 NASA（PD-USGov-NASA-AP），可以留；署名见上节。
- 分支历史不改写（总导演 10-25）：合 `pkg/lamps` 时用 squash，ISS-65 不进 main 的历史。

# R3 实际素材回传：锈漆金属已取得，其余三类仍未交齐

2026-10-26。当前仓库没有新工程交付，本轮继续原D-46/R3检索下载。**实际新增一套2K锈漆金属候选，共4张PNG、23,101,665字节（23.10MB）**；四类整体仍未完成。没有导入Unity、改变场景或替换现有美术。

## 已有实物：Poly Haven / Rusty Metal 02

[原资产页](https://polyhaven.com/a/rusty_metal_02)标明作者Rob Tuytel，类别含Rusted/Painted；下载后的原始Diffuse图确为浅色涂层上锈斑，属于本次“带锈漆面金属”候选。[站方许可](https://polyhaven.com/license)确认资产为CC0；下载当日声明保存在[LICENSE.txt](../polyhaven_rusty_metal_02/LICENSE.txt)。

- [实际文件及完整来源/哈希](../polyhaven_rusty_metal_02/source.json)：Diffuse、OpenGL Normal、官方ARM组合图、Displacement，全部2048×2048，保持原文件未改写。
- 每张PNG成功解码；实际字节数、官方files API的MD5逐一一致，同时记录实际SHA256。这里MD5仅用于核对来源传输，SHA256用于交付完整性。
- 最大单文件7,813,121字节，单文件低于95MB，本次总量低于300MB。无0字节占位、无编造哈希。
- 来源为站方[公开API](https://api.polyhaven.com/files/rusty_metal_02)给出的官方下载地址；遵照[API使用说明](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md)，采用明确的本地研究User-Agent并标注来源，没有账号、付费、代理或绕过访问限制。
- 这是供原灯包负责人挑选的素材，不是已经在工程中使用，也不代表路灯/公交材质视觉验收。

## 仍未完成及本轮实际尝试

|需求|当前状态|
|---|---|
|湿树皮|仍缺。Poly Haven Tree Bark 03可查询，但原页没有证明它是湿树皮；没有为凑数下载并标成“湿”。此前Bark006也没有湿态证据。|
|阔叶/透明图集|ambientCG LeafSet016原页可读，官方2K PNG下载仍403。cgbookcase Green Leaf 03提供正反面/Opacity和2K选项，实际官方CDN下载403。3DTexel Mimosa Leaf Atlas需登录，未下载；也不假称槐/榆已确定。|
|湿沥青|ambientCG Asphalt025C仍403；cgbookcase Single Lane Road Wet 01实际官方下载也403。后者带道路构图，不能自动当无标记的可平铺路面。|
|锈漆金属|上面一套已实际交付；原PaintedMetal012旧失败记录保留，未追改成成功。|

完整请求地址、失败状态和零成功字节见[attempts.json](attempts.json)。cgbookcase的2K链接来自页面明确选项及公开下载模块，不是付费路径；收到403后停止，没有换代理/伪装登录/重放同一失败请求。3DTexel没有尝试账户入口。许可证可用不代表文件已经下到。

参考原页：[cgbookcase许可声明](https://www.cgbookcase.com/textures)、[Green Leaf 03](https://www.cgbookcase.com/textures/green-leaf-03)、[湿路面](https://www.cgbookcase.com/textures/single-lane-road-wet-01)、[Mimosa登录要求](https://3dtexel.com/product/mimosa-leaf-atlas/)、[树皮候选](https://polyhaven.com/a/tree_bark_03)。后续只寻找符合范围且无需登录/付费的合法下载源；不重复将原403记录写成完成。

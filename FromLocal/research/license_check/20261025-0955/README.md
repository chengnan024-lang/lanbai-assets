# 两张ISS照片的原页许可核对

2026-10-25。读取灯包分支c3bcf7d的参考README，实际打开Commons原页并交叉读取NASA的官方使用条款；没有把分支资源导入Unity。

| 仓库文件 | 原页事实 | 结论 |
|---|---|---|
| ISS-62_印度西部与巴基斯坦.jpg | [Commons原页](https://commons.wikimedia.org/wiki/File:ISS-62_City_lights_of_western_India_and_Pakistan.jpg)：NASA，2020-03-20，ISS062-E-103887，PD-USGov-NASA-AP | 原页明确美国公有领域。页面同时提示Flickr目前未按其所列许可提供，使用依据应记录NASA宇航员照片条款，而非仅写Flickr免费 |
| ISS_爪哇.jpg | [Commons原页](https://commons.wikimedia.org/wiki/File:Lights_of_Java.jpg)：NASA，2018-06-09，ISS056-E-6994，PD-USGov-NASA-AP | 原页明确美国公有领域，来源链接指向NASA JSC对应照片编号 |

NASA [官方宇航员照片FAQ](https://eol.jsc.nasa.gov/FAQ/)说明：未另行标注版权的NASA素材可以复制、分发，须避免暗示NASA背书；要求注明Earth Science and Remote Sensing Unit, NASA Johnson Space Center，并建议附照片编号和源链接。[NASA通用影像指引](https://www.nasa.gov/nasa-brand-center/images-and-media/)也要求来源致谢、区分其网站上的第三方版权材料。因此原README里“不强制署名”不能作为本项目操作依据；建议两张各附NASA/JSC来源、照片编号、原页和核对日期。

**已完成的是原页许可核对**，满足本次“点原页确认”要求；尚未对分支里的去EXIF副本与原图作逐字节/像素比对。NASA两个单图检索页面本轮超时，但Commons明确给出照片编号和NASA许可标签，官方统一条款已读取。不要把本结论扩展到其他ISS照片、ESA照片、标志或人像。已删的ISS-65欧洲照片不恢复，不改写Git历史。

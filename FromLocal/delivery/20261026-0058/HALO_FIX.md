# 字幕行晕硬边修复

SpriteRenderer的_MainTex原本只靠内部属性块提供，LanbaiPoemDriver每帧用颜色属性块覆盖后，材质自身_MainTex为空，渐变alpha按白纹理采样成矩形。原PNG有0–255渐变，导入为Sprite且有alpha；不是原图缺透明。

`halo_before_explicit_texture` / `halo_after_explicit_texture`在同一冻结帧975.4比较，补_MainTex后硬边消失。持久修复只给该专用字幕材质绑定原Sprite.texture，同时PoemBake构建流程补同样设置；没有改颜色、alpha、字号或世界字列。材质和构建器的增量备份、审阅补丁已留。独立Play的`halo_fixed_en/zh/bright`再确认，未用试验MPB作为最终配置。

此前每首诗/黑边截图保留但须注明是在此修复之前；修后示例不是头显验收。

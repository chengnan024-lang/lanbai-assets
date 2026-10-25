# 蓝白 / Lanbai: assets

VRChat 世界「蓝白」的程序化资产仓库。云端的 Claude Code 会话在这里做资产、推上来；本地由 ChatGPT「阿白」拉下来，导入 Unity 工程 `dream`（2026-10-24 起，已接管）。

- `PLAN_总导演.md`：**总计划与进度表**（谁干什么、干到哪儿、下一步）
- `CONTROL_总控.md`：**云端各会话的分工和共同约定**（2026-10-22 起，谁做哪一幕、Git 协议、Unity 里踩过的坑）
- `HANDOFF_CHATGPT.md`：**本地（阿白）先读这个**：接管入口、协作边界、三层验收状态表、回传协议
- `Lanbai_Handoff.md`：历史文件（09-28 写给以前的本地 Claude；路径和备份信息仍可参考，Claude 专用的部分不适用）
- `HANDOFF_LOG.md`：云端每次推送写一条（推了什么、要本地做什么）。云端会话不能主动发消息，所以要看这里。
- `Tentacles/`：触手之门的触手库（FBX、贴图、预览图、生成脚本、摇摆 shader、README）
- `Clouds/`：体积云卡片（晨光 / 暮色 / 月光、云海地平线、积云柱、README）

clone 到 `E:\IDMdownload\VRCC\lanbai-assets\`，不要直接 clone 进 Unity 的 `Assets`，按各目录的 README 导入。

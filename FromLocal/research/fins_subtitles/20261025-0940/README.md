# R1 · Fins 字幕证据入口与当前测量阻塞

2026-10-25 09:44 America/New_York。**未完成视频逐帧实测，不能据此给D-45填写尺寸或淡入时长。** 没有把“看起来像”写成Fins的实测规格，也没有上传视频、截图或私人聊天。

## 已找到的直接入口

| 来源 | 可核实内容 | 测量状态 |
|---|---|---|
| [Fins官方PV2](https://www.youtube.com/watch?v=-KfHfyqtl6E) | 隐藏浏览器标签标题实际返回“Project: Lost Worlds PV2 - YouTube”；链接也由[预告转载的来源栏](https://www.bilibili.com/video/BV1Mh7t6qEFC/)列出为Fins @Finsworks | 【确定】视频入口；未读到播放器画面，时间戳未取证 |
| [公开观光实况](https://www.bilibili.com/video/BV1xETy6WE9R/) | 发布者说明是Project Lost Worlds的游玩记录 | 【确定】检索到入口；页面读取412，不能确认有用字幕片段 |
| [Raindance官方作品页](https://www.raindanceimmersive.com/2026-project-lost-worlds-journey-to-erios/) | World Creator: Fins；UI Help: Fionna；Japanese Translation: Riku；有独立字幕/UI协作署名 | 【确定】署名信息；不是字幕像素或VR跟随方式的证据 |
| [威尼斯官方2024作品页](https://www.labiennale.org/en/cinema/2024/venice-immersive/project-lost-worlds) | Fins / Finsworks Interactive、英文、60分钟的2024版本 | 【确定】历史版本；不能与2026视频混为同一UI版本 |
| [Complex 7官方2023作品页](https://www.labiennale.org/en/cinema/2023/venice-immersive/complex-7) | Fins作品、英文、40分钟 | 【确定】作品来源；尚无已观察字幕帧 |

## 本轮无法实测的项

| 要求 | 数值 / 判定 | 原因 |
|---|---|---|
| 底边距 / 字高 / 行数 / 行宽百分比 | 未测，不能填0 | 没有取得实际视频帧 |
| 字体、字重、颜色、描边/阴影/底衬 | 未测 | 不能由作品介绍推断样式 |
| 淡入/硬切、逐帧帧数、单句停留 | 未测 | 播放器读取不可用，不能由静态介绍推断 |
| 遮幅比例、斜角、仅序章或全程 | 未测 | 需要多个时间段的视频比较 |
| 设置面板版式 | 未测 | 官方署名只证实有UI协作，不证实布局 |
| 头锁 / 阻尼跟随 / 世界固定 | 未测 | 需要有明显头动且无剪辑干扰的VR实录 |

具体阻塞：网页抓取YouTube被限流；B站返回HTTP412；在不切前台的隐藏浏览器中成功建立视频标签，但读取标签状态和播放器DOM连续超时。未登录、未绕过限制、未为测量改用前台操作；未下载受版权视频。

后续恢复可用的后台视频读取后，从上述入口取证，逐项记录播放器版本、完整帧宽高、测量框、时间戳和帧率。每个数字标【确定】或【推测】，不把拍摄者后期字幕当世界内字幕。当前D-45所需测量仍是BLOCKED，其他独立本地部署继续。

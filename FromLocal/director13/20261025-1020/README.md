# Director 1.3 r2：待确认的具体改动

状态：**已做增量备份和差异方案，未改工程 LB_Journey/Dispatcher，未编译或验收此方案。** 依据 main 09164c9、HANDOFF_LOG 北京22:50及 HANDOFF_CHATGPT §F；交接明确要求出生状态机改写先经小楠确认。这一步超出本轮普通资源同步/局部画面修复的处理范围。

## 拟应用

- 用云端1.3r2生成器及Dispatcher重生成/重接 FullPreview，保留已采纳的初始化保护；同时同步门内/晨景出生协议、Overlay构建器。正式场景不动。
- [具体LB_Journey补丁](LB_Journey.spawn-v13-proposed.patch)：把旧3秒后直接结束出生遮罩，改为先黑场、等驱动遮罩接手或按≤0.85 EV/s独立淡入。SpawnTick在ApplyPost/实际总dEV之后。
- 站台的时间轴固定为0，不能直接把README中所有计时照抄成t；本方案把黑场/淡入经过时长改用Time.time，交接窗口仍查时间轴t。站台亮度暂取保守上界1，需实测校准。出生期间调试倒拖及卡顿是必测项，不宣称与云端仿真逐字相同。
- 保留SeaA/SeaB运行时材质、1149白优先级、字幕本地修复、各交付接管开关；Common/UdonGlobals.md与旧main不一致，是文档，先排除不覆盖。

## 确认后执行

先核对[preflight](preflight.json)中的本地哈希仍一致，再应用；编译与Udon就绪后仅在FullPreview生成1/接线2。独立静音Play验证站台、迟到、遮罩窗口边缘与倒拖，运行1.2.1 flicker_probe及transitions_sweep。任何新失败保留现场与日志、停止向后部署，不升级依赖。既有备份可按本轮文件恢复，不需要再压整工程。

这不是发布/VRChat上传申请，也不涉及收费。需要确认的只是上述状态机与分发层迁移；其他已授权工作继续。

补丁应用预检：本地混合换行，需要忽略空白作上下文匹配；git apply --check --ignore-whitespace已通过。尚未应用/编译，不能等同运行验证。
